import httpx
from .config import Settings


class SupabaseClient:
    """Bọc Supabase Auth + PostgREST (PLAN §8).

    - Auth: xác thực JWT bằng cách hỏi /auth/v1/user (không cần JWT secret).
    - figures: gọi PostgREST kèm JWT người dùng → RLS tự áp.
    - demo_usage: gọi bằng service_role key (bỏ qua RLS) để đếm theo IP.

    Nếu chưa cấu hình Supabase, các hàm trả None/fallback để app vẫn chạy demo local.
    """

    def __init__(self, settings: Settings):
        self.url = settings.supabase_url.rstrip("/") if settings.supabase_url else ""
        self.anon = settings.supabase_anon_key
        self.service = settings.supabase_service_role_key

    @property
    def configured(self) -> bool:
        return bool(self.url and self.anon)

    # ---------- Auth ----------
    async def get_user(self, jwt: str) -> dict | None:
        if not self.configured or not jwt:
            return None
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(
                f"{self.url}/auth/v1/user",
                headers={"apikey": self.anon, "Authorization": f"Bearer {jwt}"},
            )
            if r.status_code != 200:
                return None
            return r.json()

    # ---------- figures (PostgREST, dùng JWT người dùng) ----------
    def _rest_headers(self, jwt: str, extra: dict | None = None) -> dict:
        h = {
            "apikey": self.anon,
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    async def list_figures(self, jwt: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(
                f"{self.url}/rest/v1/figures",
                headers=self._rest_headers(jwt),
                params={"select": "*", "order": "created_at.desc"},
            )
            r.raise_for_status()
            return r.json()

    async def create_figure(self, jwt: str, user_id: str, payload: dict) -> dict:
        body = {
            "user_id": user_id,
            "title": payload.get("title"),
            "problem_text": payload["problem_text"],
            "commands": payload["commands"],  # jsonb
            "thumbnail_url": payload.get("thumbnail_url"),
        }
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                f"{self.url}/rest/v1/figures",
                headers=self._rest_headers(jwt, {"Prefer": "return=representation"}),
                json=body,
            )
            r.raise_for_status()
            data = r.json()
            return data[0] if isinstance(data, list) and data else data

    async def delete_figure(self, jwt: str, figure_id: str) -> None:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.delete(
                f"{self.url}/rest/v1/figures",
                headers=self._rest_headers(jwt),
                params={"id": f"eq.{figure_id}"},
            )
            r.raise_for_status()

    # ---------- demo_usage (service role, bỏ qua RLS) ----------
    def _service_headers(self) -> dict:
        return {
            "apikey": self.service,
            "Authorization": f"Bearer {self.service}",
            "Content-Type": "application/json",
        }

    async def get_demo_count(self, ip: str) -> int | None:
        if not (self.url and self.service):
            return None
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(
                f"{self.url}/rest/v1/demo_usage",
                headers=self._service_headers(),
                params={"select": "count", "ip": f"eq.{ip}"},
            )
            r.raise_for_status()
            rows = r.json()
            return rows[0]["count"] if rows else 0

    async def increment_demo(self, ip: str) -> None:
        if not (self.url and self.service):
            return
        # upsert: count += 1. Dùng RPC nếu có; ở đây làm get rồi upsert đơn giản.
        current = await self.get_demo_count(ip) or 0
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(
                f"{self.url}/rest/v1/demo_usage",
                headers={**self._service_headers(), "Prefer": "resolution=merge-duplicates"},
                json={"ip": ip, "count": current + 1, "last_seen": "now()"},
            )
            r.raise_for_status()

    @property
    def service_enabled(self) -> bool:
        return bool(self.url and self.service)

    async def insert_report(self, entry: dict) -> None:
        """Ghi report người dùng vào bảng `reports` (service_role, bỏ qua RLS).
        Dùng cho prod serverless (file logs/ mất khi scale-to-zero)."""
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(
                f"{self.url}/rest/v1/reports",
                headers=self._service_headers(),
                json=entry,
            )
            r.raise_for_status()
