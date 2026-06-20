# Kế hoạch deploy

Mục tiêu: đưa app lên cho ~20 giáo viên test + thu feedback, chi phí thấp, chấp nhận
cold start. Kiến trúc 3 phần (xem README): **frontend tĩnh** + **orchestrator** +
**ggb-service**. Hai backend chạy container; frontend là SPA tĩnh.

> Tôi KHÔNG tự deploy được vì cần tài khoản cloud + đăng nhập tương tác của bạn. Tài
> liệu này là các bước bạn chạy (lệnh interactive như login dùng `! <lệnh>` trong phiên).

---

## 0. Quyết định cần chốt trước

| Hạng mục | Lựa chọn | Khuyến nghị cho vòng test |
|---|---|---|
| Host 2 backend | Render / Cloud Run / Railway·Fly / VPS | **Render** (ít ma sát nhất) hoặc **VPS** (không cold start) |
| Host frontend | Cloudflare Pages / Vercel / cùng host | **Cloudflare Pages** hoặc Vercel |
| Supabase (login + thư viện + report bền) | bật giờ / demo-only trước | **Demo-only trước**, trừ khi cần lưu report bền (xem §5) |
| LLM | Anthropic (đang dùng) | Giữ Anthropic Claude Haiku 4.5 (nhanh, rate-limit cao, có vision) |

---

## 1. Hai điểm BẮT BUỘC nhớ (hay làm hỏng deploy)

1. **ggb-service cần RAM ≥ 1 GB** (headless Chromium). Mặc định 512 MB sẽ OOM/crash.
   Đặt 1–2 GB cho service render.
2. **`VITE_API_URL` nhúng lúc BUILD frontend.** Phải set = URL orchestrator đã deploy
   *trước khi build*, nếu không frontend gọi localhost.

---

## 2. ĐÃ CHỌN — Cloud Run (backend, scale-to-zero ~$0) + Cloudflare Pages (frontend)

Lý do chọn Cloud Run thay Render: Render scale-to-zero **chỉ có ở plan free 512MB** —
mà ggb-service (Chromium) cần ≥1GB → buộc lên plan trả phí **luôn-bật ~$32/tháng**.
Cloud Run cho **scale-to-zero THẬT + RAM 2GB**, rảnh là ~$0 (trả theo request-second;
~20 user test gần như miễn phí trong free tier). Đánh đổi: cold start (đã có UX xử lý).

Cổng `$PORT` đã sửa cho cả 2 service. `GGB_SERVICE_URL` script tự nối.

### 2a. Backend — script `deploy-cloudrun.sh` (cả 2 service)
Cần `gcloud` CLI + 1 GCP project (tạo ở https://console.cloud.google.com, bật billing —
vẫn ~$0 trong free tier). Trong phiên này:
```
! gcloud auth login
! bash deploy-cloudrun.sh <GCP_PROJECT_ID>
```
Script: bật API → deploy ggb-service (2Gi, `--no-cpu-throttling`, scale-to-zero) →
deploy orchestrator (512Mi) với env (Anthropic + Supabase + GGB_SERVICE_URL + `DEMO_LIMIT_PER_IP=2`)
đọc từ `.env` → in ra **ggb URL** + **orchestrator URL**. Lần đầu build (Cloud Build) vài phút.
- Secret KHÔNG nằm trong script (đọc `.env`). Nâng cấp prod: chuyển sang **Secret Manager**
  (`--update-secrets`) thay vì `--set-env-vars`.
- Region mặc định `asia-southeast1` (Singapore); đổi qua `REGION=... bash deploy-cloudrun.sh ...`.

> Fallback (nếu ngại gcloud, chấp nhận ~$32/tháng luôn-bật, KHÔNG cold start):
> `render.yaml` vẫn còn trong repo → Render → New → Blueprint. Xem cuối file.

### 2b. Frontend — Cloudflare Pages
1. Pages → **Create → Connect to Git** → repo này.
2. Build config: **Root directory** `frontend`, **Build command** `npm run build`,
   **Output** `dist`.
3. **Environment variables (Production)** — nhúng lúc build:
   - `VITE_API_URL` = URL orchestrator ở 2a (vd `https://orchestrator-xxx.onrender.com`)
   - `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (anon — public, OK)
4. Deploy → URL, vd `https://hinhhoc.pages.dev`.

### 2c. Supabase — cho phép đăng nhập từ domain prod (BẮT BUỘC nếu dùng login)
Supabase → **Authentication → URL Configuration**:
- **Site URL** = URL Cloudflare Pages.
- **Redirect URLs** = thêm URL Cloudflare Pages (cho xác nhận email/redirect).
Nếu chưa làm: đăng nhập/đăng ký từ domain prod sẽ lỗi redirect.

> Render free/starter ngủ khi rảnh → request đầu dính 2 cold start (orchestrator + ggb);
> frontend đã có UX "đang khởi động máy vẽ". Hết cold start hẳn: VPS luôn-bật (§3).

---

## 3. Phương án B — VPS luôn-bật (không cold start)

Hetzner CX22 (~$4–5/tháng) chạy cả stack bằng Docker Compose:
```bash
# trên VPS:
git clone <repo> && cd hin_ve_hinh
cp .env.example .env   # điền key LLM (+ Supabase nếu dùng)
# build frontend với VITE_API_URL trỏ domain orchestrator (sửa compose build args)
docker compose up -d --build
```
Thêm Caddy/nginx reverse-proxy + TLS cho domain. Ưu: đơn giản, luôn ấm. Nhược: tự quản máy.

## 3'. Phương án C — Cloud Run (đúng PLAN §4.2)
- `gcloud auth login` (chạy bằng `! gcloud auth login`), tạo project.
- Mỗi backend: `gcloud run deploy ggb-service --source ggb-service --memory 2Gi
  --allow-unauthenticated` ; tương tự orchestrator (`--memory 512Mi`, set env).
- Scale-to-zero thật, free tier rộng. Cấu hình nhiều hơn Render.

---

## 4. Biến môi trường (orchestrator)

```
# LLM (đang dùng Anthropic)
LLM_PROVIDER=anthropic
LLM_API_KEY=<anthropic key>
LLM_MODEL=claude-haiku-4-5
GENERATOR_PROVIDER=anthropic   GENERATOR_MODEL=claude-haiku-4-5   GENERATOR_API_KEY=<key>
REVIEWER_PROVIDER=anthropic    REVIEWER_MODEL=claude-haiku-4-5    REVIEWER_API_KEY=<key>
ENABLE_REVIEW=true
MAX_FIX_ROUNDS=2
MAX_LLM_CALLS_PER_REQUEST=8
USE_PLANNER=true

GGB_SERVICE_URL=<URL ggb-service>
DEMO_LIMIT_PER_IP=2            # prod: 2 (vĩnh viễn) theo PLAN §9

# Supabase (chỉ khi bật §5)
SUPABASE_URL=   SUPABASE_ANON_KEY=   SUPABASE_SERVICE_ROLE_KEY=
```
Frontend (build-time): `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

> KHÔNG commit key. Đặt trong dashboard env của host. Key Anthropic/Gemini đang trong
> `.env` local (gitignored) → rotate nếu từng lộ.

---

## 5. Lưu trữ report & fail-log khi deploy (QUAN TRỌNG)

Hiện report ghi `logs/reports.jsonl`, fail-log ghi `logs/failed_problems.jsonl`.
- **VPS luôn-bật:** file OK (ổ đĩa bền) — không cần làm gì.
- **Serverless (Render/Cloud Run scale-to-zero):** file **MẤT** khi instance ngủ/tái tạo
  → report bay mất. Muốn giữ report thì **bật Supabase** và ghi vào bảng `reports`
  (đã có sẵn trong `supabase/schema.sql`).
  - Việc cần làm (nhỏ): trong `orchestrator/app/main.py` `/report`, thay đoạn ghi file
    bằng insert vào Supabase `reports` qua service_role (mẫu có sẵn ở `supabase_client.py`).
    Có thể bọc: nếu có `SUPABASE_*` → ghi DB, không thì ghi file (fallback).
  - Tương tự cho fail-log nếu muốn giữ.

→ **Đây là đánh đổi đã bàn:** muốn report sống trong prod serverless thì phải kéo Supabase
lên sớm. Nếu chưa, chọn VPS (file bền) hoặc chấp nhận report chỉ dùng khi dev local.

---

## 6. Supabase (nếu bật login + thư viện + report bền)
1. Tạo project Supabase → lấy `SUPABASE_URL`, `anon`, `service_role`.
2. SQL editor → chạy `supabase/schema.sql` (tạo `figures`, `demo_usage`, `reports` + RLS).
3. Điền env orchestrator + build env frontend.
4. Bật ping định kỳ chống pause 7 ngày (vd cron gọi `/health` hoặc 1 query nhẹ).

---

## 7. Chi phí & an toàn
- **Host:** ~$0 khi rảnh (scale-to-zero) hoặc ~$4–5/tháng VPS.
- **LLM:** tốn theo lượt. Claude Haiku 4.5 rẻ; mỗi hình ~2–6 lời gọi. Kiểm soát bằng
  `MAX_LLM_CALLS_PER_REQUEST` + `DEMO_LIMIT_PER_IP=2`. Theo dõi billing Anthropic.
- **CORS:** orchestrator đang `allow_origins=["*"]` — ổn cho test; prod nên siết về
  domain frontend.

---

## 8. Checklist trước khi mở cho user
- [ ] ggb-service RAM ≥ 1 GB, `/health` xanh.
- [ ] orchestrator `/health` trả `provider`, `ggb.poolReady=true`.
- [ ] frontend build với `VITE_API_URL` đúng (mở app → vẽ 1 hình thật chạy được).
- [ ] `DEMO_LIMIT_PER_IP=2` (prod), thử vượt 2 lượt thấy 429.
- [ ] Bấm "Báo hình sai" → vào `reports` (file hoặc Supabase tùy §5).
- [ ] Nếu Supabase: đăng nhập + lưu/đọc thư viện chạy; ping chống pause.
- [ ] Rotate key LLM nếu cần; key chỉ nằm trong env host.

## 9. Sau khi deploy — vòng feedback
- Định kỳ đọc `reports` (đặc biệt `category=ve_sai` — lỗi im lặng).
- Mỗi report đáng giá: lấy `commands` → tái hiện bằng `scripts/coverage_plans.py` style
  → sửa primitive/planner → thêm 1 dòng regression → đánh dấu `resolved=true`.
- Đây là cơ chế mở rộng độ phủ theo thời gian (đúng tinh thần spec).
