import asyncio

import httpx


class GgbClient:
    """Client gọi Node GeoGebra service (PLAN §7.2)."""

    def __init__(self, base_url: str):
        base_url = (base_url or "").rstrip("/")
        # Render fromService 'host' trả hostname không scheme → tự thêm https://.
        if base_url and not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url
        self.base_url = base_url

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.base_url}/health")
            r.raise_for_status()
            return r.json()

    async def render(
        self,
        commands: list[str],
        formats: list[str],
        checks: list[str] | None = None,
    ) -> dict:
        # Cold start (scale-to-zero): container có thể CHƯA lắng nghe (lỗi kết nối) hoặc
        # pool Chromium chưa ấm (503). Thử lại có backoff để cold start KHÔNG văng "Lỗi
        # pipeline 503" cho người dùng — chỉ làm request đầu lâu hơn. Timeout render
        # rộng vì service tự chờ pool ấm (~60s) trước khi vẽ.
        payload = {"commands": commands, "formats": formats, "checks": checks or []}
        attempts = 4
        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=120.0) as client:
            for i in range(attempts):
                try:
                    r = await client.post(f"{self.base_url}/render", json=payload)
                    if r.status_code == 503 and i < attempts - 1:
                        # engine đang khởi động → chờ rồi thử lại.
                        await asyncio.sleep(2 * (i + 1))
                        continue
                    r.raise_for_status()
                    return r.json()
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError) as e:
                    # Container cold boot chưa nhận kết nối → đợi rồi thử lại.
                    last_exc = e
                    if i < attempts - 1:
                        await asyncio.sleep(2 * (i + 1))
                        continue
                    raise
        # Hết lượt mà vẫn 503/connection.
        if last_exc:
            raise last_exc
        raise httpx.HTTPError("ggb render: hết số lần thử mà engine vẫn chưa sẵn sàng")
