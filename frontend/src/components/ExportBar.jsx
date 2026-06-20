import { useState } from "react";
import { jsPDF } from "jspdf";

// Thanh export (PLAN §10): PNG nền trong, copy clipboard, SVG, PDF, .ggb.

function downloadDataUrl(dataUrl, filename) {
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function downloadText(text, filename, mime) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  downloadDataUrl(url, filename);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function ExportBar({ ggbRef }) {
  const [msg, setMsg] = useState("");

  const flash = (t) => {
    setMsg(t);
    setTimeout(() => setMsg(""), 2000);
  };

  const exportPNG = () => {
    const b64 = ggbRef.current?.getPNG();
    if (!b64) return flash("Chưa có hình.");
    downloadDataUrl(`data:image/png;base64,${b64}`, "hinh.png");
  };

  const copyPNG = async () => {
    const b64 = ggbRef.current?.getPNG();
    if (!b64) return flash("Chưa có hình.");
    try {
      const res = await fetch(`data:image/png;base64,${b64}`);
      const blob = await res.blob();
      await navigator.clipboard.write([
        new ClipboardItem({ "image/png": blob }),
      ]);
      flash("Đã copy ảnh — dán vào Word được.");
    } catch (e) {
      flash("Trình duyệt không cho copy ảnh; hãy tải PNG.");
    }
  };

  const exportSVG = async () => {
    const svg = await ggbRef.current?.getSVG();
    if (!svg) return flash("Chưa có hình.");
    downloadText(svg, "hinh.svg", "image/svg+xml");
  };

  const exportPDF = () => {
    const b64 = ggbRef.current?.getPNG();
    if (!b64) return flash("Chưa có hình.");
    const img = new Image();
    img.onload = () => {
      const pdf = new jsPDF({
        orientation: img.width >= img.height ? "landscape" : "portrait",
        unit: "pt",
        format: [img.width, img.height],
      });
      pdf.addImage(`data:image/png;base64,${b64}`, "PNG", 0, 0, img.width, img.height);
      pdf.save("hinh.pdf");
    };
    img.src = `data:image/png;base64,${b64}`;
  };

  const exportGGB = () => {
    const b64 = ggbRef.current?.getGGB();
    if (!b64) return flash("Chưa có hình.");
    downloadDataUrl(`data:application/vnd.geogebra.file;base64,${b64}`, "hinh.ggb");
  };

  return (
    <div className="export-bar">
      <button onClick={exportPNG}>PNG</button>
      <button onClick={copyPNG}>Copy ảnh</button>
      <button onClick={exportSVG}>SVG</button>
      <button onClick={exportPDF}>PDF</button>
      <button onClick={exportGGB}>.ggb</button>
      {msg && <span className="export-msg">{msg}</span>}
    </div>
  );
}
