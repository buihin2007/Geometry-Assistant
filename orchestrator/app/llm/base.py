from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Interface chung cho mọi provider LLM.

    Mục tiêu (PLAN §4.1): đổi model/provider KHÔNG được phép sửa logic pipeline.
    Mọi provider chỉ cần cài hai khả năng:
      - complete_text: sinh text từ prompt (dùng cho Generator).
      - complete_vision: sinh text từ prompt + ảnh PNG (dùng cho Reviewer).
    """

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    async def complete_text(self, system: str, user: str) -> str:
        ...

    @abstractmethod
    async def complete_vision(self, system: str, user: str, png_base64: str) -> str:
        """png_base64 KHÔNG kèm tiền tố data: — provider tự gói."""
        ...

    @property
    def supports_vision(self) -> bool:
        return True
