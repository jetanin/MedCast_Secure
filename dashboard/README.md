# MedCast_Secure — Dashboard

Dashboard (Streamlit) แสดงผลพยากรณ์การขาดแคลนยาข้ามโรงพยาบาล

## วิธีรัน

```powershell
pip install streamlit plotly scikit-learn pandas joblib
python dashboard/run.py
```

เปิดเบราว์เซอร์ที่ http://localhost:8501 (หรือ 8502)

> **ทำไมต้องใช้ `python dashboard/run.py` ไม่ใช่ `streamlit run`?**
> เครื่องนี้ใช้ **Python 3.10.0rc2** (release candidate) ซึ่งมีบั๊กใน `typing._no_init_or_replace_init`
> ทำให้ Streamlit websocket พัง (`WebSocketHandler.__init__() missing 2 required positional arguments`)
> ไฟล์ `run.py` patch บั๊กนี้ก่อนเปิดเซิร์ฟเวอร์
>
> ✅ **ทางแก้ระยะยาว:** ติดตั้ง Python เวอร์ชัน stable (3.11 / 3.12) แล้วใช้ `streamlit run dashboard/app.py` ได้ตามปกติ
> เช่น `winget install Python.Python.3.12`

## ต้องมีไฟล์เหล่านี้ก่อน (สร้างจาก notebook)
- `models/fedavg_dp_demand.joblib` — weight กลางจาก FedAvg (notebook 04)
- `data/hospitals/HOSP_00X.csv` + `hospital_master.csv` (scripts/generate_hospital_data.py)
- `data/clean/atc_drug_groups.csv` (notebook 01)

## 3 พาเนล
1. **Overview Map** — ตำแหน่ง รพ. + สถานะสี 🟢🟡🔴 (แย่สุดในบรรดายาของแต่ละ รพ.)
2. **AI Intelligence** — เลือก รพ./กลุ่มยา → กราฟย้อนหลัง + จุดพยากรณ์ + Confidence Score
3. **Privacy Control Center** — สถานะ Federated Learning / Differential Privacy / TLS + กระแสข้อมูล

## โครงสร้าง
- `forecasting.py` — โหลด weight กลาง + build features + พยากรณ์ทุก รพ. (ใช้ร่วมกับ notebook ได้)
- `app.py` — UI ทั้งหมด
