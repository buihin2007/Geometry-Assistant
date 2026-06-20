import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Nếu chưa cấu hình Supabase, supabase = null → app vẫn chạy chế độ demo.
export const supabase = url && anon ? createClient(url, anon) : null;
export const supabaseConfigured = Boolean(supabase);
