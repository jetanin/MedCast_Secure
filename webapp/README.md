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
python scripts/export_forecast_snapshot.py   # -> data/predictions/forecast_snapshot.csv
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
- ระบบให้ยืมได้ **เฉพาะยาที่สถานะ 🔴 ขาดแคลน** ของโรงพยาบาลนั้น (backend บังคับ)
- เลือกโรงพยาบาลผู้ให้ยืม (ระบบแนะนำเฉพาะที่ยาไม่แดง + มี surplus) → กรอกจำนวน/เหตุผล → ส่งคำขอ
- โรงพยาบาลผู้ให้ยืมเห็นคำขอ "📥 ถูกขอ" แล้วกด **อนุมัติ/ปฏิเสธ** ได้

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

> Auth = ต้องส่ง header `Authorization: Bearer <token>`

## หน้าจอ (3 พาเนล)
1. **🗺️ Overview Map** — แผนที่ Leaflet หมุด รพ. ระบายสีตามสถานะ 🟢🟡🔴
2. **🤖 AI Intelligence** — เลือก รพ. → กราฟ (Recharts) พยากรณ์ vs เฉลี่ย30วัน + ตาราง + Confidence
3. **🔒 Privacy Control** — สถานะ Federated Learning / DP / TLS + กระแสข้อมูล

## พัฒนาแบบ local (ไม่ใช้ Docker)
```powershell
# backend (ต้องมี Postgres รันอยู่ + ตั้ง env PGHOST ฯลฯ)
cd webapp/backend && npm install && npm start
# frontend (proxy /api -> localhost:4000)
cd webapp/frontend && npm install && npm run dev   # http://localhost:5173
```

## โครงสร้าง
```
webapp/
├── docker-compose.yml
├── db/init.sql              # schema (hospitals, forecasts, weights)
├── backend/                 # Express + pg + csv seeder
│   ├── server.js  db.js  seed.js  Dockerfile  package.json
└── frontend/                # React + Vite + Leaflet + Recharts
    ├── src/  Dockerfile  nginx.conf  vite.config.js  package.json
```
