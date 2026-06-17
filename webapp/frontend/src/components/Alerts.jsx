import { useEffect, useState } from "react";
import { api, auth } from "../api";
import Pagination, { usePaged } from "./Pagination.jsx";

const STATUS_TH = { green: "🟢", yellow: "🟡", red: "🔴" };

function expiryBadge(days) {
  if (days < 0) return <span className="badge red">หมดอายุแล้ว</span>;
  if (days <= 30) return <span className="badge red">{days} วัน</span>;
  if (days <= 90) return <span className="badge yellow">{days} วัน</span>;
  return <span className="badge green">{days} วัน</span>;
}

export default function Alerts() {
  const me = auth.hospital;
  const isAdmin = me?.role === "admin";
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [q, setQ] = useState("");

  const kw = q.trim().toLowerCase();
  const match = (r) =>
    kw === "" ||
    (r.drug && r.drug.toLowerCase().includes(kw)) ||
    (r.desc_th && r.desc_th.toLowerCase().includes(kw)) ||
    (r.hospital_id && r.hospital_id.toLowerCase().includes(kw));
  const fExp = (data?.expiring || []).filter(match);
  const fReo = (data?.reorder || []).filter(match);
  const fSho = (data?.shortage || []).filter(match);

  // เรียก hook ก่อน early-return เสมอ (ตามกฎ React)
  const pExp = usePaged(fExp, 10);
  const pReo = usePaged(fReo, 10);
  const pSho = usePaged(fSho, 10);

  useEffect(() => {
    api
      .alerts()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);
  if (err) return <div className="panel muted">⚠️ {err}</div>;
  if (!data) return <div className="panel muted">กำลังโหลด...</div>;

  return (
    <div>
      <div className="filterbar">
        <p className="muted" style={{ margin: 0 }}>
          การแจ้งเตือน{" "}
          {isAdmin ? "(ทุกโรงพยาบาล)" : `ของ 🏥 ${me?.name || me?.hospital_id}`}
        </p>
        <span style={{ flex: 1 }} />
        <input className="search" placeholder={`🔍 ค้นหายา ${isAdmin ? "/ รหัส รพ." : ""}`}
               value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {/* Expiry / FEFO */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <h2>⏳ ใกล้หมดอายุ (FEFO — First-Expired-First-Out)</h2>
        <table>
          <thead>
            <tr>
              {isAdmin && <th>รพ.</th>}
              <th>ยา</th>
              <th>รายละเอียด</th>
              <th>คงคลัง</th>
              <th>วันหมดอายุ</th>
              <th>เหลือ</th>
            </tr>
          </thead>
          <tbody>
            {pExp.slice.map((r, i) => (
              <tr key={i}>
                {isAdmin && <td>{r.hospital_id}</td>}
                <td>{r.drug}</td>
                <td className="muted">{r.desc_th}</td>
                <td>{r.stock_on_hand?.toFixed(0)}</td>
                <td>{r.expiry_date}</td>
                <td>{expiryBadge(r.days_to_expiry)}</td>
              </tr>
            ))}
            {fExp.length === 0 && (
              <tr>
                <td colSpan={isAdmin ? 6 : 5} className="muted">
                  {q ? "ไม่พบรายการที่ค้นหา" : "ไม่มียาใกล้หมดอายุ 🎉"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <Pagination {...pExp} />
      </div>

      <div className="row">
        {/* Reorder point */}
        <div className="panel">
          <h2>📦 ต่ำกว่าจุดสั่งซื้อ (Reorder Point)</h2>
          <table>
            <thead>
              <tr>
                {isAdmin && <th>รพ.</th>}
                <th>ยา</th>
                <th>คงคลัง</th>
                <th>จุดสั่งซื้อ</th>
                <th>เหลือ(วัน)</th>
              </tr>
            </thead>
            <tbody>
              {pReo.slice.map((r, i) => (
                <tr key={i}>
                  {isAdmin && <td>{r.hospital_id}</td>}
                  <td>
                    {STATUS_TH[r.status]} {r.drug}
                  </td>
                  <td>{r.stock_on_hand?.toFixed(0)}</td>
                  <td>{r.reorder_point?.toFixed(0)}</td>
                  <td>{r.days_of_supply?.toFixed(0)}</td>
                </tr>
              ))}
              {fReo.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4} className="muted">
                    {q ? "ไม่พบรายการที่ค้นหา" : "สต็อกเพียงพอทุกรายการ"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination {...pReo} />
        </div>

        {/* Shortage (red) */}
        <div className="panel">
          <h2>🔴 ขาดแคลนด่วน (≤3 วัน)</h2>
          <table>
            <thead>
              <tr>
                {isAdmin && <th>รพ.</th>}
                <th>ยา</th>
                <th>รายละเอียด</th>
                <th>คงคลัง</th>
                <th>เหลือ(วัน)</th>
              </tr>
            </thead>
            <tbody>
              {pSho.slice.map((r, i) => (
                <tr key={i}>
                  {isAdmin && <td>{r.hospital_id}</td>}
                  <td>{r.drug}</td>
                  <td className="muted">{r.desc_th}</td>
                  <td>{r.stock_on_hand?.toFixed(0)}</td>
                  <td>
                    <span className="badge red">
                      {r.days_of_supply?.toFixed(0)} วัน
                    </span>
                  </td>
                </tr>
              ))}
              {fSho.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4} className="muted">
                    {q ? "ไม่พบรายการที่ค้นหา" : "ไม่มียาขาดแคลน"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination {...pSho} />
        </div>
      </div>
    </div>
  );
}
