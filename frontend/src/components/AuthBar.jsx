import { useState } from "react";
import { supabase, supabaseConfigured } from "../supabase.js";

// Đăng nhập giáo viên qua Supabase Auth (email + mật khẩu).
export default function AuthBar({ session }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  if (!supabaseConfigured) {
    return (
      <div className="authbar">
        <span className="muted">Chế độ demo (chưa cấu hình Supabase)</span>
      </div>
    );
  }

  if (session) {
    return (
      <div className="authbar">
        <span>👤 {session.user.email}</span>
        <button onClick={() => supabase.auth.signOut()}>Đăng xuất</button>
      </div>
    );
  }

  const submit = async (mode) => {
    setBusy(true);
    setErr("");
    const fn =
      mode === "signup"
        ? supabase.auth.signUp({ email, password })
        : supabase.auth.signInWithPassword({ email, password });
    const { error } = await fn;
    if (error) setErr(error.message);
    setBusy(false);
  };

  return (
    <div className="authbar">
      <input
        type="email"
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        placeholder="mật khẩu"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button disabled={busy} onClick={() => submit("signin")}>
        Đăng nhập
      </button>
      <button disabled={busy} onClick={() => submit("signup")}>
        Đăng ký
      </button>
      {err && <span className="error-text">{err}</span>}
    </div>
  );
}
