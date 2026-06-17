import { useState, useMemo } from "react";

const PAGE_SIZES = [5, 10, 25, 50, 100];

// hook: แบ่งหน้า array ฝั่ง client (ปรับจำนวนแถว/หน้าได้)
export function usePaged(items, initialSize = 10) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeRaw] = useState(initialSize);
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const cur = Math.min(page, pages);
  const slice = useMemo(
    () => items.slice((cur - 1) * pageSize, cur * pageSize),
    [items, cur, pageSize]
  );
  const setPageSize = (s) => { setPageSizeRaw(s); setPage(1); };
  return { slice, page: cur, pages, total, setPage, pageSize, setPageSize };
}

export default function Pagination({ page, pages, total, setPage, pageSize, setPageSize }) {
  if (total === 0) return null;
  return (
    <div className="pager">
      {setPageSize && (
        <span className="muted">
          แสดง
          <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          /หน้า
        </span>
      )}
      <button className="pg-btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹ ก่อนหน้า</button>
      <span className="muted">หน้า {page} / {pages} ({total} รายการ)</span>
      <button className="pg-btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>ถัดไป ›</button>
    </div>
  );
}
