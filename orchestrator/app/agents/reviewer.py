import json
import re
from dataclasses import dataclass, field
from ..llm.base import LLMProvider

# Agent Reviewer (PLAN §6.3) — LLM CÓ VISION.
# Nhìn ảnh PNG render + đề gốc, đánh giá đúng quan hệ & bố cục.

SYSTEM = """\
Bạn là người soát hình học, NHÂN HẬU và THỰC TẾ. Bạn nhận ĐỀ tiếng Việt và ẢNH hình
đã vẽ bằng GeoGebra. Mục tiêu: chỉ chặn những hình SAI RÕ RÀNG, không bắt bẻ tiểu tiết.

NGUYÊN TẮC CHẤM (mặc định là PASS):
- PASS nếu hình thể hiện ĐÚNG các quan hệ chính đề yêu cầu (đủ đối tượng cần có: tam
  giác, đường cao/trung tuyến/phân giác, đường tròn, điểm đặc biệt... và quan hệ
  vuông góc/tiếp xúc/đi qua nhìn hợp lý).
- Hình KHÔNG cần đẹp hoàn hảo. Lệch nhẹ, nhãn hơi sát, tỉ lệ chưa tối ưu → VẪN PASS.
  Giáo viên sẽ tự kéo thả tinh chỉnh sau.
- Chỉ trả "revise" khi có lỗi THỰC SỰ:

KIỂM TRA KỸ QUAN HỆ ĐỀ NÊU TÊN (không chỉ "trông giống dạng đúng"):
- "tiếp tuyến": đường phải CHẠM đường tròn đúng 1 điểm (tiếp xúc), KHÔNG cắt xuyên
  qua (cát tuyến). Nếu đường kẻ cắt đường tròn tại 2 điểm → REVISE.
- "nội tiếp"/"ngoại tiếp": các đỉnh phải nằm ĐÚNG trên đường tròn / đường tròn chạm
  đủ các cạnh.
- "vuông góc": góc phải ≈ 90°. "song song": không cắt nhau. "thẳng hàng": cùng đường.
- Thiếu hẳn đối tượng đề yêu cầu, hình suy biến/chồng bẹp, hoặc trống trơn → REVISE.

KIỂM TRA NÉT THỪA:
- Nếu có ĐƯỜNG THẲNG kéo dài tràn ra ngoài tam giác/hình trong khi đề chỉ cần ĐOẠN
  (đường cao, trung tuyến, phân giác trong tam giác) → REVISE (yêu cầu vẽ đoạn hữu hạn).

Trả về CHỈ JSON, không markdown:
{"status": "pass"}  — mặc định, dùng khi các quan hệ chính đã đúng.
{"status": "revise", "suggestions": ["lỗi cụ thể + cách sửa", ...]}  — chỉ khi sai rõ ràng.
Gợi ý phải cụ thể về QUAN HỆ/đối tượng còn thiếu hoặc sai, không nói chung chung về thẩm mỹ.
"""


@dataclass
class ReviewResult:
    passed: bool
    suggestions: list[str] = field(default_factory=list)

    def feedback_text(self) -> str:
        return "\n".join(f"- {s}" for s in self.suggestions)


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


class Reviewer:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def review(self, problem: str, png_base64: str) -> ReviewResult:
        user = (
            f'Đề: "{problem}"\n\n'
            "Đánh giá hình trong ảnh đính kèm theo hướng dẫn hệ thống."
        )
        raw = await self.provider.complete_vision(SYSTEM, user, png_base64)
        try:
            data = _extract_json(raw)
        except json.JSONDecodeError:
            # Không parse được → coi như pass để tránh kẹt vòng lặp.
            return ReviewResult(passed=True)
        status = (data.get("status") or "").lower()
        if status == "pass":
            return ReviewResult(passed=True)
        return ReviewResult(passed=False, suggestions=data.get("suggestions", []))
