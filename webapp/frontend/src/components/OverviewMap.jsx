import { useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import Pagination, { usePaged } from "./Pagination.jsx";

const COLOR = { green: "#2ecc71", yellow: "#f1c40f", red: "#e74c3c" };
const STATUS_TH = { green: "🟢 เพียงพอ", yellow: "🟡 ใกล้หมด", red: "🔴 ขาดแคลน" };

export default function OverviewMap({ hospitals }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");

  const kw = q.trim().toLowerCase();
  const filtered = hospitals.filter(
    (h) =>
      (status === "all" || h.worst_status === status) &&
      (kw === "" ||
        h.name.toLowerCase().includes(kw) ||
        h.hospital_id.toLowerCase().includes(kw))
  );

  const paged = usePaged(filtered, 15);
  const center = hospitals.length
    ? [
        hospitals.reduce((s, h) => s + h.latitude, 0) / hospitals.length,
        hospitals.reduce((s, h) => s + h.longitude, 0) / hospitals.length,
      ]
    : [13.7, 100.5];

  return (
    <div className="panel">
      <h2>🗺️ Overview Map — ตำแหน่งโรงพยาบาลและสถานะยา</h2>

      <div className="filterbar">
        <input className="search" placeholder="🔍 ค้นหาโรงพยาบาล (ชื่อ / รหัส)"
               value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">ทุกสถานะ</option>
          <option value="red">🔴 ขาดแคลน</option>
          <option value="yellow">🟡 ใกล้หมด</option>
          <option value="green">🟢 เพียงพอ</option>
        </select>
        <span className="muted">{filtered.length}/{hospitals.length} แห่ง</span>
      </div>

      <MapContainer center={center} zoom={6} style={{ height: 440, width: "100%" }}>
        <TileLayer
          attribution="&copy; OpenStreetMap"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {filtered.map((h) => (
          <CircleMarker
            key={h.hospital_id}
            center={[h.latitude, h.longitude]}
            radius={12}
            pathOptions={{ color: COLOR[h.worst_status], fillColor: COLOR[h.worst_status], fillOpacity: 0.8 }}
          >
            <Tooltip>
              <b>{h.name}</b> ({h.hospital_id})<br />
              สถานะ: {STATUS_TH[h.worst_status]}<br />
              🔴 {h.n_red} · 🟡 {h.n_yellow} · Confidence {Math.round(h.avg_confidence * 100)}%
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>

      <table style={{ marginTop: 14 }}>
        <thead>
          <tr><th>รหัส</th><th>โรงพยาบาล</th><th>สถานะรวม</th><th>ยาขาด</th><th>ใกล้หมด</th><th>Confidence</th></tr>
        </thead>
        <tbody>
          {paged.slice.map((h) => (
            <tr key={h.hospital_id}>
              <td>{h.hospital_id}</td>
              <td>{h.name}</td>
              <td><span className={`badge ${h.worst_status}`}>{STATUS_TH[h.worst_status]}</span></td>
              <td>{h.n_red}</td>
              <td>{h.n_yellow}</td>
              <td>{Math.round(h.avg_confidence * 100)}%</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan="6" className="muted">ไม่พบโรงพยาบาลที่ตรงเงื่อนไข</td></tr>
          )}
        </tbody>
      </table>
      <Pagination {...paged} />
    </div>
  );
}
