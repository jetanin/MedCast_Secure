# MedCast_Secure

> ระบบพยากรณ์ความต้องการยาข้ามโรงพยาบาลแบบรักษาความเป็นส่วนตัว
> **Logistics Innovation Hackathon 2026**

MedCast_Secure คือต้นแบบระบบ AI ที่ช่วยให้ศูนย์กลางการกระจายยา (เช่น คลังยาส่วนกลาง / สปสช.) สามารถ **พยากรณ์ล่วงหน้าได้ว่ายาตัวไหนกำลังจะหมดหรือขาดแคลนที่โรงพยาบาลท้องถิ่นแห่งใด ในช่วงเวลาใด** เพื่อจัดส่งยาได้ทันเวลา โดย **ข้อมูลคนไข้/คลังยาดิบไม่เคยออกจากโรงพยาบาล** — ป้องกันข้อมูลรั่วไหลและสอดคล้องกับ PDPA

---

## 🎯 ปัญหาที่แก้ (Problem)

- โรงพยาบาลท้องถิ่นมักรู้ตัวว่า "ยาขาด" ก็ต่อเมื่อยาหมดแล้ว → จัดส่งไม่ทัน
- การส่งข้อมูลคลังยา/การใช้ยาแบบดิบไปศูนย์กลาง = เสี่ยงข้อมูลคนไข้รั่วไหล + ผิด PDPA
- ต้นทุน cloud สูงถ้าต้องรวมข้อมูลดิบทั้งหมดไว้ที่เดียว

## 💡 แนวคิดหลัก (Solution)

| ด้าน                                  | วิธีการ                                                                                                                                       |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **เก็บข้อมูลอัตโนมัติ**               | AI ในโรงพยาบาลดึงข้อมูลการใช้ยาเอง — _zero manual input_                                                                                      |
| **เรียนรู้ร่วมกันโดยไม่ส่งข้อมูลดิบ** | **Federated Learning (FedAvg)** — ส่งแค่ _weights_ ของโมเดล ไม่ใช่ข้อมูลคนไข้                                                                 |
| **ลดต้นทุน cloud**                    | ประมวลผลที่ปลายทาง (edge) ออกแบบให้ _scalable_                                                                                                |
| **พยากรณ์แบบเรียลไทม์**               | AI พยากรณ์ว่ายาตัวไหนจะหมด/ขาดช่วงไหน + แสดง **Confidence Score**                                                                             |
| **ป้องกันข้อมูลรั่วไหล**              | **Differential Privacy** (เพิ่ม noise) + **Secure Aggregation** + **TLS/SSL** ระดับเดียวกับธนาคาร — ตัวเลขที่ถูกดักจับไปจะไร้ความหมายทางสถิติ |

### Pipeline แบบย่อ

```
รพ.ท้องถิ่น (edge AI)                        ศูนย์กลาง (server)
─────────────────────                       ──────────────────
ข้อมูลใช้ยา (อยู่ในรพ.)
   │ zero manual input
   ▼
เทรนโมเดล → weights
   │ + Differential Privacy noise
   │ + Secure Aggregation
   │ ── TLS/SSL ──────────────────────────▶  FedAvg รวม weights
                                                   │
                                                   ▼
                                        Real-time forecast + Confidence
                                                   │
                                                   ▼
                                            จัดส่งยาเชิงรุก
```

---

## 📊 Dashboard (Web App)

1. **Overview Map** — แผนที่ตำแหน่งโรงพยาบาลทั้งหมด พร้อมสถานะ
   - 🟢 เขียว = ยาเพียงพอ
   - 🟡 เหลือง = ใกล้หมด
   - 🔴 แดง = ขาดแคลน
2. **AI Intelligence Panel** — กราฟพยากรณ์ความต้องการยา
3. **Confidence Score** — บอกว่า AI พยากรณ์แม่นแค่ไหน
4. **Privacy Control Center** — ดูว่ารพ.ไหนเชื่อมต่อบ้าง สถานะ Secure Aggregation และการเข้ารหัส

---

## 🗂️ โครงสร้างโปรเจกต์

```
MedCast_Secure/
├── data/                       # ชุดข้อมูล (ถูก gitignore — โหลดเอง ดูด้านล่าง)
├── notebook/
│   ├── 00_load_data.ipynb      # โหลดข้อมูลจาก Kaggle + แปลงเป็น CSV
│   ├── 01_data_cleaning.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_feature_engineer.ipynb
│   ├── 04_model_training.ipynb
│   └── 05_model_evaluation.ipynb
├── .env                        # เก็บ credential ของ Kaggle (ถูก gitignore)
└── README.MD
```

---

## 🚀 การติดตั้งและโหลดข้อมูล

### 1. ติดตั้ง dependencies

```powershell
pip install kaggle pandas python-dotenv openpyxl json5
```

### 2. สร้างไฟล์ `.env`

สร้างไฟล์ชื่อ `.env` ไว้ที่ราก (root) ของโปรเจกต์ แล้วใส่ Kaggle credential:

```env
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_api_key
```

> **วิธีหา KAGGLE_KEY:** เข้า [kaggle.com/settings](https://www.kaggle.com/settings) → หัวข้อ **API** → กด **Create New Token**
> จะได้ไฟล์ `kaggle.json` มา ภายในมี `"username"` และ `"key"` ให้นำมาใส่ใน `.env`

> ⚠️ `.env` ถูกใส่ไว้ใน `.gitignore` แล้ว — **ห้าม commit ขึ้น git** เพราะมีข้อมูลลับ

### 3. รันโหลดข้อมูล

เปิด [notebook/00_load_data.ipynb](notebook/00_load_data.ipynb) แล้วรันทุก cell จากบนลงล่าง notebook จะ:

1. อ่าน credential จาก `.env` เข้า environment ก่อน import `kaggle`
2. ดาวน์โหลด 4 ชุดข้อมูลจาก Kaggle ลงใน `data/` (ข้ามชุดที่มีอยู่แล้ว)
3. แปลงไฟล์ที่ไม่ใช่ CSV (`.xlsx`, `.js`) ให้เป็น `.csv`
4. แสดงตัวอย่างข้อมูลแต่ละชุด

### ชุดข้อมูลที่ใช้ (Kaggle)

| ชุดข้อมูล                                                                                                                              | ใช้ทำอะไร                                                             |
| -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [pharma-sales-data](https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data)                                                 | ยอดขาย/การใช้ยาตามเวลา (รายชั่วโมง/วัน/สัปดาห์/เดือน) — ใช้ฝึกพยากรณ์ |
| [inventory-data-for-pharmacy](https://www.kaggle.com/datasets/pritipoddar/inventory-data-for-pharmacy-website-in-json-format)          | ข้อมูลคลังยา (ชื่อยา, ผู้ผลิต, วันหมดอายุ, จำนวนคงเหลือ)              |
| [pharmaceutical-supply-chain-optimization](https://www.kaggle.com/datasets/mohammedashraf000/pharmaceutical-supply-chain-optimization) | ข้อมูล supply chain การกระจายยา                                       |
| [pharmacy-products-dataset](https://www.kaggle.com/datasets/hossam82/pharmacy-products-dataset)                                        | รายการสินค้า/ยา                                                       |

---

## 🛠️ เทคโนโลยี (Tech Stack)

- **AI / ML:** Python, pandas, scikit-learn / PyTorch (forecasting)
- **Federated Learning:** FedAvg (federated averaging)
- **Privacy & Security:** Differential Privacy, Secure Aggregation, TLS/SSL
- **Dashboard:** Web app (map + charts + privacy panel)
