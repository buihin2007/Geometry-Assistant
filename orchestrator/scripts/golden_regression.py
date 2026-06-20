"""Chạy golden set qua ggb-service và kiểm hồi quy (PLAN §11 / §12 Phase 8).

Mỗi cặp golden phải: (a) mọi lệnh evalCommand thành công, (b) mọi object defined,
(c) không suy biến. Đây là bộ test xác nhận lệnh GeoGebra còn đúng cú pháp.

Cách chạy (cần ggb-service đang chạy):
    GGB_SERVICE_URL=http://localhost:8081 ./.venv/Scripts/python -m scripts.golden_regression
"""
import asyncio
import os
import sys

# Cho phép chạy như `python -m scripts.golden_regression` hoặc trực tiếp.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ggb_client import GgbClient
from app.agents.validator import validate
from app.prompts.golden import GOLDEN


async def main() -> int:
    url = os.environ.get("GGB_SERVICE_URL", "http://localhost:8081")
    client = GgbClient(url)
    failures = 0

    for i, ex in enumerate(GOLDEN, 1):
        asserts = ex.get("asserts", [])
        try:
            render = await client.render(ex["commands"], ["png"], checks=asserts)
        except Exception as e:
            print(f"[{i}] LỖI gọi render: {e}")
            failures += 1
            continue
        result = validate(ex["commands"], render)
        status = "OK " if result.ok else "FAIL"
        chk = render.get("checkResults", [])
        chk_str = " ".join(f"{c['expr']}={c['value']}" for c in chk)
        print(f"[{i}] {status} — {ex['problem'][:55]}")
        if chk_str:
            print(f"      asserts: {chk_str}")
        if result.warnings:
            for w in result.warnings:
                print(f"      ⚠ {w}")
        if not result.ok:
            failures += 1
            for err in result.errors:
                print(f"      • {err}")

    total = len(GOLDEN)
    print(f"\n{total - failures}/{total} cặp đạt.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
