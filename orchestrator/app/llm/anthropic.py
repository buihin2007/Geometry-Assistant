import httpx
from .base import LLMProvider
from .retry import post_with_retry

# Anthropic Claude (Messages API). Rate limit cao hơn nhiều free tier Groq/Gemini,
# có vision → dùng được cho cả planner (text) lẫn reviewer (ảnh).
URL = "https://api.anthropic.com/v1/messages"
HEADERS_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": HEADERS_VERSION,
            "content-type": "application/json",
        }

    async def _messages(self, system: str, content) -> str:
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            payload["system"] = system
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await post_with_retry(client, URL, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
        try:
            # Ghép mọi block text trong content.
            return "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Anthropic response không đọc được: {data}") from e

    async def complete_text(self, system: str, user: str) -> str:
        return await self._messages(system, user)

    async def complete_vision(self, system: str, user: str, png_base64: str) -> str:
        content = [
            {"type": "text", "text": user},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": png_base64,
                },
            },
        ]
        return await self._messages(system, content)
