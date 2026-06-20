import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import { GgbPool } from "./ggbPool.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Render (và nhiều PaaS) tự cấp PORT — phải lắng nghe đúng cổng đó.
const PORT = parseInt(process.env.PORT || process.env.GGB_SERVICE_PORT || "8081", 10);
const POOL_SIZE = parseInt(process.env.GGB_POOL_SIZE || "1", 10);

const app = express();
app.use(express.json({ limit: "1mb" }));

// Trang host GeoGebra được serve tĩnh; pool sẽ trỏ Playwright vào đây.
app.use("/static", express.static(path.join(__dirname, "..", "public")));

let pool = null;
let poolReady = false;

app.get("/health", (req, res) => {
  res.json({ ok: true, poolReady, poolSize: POOL_SIZE });
});

// POST /render
// body: { commands: string[], formats?: ["png","svg","pdf","ggb"] }
// trả: { perCommandStatus, objects, pngBase64, svg, ggbBase64 }
app.post("/render", async (req, res) => {
  const { commands, formats = ["png"], checks = [] } = req.body || {};
  if (!Array.isArray(commands) || commands.length === 0) {
    return res.status(400).json({ error: "commands phải là mảng không rỗng" });
  }
  if (!poolReady) {
    return res.status(503).json({ error: "render engine đang khởi động", warming: true });
  }

  try {
    const result = await pool.withPage(async (page) => {
      const perCommandStatus = await page.evaluate(
        (cmds) => window.__ggbRunCommands(cmds),
        commands
      );
      // Đánh giá assert quan hệ TRƯỚC khi ẩn aux (assert có thể tham chiếu aux).
      const checkResults = await page.evaluate(
        (cs) => window.__ggbRunChecks(cs),
        checks
      );
      // Ẩn đối tượng phụ (aux*) để ảnh render/preview không có nét thừa.
      await page.evaluate(() => window.__ggbHideAux());
      const objects = await page.evaluate(() => window.__ggbInspect());
      const exported = await page.evaluate(
        (fmts) => window.__ggbExport(fmts),
        formats
      );
      // SVG xuất qua callback nên gọi riêng.
      if (formats.includes("svg")) {
        exported.svg = await page.evaluate(() => window.__ggbExportSVG());
      }
      return { perCommandStatus, checkResults, objects, ...exported };
    });
    res.json(result);
  } catch (err) {
    console.error("[render] error:", err);
    res.status(500).json({ error: String(err && err.message ? err.message : err) });
  }
});

async function main() {
  const server = http.createServer(app);
  server.listen(PORT, () => {
    console.log(`[ggb-service] listening on :${PORT}`);
  });

  // hostUrl trỏ vào chính server này (trang tĩnh ggb.html).
  const hostUrl = `http://127.0.0.1:${PORT}/static/ggb.html`;
  pool = new GgbPool({ hostUrl, size: POOL_SIZE });
  await pool.init();
  // Khởi tạo sẵn 1 page để giảm cold start lần render đầu.
  try {
    await pool.withPage(async () => true);
  } catch (e) {
    console.warn("[ggb-service] warmup failed (sẽ thử lại khi có request):", e.message);
  }
  poolReady = true;
  console.log("[ggb-service] pool ready");

  const shutdown = async () => {
    console.log("[ggb-service] shutting down…");
    try { await pool.close(); } catch (e) {}
    server.close(() => process.exit(0));
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((e) => {
  console.error("[ggb-service] fatal:", e);
  process.exit(1);
});
