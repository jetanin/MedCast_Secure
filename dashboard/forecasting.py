"""โมดูลพยากรณ์สำหรับ dashboard ของ MedCast_Secure

- build_features(): สร้างฟีเจอร์ชุดเดียวกับ notebook 03/04 จากข้อมูลดิบ drug_usage
- load_global_model(): โหลด weight กลางจาก FedAvg (fedavg_dp_demand.joblib)
- forecast_all(): พยากรณ์ demand วันถัดไปของทุกโรงพยาบาล/ทุกกลุ่มยา + สถานะสี + confidence
"""
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parents[1]
HOSP_DIR = ROOT / "data" / "hospitals"
MODELS = ROOT / "models"
CLEAN = ROOT / "data" / "clean"

EPS = 1e-6


def build_features(usage: pd.DataFrame) -> pd.DataFrame:
    """สร้างฟีเจอร์จากข้อมูลดิบ drug_usage (date, drug_id, quantity_dispensed, hospital_id)."""
    g = usage.rename(columns={"quantity_dispensed": "demand", "drug_id": "drug"}).copy()
    g["datum"] = pd.to_datetime(g["date"])
    g = g.sort_values(["drug", "datum"]).reset_index(drop=True)
    d = g["datum"].dt
    g["year"] = d.year; g["month"] = d.month; g["day"] = d.day; g["dayofweek"] = d.dayofweek
    g["dayofyear"] = d.dayofyear; g["weekofyear"] = d.isocalendar().week.astype(int); g["quarter"] = d.quarter
    g["is_weekend"] = (d.dayofweek >= 5).astype(int)
    g["is_month_start"] = d.is_month_start.astype(int); g["is_month_end"] = d.is_month_end.astype(int)
    g["month_sin"] = np.sin(2 * np.pi * g.month / 12); g["month_cos"] = np.cos(2 * np.pi * g.month / 12)
    g["dow_sin"] = np.sin(2 * np.pi * g.dayofweek / 7); g["dow_cos"] = np.cos(2 * np.pi * g.dayofweek / 7)
    gb = g.groupby("drug")["demand"]
    for l in [1, 2, 3, 7, 14, 28]:
        g[f"lag_{l}"] = gb.shift(l)
    sh = gb.shift(1)
    for w in [7, 14, 30]:
        r = sh.groupby(g["drug"]).rolling(w)
        g[f"roll_mean_{w}"] = r.mean().reset_index(0, drop=True)
        g[f"roll_std_{w}"] = r.std().reset_index(0, drop=True)
        g[f"roll_min_{w}"] = r.min().reset_index(0, drop=True)
        g[f"roll_max_{w}"] = r.max().reset_index(0, drop=True)
    g["trend_7_30"] = g["roll_mean_7"] - g["roll_mean_30"]
    g["cv_30"] = g["roll_std_30"] / (g["roll_mean_30"] + EPS)
    g["mom_1_7"] = g["lag_1"] / (g["roll_mean_7"] + EPS)
    g["wow_diff"] = g["lag_1"] - g["lag_7"]
    g["accel"] = (g["lag_1"] - g["lag_2"]) - (g["lag_2"] - g["lag_3"])
    g["market_lag1"] = g.groupby("datum")["lag_1"].transform("sum")
    g["drug_share_lag1"] = g["lag_1"] / (g["market_lag1"] + EPS)
    nap = ("lag_", "roll_", "trend_", "cv_", "mom_", "wow_", "accel", "market_", "drug_share_")
    g = g.dropna(subset=[c for c in g.columns if c.startswith(nap)]).reset_index(drop=True)
    g = pd.concat([g, pd.get_dummies(g["drug"], prefix="drug")], axis=1)
    return g


def status_from_ratio(ratio: float) -> str:
    if pd.isna(ratio) or ratio <= 1.0:
        return "green"
    if ratio <= 1.5:
        return "yellow"
    return "red"


def load_global_model():
    """โหลด weight กลางจาก FedAvg + scaler + รายชื่อฟีเจอร์."""
    return joblib.load(MODELS / "fedavg_dp_demand.joblib")


def load_atc_names() -> dict:
    atc = pd.read_csv(CLEAN / "atc_drug_groups.csv")
    return dict(zip(atc["atc_code"], atc["description_th"]))


def load_hospital_master() -> pd.DataFrame:
    return pd.read_csv(HOSP_DIR / "hospital_master.csv")


def list_hospital_files():
    return sorted(HOSP_DIR.glob("HOSP_*.csv"))


def forecast_all():
    """พยากรณ์วันถัดไปของทุก รพ./ทุกกลุ่มยา ด้วย weight กลาง.

    คืน (forecast_df, history) :
      forecast_df : 1 แถวต่อ (รพ., ยา) พร้อม pred, status, confidence, days_to_*
      history     : ฟีเจอร์เต็ม (ไว้พล็อตกราฟย้อนหลัง)
    """
    bundle = load_global_model()
    coef, intercept = bundle["coef"], bundle["intercept"]
    scaler, FEATURES = bundle["scaler"], bundle["features"]

    rows, history = [], {}
    for fp in list_hospital_files():
        hid = fp.stem
        feats = build_features(pd.read_csv(fp))
        history[hid] = feats

        latest = feats.sort_values("datum").groupby("drug").tail(1)
        X = scaler.transform(latest[FEATURES])
        pred = np.clip(X @ coef + intercept, 0, None)

        ratio = pred / latest["roll_mean_30"].replace(0, np.nan).values
        # confidence: ความผันผวนสัมพัทธ์ต่ำ -> มั่นใจมาก (0-1)
        conf = (1.0 / (1.0 + latest["cv_30"].values)).round(3)

        for i, (_, r) in enumerate(latest.iterrows()):
            rows.append({
                "hospital_id": hid,
                "drug": r["drug"],
                "last_date": r["datum"].date(),
                "pred_next_day": round(float(pred[i]), 1),
                "avg_30d": round(float(r["roll_mean_30"]), 1),
                "ratio": round(float(ratio[i]), 2) if not np.isnan(ratio[i]) else np.nan,
                "status": status_from_ratio(ratio[i]),
                "confidence": float(conf[i]),
            })

    forecast_df = pd.DataFrame(rows)
    return forecast_df, history
