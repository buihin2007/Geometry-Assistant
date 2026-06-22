"""Sửa TẤT ĐỊNH thứ tự đỉnh tứ giác (không cần LLM): nếu Polygon 4 đỉnh bị BẮT CHÉO
(các cạnh đối cắt nhau ⇒ AC/BD hết là đường chéo), GÁN LẠI tọa độ 4 nhãn theo thứ tự
VÒNG QUANH (sắp theo góc quanh trọng tâm) ⇒ A→B→C→D đi vòng, AC & BD là đường chéo.

Chỉ gán lại giữa các đỉnh là ĐIỂM TỰ DO (X=(a,b)) — giữ nguyên tập 4 vị trí (cùng hình),
chỉ đổi nhãn để không bắt chéo. Đỉnh phụ thuộc (primitive đã dựng đúng) → bỏ qua.
"""
import math
import re

_POLY = re.compile(r"^(\w+)\s*=\s*Polygon\(([^)]*)\)\s*$")
_FREE = re.compile(r"^(\w+)\s*=\s*\(\s*-?[\d.]+\s*,\s*-?[\d.]+\s*\)\s*$")


def _seg_cross(p, q, r, s):
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    return (cr(p, q, r) > 0) != (cr(p, q, s) > 0) and (cr(r, s, p) > 0) != (cr(r, s, q) > 0)


def reorder_crossed_quads(commands: list[str], objects: list[dict]) -> tuple[list[str], bool]:
    pts = {
        o["name"]: (float(o["x"]), float(o["y"]))
        for o in objects
        if (o.get("type") or "").lower() == "point" and o.get("x") is not None
    }
    free_idx = {m.group(1): i for i, c in enumerate(commands) if (m := _FREE.match(c.strip()))}
    cmds = list(commands)
    changed = False

    for cmd in commands:
        m = _POLY.match(cmd.strip())
        if not m:
            continue
        vs = [v.strip() for v in m.group(2).split(",")]
        if len(vs) != 4 or not all(v in pts for v in vs):
            continue
        a, b, c, d = (pts[v] for v in vs)
        if not (_seg_cross(a, b, c, d) or _seg_cross(b, c, d, a)):
            continue  # đã đơn (không chéo)
        if not all(v in free_idx for v in vs):
            continue  # có đỉnh phụ thuộc (primitive) → không tự ý dời
        # sắp 4 vị trí theo góc quanh trọng tâm (vòng CCW) rồi gán lại cho A,B,C,D
        cx = sum(p[0] for p in (a, b, c, d)) / 4
        cy = sum(p[1] for p in (a, b, c, d)) / 4
        ordered = sorted([a, b, c, d], key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        for v, pos in zip(vs, ordered):
            cmds[free_idx[v]] = f"{v}=({pos[0]:.6f},{pos[1]:.6f})"
        changed = True

    return cmds, changed
