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
        # Cold start service render có thể vài chục giây (PLAN §4.2) → timeout rộng.
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/render",
                json={
                    "commands": commands,
                    "formats": formats,
                    "checks": checks or [],
                },
            )
            r.raise_for_status()
            return r.json()
