"""Bộ ĐO end-to-end (qua LLM) — đo % vẽ ĐÚNG thật của planner trên đề thi-vào-10.

Khác coverage_plans (golden plan tất định, không LLM): ở đây CHẠY THẬT planner →
compiler → render → verifier → (escalate). Mục tiêu: có SỐ ĐO + phân loại nguyên nhân
fail để biết sửa gì trước, thay vì sửa mù. Bạn thêm đề dần vào CASES.

Phân loại:
  PASS    : verified, không cảnh báo, không partial.
  PASS*   : verified nhưng còn cảnh báo nhỏ (vd nét thừa/review chưa hoàn hảo).
  PARTIAL : chỉ dựng được một phần (vượt tầm / thiếu primitive).
  FAIL    : không verified / không ra hình.

Chạy:  GGB_SERVICE_URL=<url> ENABLE_REVIEW=false \
          ./.venv/Scripts/python -u -m scripts.eval_set
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import get_settings
from app.pipeline import Pipeline

# ~30 đề thi-vào-10 điển hình (đại diện các nhóm cấu hình; bạn phát triển thêm).
CASES = [
    # — Tam giác & đường/điểm đặc biệt —
    ("TG01", "Vẽ tam giác ABC."),
    ("TG02", "Vẽ tam giác ABC cân tại A."),
    ("TG03", "Vẽ tam giác ABC vuông tại A."),
    ("TG04", "Cho tam giác ABC, kẻ đường cao AH xuống BC."),
    ("TG05", "Cho tam giác ABC, vẽ trung tuyến AM."),
    ("TG06", "Cho tam giác ABC, vẽ tia phân giác AD của góc A (D thuộc BC)."),
    ("TG07", "Cho tam giác ABC, xác định trọng tâm G."),
    ("TG08", "Cho tam giác ABC nhọn, xác định trực tâm H."),
    ("TG09", "Cho tam giác ABC, xác định tâm I của đường tròn nội tiếp."),
    ("TG10", "Cho tam giác ABC, xác định tâm O của đường tròn ngoại tiếp."),
    # — Đường tròn & tiếp tuyến —
    ("DT01", "Cho tam giác ABC nội tiếp đường tròn tâm O."),
    ("DT02", "Cho tam giác ABC, vẽ đường tròn nội tiếp tâm I."),
    ("DT03", "Cho đường tròn (O), từ điểm A ngoài đường tròn kẻ hai tiếp tuyến AB, AC (B, C là tiếp điểm)."),
    ("DT04", "Cho đường tròn (O) đường kính AB, vẽ tiếp tuyến tại A."),
    ("DT05", "Cho đường tròn tâm O bán kính 3, vẽ một dây cung MN."),
    ("DT06", "Cho tam giác ABC, vẽ đường tròn đường kính BC."),
    ("DT07", "Cho nửa đường tròn đường kính MN, lấy điểm P trên nửa đường tròn."),
    ("DT08", "Cho đường tròn (O), hai dây AB và CD cắt nhau tại điểm E bên trong."),
    # — Tứ giác —
    ("TU01", "Vẽ hình bình hành ABCD, hai đường chéo cắt nhau tại O."),
    ("TU02", "Vẽ hình chữ nhật ABCD."),
    ("TU03", "Vẽ hình vuông ABCD, hai đường chéo cắt nhau tại O."),
    ("TU04", "Vẽ hình thoi ABCD có góc BAD bằng 60 độ."),
    ("TU05", "Vẽ hình thang ABCD (AB song song CD), hai đường chéo AC và BD cắt nhau tại I."),
    ("TU06", "Vẽ hình thang cân ABCD (AB song song CD)."),
    ("TU07", "Cho tứ giác ABCD nội tiếp đường tròn tâm O."),
    # — Tổng hợp nhiều bước (thi vào 10) —
    ("TH01", "Cho tam giác ABC nhọn nội tiếp đường tròn (O), các đường cao BE và CF cắt nhau tại H."),
    ("TH02", "Cho đường tròn (O) và điểm A ngoài đường tròn, kẻ hai tiếp tuyến AB, AC; OA cắt BC tại H."),
    ("TH03", "Cho tam giác ABC nội tiếp (O), tiếp tuyến tại B và C cắt nhau tại P."),
    ("TH04", "Cho tam giác ABC, M là trung điểm BC, từ M kẻ vuông góc xuống AB tại K và xuống AC tại L."),
    ("TH05", "Cho hình vuông ABCD, lấy M là trung điểm BC, N là trung điểm CD, nối AM và AN."),
]


def classify(res) -> str:
    if res.partial:
        return "PARTIAL"
    if res.verified:
        return "PASS" if not res.warnings else "PASS*"
    return "FAIL"


async def main() -> int:
    s = get_settings()
    if os.environ.get("ENABLE_REVIEW", "").lower() in ("0", "false", ""):
        s.enable_review = False
    pipe = Pipeline(s)
    counts: dict[str, int] = {}
    rows = []
    for cid, prob in CASES:
        try:
            res = await pipe.run(prob)
            tag = classify(res)
            note = ""
            if tag in ("PARTIAL", "FAIL", "PASS*"):
                note = (res.warnings[0] if res.warnings else "")[:80]
            esc = " ESC" if any("escalate" in l for l in res.log) else ""
            rows.append((cid, tag, esc, res.rounds, len(res.commands), note))
        except Exception as e:
            tag = "ERROR"
            rows.append((cid, tag, "", "-", 0, str(e)[:80]))
        counts[tag] = counts.get(tag, 0) + 1
        last = rows[-1]
        print(f"{last[1]:8}{last[2]:4} {cid}  r{last[3]} cmds={last[4]}  {last[5]}",
              flush=True)

    print("\n=== TỔNG ===")
    for k in ("PASS", "PASS*", "PARTIAL", "FAIL", "ERROR"):
        if counts.get(k):
            print(f"  {k:8}: {counts[k]}")
    npass = counts.get("PASS", 0) + counts.get("PASS*", 0)
    print(f"  → dựng hợp lệ {npass}/{len(CASES)} = {100*npass//len(CASES)}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
