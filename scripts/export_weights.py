"""Export weight ของโมเดล Federated Learning ออกเป็น CSV

ผลลัพธ์:
- models/global_weights.csv    : weight กลางจาก FedAvg (feature -> weight) + bias
- models/hospital_weights.csv  : weight ที่ \"แต่ละโรงพยาบาลส่งขึ้นศูนย์กลาง\" (long format)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import SGDRegressor

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
sys.path.insert(0, str(ROOT / "dashboard"))
from forecasting import build_features, list_hospital_files  # noqa: E402


def export_global():
    b = joblib.load(MODELS / "fedavg_dp_demand.joblib")
    coef, intercept, features = b["coef"], b["intercept"], b["features"]
    df = pd.DataFrame({"feature": features, "weight": np.round(coef, 6)})
    df = pd.concat([df, pd.DataFrame([{"feature": "__bias__", "weight": round(float(intercept[0]), 6)}])],
                   ignore_index=True)
    out = MODELS / "global_weights.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[saved] {out.name}: {len(features)} weights + bias")
    return b


def export_per_hospital(bundle):
    """เทรน local model ของแต่ละ รพ. แล้ว export weight ที่ส่งออก (เหมือนตอนทำ FedAvg)."""
    scaler, features = bundle["scaler"], bundle["features"]
    cutoff = pd.Timestamp("2025-05-01")
    rows = []
    for fp in list_hospital_files():
        hid = fp.stem
        feats = build_features(pd.read_csv(fp))
        tr = feats[feats["datum"] <= cutoff]
        Xs = scaler.transform(tr[features])
        local = SGDRegressor(max_iter=1000, random_state=0).fit(Xs, tr["demand"])
        for f, w in zip(features, local.coef_):
            rows.append({"hospital_id": hid, "feature": f, "weight": round(float(w), 6)})
        rows.append({"hospital_id": hid, "feature": "__bias__", "weight": round(float(local.intercept_[0]), 6)})
    df = pd.DataFrame(rows)
    out = MODELS / "hospital_weights.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[saved] {out.name}: {df['hospital_id'].nunique()} hospitals x {len(features)+1} weights")
    # เวอร์ชัน wide (1 คอลัมน์ต่อ รพ.) อ่านง่ายขึ้น
    wide = df.pivot(index="feature", columns="hospital_id", values="weight").reset_index()
    wide.to_csv(MODELS / "hospital_weights_wide.csv", index=False, encoding="utf-8-sig")
    print(f"[saved] hospital_weights_wide.csv")


if __name__ == "__main__":
    bundle = export_global()
    export_per_hospital(bundle)
