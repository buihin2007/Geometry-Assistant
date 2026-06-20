import { useEffect, useState } from "react";
import { listFigures, deleteFigure } from "../api.js";

// Thư viện hình đã lưu (PLAN §8) — chỉ khi đã đăng nhập. Lưu LỆNH TEXT.
export default function Library({ token, onLoad, refreshKey }) {
  const [figures, setFigures] = useState([]);
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      setFigures(await listFigures(token));
    } catch (e) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    if (token) load();
  }, [token, refreshKey]);

  if (!token) return null;

  const remove = async (id) => {
    await deleteFigure(id, token);
    load();
  };

  return (
    <div className="library">
      <h3>Thư viện của tôi</h3>
      {err && <div className="error-text">{err}</div>}
      {figures.length === 0 && <div className="muted">Chưa có hình nào.</div>}
      <ul>
        {figures.map((f) => (
          <li key={f.id}>
            <button className="link" onClick={() => onLoad(f)}>
              {f.title || f.problem_text.slice(0, 40)}
            </button>
            <button className="del" onClick={() => remove(f.id)} title="Xóa">
              ✕
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
