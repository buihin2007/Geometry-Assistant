import { useState } from "react";
import { sendReport } from "../api.js";

// Báo hình SAI / góp ý — bắt lỗi im lặng (app vẽ ra nhưng sai quan hệ) mà auto-log
// không thấy. Gửi kèm commands để tái hiện tất định. Không gửi ảnh (nhẹ).
const CATEGORIES = [
  { key: "ve_sai", label: "Vẽ sai quan hệ" },
  { key: "khong_ve_duoc", label: "Không vẽ được" },
  { key: "bo_cuc", label: "Bố cục xấu" },
  { key: "khac", label: "Khác" },
];

export default function ReportPanel({ problem, commands, meta }) {
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("ve_sai");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState(""); // "", "sending", "done", "error"

  if (!commands || commands.length === 0) return null;

  const submit = async () => {
    setStatus("sending");
    try {
      await sendReport({
        problem_text: problem,
        commands,
        category,
        note,
        review_passed: meta?.reviewPassed ?? null,
        warnings: meta?.warnings || [],
      });
      setStatus("done");
      setNote("");
      setTimeout(() => {
        setOpen(false);
        setStatus("");
      }, 1500);
    } catch (e) {
      setStatus("error");
    }
  };

  if (!open) {
    return (
      <button className="report-toggle" onClick={() => setOpen(true)}>
        ⚠ Báo hình sai / góp ý
      </button>
    );
  }

  return (
    <div className="report-panel">
      <div className="report-cats">
        {CATEGORIES.map((c) => (
          <button
            key={c.key}
            className={"chip" + (category === c.key ? " chip-active" : "")}
            onClick={() => setCategory(c.key)}
          >
            {c.label}
          </button>
        ))}
      </div>
      <textarea
        className="report-note"
        rows={2}
        placeholder="Mô tả ngắn chỗ sai (vd: 'A trùng N', 'thiếu tiếp tuyến')…"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="report-actions">
        <button className="primary" disabled={status === "sending"} onClick={submit}>
          {status === "sending" ? "Đang gửi…" : "Gửi góp ý"}
        </button>
        <button onClick={() => setOpen(false)}>Hủy</button>
        {status === "done" && <span className="info-text">Cảm ơn đã góp ý! 🙏</span>}
        {status === "error" && <span className="error-text">Gửi lỗi, thử lại.</span>}
      </div>
    </div>
  );
}
