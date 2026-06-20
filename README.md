# Trợ lý vẽ hình học phẳng (GeoGebra + LLM)

Web app cho giáo viên THCS nhập đề hình học phẳng bằng **tiếng Việt tự nhiên** và nhận
lại **hình vẽ đúng quan hệ, kéo thả tinh chỉnh, xuất file** (PNG/SVG/PDF/.ggb).

Nguyên tắc cốt lõi: **LLM mô tả quan hệ, KHÔNG đoán tọa độ.** LLM sinh *lệnh dựng
GeoGebra*; engine GeoGebra tự tính cấu hình thỏa mãn quan hệ. Xem `PLAN.md` để biết
toàn bộ thiết kế và quyết định.

## Kiến trúc

```
frontend (React+Vite)  ──HTTP──►  orchestrator (FastAPI)  ──HTTP──►  ggb-service (Node+Playwright)
   │ GeoGebra applet                │ pipeline agent                   │ GeoGebra headless render
   │ (kéo thả + export)             │ + Supabase (auth/DB)             │ → per-command status + PNG/SVG/.ggb
```

- **`frontend/`** — SPA tĩnh. Trái: chat nhập đề. Phải: GeoGebra applet (kéo thả) + export. Auth + thư viện.
- **`orchestrator/`** — FastAPI. Mặc định kiến trúc **planner + compiler** (xem dưới): Planner (LLM) → Plan validator → Compiler tất định → Technical/relation Validator → Reviewer (LLM vision). Vòng sửa `MAX_FIX_ROUNDS`, trần `MAX_LLM_CALLS_PER_REQUEST`. Gating demo theo IP. Supabase.
- **`ggb-service/`** — Express + Playwright. `POST /render`: nạp lệnh vào GeoGebra headless, ẩn đối tượng `aux*`, đánh giá `checks` (assert quan hệ), trả trạng thái từng lệnh + ảnh.
- **`supabase/schema.sql`** — bảng `figures` (lưu lệnh text, RLS) + `demo_usage` (2 lượt/IP).

### Kiến trúc planner + thư viện primitive (THCS_construction_library_spec)

Thay vì để LLM viết lệnh GeoGebra thô (dễ sai cú pháp), hệ tách đôi:

```
Đề → PLANNER (LLM, chọn primitive từ menu đóng) → PLAN (JSON DSL)
   → VALIDATE PLAN (tất định: op/ref/tham số/vòng)
   → COMPILER (tất định, KHÔNG LLM): bung mỗi primitive ra template ĐÃ VERIFY
   → render → VALIDATOR quan hệ (IsTangent/AreCollinear/... qua GeoGebra) → Reviewer
```

- **`app/primitives/registry.py`** — ~53 primitive THCS, mỗi cái là template GeoGebra đã **verify trên applet thật** rồi khóa vào `primitives_verified.json`. LLM không bao giờ viết cú pháp ⇒ hết lỗi cú pháp.
- **`app/primitives/compiler.py`** — validate plan + compile plan → lệnh + asserts. Tự đặt tên `aux*` (tự ẩn).
- **`app/agents/planner.py`** — LLM chỉ chọn primitive & nối tham chiếu; có **escape hatch** `RAW` → rớt về Generator lệnh-thô khi gặp thao tác chưa có primitive (ghi log để bổ sung).
- Verify primitive: `python -m scripts.verify_primitives` (cần ggb-service). "Verified = đúng mãi."
- Coverage/regression THCS: `python -m scripts.coverage_test`.
- Tắt kiến trúc này (về generator thô): `USE_PLANNER=false`.

## Pipeline một yêu cầu (PLAN §5)

1. Frontend POST `/generate` (kèm JWT nếu đã đăng nhập).
2. Gating: đã đăng nhập → bỏ giới hạn; demo → kiểm IP (≥2 lượt → 429).
3. Generator: đề → JSON lệnh GeoGebra.
4. ggb-service render → trạng thái từng lệnh + object inspection + PNG.
5. Technical Validator: bắt lỗi cứng (lệnh fail, object undefined, tam giác suy biến, R≤0) → feed lại Generator.
6. Reviewer (vision): nhìn PNG + đề → `pass` hoặc gợi ý sửa.
7. Lặp tối đa `MAX_FIX_ROUNDS`; trả lệnh cuối + ảnh cho frontend.

## Chạy local

### Cách 1 — Docker Compose (cả 3 service)

```bash
cp .env.example .env          # điền LLM_API_KEY, (tùy chọn) Supabase
docker compose up --build
# frontend: http://localhost:5173   orchestrator: http://localhost:8080
```

> Lưu ý: biến `VITE_*` được nhúng lúc build frontend. Khi build qua compose, truyền
> chúng làm build args nếu cần Supabase ở client (xem `frontend/Dockerfile`).

### Cách 2 — chạy từng service (dev)

```bash
# 1) ggb-service (Node 20+)
cd ggb-service && npm install && GGB_SERVICE_PORT=8081 npm start

# 2) orchestrator (Python 3.12+)
cd orchestrator && py -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt
GGB_SERVICE_URL=http://localhost:8081 LLM_PROVIDER=mock ./.venv/Scripts/python -m uvicorn app.main:app --port 8080

# 3) frontend (Node 20+)
cd frontend && npm install && cp .env.example .env && npm run dev
```

`LLM_PROVIDER=mock` cho phép chạy **offline không cần API key** (sinh lệnh tam giác mẫu,
review luôn pass) — tiện smoke test cả pipeline.

## Cấu hình (xem `.env.example` và PLAN §13)

- **LLM**: `LLM_PROVIDER` (`gemini`|`groq`|`openrouter`|`mock`), `LLM_API_KEY`, `LLM_MODEL`.
  Có thể tách `GENERATOR_*` (vd Groq, text) và `REVIEWER_*` (vd Gemini, vision) để tiết kiệm quota.
- **Trần chi phí**: `ENABLE_REVIEW`, `MAX_FIX_ROUNDS=3`, `MAX_LLM_CALLS_PER_REQUEST=8`.
- **Supabase**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. Để trống → chạy chế độ demo (gating đếm trong RAM, không có thư viện).
- **Demo**: `DEMO_LIMIT_PER_IP=2` (vĩnh viễn).

### Đổi sang Gemini thật

```
LLM_PROVIDER=gemini
LLM_API_KEY=<key Google AI Studio>
LLM_MODEL=gemini-2.5-flash      # model có vision
```

Provider được bọc sau interface chung (`orchestrator/app/llm/`), đổi provider/model
**không cần sửa logic pipeline** (PLAN §4.1).

## Triển khai (PLAN §4.2)

- **frontend**: host tĩnh free (Cloudflare Pages / Vercel) — build `frontend/`.
- **orchestrator + ggb-service**: container scale-to-zero, ưu tiên **Google Cloud Run**
  (chạy được headless Chromium; KHÔNG dùng Vercel functions cho Playwright). Mỗi service
  có `Dockerfile` riêng. Chấp nhận cold start; frontend đã có UX "đang khởi động máy vẽ".

## Trạng thái build (PLAN §12)

| Phase | Nội dung | Trạng thái |
|---|---|---|
| 0 | Scaffold monorepo, compose, schema | ✅ |
| 1 | ggb-service render (per-command status + PNG/SVG/.ggb) | ✅ đã test VD1–VD4 |
| 2–3 | Generator + Technical Validator + vòng sửa | ✅ |
| 4 | Frontend (chat + applet kéo thả + export) | ✅ |
| 5 | Reviewer vision + `ENABLE_REVIEW` | ✅ |
| 6–7 | Supabase auth/thư viện + gating IP | ✅ (cần Supabase thật để dùng thư viện) |
| 8 | Cứng hóa: trần chi phí, mở golden set 20–30, ping Supabase | ⏳ một phần (trần chi phí xong) |

## Việc còn lại (PLAN §8, §14)

- Mở rộng golden set lên 20–30 cặp và chạy như **test hồi quy** (hiện có 4 cặp đã verify).
- Ping định kỳ giữ Supabase khỏi pause 7 ngày.
- Xác nhận tên model Gemini vision cụ thể + có tách Groq cho Generator không (PLAN §14.1).
- Quy ước nhãn/màu tiếng Việt trong prompt Generator (PLAN §14.6).
