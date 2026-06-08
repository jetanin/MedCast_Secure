// Seed Postgres จากไฟล์ CSV ที่ mount ไว้ที่ /seed
// - /seed/data/hospitals/hospital_master.csv
// - /seed/data/predictions/forecast_snapshot.csv
// - /seed/models/global_weights.csv
const fs = require("fs");
const path = require("path");
const bcrypt = require("bcryptjs");
const { parse } = require("csv-parse/sync");
const { pool } = require("./db");

const SEED_DIR = process.env.SEED_DIR || "/seed";
const DEFAULT_PASSWORD = process.env.DEFAULT_PASSWORD || "medcast123";

function readCsv(relPath) {
  const full = path.join(SEED_DIR, relPath);
  if (!fs.existsSync(full)) {
    console.warn(`[seed] missing file: ${full}`);
    return [];
  }
  const raw = fs.readFileSync(full, "utf-8").replace(/^﻿/, ""); // strip BOM
  return parse(raw, { columns: true, skip_empty_lines: true });
}

async function ensureSchema() {
  // idempotent — เผื่อ init.sql ไม่ได้รัน
  await pool.query(`
    CREATE TABLE IF NOT EXISTS hospitals (
      hospital_id TEXT PRIMARY KEY, name TEXT NOT NULL,
      latitude DOUBLE PRECISION, longitude DOUBLE PRECISION, lead_time_days INTEGER);
    CREATE TABLE IF NOT EXISTS forecasts (
      id SERIAL PRIMARY KEY, hospital_id TEXT, drug TEXT NOT NULL, desc_th TEXT,
      last_date DATE, pred_next_day DOUBLE PRECISION, avg_30d DOUBLE PRECISION,
      ratio DOUBLE PRECISION, status TEXT, confidence DOUBLE PRECISION,
      UNIQUE (hospital_id, drug));
    CREATE TABLE IF NOT EXISTS weights (feature TEXT PRIMARY KEY, weight DOUBLE PRECISION);
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
      hospital_id TEXT, created_at TIMESTAMPTZ DEFAULT now());
    CREATE TABLE IF NOT EXISTS borrow_requests (
      id SERIAL PRIMARY KEY, from_hospital TEXT, to_hospital TEXT, drug TEXT NOT NULL,
      quantity DOUBLE PRECISION NOT NULL, reason TEXT,
      status TEXT NOT NULL DEFAULT 'pending', created_at TIMESTAMPTZ DEFAULT now());
  `);
}

async function seedUsers(hospitals) {
  const hash = bcrypt.hashSync(DEFAULT_PASSWORD, 10);
  for (const h of hospitals) {
    // username = hospital_id, รหัสผ่านเริ่มต้น = DEFAULT_PASSWORD
    await pool.query(
      `INSERT INTO users (username, password_hash, hospital_id)
       VALUES ($1, $2, $3) ON CONFLICT (username) DO NOTHING`,
      [h.hospital_id, hash, h.hospital_id]
    );
  }
  console.log(`[seed] users: ${hospitals.length} (password ตั้งต้น = "${DEFAULT_PASSWORD}")`);
}

async function seed() {
  await ensureSchema();

  const hospitals = readCsv("data/hospitals/hospital_master.csv");
  for (const h of hospitals) {
    await pool.query(
      `INSERT INTO hospitals (hospital_id, name, latitude, longitude, lead_time_days)
       VALUES ($1,$2,$3,$4,$5)
       ON CONFLICT (hospital_id) DO UPDATE SET
         name=EXCLUDED.name, latitude=EXCLUDED.latitude,
         longitude=EXCLUDED.longitude, lead_time_days=EXCLUDED.lead_time_days`,
      [h.hospital_id, h.name, parseFloat(h.latitude), parseFloat(h.longitude),
       parseInt(h.lead_time_days, 10) || null]
    );
  }
  console.log(`[seed] hospitals: ${hospitals.length}`);
  await seedUsers(hospitals);

  const forecasts = readCsv("data/predictions/forecast_snapshot.csv");
  for (const f of forecasts) {
    await pool.query(
      `INSERT INTO forecasts
         (hospital_id, drug, desc_th, last_date, pred_next_day, avg_30d, ratio, status, confidence)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
       ON CONFLICT (hospital_id, drug) DO UPDATE SET
         desc_th=EXCLUDED.desc_th, last_date=EXCLUDED.last_date,
         pred_next_day=EXCLUDED.pred_next_day, avg_30d=EXCLUDED.avg_30d,
         ratio=EXCLUDED.ratio, status=EXCLUDED.status, confidence=EXCLUDED.confidence`,
      [f.hospital_id, f.drug, f.desc_th, f.last_date || null,
       parseFloat(f.pred_next_day), parseFloat(f.avg_30d),
       f.ratio === "" ? null : parseFloat(f.ratio), f.status, parseFloat(f.confidence)]
    );
  }
  console.log(`[seed] forecasts: ${forecasts.length}`);

  const weights = readCsv("models/global_weights.csv");
  for (const w of weights) {
    await pool.query(
      `INSERT INTO weights (feature, weight) VALUES ($1,$2)
       ON CONFLICT (feature) DO UPDATE SET weight=EXCLUDED.weight`,
      [w.feature, parseFloat(w.weight)]
    );
  }
  console.log(`[seed] weights: ${weights.length}`);
}

module.exports = { seed };

if (require.main === module) {
  const { waitForDb } = require("./db");
  waitForDb().then(seed).then(() => process.exit(0)).catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
