import httpx
from .base import LLMProvider
from .retry import post_with_retry

# Provider tương thích OpenAI chat-completions: Groq, OpenRouter, v.v.
# Groq (PLAN §4.1): nhanh/rẻ cho khâu sinh lệnh (text). OpenRouter: có model vision.
ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}


class OpenAICompatProvider(LLMProvider):
    def __init__(self, model: str, api_key: str, endpoint: str, vision: bool = True):
        super().__init__(model, api_key)
        self.endpoint = endpoint
        self._vision = vision

    @property
    def supports_vision(self) -> bool:
        return self._vision

    async def _chat(self, messages: list[dict]) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "messages": messages, "temperature": 0.4}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await post_with_retry(
                client, self.endpoint, headers=headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def complete_text(self, system: str, user: str) -> str:
        return await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )

    async def complete_vision(self, system: str, user: str, png_base64: str) -> str:
        if not self._vision:
            raise RuntimeError(f"Provider model {self.model} không hỗ trợ vision")
        return await self._chat(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{png_base64}"
                            },
                        },
                    ],
                },
            ]
        )
