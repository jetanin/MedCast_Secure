import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";
import { api } from "../api";

const COLOR = { green: "#2ecc71", yellow: "#f1c40f", red: "#e74c3c" };
const STATUS_TH = { green: "🟢 เพียงพอ", yellow: "🟡 ใกล้หมด", red: "🔴 ขาดแคลน" };

export default function AIIntelligence({ hospitals }) {
  const [hid, setHid] = useState(hospitals[0]?.hospital_id || "");
  const [rows, setRows] = useState([]);

  useEffect(() => {
    if (hid) api.forecasts(hid).then(setRows).catch(console.error);
  }, [hid]);

  const chartData = rows.map((r) => ({
    drug: r.drug,
    "เหลือ(วัน)": Math.round(r.days_of_supply * 10) / 10,
    status: r.status,
  }));

  return (
    <div className="panel">
      <h2>🤖 AI Intelligence — พยากรณ์ความต้องการยา</h2>
      <label className="muted">เลือกโรงพยาบาล:&nbsp;</label>
      <select value={hid} onChange={(e) => setHid(e.target.value)}>
        {hospitals.map((h) => (
          <option key={h.hospital_id} value={h.hospital_id}>
            {h.hospital_id} — {h.name}
          </option>
        ))}
      </select>

      <p className="muted" style={{ fontSize: "0.82rem" }}>
        จำนวนวันที่ยาเหลือในคลัง (days-of-supply) — 🟢 ≥14 · 🟡 4–13 · 🔴 ≤3 วัน
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="drug" stroke="#94a3b8" />
          <YAxis stroke="#94a3b8" />
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
          <Legend />
          <Bar dataKey="เหลือ(วัน)">
            {chartData.map((d, i) => <Cell key={i} fill={COLOR[d.status]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <table style={{ marginTop: 14 }}>
        <thead>
          <tr><th>กลุ่มยา</th><th>รายละเอียด</th><th>พยากรณ์/วัน</th><th>คงคลัง</th><th>เหลือ(วัน)</th><th>สถานะ</th><th>Conf.</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.drug}>
              <td>{r.drug}</td>
              <td className="muted">{r.desc_th}</td>
              <td>{r.pred_next_day?.toFixed(1)}</td>
              <td>{r.stock_on_hand?.toFixed(0)}</td>
              <td>{r.days_of_supply?.toFixed(0)}</td>
              <td><span className={`badge ${r.status}`}>{STATUS_TH[r.status]}</span></td>
              <td>{Math.round(r.confidence * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
