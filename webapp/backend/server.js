const express = require("express");
const cors = require("cors");
const bcrypt = require("bcryptjs");
const { pool, waitForDb } = require("./db");
const { seed } = require("./seed");
const { signToken, requireAuth } = require("./auth");

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

// health check
app.get("/api/health", async (_req, res) => {
  try {
    await pool.query("SELECT 1");
    res.json({ status: "ok", db: "connected" });
  } catch (e) {
    res.status(500).json({ status: "error", error: e.message });
  }
});

// รายชื่อโรงพยาบาล + สถานะรวม (แย่สุดในบรรดายา) สำหรับ Overview Map
app.get("/api/hospitals", async (_req, res, next) => {
  try {
    const { rows } = await pool.query(`
      SELECT h.hospital_id, h.name, h.latitude, h.longitude, h.lead_time_days,
             COUNT(*) FILTER (WHERE f.status='red')    AS n_red,
             COUNT(*) FILTER (WHERE f.status='yellow') AS n_yellow,
             ROUND(AVG(f.confidence)::numeric, 3)      AS avg_confidence,
             CASE WHEN COUNT(*) FILTER (WHERE f.status='red')>0 THEN 'red'
                  WHEN COUNT(*) FILTER (WHERE f.status='yellow')>0 THEN 'yellow'
                  ELSE 'green' END                     AS worst_status
      FROM hospitals h
      LEFT JOIN forecasts f ON f.hospital_id = h.hospital_id
      GROUP BY h.hospital_id
      ORDER BY h.hospital_id`);
    res.json(rows);
  } catch (e) { next(e); }
});

// พยากรณ์ทั้งหมด (กรองด้วย ?hospital_id= / ?status= ได้)
app.get("/api/forecasts", async (req, res, next) => {
  try {
    const { hospital_id, status } = req.query;
    const where = [];
    const params = [];
    if (hospital_id) { params.push(hospital_id); where.push(`hospital_id=$${params.length}`); }
    if (status) { params.push(status); where.push(`status=$${params.length}`); }
    const clause = where.length ? `WHERE ${where.join(" AND ")}` : "";
    const { rows } = await pool.query(
      `SELECT hospital_id, drug, desc_th, last_date, pred_next_day, avg_30d,
              ratio, status, confidence
       FROM forecasts ${clause}
       ORDER BY hospital_id, drug`, params);
    res.json(rows);
  } catch (e) { next(e); }
});

// KPI สรุปภาพรวม
app.get("/api/summary", async (_req, res, next) => {
  try {
    const { rows } = await pool.query(`
      SELECT
        (SELECT COUNT(*) FROM hospitals) AS hospitals,
        COUNT(*) FILTER (WHERE status='red')    AS red_items,
        COUNT(*) FILTER (WHERE status='yellow') AS yellow_items,
        COUNT(*) FILTER (WHERE status='green')  AS green_items,
        ROUND(AVG(confidence)::numeric, 3)      AS avg_confidence
      FROM forecasts`);
    res.json(rows[0]);
  } catch (e) { next(e); }
});

// ศูนย์ควบคุมความเป็นส่วนตัว: จำนวน weight ที่ส่ง + รายชื่อ รพ.
app.get("/api/privacy", async (_req, res, next) => {
  try {
    const w = await pool.query("SELECT COUNT(*) AS n_weights FROM weights");
    const h = await pool.query("SELECT hospital_id, name FROM hospitals ORDER BY hospital_id");
    res.json({
      federated_learning: "active",
      differential_privacy: { enabled: true, sigma: 0.1 },
      transport: "TLS/SSL",
      secure_aggregation: true,
      n_weights: parseInt(w.rows[0].n_weights, 10),
      hospitals: h.rows.map((r) => ({ ...r, online: true })),
    });
  } catch (e) { next(e); }
});

// weight กลาง (โมเดลที่ส่งข้ามเครือข่าย)
app.get("/api/weights", async (_req, res, next) => {
  try {
    const { rows } = await pool.query("SELECT feature, weight FROM weights ORDER BY ABS(weight) DESC");
    res.json(rows);
  } catch (e) { next(e); }
});

// ---------- AUTH ----------
// เข้าสู่ระบบ: { username, password } -> token
app.post("/api/login", async (req, res, next) => {
  try {
    const { username, password } = req.body || {};
    if (!username || !password) return res.status(400).json({ error: "กรอก username/password" });
    const { rows } = await pool.query(
      `SELECT u.username, u.password_hash, u.hospital_id, h.name
       FROM users u LEFT JOIN hospitals h ON h.hospital_id = u.hospital_id
       WHERE u.username = $1`, [username]);
    const user = rows[0];
    if (!user || !bcrypt.compareSync(password, user.password_hash)) {
      return res.status(401).json({ error: "username หรือ password ไม่ถูกต้อง" });
    }
    const token = signToken({ hospital_id: user.hospital_id, name: user.name });
    res.json({ token, hospital_id: user.hospital_id, name: user.name });
  } catch (e) { next(e); }
});

// ข้อมูลผู้ใช้ปัจจุบัน
app.get("/api/me", requireAuth, (req, res) => {
  res.json({ hospital_id: req.user.hospital_id, name: req.user.name });
});

// ---------- BORROW (ยืมยา) ----------
// รพ. ที่สามารถให้ยืมยา drug หนึ่งได้ (สถานะไม่แดง) — สำหรับ dropdown ในฟอร์ม
app.get("/api/lenders", requireAuth, async (req, res, next) => {
  try {
    const { drug } = req.query;
    const { rows } = await pool.query(
      `SELECT f.hospital_id, h.name, f.status, f.pred_next_day, f.avg_30d
       FROM forecasts f JOIN hospitals h ON h.hospital_id = f.hospital_id
       WHERE f.drug = $1 AND f.status <> 'red' AND f.hospital_id <> $2
       ORDER BY (f.avg_30d - f.pred_next_day) DESC`,
      [drug, req.user.hospital_id]);
    res.json(rows);
  } catch (e) { next(e); }
});

// สร้างคำขอยืมยา — อนุญาตเฉพาะยาที่ \"สถานะแดง\" ของโรงพยาบาลผู้ขอ
app.post("/api/borrow", requireAuth, async (req, res, next) => {
  try {
    const from = req.user.hospital_id;
    const { to_hospital, drug, quantity, reason } = req.body || {};
    if (!to_hospital || !drug || !quantity) {
      return res.status(400).json({ error: "กรอก to_hospital / drug / quantity ให้ครบ" });
    }
    if (to_hospital === from) return res.status(400).json({ error: "ยืมจากโรงพยาบาลตัวเองไม่ได้" });

    const chk = await pool.query(
      "SELECT status FROM forecasts WHERE hospital_id=$1 AND drug=$2", [from, drug]);
    if (!chk.rows[0]) return res.status(400).json({ error: "ไม่พบยานี้ในระบบของโรงพยาบาล" });
    if (chk.rows[0].status !== "red") {
      return res.status(403).json({ error: "ยืมยาได้เฉพาะรายการที่สถานะ 🔴 ขาดแคลนเท่านั้น" });
    }

    const { rows } = await pool.query(
      `INSERT INTO borrow_requests (from_hospital, to_hospital, drug, quantity, reason)
       VALUES ($1,$2,$3,$4,$5) RETURNING *`,
      [from, to_hospital, drug, parseFloat(quantity), reason || null]);
    res.status(201).json(rows[0]);
  } catch (e) { next(e); }
});

// รายการคำขอที่เกี่ยวข้องกับโรงพยาบาลของฉัน (ทั้งขอ + ถูกขอ)
app.get("/api/borrow", requireAuth, async (req, res, next) => {
  try {
    const me = req.user.hospital_id;
    const { rows } = await pool.query(
      `SELECT b.*, hf.name AS from_name, ht.name AS to_name
       FROM borrow_requests b
       LEFT JOIN hospitals hf ON hf.hospital_id = b.from_hospital
       LEFT JOIN hospitals ht ON ht.hospital_id = b.to_hospital
       WHERE b.from_hospital = $1 OR b.to_hospital = $1
       ORDER BY b.created_at DESC`, [me]);
    res.json(rows.map((r) => ({ ...r, direction: r.from_hospital === me ? "outgoing" : "incoming" })));
  } catch (e) { next(e); }
});

// ผู้ให้ยืม (to_hospital) อนุมัติ/ปฏิเสธคำขอ
app.patch("/api/borrow/:id", requireAuth, async (req, res, next) => {
  try {
    const { status } = req.body || {};
    if (!["approved", "rejected"].includes(status)) {
      return res.status(400).json({ error: "status ต้องเป็น approved หรือ rejected" });
    }
    const cur = await pool.query("SELECT * FROM borrow_requests WHERE id=$1", [req.params.id]);
    if (!cur.rows[0]) return res.status(404).json({ error: "ไม่พบคำขอ" });
    if (cur.rows[0].to_hospital !== req.user.hospital_id) {
      return res.status(403).json({ error: "เฉพาะโรงพยาบาลผู้ให้ยืมเท่านั้นที่ตอบคำขอได้" });
    }
    const { rows } = await pool.query(
      "UPDATE borrow_requests SET status=$1 WHERE id=$2 RETURNING *", [status, req.params.id]);
    res.json(rows[0]);
  } catch (e) { next(e); }
});

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: err.message });
});

async function start() {
  await waitForDb();
  try {
    await seed();
  } catch (e) {
    console.error("[seed] failed (continuing):", e.message);
  }
  app.listen(PORT, () => console.log(`[api] listening on :${PORT}`));
}

start();
