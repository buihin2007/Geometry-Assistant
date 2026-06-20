"""Sinh MENU primitive (đóng) để nhồi vào prompt Planner (đặc tả PHẦN 2).
Mỗi dòng: op(args) -> n output  — mô tả — khi nào dùng.
"""
from .registry import PRIMITIVES


def build_menu(compact: bool = True) -> str:
    """compact=True: gọn token (name(args)→N: desc) để vừa rate-limit + nhanh/rẻ.
    compact=False: kèm cả 'dùng khi' (chi tiết hơn, tốn token hơn)."""
    lines = []
    for p in PRIMITIVES.values():
        sig = ",".join(p.args)
        if compact:
            lines.append(f"{p.name}({sig})→{p.n_out}: {p.desc}")
        else:
            lines.append(f"- {p.name}({sig}) → {p.n_out} out | {p.desc} | dùng khi: {p.when}")
    return "\n".join(lines)
