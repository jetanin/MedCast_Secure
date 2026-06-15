# MedCast_Secure — Web App

Full-stack web app: **React (frontend) + Node/Express (backend) + PostgreSQL** ทั้งหมดรันด้วย **Docker Compose**

```
┌─────────────┐   /api    ┌──────────────┐   SQL   ┌────────────┐
│  React (8080)│ ───────▶ │ Express (4000)│ ──────▶ │ Postgres   │
│  nginx       │          │  REST API     │         │ (medcast)  │
└─────────────┘           └──────────────┘         └────────────┘
        ▲ seed จาก CSV (../data, ../models)
```

## ก่อนรัน — เตรียมข้อมูล seed
จากโฟลเดอร์ราก โปรเจกต์ (รัน notebook 00–05 + scripts มาก่อน):

```powershell
python scripts/generate_stock_snapshot.py     # -> data/hospitals/stock_snapshot.csv (คลังยา)
python scripts/export_forecast_snapshot.py    # -> data/predictions/forecast_snapshot.csv
python scripts/export_weights.py              # -> models/global_weights.csv
```

backend จะ seed จากไฟล์เหล่านี้ + `data/hospitals/hospital_master.csv` อัตโนมัติตอนเริ่ม

## รันด้วย Docker

```powershell
cd webapp
docker compose up --build
```

- **Frontend:** http://localhost:8080
- **Backend API:** http://localhost:4000/api/health
- **Adminer (จัดการ DB):** http://localhost:8081 — System `PostgreSQL` · Server `db` · user/pass/db = `medcast`
- **Postgres:** localhost:5432 (user/pass/db = `medcast`)

ปิด: `docker compose down`  ·  ล้างข้อมูล DB ด้วย: `docker compose down -v`

## 🔑 บัญชีเข้าสู่ระบบ (Login)

มี 1 บัญชีต่อโรงพยาบาล (seed อัตโนมัติ):

| Username | Password |
| --- | --- |
| `HOSP_001` … `HOSP_004` | `medcast123` |

> เปลี่ยนรหัสตั้งต้นได้ด้วย env `DEFAULT_PASSWORD` ของ backend · เปลี่ยน JWT secret ด้วย `JWT_SECRET`

## 🤝 ยืมยา (Borrow)

โรงพยาบาลที่ล็อกอินแล้ว ไปแท็บ **🤝 ยืมยา**:
- ระบบให้ยืมได้ **เฉพาะยาที่สถานะ 🔴 ขาดแคลน** (เหลือ ≤3 วัน) ของโรงพยาบาลนั้น (backend บังคับ)
- ผู้ให้ยืมต้องเป็น **🟢 (เหลือ ≥14 วัน)** — ระบบเรียงตาม **ระยะทาง GPS ใกล้สุด** (Smart Borrowing)
- เลือกผู้ให้ยืม → กรอกจำนวน/เหตุผล → ส่งคำขอ
- โรงพยาบาลผู้ให้ยืมเห็นคำขอ "📥 ถูกขอ" แล้วกด **อนุมัติ/ปฏิเสธ** ได้
- ปุ่ม **📄 เอกสาร** ในแต่ละคำขอ → เปิด **"บันทึกข้อความ ขอยืมยา/เวชภัณฑ์มิใช่ยา ในการเยี่ยมบ้าน"**
  ตามแบบฟอร์มราชการ (เติมข้อมูลอัตโนมัติ + แก้ไขในช่องได้) แล้วกด **🖨️ พิมพ์ / บันทึก PDF**
  (ใช้ระบบพิมพ์ของเบราว์เซอร์ → เลือก "Save as PDF")

## REST API

| Endpoint | Auth | คืนค่า |
| --- | :---: | --- |
| `GET /api/health` | | สถานะ + การเชื่อม DB |
| `GET /api/summary` | | KPI (จำนวน รพ., ยาขาด/ใกล้หมด, confidence) |
| `GET /api/hospitals` | | รายชื่อ รพ. + พิกัด + สถานะรวม (แผนที่) |
| `GET /api/forecasts?hospital_id=&status=` | | พยากรณ์รายยา (กรองได้) |
| `GET /api/privacy` | | สถานะ FL / DP / TLS / weight |
| `GET /api/weights` | | weight กลาง |
| `POST /api/login` | | `{username,password}` → JWT token |
| `GET /api/me` | ✅ | ข้อมูลผู้ใช้ปัจจุบัน |
| `GET /api/lenders?drug=` | ✅ | รพ. ที่ให้ยืมยานั้นได้ (ไม่แดง) |
| `POST /api/borrow` | ✅ | สร้างคำขอยืม (เฉพาะยาแดง) |
| `GET /api/borrow` | ✅ | คำขอที่เกี่ยวกับ รพ. ฉัน (ขอ/ถูกขอ) |
| `PATCH /api/borrow/:id` | ✅ | ผู้ให้ยืมอนุมัติ/ปฏิเสธ |
| `GET /api/alerts` | ✅ | แจ้งเตือน: ใกล้หมดอายุ (FEFO) / ต่ำกว่าจุดสั่งซื้อ / ขาดแคลน |
| `GET /api/audit` | ✅ | Audit Trail (timestamp + IP ทุกธุรกรรม) |

> Auth = ต้องส่ง header `Authorization: Bearer <token>`

## หน้าจอ (3 พาเนล)
1. **🗺️ Overview Map** — แผนที่ Leaflet หมุด รพ. ระบายสีตามสถานะ 🟢🟡🔴
2. **🤖 AI Intelligence** — เลือก รพ. → กราฟ days-of-supply (Recharts) + คงคลัง + Confidence
3. **🔔 แจ้งเตือน** — ใกล้หมดอายุ (FEFO) / ต่ำกว่าจุดสั่งซื้อ (Reorder) / ขาดแคลนด่วน
4. **🤝 ยืมยา** — ฟอร์ม + บันทึกข้อความ PDF (Smart Borrowing GPS)
5. **📜 Audit Trail** — บันทึกทุกธุรกรรม timestamp + IP (แก้ย้อนหลังไม่ได้)
6. **🔒 Privacy Control** — สถานะ Federated Learning / DP / TLS + กระแสข้อมูล

## 💻 พัฒนาแบบ local (`npm run dev`)

รัน **เฉพาะ database + Adminer** ด้วย Docker ส่วน backend/frontend รันด้วย npm (hot reload):

```powershell
cd webapp
npm install          # ติดตั้ง concurrently (root)
npm run install:all  # ติดตั้ง deps ของ backend + frontend

npm run db           # (เทอร์มินัลที่ 1) เปิด Postgres + Adminer ด้วย Docker
npm run dev          # (เทอร์มินัลที่ 2) เปิด backend (:4000) + frontend (:5173) พร้อมกัน
```

- Frontend (dev): http://localhost:5173 — Vite proxy `/api` → backend `:4000`
- Backend ใช้ `PGHOST=localhost` เชื่อม Postgres ใน Docker (port 5432) และ seed จาก `../data`, `../models` อัตโนมัติ
- Adminer: http://localhost:8081

> รันแยกทีละตัวได้ด้วย `npm run dev:backend` / `npm run dev:frontend`
> ถ้าไม่มี Docker เลย ให้ติดตั้ง PostgreSQL เองแล้วตั้ง env `PGHOST/PGUSER/PGPASSWORD/PGDATABASE`

## โครงสร้าง
```
webapp/
├── docker-compose.yml       # db + adminer + backend + frontend
├── package.json             # สคริปต์ dev (concurrently)
├── db/init.sql              # schema (hospitals, forecasts, weights, users, borrow_requests)
├── backend/                 # Express + pg + csv seeder
│   ├── server.js  db.js  seed.js  auth.js  Dockerfile  package.json
└── frontend/                # React + Vite + Leaflet + Recharts
    ├── src/  Dockerfile  nginx.conf  vite.config.js  package.json
```
