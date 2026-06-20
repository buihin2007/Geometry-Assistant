"""Coverage checklist THCS (đặc tả PHẦN 3) chạy như test hồi quy end-to-end.

Mỗi mục: đề test → pipeline (planner→compiler→render→validator). Trạng thái:
  ☑ pass  : ra lệnh, không lỗi/cảnh báo, KHÔNG phải rớt về generator (đi đúng primitive).
  ◐ escape: chạy được nhưng qua escape hatch (generator/RAW) → cần thêm primitive.
  ☐ fail  : lỗi / không ra hình.

Chạy (cần ggb-service + planner provider trong .env):
    GGB_SERVICE_URL=http://localhost:8081 ENABLE_REVIEW=false \
        ./.venv/Scripts/python -m scripts.coverage_test
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.pipeline import Pipeline

CASES = [
    ("B01", "Vẽ đoạn AB và trung điểm M"),
    ("B02", "Vẽ đường thẳng d, điểm A ngoài d, kẻ AH vuông góc d"),
    ("B03", "Cho đường thẳng d và điểm A ngoài d, qua A kẻ đường song song với d"),
    ("B04", "Vẽ trung trực của đoạn AB"),
    ("B05", "Vẽ tia phân giác của góc xOy"),
    ("T01", "Vẽ tam giác ABC"),
    ("T02", "Vẽ tam giác ABC cân tại A"),
    ("T03", "Tam giác ABC, kẻ đường cao AH"),
    ("T04", "Tam giác ABC có ba đường cao, xác định trực tâm H"),
    ("T05", "Vẽ tam giác ABC, ba trung tuyến và trọng tâm G"),
    ("T06", "Tam giác ABC, phân giác trong góc A cắt BC tại D"),
    ("T07", "Tam giác ABC, xác định tâm đường tròn ngoại tiếp O"),
    ("T08", "Vẽ đường trung bình của tam giác ABC"),
    ("T09", "Tam giác ABC có đường tròn nội tiếp tâm I"),
    ("C01", "Vẽ đường tròn tâm O bán kính 3"),
    ("C02", "Tam giác ABC nội tiếp đường tròn tâm O"),
    ("C03", "Đường tròn (O), vẽ dây AB và đường kính CD"),
    ("C04", "Đường tròn (O), góc nội tiếp BAC chắn cung BC"),
    ("C05", "Từ điểm A ngoài (O) kẻ hai tiếp tuyến AB, AC"),
    ("C06", "Vẽ tiếp tuyến của đường tròn (O) tại điểm A trên đường tròn"),
    ("C07", "Hai đường tròn (O) và (O') cắt nhau tại A, B"),
    ("C08", "Vẽ nửa đường tròn đường kính MN"),
    ("Q01", "Hình bình hành ABCD, hai đường chéo cắt nhau tại O"),
    ("Q02", "Vẽ hình chữ nhật ABCD"),
    ("Q03", "Vẽ hình vuông ABCD"),
    ("Q04", "Hình thoi ABCD, vẽ hai đường chéo"),
    ("Q05", "Vẽ hình thang ABCD có AB song song CD"),
    ("S01", "Vẽ điểm A' đối xứng với A qua đường thẳng d"),
    ("S02", "Vẽ điểm A' đối xứng với A qua điểm O"),
    ("X01", "Nửa đường tròn đường kính MN, lấy P trên MO, từ P kẻ vuông góc MN cắt nửa đường tròn tại Q"),
    ("X03", "Từ A ngoài (O) kẻ hai tiếp tuyến AB, AC; đoạn OA cắt BC tại H"),
]


async def main() -> int:
    settings = get_settings()
    pipe = Pipeline(settings)
    # Pacing: Groq free tier giới hạn 12k token/phút; prompt planner lớn nên giãn cách
    # các case để không vượt TPM (đọc PACE_SECONDS từ env, mặc định 20s).
    pace = float(os.environ.get("PACE_SECONDS", "20"))
    rows = []
    for i, (cid, problem) in enumerate(CASES):
        if i:
            time.sleep(pace)
        try:
            res = await pipe.run(problem, formats=["png"])
            escaped = any("escape" in x or "generator →" in x for x in res.log)
            has_png = bool(res.png_base64)
            if not has_png or not res.commands:
                status = "☐ fail"
            elif escaped:
                status = "◐ escape"
            elif res.warnings:
                status = "◐ warn"
            else:
                status = "☑ pass"
        except Exception as e:
            status = f"☐ fail ({e})"
        print(f"{status:10} {cid}  {problem[:50]}")
        rows.append(status)

    n_pass = sum(1 for r in rows if r.startswith("☑"))
    n_part = sum(1 for r in rows if r.startswith("◐"))
    print(f"\n☑ {n_pass}  ◐ {n_part}  ☐ {len(rows)-n_pass-n_part}  / {len(rows)} mục")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
