import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  forwardRef,
  useState,
} from "react";

// Nhúng GeoGebra applet (PLAN §7.1): nạp lệnh, cho kéo thả điểm tự do, export.
// deployggb.js được load ở index.html → window.GGBApplet có sẵn.
//
// Yêu cầu responsive:
//  - wrapper chiếm 100% W/H container cha;
//  - applet luôn khít container (ResizeObserver → setWidth/setHeight);
//  - sau khi nạp construction, fit khung nhìn vào hình (ZoomFit + lề, giữ tỉ lệ 1:1).

const FIT_PADDING = 1.15; // 15% lề quanh hình
const MIN_DIM = 200;

// Parse phương trình đường tròn GeoGebra → {cx, cy, r}.
// Dạng: "circ: (x - 3)² + (y - 1.7)² = 11.89" (vế phải là r²).
// (x - a) ⇒ tâm +a; (x + a) ⇒ tâm -a; thiếu hạng (x²) ⇒ tâm 0.
function parseCircle(valueString) {
  if (!valueString) return null;
  const body = valueString.includes(":")
    ? valueString.slice(valueString.indexOf(":") + 1)
    : valueString;
  const rhs = body.match(/=\s*(-?[\d.]+(?:[eE][+-]?\d+)?)\s*$/);
  if (!rhs) return null;
  const r2 = parseFloat(rhs[1]);
  if (!(r2 > 0)) return null;
  const xm = body.match(/x\s*([+-])\s*([\d.]+)\s*\)/);
  const ym = body.match(/y\s*([+-])\s*([\d.]+)\s*\)/);
  const cx = xm ? (xm[1] === "-" ? +xm[2] : -+xm[2]) : 0;
  const cy = ym ? (ym[1] === "-" ? +ym[2] : -+ym[2]) : 0;
  return { cx, cy, r: Math.sqrt(r2) };
}

const GeoGebraView = forwardRef(function GeoGebraView({ commands, gridVisible = true }, ref) {
  const wrapRef = useRef(null); // hộp đo kích thước (khít container cha)
  const targetRef = useRef(null); // chỗ inject applet
  const appletRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState(false); // applet không khởi tạo được
  const [retry, setRetry] = useState(0); // bấm "thử lại" → chạy lại effect khởi tạo

  // Đồng bộ kích thước applet đúng bằng kích thước container hiện tại.
  // GeoGebra bọc applet trong .applet_scaler và TỰ áp transform:scale khi window
  // resize → chỏi với việc fill của ta. Nên: (1) gỡ transform + ép scaler đầy
  // container, (2) setWidth/setHeight để GeoGebraFrame (canvas) đúng kích thước px.
  const sizeToContainer = useCallback(() => {
    const api = appletRef.current;
    const wrap = wrapRef.current;
    if (!api || !wrap) return;
    const w = Math.max(MIN_DIM, Math.floor(wrap.clientWidth));
    const h = Math.max(MIN_DIM, Math.floor(wrap.clientHeight));
    const scaler = wrap.querySelector(".applet_scaler");
    if (scaler) {
      scaler.style.transform = "none";
      scaler.style.transformOrigin = "0 0";
      scaler.style.width = w + "px";
      scaler.style.height = h + "px";
    }
    try {
      api.setWidth(w);
      api.setHeight(h);
    } catch (e) {}
  }, []);

  // Fit khung nhìn vào hình (GeoGebra applet KHÔNG có ZoomFit/getXmin nên tự tính):
  //  1) Tính bounding box: điểm qua getXcoord/getYcoord; đường tròn parse từ
  //     getValueString "(x - a)² + (y - b)² = r²" để lấy tâm + bán kính.
  //  2) setCoordSystem với tỉ lệ ĐỒNG NHẤT 2 trục (unitX == unitY) khớp khung
  //     hình chữ nhật của container ⇒ tròn vẫn tròn, hình cân giữa, có lề.
  const fitView = useCallback(() => {
    const api = appletRef.current;
    const wrap = wrapRef.current;
    if (!api || !wrap) return;

    // Tỉ lệ phải tính theo vùng ĐỒ HỌA thật, không phải cả wrap (nếu không tròn
    // sẽ thành elip). Algebra đã ẩn ⇒ graphics rộng = wrap; cao = wrap - toolbar.
    // Đọc từ DOM (đồng bộ) thay vì đo canvas (resize bất đồng bộ, hay đọc nhầm).
    const toolbar = wrap.querySelector(".ggbtoolbarpanel");
    const tb = toolbar ? toolbar.offsetHeight : 0;
    const W = Math.max(MIN_DIM, wrap.clientWidth);
    const H = Math.max(MIN_DIM, wrap.clientHeight - tb);

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    let found = false;
    const add = (x, y) => {
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      found = true;
    };

    for (const name of api.getAllObjectNames()) {
      let type = "";
      try { type = api.getObjectType(name); } catch (e) { continue; }
      if (type === "point") {
        try { add(api.getXcoord(name), api.getYcoord(name)); } catch (e) {}
      } else if (type === "circle" || type === "conic") {
        let vs = "";
        try { vs = api.getValueString(name); } catch (e) { continue; }
        const c = parseCircle(vs);
        if (c) { add(c.cx - c.r, c.cy - c.r); add(c.cx + c.r, c.cy + c.r); }
      }
    }
    if (!found) return;

    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    // chống chia 0 với hình "phẳng" (mọi điểm thẳng hàng ngang/dọc)
    const bw = Math.max(maxX - minX, 1e-6);
    const bh = Math.max(maxY - minY, 1e-6);
    // đơn vị toán/pixel: lấy trục chật hơn để mọi thứ lọt, nhân lề.
    const unit = Math.max((bw * FIT_PADDING) / W, (bh * FIT_PADDING) / H);
    const halfW = (unit * W) / 2;
    const halfH = (unit * H) / 2;
    try {
      api.setCoordSystem(cx - halfW, cx + halfW, cy - halfH, cy + halfH);
    } catch (e) {}
  }, []);

  // GeoGebra resize canvas BẤT ĐỒNG BỘ sau setWidth/setHeight → fit ngay sẽ đọc
  // nhầm kích thước cũ (hình bị tràn/clip). Fit lại nhiều lần qua các mốc thời gian:
  // lần sớm cho phản hồi nhanh, lần muộn dùng kích thước canvas đã ổn định.
  const fitTimersRef = useRef([]);
  const scheduleFit = useCallback(() => {
    fitTimersRef.current.forEach(clearTimeout);
    fitTimersRef.current = [60, 180, 360, 650].map((d) =>
      setTimeout(() => {
        if (appletRef.current) fitView();
      }, d)
    );
  }, [fitView]);

  const loadCommands = useCallback(
    (api, cmds) => {
      api.reset();
      api.newConstruction();
      for (const cmd of cmds) {
        try {
          api.evalCommand(cmd);
        } catch (e) {
          console.warn("evalCommand lỗi:", cmd, e);
        }
      }
      // Ẩn đối tượng phụ (aux*) + BẬT NHÃN cho các đối tượng hiển thị có tên
      // (điểm/đoạn/đường tròn). Frontend mặc định tạo điểm với nhãn TẮT nên phải
      // bật tay (spec yêu cầu hiện tên điểm). Điểm tự do vẫn kéo thả được.
      try {
        for (const name of api.getAllObjectNames()) {
          if (String(name).toLowerCase().startsWith("aux")) {
            api.setVisible(name, false);
          } else if (api.getObjectType(name) === "point") {
            api.setLabelVisible(name, true); // hiện TÊN ĐIỂM
          } else {
            api.setLabelVisible(name, false); // ẩn nhãn đa giác/đoạn (tri,a,b,AH...) cho gọn
          }
        }
      } catch (e) {}
      fitView();
    },
    [fitView]
  );

  // Khởi tạo applet với kích thước theo container THẬT.
  useEffect(() => {
    let cancelled = false;
    let settled = false; // đã xong (ready) HOẶC đã báo lỗi → không xử lý nữa

    // Thoát trạng thái "đang tải" khi thất bại — DÙ nguyên nhân là gì: script
    // deployggb.js không tải được, HAY appletOnLoad không bao giờ chạy (engine
    // GeoGebra từ geogebra.org bị chặn/chậm ở mạng người dùng). Không để treo vô hạn.
    const fail = (why) => {
      if (cancelled || settled) return;
      settled = true;
      clearTimeout(masterTimer);
      clearInterval(poll);
      console.error("[GeoGebra] không khởi tạo được bảng vẽ:", why);
      setLoadError(true);
    };

    const injectApplet = (w, h) => {
      const params = {
        appName: "classic",
        width: w,
        height: h,
        perspective: "G", // chỉ hiện Graphics view (ẩn Algebra) → hình lấp đầy khung
        showToolBar: true,
        showAlgebraInput: false,
        showMenuBar: false,
        enableLabelDrags: true,
        enableShiftDragZoom: true,
        enableRightClick: true,
        errorDialogsActive: false,
        // KHÔNG bật allowUpscale/scaleContainerClass: chúng kích hoạt cơ chế
        // transform:scale tự động của GeoGebra, chỏi với việc setWidth/setHeight
        // để fill khít. Ta tự quản kích thước qua ResizeObserver.
        appletOnLoad: (api) => {
          if (cancelled || settled) return;
          settled = true;
          clearTimeout(masterTimer);
          clearInterval(poll);
          appletRef.current = api;
          setReady(true);
          sizeToContainer();
          try { api.setGridVisible(gridVisible); } catch (e) {}
          if (commands && commands.length) loadCommands(api, commands);
        },
      };
      try {
        // Xóa DOM applet cũ (nếu "thử lại") để không inject chồng.
        if (targetRef.current) targetRef.current.innerHTML = "";
        const applet = new window.GGBApplet(params, true);
        applet.inject(targetRef.current);
      } catch (e) {
        fail("inject ném lỗi: " + (e && e.message ? e.message : e));
      }
    };

    const init = () => {
      if (cancelled || settled) return;
      const wrap = wrapRef.current;
      const w = Math.max(MIN_DIM, Math.floor(wrap?.clientWidth || 760));
      const h = Math.max(MIN_DIM, Math.floor(wrap?.clientHeight || 620));
      injectApplet(w, h);
    };

    // Timeout TỔNG: bao trùm CẢ hai pha (chờ GGBApplet + chờ appletOnLoad). Đây là
    // điểm khác bản trước (chỉ timeout pha 1). 15s không xong ⇒ báo lỗi + cho thử lại.
    const APPLET_TIMEOUT = 15000;
    const masterTimer = setTimeout(
      () => fail(`quá ${APPLET_TIMEOUT}ms chưa khởi tạo xong (engine GeoGebra không tải được?)`),
      APPLET_TIMEOUT
    );

    // Chờ window.GGBApplet (script deployggb.js) sẵn sàng rồi mới inject.
    const STEP = 150;
    const poll = setInterval(() => {
      if (cancelled || settled) return clearInterval(poll);
      if (typeof window.GGBApplet === "function") {
        clearInterval(poll);
        init();
      }
    }, STEP);

    return () => {
      cancelled = true;
      clearTimeout(masterTimer);
      clearInterval(poll);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retry]);

  // Container đổi kích thước → resize applet + fit lại (debounce theo animation frame).
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap || typeof ResizeObserver === "undefined") return;
    let raf = 0;
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        if (!appletRef.current) return;
        sizeToContainer();
        scheduleFit(); // fit sau khi canvas settle (resize async)
      });
    });
    ro.observe(wrap);
    return () => {
      cancelAnimationFrame(raf);
      fitTimersRef.current.forEach(clearTimeout);
      ro.disconnect();
    };
  }, [sizeToContainer, scheduleFit]);

  // Nạp danh sách lệnh mỗi khi đổi (PLAN §5 bước 9).
  useEffect(() => {
    const api = appletRef.current;
    if (!ready || !api || !commands || commands.length === 0) return;
    loadCommands(api, commands);
  }, [commands, ready, loadCommands]);

  // Bật/tắt LƯỚI theo lựa chọn người dùng.
  useEffect(() => {
    const api = appletRef.current;
    if (!ready || !api) return;
    try { api.setGridVisible(gridVisible); } catch (e) {}
  }, [gridVisible, ready]);

  useImperativeHandle(ref, () => ({
    // Export phía client (PLAN §10). Trả về data/base64.
    getPNG: () => {
      const api = appletRef.current;
      if (!api) return null;
      return api.getPNGBase64(2, true, 72); // scale 2, nền trong, 72dpi
    },
    getSVG: () =>
      new Promise((resolve) => {
        const api = appletRef.current;
        if (!api) return resolve(null);
        api.exportSVG((html) => resolve(html));
      }),
    getGGB: () => {
      const api = appletRef.current;
      return api ? api.getBase64() : null;
    },
    refit: () => fitView(),
    // Lệnh hiện tại (sau khi giáo viên có thể đã chỉnh tay).
    getCurrentCommands: () => commands || [],
  }));

  return (
    <div className="ggb-wrap" ref={wrapRef}>
      {!ready && !loadError && (
        <div className="ggb-loading">Đang tải bảng vẽ GeoGebra…</div>
      )}
      {loadError && (
        <div className="ggb-loading" style={{ textAlign: "center", padding: 20 }}>
          <div style={{ marginBottom: 12 }}>
            Không tải được bảng vẽ GeoGebra.<br />
            Mạng có thể chậm hoặc bị chặn — vui lòng thử lại.
          </div>
          <button
            className="primary"
            onClick={() => {
              setLoadError(false);
              setReady(false);
              setRetry((r) => r + 1);
            }}
          >
            Thử lại
          </button>
        </div>
      )}
      <div className="ggb-target" ref={targetRef} />
    </div>
  );
});

export default GeoGebraView;
