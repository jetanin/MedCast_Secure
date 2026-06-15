"""สร้าง snapshot คลังยาปัจจุบันของแต่ละโรงพยาบาล (ตามที่ proposal ต้องการ)

ผลลัพธ์: data/hospitals/stock_snapshot.csv
คอลัมน์: hospital_id, drug, stock_on_hand, reorder_point, expiry_date

stock ถูกสุ่มให้กระจายเป็น 🔴/🟡/🟢 ตามจำนวนวันที่ยาเหลือ (days-of-supply)
เพื่อให้เห็นทั้งสามสถานะบน dashboard (red ≤3, yellow 4–13, green ≥14 วัน)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HOSP_DIR = ROOT / "data" / "hospitals"

# โซนจำนวนวันคงคลัง (days-of-supply) + น้ำหนักการสุ่ม
ZONES = [("red", 1, 3), ("yellow", 5, 13), ("green", 14, 45)]
WEIGHTS = [0.25, 0.35, 0.40]


def main():
    rng = np.random.default_rng(42)
    rows = []
    for fp in sorted(HOSP_DIR.glob("HOSP_*.csv")):
        hid = fp.stem
        usage = pd.read_csv(fp, parse_dates=["date"])
        # ค่าเฉลี่ยการจ่ายยา 30 วันล่าสุด ต่อกลุ่มยา = อัตราการใช้ต่อวัน
        recent = usage.sort_values("date").groupby("drug_id").tail(30)
        mean_daily = recent.groupby("drug_id")["quantity_dispensed"].mean()

        for drug, rate in mean_daily.items():
            rate = max(float(rate), 0.3)  # กันหารศูนย์
            zone = rng.choice(len(ZONES), p=WEIGHTS)
            _, lo, hi = ZONES[zone]
            target_days = rng.integers(lo, hi + 1)
            stock = int(round(rate * target_days))
            expiry = pd.Timestamp("2026-06-09") + pd.Timedelta(days=int(rng.integers(60, 540)))
            rows.append({
                "hospital_id": hid,
                "drug": drug,
                "stock_on_hand": stock,
                "reorder_point": int(round(rate * 7)),   # จุดสั่งซื้อ ≈ ใช้ 7 วัน
                "expiry_date": expiry.strftime("%Y-%m-%d"),
            })

    df = pd.DataFrame(rows)
    out = HOSP_DIR / "stock_snapshot.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[saved] {out.name}: {len(df)} rows ({df['hospital_id'].nunique()} hospitals)")


if __name__ == "__main__":
    main()
