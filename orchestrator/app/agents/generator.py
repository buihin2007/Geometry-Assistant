import json
import re
from ..llm.base import LLMProvider
from ..prompts.cheatsheet import CHEATSHEET
from ..prompts.golden import format_fewshot

SYSTEM = f"""\
Bạn là trợ lý dựng hình học phẳng bằng lệnh GeoGebra cho giáo viên THCS Việt Nam.

NGUYÊN TẮC CỐT LÕI: bạn MÔ TẢ QUAN HỆ, KHÔNG đoán tọa độ cho đối tượng phụ thuộc.
Chỉ điểm TỰ DO mới có tọa độ; mọi thứ khác để GeoGebra tự tính.

{CHEATSHEET}

ĐỊNH DẠNG OUTPUT (bắt buộc): chỉ trả về JSON đúng dạng:
{{"commands": ["...", "..."], "asserts": ["...", "..."]}}
Không kèm giải thích, không markdown, không ```.

"asserts" = các biểu thức BOOLEAN GeoGebra kiểm chứng QUAN HỆ mà đề NÊU TÊN, kỳ vọng
ĐÚNG (true). Hệ thống sẽ tự đánh giá; nếu sai sẽ bắt bạn dựng lại. Dùng các lệnh:
- Tiếp tuyến:   IsTangent(auxT_1,circ)   (cho mỗi tiếp tuyến)
- Thẳng hàng:   AreCollinear(A,B,C)
- Vuông góc:    ArePerpendicular(aux_h,Line(B,C))
- Song song:    AreParallel(d1,d2)
- Bằng nhau:    AreEqual(Distance(O,B),Radius(circ))
- Đồng quy:     AreConcurrent(med_a,med_b,med_c)
- Nội tiếp (điểm trên đường tròn): AreEqual(Distance(A,O),Radius(circ))
Chỉ thêm assert cho quan hệ đề THỰC SỰ nêu; đề đơn giản có thể để "asserts": [].

VÍ DỤ MẪU (golden set):
{format_fewshot()}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Bóc khối ```json ... ``` nếu model lỡ bọc.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # Tìm object JSON đầu tiên.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


# Dấu hiệu đề "nhiều mệnh đề phụ thuộc liên tiếp" → nên phân tích trước (PLAN Vấn đề 3).
_COMPLEX_MARKERS = ("rồi", "từ đó", "sau đó", "tiếp theo", "lần lượt", "gọi ",
                    "cắt", "kéo dài", "trên tia", "trên đoạn", "trên cạnh")

ANALYSIS_SYSTEM = """\
Bạn phân tích đề hình học phẳng tiếng Việt thành DANH SÁCH đối tượng cần dựng, theo
đúng thứ tự phụ thuộc. KHÔNG viết lệnh GeoGebra. Mỗi dòng: tên — loại — phụ thuộc vào gì.
Ngắn gọn. Mục tiêu: làm rõ cấu trúc trước khi sinh lệnh.
"""


def is_complex(problem: str) -> bool:
    p = problem.lower()
    hits = sum(1 for m in _COMPLEX_MARKERS if m in p)
    return hits >= 2 or len(problem) > 140


class Generator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def analyze(self, problem: str) -> str:
        """Bước trung gian cho đề phức tạp: liệt kê đối tượng trước khi sinh lệnh."""
        return await self.provider.complete_text(
            ANALYSIS_SYSTEM, f'Đề: "{problem}"\n\nLiệt kê các đối tượng cần dựng.'
        )

    async def generate(
        self,
        problem: str,
        previous: list[str] | None = None,
        feedback: str | None = None,
        analysis: str | None = None,
    ) -> tuple[list[str], list[str]]:
        """Trả (commands, asserts). asserts = biểu thức boolean GeoGebra kỳ vọng đúng
        để Validator kiểm chứng quan hệ đề nêu tên (PLAN Vấn đề 1)."""
        analysis_block = (
            f"Phân tích đối tượng cần dựng (theo thứ tự):\n{analysis}\n\n" if analysis else ""
        )
        if previous and feedback:
            user = (
                f'Đề: "{problem}"\n\n'
                f"{analysis_block}"
                f"Lệnh trước đó:\n{json.dumps(previous, ensure_ascii=False)}\n\n"
                f"Vấn đề cần sửa:\n{feedback}\n\n"
                "Trả về JSON {commands, asserts} ĐÃ SỬA hoàn chỉnh (cả danh sách)."
            )
        else:
            user = f'Đề: "{problem}"\n\n{analysis_block}Trả về JSON {{commands, asserts}}.'

        raw = await self.provider.complete_text(SYSTEM, user)
        data = _extract_json(raw)
        commands = data.get("commands", [])
        if not isinstance(commands, list) or not all(isinstance(c, str) for c in commands):
            raise ValueError(f"Generator trả commands không hợp lệ: {raw[:300]}")
        asserts = data.get("asserts", []) or []
        if not isinstance(asserts, list):
            asserts = []
        asserts = [a.strip() for a in asserts if isinstance(a, str) and a.strip()]
        return [c.strip() for c in commands if c and c.strip()], asserts
