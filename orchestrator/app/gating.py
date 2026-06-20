from fastapi import Request
from .config import Settings
from .supabase_client import SupabaseClient

# Gating demo theo IP (PLAN §9): 2 lượt/IP VĨNH VIỄN, đã đăng nhập thì bỏ qua.
# Fallback: nếu Supabase chưa cấu hình → đếm trong bộ nhớ (chỉ cho dev local).

_memory_counts: dict[str, int] = {}


def client_ip(request: Request) -> str:
    # Sau proxy/Cloud Run: lấy IP thật từ X-Forwarded-For (PLAN §9).
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class GatingDecision:
    def __init__(self, allowed: bool, reason: str = "", remaining: int | None = None):
        self.allowed = allowed
        self.reason = reason
        self.remaining = remaining


class Gating:
    def __init__(self, settings: Settings, supabase: SupabaseClient):
        self.s = settings
        self.sb = supabase

    async def check(self, request: Request, authenticated: bool) -> GatingDecision:
        # Đã đăng nhập → KHÔNG áp giới hạn (bắt buộc, PLAN §9).
        if authenticated:
            return GatingDecision(allowed=True, reason="authenticated")

        ip = client_ip(request)
        limit = self.s.demo_limit_per_ip

        count = await self.sb.get_demo_count(ip)
        if count is None:
            # Fallback bộ nhớ.
            count = _memory_counts.get(ip, 0)

        if count >= limit:
            return GatingDecision(
                allowed=False,
                reason=f"Đã hết {limit} lượt dùng thử cho IP này. Đăng ký để dùng tiếp.",
                remaining=0,
            )
        return GatingDecision(allowed=True, reason="demo", remaining=limit - count)

    async def consume(self, request: Request, authenticated: bool) -> None:
        if authenticated:
            return
        ip = client_ip(request)
        if self.sb.url and self.sb.service:
            await self.sb.increment_demo(ip)
        else:
            _memory_counts[ip] = _memory_counts.get(ip, 0) + 1
