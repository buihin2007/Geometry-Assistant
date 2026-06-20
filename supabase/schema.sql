-- Supabase / Postgres schema (PLAN §8).
-- Nguyên tắc: lưu LỆNH DỰNG (text) trong DB, KHÔNG lưu PNG. Ảnh để Storage nếu cần.
-- Chạy trong Supabase SQL editor.

-- Người dùng dùng auth.users của Supabase Auth (không tạo lại).

create table if not exists figures (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  title         text,
  problem_text  text not null,          -- đề gốc tiếng Việt
  commands      jsonb not null,         -- mảng lệnh GeoGebra (text)
  thumbnail_url text,                   -- optional, trỏ Supabase Storage
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create table if not exists demo_usage (
  ip          inet primary key,
  count       int not null default 0,   -- 2 lượt/IP VĨNH VIỄN
  first_seen  timestamptz default now(),
  last_seen   timestamptz default now()
);

-- RLS: figures chỉ chủ sở hữu đọc/ghi.
alter table figures enable row level security;

drop policy if exists "own figures" on figures;
create policy "own figures" on figures
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- demo_usage chỉ service_role (orchestrator) đụng tới; bật RLS, không tạo policy
-- cho anon → mặc định chặn, service_role bỏ qua RLS.
alter table demo_usage enable row level security;

-- Report người dùng gửi (hình sai / góp ý) — bắt lỗi im lặng để mở rộng regression.
-- Prod serverless PHẢI dùng bảng này (file logs/ mất khi scale-to-zero). Lưu commands
-- (text) để tái hiện tất định; KHÔNG lưu ảnh.
create table if not exists reports (
  id            uuid primary key default gen_random_uuid(),
  ip            inet,
  category      text,                    -- ve_sai | khong_ve_duoc | bo_cuc | khac
  note          text,
  problem_text  text not null,
  commands      jsonb not null default '[]',
  review_passed boolean,
  warnings      jsonb default '[]',
  resolved      boolean default false,   -- đánh dấu khi đã xử lý → thêm regression
  created_at    timestamptz default now()
);
-- Chỉ service_role (orchestrator) ghi/đọc; chặn anon.
alter table reports enable row level security;
