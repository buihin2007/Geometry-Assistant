import { useEffect, useRef, useState } from "react";
import { generate, saveFigure } from "./api.js";
import { supabase, supabaseConfigured } from "./supabase.js";
import GeoGebraView from "./components/GeoGebraView.jsx";
import ExportBar from "./components/ExportBar.jsx";
import AuthBar from "./components/AuthBar.jsx";
import Library from "./components/Library.jsx";
import ReportPanel from "./components/ReportPanel.jsx";

const EXAMPLES = [
  "Vẽ tam giác ABC, kẻ đường cao AH xuống BC",
  "Tam giác ABC nội tiếp đường tròn tâm O",
  "Tam giác ABC với đường tròn nội tiếp tâm I",
  "Vẽ ba trung tuyến của tam giác ABC, xác định trọng tâm G",
];

export default function App() {
  const [problem, setProblem] = useState("");
  const [commands, setCommands] = useState(null);
  const [loading, setLoading] = useState(false);
  const [slow, setSlow] = useState(false); // cold start UX
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [resultMeta, setResultMeta] = useState(null); // {reviewPassed, warnings} cho report
  const [session, setSession] = useState(null);
  const [libRefresh, setLibRefresh] = useState(0);
  const [gridVisible, setGridVisible] = useState(true); // lưới ô vuông (người dùng tắt được)
  const ggbRef = useRef(null);

  // Theo dõi phiên đăng nhập Supabase.
  useEffect(() => {
    if (!supabaseConfigured) return;
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) =>
      setSession(s)
    );
    return () => sub.subscription.unsubscribe();
  }, []);

  const token = session?.access_token;

  const onGenerate = async (text) => {
    const q = (text ?? problem).trim();
    if (!q) return;
    setLoading(true);
    setSlow(false);
    setError("");
    setInfo("");
    // Cold start (PLAN §4.2): nếu lâu, báo "đang khởi động máy vẽ".
    const slowTimer = setTimeout(() => setSlow(true), 4000);
    try {
      const res = await generate(q, ["png", "svg", "ggb"], token);
      setCommands(res.commands);
      setResultMeta({ reviewPassed: res.reviewPassed, warnings: res.warnings || [] });
      const parts = [];
      if (res.reviewPassed === false)
        parts.push("Hình có thể chưa hoàn hảo (review chưa đạt).");
      if (res.warnings?.length) parts.push(res.warnings.join(" "));
      if (typeof res.remaining === "number")
        parts.push(`Còn ${res.remaining} lượt dùng thử.`);
      setInfo(parts.join(" "));
    } catch (e) {
      if (e.status === 429) {
        setError(e.message + " (Đăng ký tài khoản để dùng tiếp.)");
      } else {
        setError(e.message || "Có lỗi xảy ra.");
      }
    } finally {
      clearTimeout(slowTimer);
      setLoading(false);
      setSlow(false);
    }
  };

  const onSave = async () => {
    if (!token || !commands) return;
    try {
      await saveFigure(
        {
          title: problem.slice(0, 60),
          problem_text: problem,
          commands,
        },
        token
      );
      setInfo("Đã lưu vào thư viện.");
      setLibRefresh((k) => k + 1);
    } catch (e) {
      setError(e.message);
    }
  };

  const loadFromLibrary = (fig) => {
    setProblem(fig.problem_text);
    setCommands(fig.commands);
    setInfo(`Đã mở: ${fig.title || fig.problem_text.slice(0, 30)}`);
  };

  return (
    <div className="app">
      <header className="topbar">
        <h1>✏️ Trợ lý vẽ hình học phẳng</h1>
        <AuthBar session={session} />
      </header>

      <div className="layout">
        {/* Trái: chat nhập đề */}
        <aside className="panel left">
          <label className="field-label">Nhập đề hình học (tiếng Việt)</label>
          <textarea
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            placeholder="VD: Vẽ tam giác ABC, kẻ đường cao AH xuống BC"
            rows={4}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onGenerate();
            }}
          />
          <button className="primary" disabled={loading} onClick={() => onGenerate()}>
            {loading ? "Đang vẽ…" : "Vẽ hình"}
          </button>

          {loading && slow && (
            <div className="notice">
              ⏳ Đang khởi động máy vẽ, lần đầu hơi lâu (vài chục giây)…
            </div>
          )}
          {error && <div className="error-box">{error}</div>}
          {info && <div className="info-box">{info}</div>}

          <div className="examples">
            <div className="muted">Ví dụ nhanh:</div>
            {EXAMPLES.map((ex) => (
              <button key={ex} className="chip" onClick={() => { setProblem(ex); onGenerate(ex); }}>
                {ex}
              </button>
            ))}
          </div>

          {token && commands && (
            <button className="secondary" onClick={onSave}>
              💾 Lưu vào thư viện
            </button>
          )}

          <Library token={token} onLoad={loadFromLibrary} refreshKey={libRefresh} />
        </aside>

        {/* Phải: applet GeoGebra + export */}
        <main className="panel right">
          <label className="grid-toggle">
            <input
              type="checkbox"
              checked={gridVisible}
              onChange={(e) => setGridVisible(e.target.checked)}
            />
            Hiện lưới
          </label>
          <GeoGebraView ref={ggbRef} commands={commands} gridVisible={gridVisible} />
          <ExportBar ggbRef={ggbRef} />
          <ReportPanel problem={problem} commands={commands} meta={resultMeta} />
          {commands && (
            <details className="cmd-dump">
              <summary>Lệnh dựng ({commands.length})</summary>
              <pre>{commands.join("\n")}</pre>
            </details>
          )}
        </main>
      </div>
    </div>
  );
}
