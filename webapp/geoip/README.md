# GeoLite2 DB (สำหรับ IP geolocation แบบ offline)

วางไฟล์ **`GeoLite2-City.mmdb`** ในโฟลเดอร์นี้ เพื่อให้ backend (`IP_GEO=maxmind`) แปลง IP เป็นตำแหน่งแบบออฟไลน์

## วิธีโหลด (ฟรี ต้องสมัคร)
1. สมัครบัญชีฟรีที่ https://www.maxmind.com/en/geolite2/signup
2. ไปที่ **Download Files** → ดาวน์โหลด **GeoLite2 City** (รูปแบบ `.mmdb`)
3. แตกไฟล์ แล้ววาง `GeoLite2-City.mmdb` ไว้ที่ `webapp/geoip/GeoLite2-City.mmdb`

> ไฟล์ `.mmdb` ถูก gitignore (มี license ของ MaxMind ห้าม redistribute)

## หมายเหตุ
- ถ้าไม่มีไฟล์นี้ + `IP_GEO=maxmind` → audit จะบันทึก "ไม่ทราบตำแหน่ง (ไม่มี GeoLite2 DB)"
- อยากได้ระดับเขต/อำเภอ (เช่น "Bang Khae") โดยไม่ต้องมีไฟล์ → ตั้ง env `IP_GEO=ipapi` (ออนไลน์)
- GeoLite2 ให้ความละเอียดระดับ **เมือง/จังหวัด** (ไม่ถึงระดับเขตของไทย)
