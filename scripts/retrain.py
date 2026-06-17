"""Retrain รายวัน — เทรน Federated Learning (FedAvg) ใหม่จากข้อมูลล่าสุดของทุกโรงพยาบาล

ขั้นตอน:
  1. สร้างฟีเจอร์จากข้อมูลดิบของแต่ละ รพ. (build_features)
  2. เทรน local SGD ในแต่ละ รพ. -> ใส่ Differential Privacy noise -> เฉลี่ยเป็น weight กลาง (FedAvg)
  3. บันทึก models/fedavg_dp_demand.joblib + models/global_weights.csv
  4. คำนวณ forecast snapshot ใหม่ (data/predictions/forecast_snapshot.csv)
  5. (ถ้าตั้ง env BACKEND_URL) สั่ง backend reseed ข้อมูลใหม่เข้า Postgres

รันมือ:  python scripts/retrain.py
รันอัตโนมัติรายวัน: docker compose (service `retrainer`) หรือ cron / Windows Task Scheduler
"""
import os
import sys
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

try:  # กัน UnicodeEncodeError เวลาพิมพ์ภาษาไทยบน console Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
PRED = ROOT / "data" / "predictions"
sys.path.insert(0, str(ROOT / "dashboard"))
from forecasting import build_features, list_hospital_files, forecast_all, load_atc_names  # noqa: E402

DP_SIGMA = float(os.getenv("DP_SIGMA", "0.1"))


def feature_columns(sample: pd.DataFrame):
    dummies = [c for c in sample.columns if c.startswith("drug_") and c != "drug_share_lag1"]
    num = [c for c in sample.columns if c not in ["date", "datum", "drug", "demand", "hospital_id"] + dummies]
    return num + dummies


def federated_retrain(freq="D", dp_sigma=DP_SIGMA, seed=0):
    suf = "" if freq == "D" else f"_{freq}"
    feats = {fp.stem: build_features(pd.read_csv(fp), freq=freq) for fp in list_hospital_files()}
    if not feats:
        raise SystemExit("ไม่พบข้อมูลโรงพยาบาลใน data/hospitals/")
    FEATURES = feature_columns(next(iter(feats.values())))

    # shared scaler (ในทางปฏิบัติตกลงร่วมผ่าน secure aggregation)
    pooled = pd.concat(feats.values(), ignore_index=True)
    scaler = StandardScaler().fit(pooled[FEATURES])

    rng = np.random.default_rng(seed)
    coefs, intercepts, sizes = [], [], []
    for hid, df in feats.items():
        Xs = scaler.transform(df[FEATURES])
        local = SGDRegressor(max_iter=1000, random_state=0).fit(Xs, df["demand"])
        c, b = local.coef_.copy(), local.intercept_.copy()
        if dp_sigma > 0:  # Differential Privacy noise ก่อนส่งออกจาก รพ.
            c = c + rng.normal(0, dp_sigma, c.shape)
            b = b + rng.normal(0, dp_sigma, b.shape)
        coefs.append(c); intercepts.append(b); sizes.append(len(df))

    w = np.array(sizes) / sum(sizes)
    coef = np.average(coefs, axis=0, weights=w)
    intercept = np.average(intercepts, axis=0, weights=w)

    joblib.dump({"coef": coef, "intercept": intercept, "scaler": scaler, "features": FEATURES},
                MODELS / f"fedavg_dp_demand{suf}.joblib")
    gw = pd.DataFrame({"feature": FEATURES, "weight": np.round(coef, 6)})
    gw = pd.concat([gw, pd.DataFrame([{"feature": "__bias__", "weight": round(float(intercept[0]), 6)}])],
                   ignore_index=True)
    gw.to_csv(MODELS / f"global_weights{suf}.csv", index=False, encoding="utf-8-sig")

    # โมเดลความแม่น (RandomForest) สำหรับคำนวณ confidence
    rf = RandomForestRegressor(
        n_estimators=200, max_depth=14, min_samples_leaf=5, n_jobs=-1, random_state=42
    ).fit(pooled[FEATURES], pooled["demand"])
    joblib.dump({"model": rf, "features": FEATURES}, MODELS / f"accuracy_model{suf}.joblib")

    return len(feats), len(FEATURES)


def refresh_snapshot():
    """รวม snapshot ทั้งรายวัน (daily) และรายสัปดาห์ (weekly) ไว้ในไฟล์เดียว (มีคอลัมน์ freq)."""
    atc = load_atc_names()
    parts = []
    for freq, label in [("D", "daily"), ("W", "weekly")]:
        fc, _ = forecast_all(freq)
        fc["freq"] = label
        fc["desc_th"] = fc["drug"].map(atc).fillna("")
        parts.append(fc)
    allfc = pd.concat(parts, ignore_index=True)
    cols = ["freq", "hospital_id", "drug", "desc_th", "last_date", "pred_next_day",
            "stock_on_hand", "reorder_point", "expiry_date", "days_of_supply",
            "status", "confidence"]
    PRED.mkdir(parents=True, exist_ok=True)
    allfc[cols].to_csv(PRED / "forecast_snapshot.csv", index=False, encoding="utf-8-sig")
    return len(allfc)


def trigger_reseed():
    """สั่ง backend โหลดข้อมูลใหม่เข้า Postgres (ถ้าตั้ง BACKEND_URL)."""
    base = os.getenv("BACKEND_URL")
    if not base:
        return
    url = base.rstrip("/") + "/api/reseed"
    req = urllib.request.Request(
        url, data=b"{}", method="POST",
        headers={"Content-Type": "application/json",
                 "X-Reseed-Token": os.getenv("RESEED_TOKEN", "changeme")})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"[retrain] reseed -> {r.status} {r.read().decode()[:120]}")
    except Exception as e:
        print(f"[retrain] reseed failed (ข้ามได้): {e}")


def main():
    for freq, label in [("D", "รายวัน"), ("W", "รายสัปดาห์")]:
        n_hosp, n_feat = federated_retrain(freq)
        print(f"[retrain] FedAvg {label} ({freq}): {n_hosp} รพ. · {n_feat} ฟีเจอร์")
    n_rows = refresh_snapshot()
    print(f"[retrain] snapshot รวม {n_rows} แถว (daily + weekly)")
    trigger_reseed()


if __name__ == "__main__":
    main()
