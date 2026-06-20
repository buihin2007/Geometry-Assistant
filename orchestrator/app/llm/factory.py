from .base import LLMProvider
from .gemini import GeminiProvider
from .openai_compat import OpenAICompatProvider, ENDPOINTS
from .anthropic import AnthropicProvider
from .mock import MockProvider


def make_provider(provider: str, model: str, api_key: str) -> LLMProvider:
    """Tạo provider từ tên. Đây là chỗ DUY NHẤT biết về provider cụ thể —
    phần còn lại của pipeline chỉ thấy interface LLMProvider (PLAN §4.1)."""
    p = (provider or "mock").lower()
    if p == "mock":
        return MockProvider(model, api_key)
    if p == "gemini":
        return GeminiProvider(model, api_key)
    if p in ("anthropic", "claude"):
        return AnthropicProvider(model, api_key)
    if p in ENDPOINTS:
        # Vision do MODEL quyết định, không phải provider: Groq có model vision
        # (vd meta-llama/llama-4-scout). Bật vision; API sẽ báo lỗi nếu model
        # không nhận ảnh. Reviewer phải chọn model vision trong env.
        return OpenAICompatProvider(model, api_key, ENDPOINTS[p], vision=True)
    raise ValueError(f"Provider không hỗ trợ: {provider}")
