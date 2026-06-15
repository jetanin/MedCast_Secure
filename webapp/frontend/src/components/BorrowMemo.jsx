import { useState } from "react";

// บันทึกข้อความ "ขอยืมยา/เวชภัณฑ์มิใช่ยา ในการเยี่ยมบ้าน" — แก้ไขได้ + พิมพ์/บันทึก PDF
export default function BorrowMemo({ request, onClose }) {
  const today = new Date();
  const initItems = Array.from({ length: 10 }, (_, i) =>
    i === 0 && request
      ? { name: request.drug, qty: String(request.quantity ?? "") }
      : { name: "", qty: "" }
  );

  const [day, setDay] = useState(String(today.getDate()));
  const [month, setMonth] = useState(
    today.toLocaleDateString("th-TH", { month: "long" })
  );
  const [year, setYear] = useState(String(today.getFullYear() + 543)); // พ.ศ.
  const [org, setOrg] = useState(request?.from_name || "");
  const [items, setItems] = useState(initItems);
  const [officer, setOfficer] = useState("");
  const [officerPos, setOfficerPos] = useState("");
  const [pharm, setPharm] = useState("");
  const [pharmPos, setPharmPos] = useState("");

  const setItem = (i, key, val) =>
    setItems((arr) => arr.map((it, j) => (j === i ? { ...it, [key]: val } : it)));

  return (
    <div className="memo-overlay">
      <div className="memo-toolbar no-print">
        <button className="tab active" onClick={() => window.print()}>🖨️ พิมพ์ / บันทึก PDF</button>
        <button className="tab" onClick={onClose}>ปิด</button>
        <span className="muted">แก้ไขข้อความในช่องได้โดยตรง แล้วกดพิมพ์</span>
      </div>

      <div id="memo" className="memo-paper">
        <h1 className="memo-title">บันทึกข้อความ</h1>

        <p className="memo-center">
          วันที่ <input className="ln w2" value={day} onChange={(e) => setDay(e.target.value)} />
          เดือน <input className="ln w6" value={month} onChange={(e) => setMonth(e.target.value)} />
          พ.ศ. <input className="ln w3" value={year} onChange={(e) => setYear(e.target.value)} />
        </p>

        <p><b>เรื่อง</b>&nbsp;&nbsp;ขอยืมยา / เวชภัณฑ์มิใช่ยา ในการเยี่ยมบ้าน</p>
        <p><b>เรียน</b>&nbsp;&nbsp;ฝ่ายเภสัชกรรม</p>

        <p>
          เนื่องด้วย{" "}
          <input className="ln w-grow" value={org} onChange={(e) => setOrg(e.target.value)} />{" "}
          มีความประสงค์จะขอเบิกยา / เวชภัณฑ์มิใช่ยา เพื่อใช้ในการเยี่ยมบ้านตามรายการดังนี้
        </p>

        <ol className="memo-list">
          {items.map((it, i) => (
            <li key={i}>
              <input className="ln w-item" value={it.name}
                     onChange={(e) => setItem(i, "name", e.target.value)} />
              เป็นจำนวน
              <input className="ln w3" value={it.qty}
                     onChange={(e) => setItem(i, "qty", e.target.value)} />
            </li>
          ))}
        </ol>

        <div className="memo-signs">
          <div className="memo-sign">
            <div>เจ้าหน้าที่ผู้รับผิดชอบ</div>
            <div>ลงชื่อ ...................................................</div>
            <div>( <input className="ln w8" value={officer} onChange={(e) => setOfficer(e.target.value)} /> )</div>
            <div>ตำแหน่ง <input className="ln w8" value={officerPos} onChange={(e) => setOfficerPos(e.target.value)} /></div>
          </div>
          <div className="memo-sign">
            <div>เจ้าหน้าที่ฝ่ายเภสัชกรรม</div>
            <div>ลงชื่อ ...................................................</div>
            <div>( <input className="ln w8" value={pharm} onChange={(e) => setPharm(e.target.value)} /> )</div>
            <div>ตำแหน่ง <input className="ln w8" value={pharmPos} onChange={(e) => setPharmPos(e.target.value)} /></div>
          </div>
        </div>
      </div>
    </div>
  );
}
