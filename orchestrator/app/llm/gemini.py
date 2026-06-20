import httpx
from .base import LLMProvider
from .retry import post_with_retry

# Google AI Studio (Gemini) REST API — mặc định v1 (PLAN §4.1).
# Có vision, free tier rộng. Tên model lấy từ env (LLM_MODEL / REVIEWER_MODEL).
BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    async def _generate(self, parts: list[dict], system: str) -> str:
        url = f"{BASE}/models/{self.model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await post_with_retry(
                client, url, params={"key": self.api_key}, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Gemini response không đọc được: {data}") from e

    async def complete_text(self, system: str, user: str) -> str:
        return await self._generate([{"text": user}], system)

    async def complete_vision(self, system: str, user: str, png_base64: str) -> str:
        parts = [
            {"text": user},
            {"inline_data": {"mime_type": "image/png", "data": png_base64}},
        ]
        return await self._generate(parts, system)
