# Plan triển khai: Agent vẽ hình học phẳng bằng GeoGebra

> Tài liệu này dùng để feed cho Claude Code. Đọc toàn bộ trước khi scaffold. Code identifiers giữ tiếng Anh; mô tả tiếng Việt.

---

## 1. Mục tiêu

Web app cho **giáo viên** (chủ yếu THCS) nhập đề hình học phẳng bằng **ngôn ngữ tự nhiên tiếng Việt** và nhận lại **hình vẽ đúng quan hệ, có thể kéo thả tinh chỉnh, xuất ra file** để chèn vào tài liệu (Word/PDF).

Nguyên tắc cốt lõi: **LLM mô tả quan hệ, KHÔNG tự đoán tọa độ.** LLM sinh *lệnh dựng GeoGebra*; engine GeoGebra tự tính cấu hình tọa độ thỏa mãn quan hệ. Hình chỉ cần đúng quan hệ và cân đối, không gắn tọa độ cố định.

---

## 2. Phạm vi v1

### In-scope (mức 1 — hình THCS lớp 7–9)
- Điểm, đoạn thẳng, đường thẳng, tia.
- Tam giác và các đường/điểm đặc biệt: đường cao, trung tuyến, trung trực, phân giác; trực tâm, trọng tâm, tâm nội tiếp, tâm ngoại tiếp.
- Đường tròn: qua tâm + bán kính, qua 3 điểm (ngoại tiếp), nội tiếp tam giác.
- Tiếp tuyến cơ bản, giao điểm, trung điểm, đường song song/vuông góc.
- Nhãn điểm/đoạn, ký hiệu góc cơ bản.

### Out-of-scope (để dành cho v2+)
- Conic (elip/parabol/hypebol), quỹ tích, phép biến hình, cấu hình olympic.
- Xử lý **hàng loạt** (dán cả đề → sinh nhiều hình). v1 chỉ **một hình một lượt**.
- Đồng bộ đa thiết bị nâng cao, chia sẻ public, cộng tác realtime.

### Non-goals
- Không làm tính năng giải toán/chứng minh. Chỉ vẽ hình.
- Không tự thiết kế engine hình học — tái dùng GeoGebra.

---

## 3. Kiến trúc tổng thể

Ba thành phần + Supabase:

```
┌─────────────┐     HTTP      ┌──────────────────┐    HTTP     ┌─────────────────────┐
│  Frontend   │ ───────────►  │ Python Orchestr. │ ──────────► │ Node GeoGebra svc   │
│ (web app)   │ ◄───────────  │  (bộ não/agents) │ ◄────────── │ (headless render)   │
└─────────────┘               └──────────────────┘             └─────────────────────┘
      │                                │
      │ GeoGebra applet (kéo thả)      │ Supabase (Auth + Postgres + Storage)
      └────────────────────────────────┘
```

- **Frontend**: web app. Bên trái khung chat nhập đề; bên phải **GeoGebra applet nhúng** (deployggb / GeoGebra Math Apps API) để hiện hình và cho giáo viên kéo thả chỉnh tay. Nút export. Đăng nhập qua Supabase Auth. Quản thư viện hình (khi đã đăng nhập).
- **Python Orchestrator**: "bộ não". Chạy pipeline các agent (Generator → Technical Validator → Reviewer), gọi Node service để render, gọi LLM API, áp gating demo theo IP, đọc/ghi Supabase.
- **Node GeoGebra service**: service nhỏ chỉ làm một việc — nhận một danh sách lệnh GeoGebra, nạp vào **GeoGebra headless trong trình duyệt ẩn (Playwright/Puppeteer)**, trả về: trạng thái lỗi từng lệnh, ảnh PNG/SVG/PDF, file .ggb, và (cho agent review) ảnh PNG để LLM nhìn.
- **Supabase**: Auth (đăng nhập giáo viên), Postgres (thư viện hình — **lưu lệnh dựng dạng text, KHÔNG lưu PNG**), Storage (nếu cần lưu ảnh thật thì để đây, tách khỏi DB).

### Vì sao tách Python + Node
GeoGebra runtime là JavaScript; điều khiển headless tự nhiên bằng Node + Playwright. Hệ sinh thái AI/agent mạnh ở Python. Tách hai service qua HTTP nội bộ để mỗi bên làm thứ nó mạnh, và để scale phần render độc lập sau này.

---

## 4. Tech stack đề xuất

| Thành phần | Lựa chọn | Ghi chú |
|---|---|---|
| Frontend | React + Vite (hoặc Next.js) | Nhúng GeoGebra qua `deployggb.js` |
| GeoGebra embed | GeoGebra Math Apps + JS API | `ggbApplet.evalCommand`, `getPNGBase64`, `exportSVG` |
| Python svc | FastAPI | Pipeline agent + orchestration |
| Node svc | Express/Fastify + Playwright | Headless GeoGebra render |
| LLM | **Gemini (Google AI Studio, free tier)** có vision — dùng cho cả generate lẫn review | Xem §4.1; tên model trong env, đổi được |
| Auth/DB/Storage | Supabase | Free tier đủ cho ~20 user |
| Rate limit demo | Theo IP (xem §9) | Lưu count ở Postgres hoặc Redis nhẹ |

> Frontend tham khảo skill `frontend-design` để có hướng thẩm mỹ rõ ràng, tránh giao diện template mặc định.

### 4.1 LLM provider: Gemini free tier + đường nâng cấp

**Mặc định v1: Google AI Studio (Gemini).** Lý do: gần như là model frontier đóng duy nhất còn cho dùng **miễn phí**, lại **có vision** (bắt buộc cho Agent Reviewer nhìn ảnh render), và hạn mức rộng (Gemini Flash: ~1.500 request/ngày, context 1M, không cần thẻ). Dùng **một key Gemini cho cả Generator lẫn Reviewer** cho gọn.

**Trừu tượng hóa provider (bắt buộc):** Bọc mọi lời gọi LLM sau một interface chung (`generate_commands()`, `review_image()`), tên model + provider lấy từ env. Lý do: danh mục model free hay bị xóa đột ngột; đổi model/provider không được phép sửa logic.

**Đường nâng cấp khi chạm trần / lên production:**
- Mỗi hình tốn ~5–8 lời gọi (sinh + tối đa 3 vòng sửa + review). 20 user × ngày đông có thể chạm trần free của Gemini.
- Tùy chọn tiết kiệm quota: tách **Groq** (nhanh, rẻ, text) cho khâu **sinh lệnh**, để Gemini lo riêng **review (vision)**. Interface chung ở trên cho phép trộn provider mà không sửa pipeline.
- Khi dùng thật nhiều: chuyển khâu chạm trần trước (thường là review vision) sang **gói trả phí** cùng provider.

**Lưu ý vận hành:**
- Free tier có thể **dùng prompt để train** — đề hình học độ nhạy thấp nên chấp nhận được, nhưng đừng đẩy dữ liệu nhạy cảm vào. Bật opt-out nếu provider hỗ trợ.
- **Kiểm license dùng thương mại** của provider (một số trial key cấm), vì đây là sản phẩm có người dùng ngoài.
- Đặt `MAX_LLM_CALLS_PER_REQUEST` và `MAX_FIX_ROUNDS` để vừa chặn chi phí vừa tránh nuốt hết quota free trong một request lỗi lặp.

### 4.2 Triển khai (deployment)

Mục tiêu: **chi phí thấp nhất**, chấp nhận cold start.

**Frontend**: React + **Vite** (SPA tĩnh, không cần Next/SSR vì app nội bộ ~20 user, không cần SEO). Host tĩnh free: Cloudflare Pages hoặc Vercel.

**Hai service backend** (FastAPI orchestrator + Node-GeoGebra): **container scale-to-zero**.
- Nền tảng đề xuất: **Google Cloud Run** (scale-to-zero thật, chạy container nên headless Chromium OK — khác Vercel functions; free tier rộng). Phương án $0 đơn giản hơn (ngại cấu hình GCP): **Render Hobby** (ngủ sau khi rảnh).
- **KHÔNG dùng Vercel cho service Playwright**: vướng giới hạn bundle ~50MB, cold start nặng, không hợp pool browser thường trực.

**Cold start — đã chấp nhận, nhưng phải xử lý UX:**
- Service render (Chromium) là chỗ cold start nặng nhất (vài chục giây khi vừa thức).
- Hai service cùng ngủ ⇒ một request có thể dính **hai cold start liên tiếp**. Nếu lần đầu quá lâu, cân nhắc **gộp hai service làm một** (đảo lại quyết định tách Python/Node — cân nhắc sau).
- **Frontend phải hiện trạng thái khởi động rõ ràng** ở lần vẽ đầu ("đang khởi động máy vẽ, lần đầu hơi lâu…") + spinner, tránh giáo viên tưởng treo.
- Trong một instance đã ấm, **giữ trang GeoGebra/Chromium sống để tái dùng** giữa các request; chỉ request đầu sau khi ngủ mới chậm.

**Chi phí thực tế ở quy mô này:** host gần như $0 khi rảnh (scale-to-zero). Khoản có thể phình to là **LLM nếu vượt free tier** (review vision) — kiểm soát bằng `MAX_LLM_CALLS_PER_REQUEST`, không phải bằng việc tiết kiệm host. Supabase free tier đủ; nhớ ping định kỳ né pause 7 ngày.

> Ghi chú: nếu sau này muốn bỏ cold start hoàn toàn, đường nâng cấp là một VPS luôn-bật (vd Hetzner CX22 ~$4–5/tháng chạy cả stack bằng Docker Compose), hoặc đặt `min-instances=1` trên Cloud Run (mất phần lớn lợi ích scale-to-zero).

---

## 5. Luồng xử lý một yêu cầu

1. Giáo viên nhập đề tiếng Việt ở frontend → POST tới Python `/generate`.
2. **Gating** (Python):
   - Nếu **đã đăng nhập** (Supabase JWT hợp lệ) → bỏ qua giới hạn, full tính năng.
   - Nếu **demo (không đăng nhập)** → kiểm IP: đã dùng ≥ 2 lượt thì trả 429 + lời mời đăng ký. Còn lượt thì cho chạy (vẫn bật review), tăng count.
3. **Agent Generator** (LLM): đề → danh sách lệnh GeoGebra (construction commands).
4. Python gọi **Node service** `/render` với danh sách lệnh.
5. Node nạp từng lệnh vào GeoGebra headless, thu trạng thái lỗi mỗi lệnh + ảnh PNG.
6. **Technical Validator** (Python, deterministic): phát hiện lỗi cứng — lệnh báo lỗi, đối tượng `undefined`, điểm trùng/thẳng hàng khi đáng lẽ là tam giác, đường tròn không dựng được. Nếu lỗi → gửi thông báo lỗi + lệnh gốc lại cho **Agent Generator** sửa. Lặp tối đa `MAX_FIX_ROUNDS` (mặc định 3).
7. **Agent Reviewer** (LLM vision): nhận ảnh PNG đã render + đề gốc → đánh giá hình có đúng quan hệ và bố cục/cân đối/nhãn không đè không. Nếu chưa đạt → trả gợi ý sửa cho Generator (đếm vào cùng `MAX_FIX_ROUNDS`).
8. Khi đạt: trả về frontend **danh sách lệnh cuối** + ảnh preview.
9. Frontend nạp lệnh vào **GeoGebra applet** → giáo viên **kéo thả tinh chỉnh**.
10. Giáo viên bấm **export** (PNG/copy/SVG/PDF/.ggb). Nếu đã đăng nhập, có thể **Lưu vào thư viện** (ghi lệnh text vào Postgres).

> Tổng số lời gọi LLM mỗi yêu cầu phải có trần (`MAX_LLM_CALLS_PER_REQUEST`) để chặn chi phí chạy lố.

---

## 6. Các agent

### 6.1 Generator
- **Input**: đề tiếng Việt (+ ở vòng sửa: lệnh trước + thông báo lỗi/gợi ý review).
- **Output**: JSON mảng lệnh GeoGebra theo thứ tự dựng.
- **Grounding**: few-shot + **cheatsheet lệnh mức 1** + **golden example set** (§11) nhồi vào system prompt. KHÔNG dùng RAG/fine-tune ở v1 (vocab nhỏ, chưa cần).
- Quy ước: đặt vài điểm tự do ở vị trí mặc định "đẹp" để hình ban đầu cân đối; các đối tượng phụ thuộc để GeoGebra tự tính.

### 6.2 Technical Validator
- Deterministic (không phải LLM). Đọc kết quả render từ Node: lệnh nào lỗi, đối tượng nào undefined, kiểm tra suy biến (diện tích tam giác ≈ 0, hai điểm trùng, bán kính ≤ 0…).
- Trả về danh sách lỗi máy-đọc-được để feed lại Generator.

### 6.3 Reviewer
- LLM có **vision**. Input: ảnh PNG render + đề gốc.
- Đánh giá: (a) đúng quan hệ đề yêu cầu? (b) bố cục cân đối, nhãn không đè, hình không quá lệch/nhỏ? 
- Output: `pass` hoặc danh sách gợi ý sửa cụ thể.
- Có **cờ bật/tắt** (`ENABLE_REVIEW`). Demo: vẫn BẬT (theo quyết định sản phẩm). Có thể tắt khi cần chạy nhanh/tiết kiệm.

---

## 7. GeoGebra integration

### 7.1 Frontend (applet nhúng)
- Dùng `deployggb.js`, tạo `GGBApplet`, `evalCommand(cmd)` cho từng lệnh.
- Bật cho phép kéo thả điểm tự do.
- Export phía client khi được: `getPNGBase64`, `exportSVG`. PDF có thể làm phía Node cho chắc.

### 7.2 Node service (headless)
- Endpoint `POST /render`: body = `{ commands: string[], formats: ["png","svg","pdf","ggb"] }`.
- Mở một trang GeoGebra Math Apps trong Playwright (Chromium), `evalCommand` từng lệnh, đọc lỗi từng lệnh (kiểm `ggbApplet.isDefined(label)` / giá trị trả về của `evalCommand`).
- Trả `{ perCommandStatus, pngBase64, svg, pdfBase64, ggbBase64 }`.
- Giữ một pool nhỏ trang headless để tái dùng (20 user, bursty → pool 1–2 là đủ; xếp hàng nếu nghẽn).

> Lưu ý: tên lệnh GeoGebra phải verify trên GeoGebra thật. Ví dụ đường tròn ngoại tiếp là `Circle(A,B,C)`; tâm nội tiếp dựng bằng giao hai phân giác (`AngleBisector`), bán kính nội tiếp = `Distance(I, Line(A,B))`. Đừng giả định có lệnh `Incircle` nếu chưa kiểm.

---

## 8. Data model (Supabase / Postgres)

**Nguyên tắc: lưu lệnh dựng (text) trong DB, KHÔNG lưu PNG trong DB.** Ảnh thật (nếu cần) để Supabase Storage.

```sql
-- Người dùng: dùng auth.users của Supabase Auth.

create table figures (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  title         text,
  problem_text  text not null,          -- đề gốc tiếng Việt
  commands      jsonb not null,         -- mảng lệnh GeoGebra (text)
  thumbnail_url text,                   -- optional, trỏ Supabase Storage
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create table demo_usage (
  ip          inet primary key,
  count       int not null default 0,   -- 2 lượt/IP VĨNH VIỄN
  first_seen  timestamptz default now(),
  last_seen   timestamptz default now()
);

-- RLS: figures chỉ chủ sở hữu đọc/ghi.
alter table figures enable row level security;
create policy "own figures" on figures
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

---

## 9. Gating demo (theo IP)

- **2 lượt/IP, VĨNH VIỄN** (không reset theo thời gian — đây là quyết định đã chốt).
- Lưu ở bảng `demo_usage`. Mỗi `/generate` không-đăng-nhập: đọc count theo IP, nếu ≥ 2 → trả 429 + CTA đăng ký; nếu < 2 → chạy rồi `count += 1`.
- **Tài khoản đã đăng nhập: KHÔNG áp giới hạn IP** (bắt buộc — nếu không cả trường chung IP vừa hết demo vừa kẹt bản chính).
- Demo vẫn BẬT agent review (full chất lượng) ⇒ mỗi lượt demo là full chi phí ⇒ trần 2 lượt phải thực thi server-side chắc chắn, lấy IP thật (xử lý `X-Forwarded-For` nếu sau proxy).
- Chấp nhận đánh đổi đã biết: trường chung IP có thể bị khóa demo sau 2 lượt; đường thoát là tạo tài khoản.

---

## 10. Export

v1 hỗ trợ: **PNG nền trong**, **copy-to-clipboard** (ảnh), **SVG**, **PDF**, **.ggb** (tặng kèm).
- PNG/copy: ưu tiên trải nghiệm Word của giáo viên.
- SVG/PDF: bản in chất lượng cao / LaTeX.
- .ggb: mở lại chỉnh sâu trong GeoGebra.

---

## 11. Golden example set (seed — PHẢI verify trên GeoGebra)

Dưới đây là **bản nháp khung** để bắt đầu; mỗi cặp phải được nạp vào GeoGebra thật để xác nhận lệnh chạy đúng trước khi đưa vào few-shot. Mục tiêu: mở rộng lên **20–30 cặp** phủ mức 1, đồng thời dùng làm **bộ test hồi quy**.

Định dạng mỗi mục: `problem_text` (tiếng Việt) → `commands` (mảng).

**VD1 — Tam giác và đường cao**
- Đề: "Vẽ tam giác ABC, kẻ đường cao AH xuống BC."
- Lệnh (nháp, cần verify):
  ```
  A=(0,0)
  B=(6,0)
  C=(1.5,4.5)
  tri=Polygon(A,B,C)
  H=ClosestPoint(Line(B,C),A)
  alt=Segment(A,H)
  ```

**VD2 — Đường tròn ngoại tiếp**
- Đề: "Tam giác ABC nội tiếp đường tròn tâm O."
- Lệnh (nháp):
  ```
  A=(0,0)
  B=(6,0)
  C=(2,5)
  tri=Polygon(A,B,C)
  circ=Circle(A,B,C)
  O=Center(circ)
  ```

**VD3 — Đường tròn nội tiếp**
- Đề: "Tam giác ABC với đường tròn nội tiếp tâm I."
- Lệnh (nháp — dựng I bằng giao hai phân giác):
  ```
  A=(0,0)
  B=(6,0)
  C=(2,5)
  tri=Polygon(A,B,C)
  bi1=AngleBisector(B,A,C)
  bi2=AngleBisector(A,B,C)
  I=Intersect(bi1,bi2)
  r=Distance(I,Line(A,B))
  incirc=Circle(I,r)
  ```

**VD4 — Trung tuyến & trọng tâm**
- Đề: "Vẽ ba trung tuyến của tam giác ABC, xác định trọng tâm G."
- Lệnh (nháp):
  ```
  A=(0,0)
  B=(6,0)
  C=(2,5)
  tri=Polygon(A,B,C)
  Ma=Midpoint(B,C)
  Mb=Midpoint(A,C)
  Mc=Midpoint(A,B)
  med_a=Segment(A,Ma)
  med_b=Segment(B,Mb)
  med_c=Segment(C,Mc)
  G=Centroid(tri)
  ```

> Giao cho người dùng (giáo viên) duyệt từng lệnh trong GeoGebra. Cặp nào sai cú pháp thì sửa rồi chốt làm gold.

---

## 12. Build phases (cho Claude Code làm tuần tự)

**Phase 0 — Scaffold**
- Monorepo: `/frontend` (React+Vite), `/orchestrator` (FastAPI), `/ggb-service` (Node+Playwright).
- Docker Compose để chạy 3 service **local**. Mỗi backend service có Dockerfile để deploy lên **Cloud Run** (scale-to-zero) — xem §4.2.

**Phase 1 — Render service (Node)**
- `/render` nhận lệnh, nạp GeoGebra headless, trả per-command status + PNG. Test bằng VD1–VD4 hard-code.

**Phase 2 — Generator + pipeline tối thiểu (Python)**
- `/generate`: gọi LLM (few-shot từ §11) → lệnh → gọi `/render` → trả ảnh. Chưa có review/auth.

**Phase 3 — Technical Validator + vòng sửa**
- Bắt lỗi cứng, feed lại Generator, `MAX_FIX_ROUNDS`.

**Phase 4 — Frontend cơ bản**
- Khung chat + nhúng GeoGebra applet nạp lệnh + kéo thả. Export PNG/copy/SVG/PDF/.ggb.

**Phase 5 — Agent Reviewer (vision)**
- Thêm review vào pipeline, cờ `ENABLE_REVIEW`.

**Phase 6 — Supabase Auth + thư viện**
- Đăng nhập, lưu/đọc `figures` (lệnh text), RLS.

**Phase 7 — Demo gating theo IP**
- Bảng `demo_usage`, 2 lượt/IP vĩnh viễn, bỏ qua khi đã đăng nhập.

**Phase 8 — Cứng hóa**
- Trần chi phí (`MAX_LLM_CALLS_PER_REQUEST`), xử lý lỗi, ping giữ Supabase khỏi pause 7 ngày, mở rộng golden set lên 20–30 và chạy như test hồi quy.

---

## 13. Cấu hình / env

```
# LLM (xem §4.1) — bọc sau interface chung, đổi provider không sửa logic
LLM_PROVIDER=gemini          # gemini | groq | openrouter | ...
LLM_API_KEY=                 # key Google AI Studio cho mặc định v1
LLM_MODEL=                   # model Gemini có vision (vd gemini-2.5-flash)
# Tùy chọn tách provider để tiết kiệm quota:
GENERATOR_PROVIDER=          # vd groq cho khâu sinh lệnh (text)
GENERATOR_MODEL=
REVIEWER_PROVIDER=gemini     # provider có vision cho khâu review
REVIEWER_MODEL=
ENABLE_REVIEW=true
MAX_FIX_ROUNDS=3
MAX_LLM_CALLS_PER_REQUEST=8

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Services
GGB_SERVICE_URL=http://ggb-service:PORT

# Demo
DEMO_LIMIT_PER_IP=2   # vĩnh viễn
```

---

## 14. Câu hỏi cần xác nhận khi build

1. LLM: mặc định **Gemini free tier** (§4.1) — xác nhận tên model Gemini có vision cụ thể, và có tách Groq cho Generator không?
2. ✅ Frontend: **React + Vite** (SPA tĩnh). Host tĩnh free (Cloudflare Pages / Vercel).
3. ✅ Backend host: **container scale-to-zero, ưu tiên Google Cloud Run** (Render Hobby nếu muốn $0 đơn giản hơn). Chấp nhận cold start.
4. ✅ Vercel KHÔNG dùng cho service Playwright. Cold start được chấp nhận, xử lý bằng UX khởi động (§4.2). — Xác nhận: dùng Cloud Run hay Render Hobby?
5. Có cần custom domain / chứng chỉ không?
6. Quy ước nhãn/ký hiệu tiếng Việt (kiểu chữ, màu mặc định) — chuẩn hóa trong prompt Generator?

---

*Quyết định đã chốt qua quá trình thiết kế: cơ chế lệnh-GeoGebra (không đoán tọa độ); Python brain + Node render; một hình/lượt; mức 1 THCS; few-shot + golden set; export PNG/copy/SVG/PDF/.ggb; có tài khoản (Supabase) + thư viện lưu-lệnh-text; demo 2 lượt/IP vĩnh viễn vẫn bật review; LLM mặc định Gemini free tier (có vision) sau interface đổi-provider-được; frontend Vite tĩnh + backend scale-to-zero (Cloud Run) chấp nhận cold start; ~20 user, free tier.*
