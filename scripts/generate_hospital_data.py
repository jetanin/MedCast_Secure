"""สร้างข้อมูลจำลอง drug_usage ของ 4 โรงพยาบาล (แยกไฟล์ละ รพ.)

ใช้ profile จากข้อมูลจริง (data/clean/salesdaily.csv) เป็นฐาน แล้วปรับ
- scale ต่างกันตามขนาด รพ.
- ตัวคูณรายกลุ่มยา (แต่ละ รพ. ใช้ยาแต่ละกลุ่มไม่เท่ากัน)
- noise รายวัน
เพื่อให้แต่ละ รพ. มี distribution ต่างกัน (เหมาะกับการสาธิต Federated Learning)

ผลลัพธ์: data/hospitals/HOSP_00X.csv  (คอลัมน์: date, drug_id, quantity_dispensed, hospital_id)
         data/hospitals/hospital_master.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "data" / "hospitals"
OUT.mkdir(parents=True, exist_ok=True)

DRUG_COLS = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]

# คุณลักษณะของแต่ละโรงพยาบาล (id, ชื่อ, ขนาด-scale, พิกัด, lead time)
HOSPITALS = [
    ("HOSP_001", "รพศ. เมืองกลาง",      1.30, 13.7563, 100.5018, 1),  # โรงพยาบาลศูนย์ ใหญ่
    ("HOSP_002", "รพท. ลำธารเหนือ",     1.00, 18.7883, 98.9853, 2),   # โรงพยาบาลทั่วไป
    ("HOSP_003", "รพช. บ้านหนองคู",     0.55, 14.9802, 102.0978, 3),  # โรงพยาบาลชุมชน เล็ก
    ("HOSP_004", "รพ.สต. ทุ่งทอง",      0.35, 7.0083, 100.4767, 4),   # รพ.ส่งเสริมสุขภาพ เล็กสุด
]

# ช่วงวันที่: เลื่อน profile จริงให้สิ้นสุดใกล้ปัจจุบัน (ให้รู้สึก "live")
END_DATE = pd.Timestamp("2026-06-03")


def main():
    base = pd.read_csv(CLEAN / "salesdaily.csv", parse_dates=["datum"]).sort_values("datum")
    # เลื่อนวันที่ให้แถวสุดท้าย = END_DATE
    offset = END_DATE - base["datum"].max()
    base["date"] = base["datum"] + offset

    master_rows = []
    for hid, name, scale, lat, lon, lead in HOSPITALS:
        rng = np.random.default_rng(abs(hash(hid)) % (2**32))
        # ตัวคูณรายกลุ่มยาเฉพาะ รพ. (0.5–1.5) — แต่ละ รพ. ใช้ยาต่างกัน
        drug_mult = {d: rng.uniform(0.5, 1.5) for d in DRUG_COLS}

        records = []
        for d in DRUG_COLS:
            vals = base[d].to_numpy() * scale * drug_mult[d]
            # multiplicative noise + ปัดเป็นจำนวนเต็มไม่ติดลบ
            noisy = vals * rng.normal(1.0, 0.15, size=len(vals))
            qty = np.clip(np.round(noisy), 0, None).astype(int)
            records.append(pd.DataFrame({
                "date": base["date"].dt.strftime("%Y-%m-%d"),
                "drug_id": d,
                "quantity_dispensed": qty,
                "hospital_id": hid,
            }))
        df = pd.concat(records, ignore_index=True).sort_values(["date", "drug_id"])
        path = OUT / f"{hid}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"[saved] {path.name}: {len(df):,} rows "
              f"({df['date'].nunique()} days x {df['drug_id'].nunique()} drugs)")

        master_rows.append({
            "hospital_id": hid, "name": name,
            "latitude": lat, "longitude": lon, "lead_time_days": lead,
        })

    master = pd.DataFrame(master_rows)
    master.to_csv(OUT / "hospital_master.csv", index=False, encoding="utf-8-sig")
    print(f"[saved] hospital_master.csv: {len(master)} hospitals")


if __name__ == "__main__":
    main()
