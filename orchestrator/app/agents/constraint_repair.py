"""Sửa CƠ HỌC (deterministic, không LLM) khi ràng buộc bất đẳng thức khoảng cách bị
vi phạm — ưu tiên dùng trước khi tốn vòng LLM (ràng buộc "sao cho").

Ca phủ: điểm P trên ĐƯỜNG TRÒN/CUNG (P=Point(...)) với Distance(P,X) </> Distance(P,Y).
"P gần X hơn Y" ⟺ P cùng phía X so với trung trực XY. Đặt P về điểm trên đường tròn
NGHIÊNG HẲN về phía X: target = O + r·unit(X−Y) (xử lý được cả ca P đang cách đều X,Y,
nơi phản chiếu qua trung trực là vô tác dụng). Thêm SetCoords(P,target) → P snap về path,
VẪN kéo được. Ca không suy ra được tâm/path → changed=False để pipeline fallback LLM.
"""
import math
import re

from .geometry_verify import build_geometry, Pt, Cir

_DIST = re.compile(r"^Distance\(\s*(\w+)\s*,\s*(\w+)\s*\)$")
_POINT_OF = re.compile(r"^(\w+)\s*=\s*Point\((\w+)")          # P = Point(obj...)
_ARC_OF = re.compile(r"^(\w+)\s*=\s*CircularArc\((\w+)\s*,")  # arc = CircularArc(O,...)


def repair_distance_constraints(
    commands: list[str], violated: list[dict], objects: list[dict]
) -> tuple[list[str], bool]:
    geo = build_geometry(objects)
    cmds = list(commands)
    changed = False
    point_of = {m.group(1): m.group(2) for c in cmds if (m := _POINT_OF.match(c.strip()))}
    arc_center = {m.group(1): m.group(2) for c in cmds if (m := _ARC_OF.match(c.strip()))}

    def circle_of(P):
        """(center Pt, radius) của đường tròn/cung mà P nằm trên, hoặc None."""
        obj = point_of.get(P)
        if obj is None:
            return None
        g = geo.get(obj)
        if isinstance(g, Cir):
            return Pt(g.cx, g.cy), g.r
        if obj in arc_center and isinstance(geo.get(arc_center[obj]), Pt):
            return geo[arc_center[obj]], None  # bán kính suy từ điểm tham chiếu sau
        return None

    for c in violated:
        rel = c.get("rel")
        if rel not in ("lt", "gt", "le", "ge"):
            continue
        lm = _DIST.match(c["lhs"].strip())
        rm = _DIST.match(c["rhs"].strip())
        if not lm or not rm or lm.group(1) != rm.group(1):
            continue
        P, X, Y = lm.group(1), lm.group(2), rm.group(2)
        near, far = (X, Y) if rel in ("lt", "le") else (Y, X)  # P GẦN 'near' hơn 'far'
        if not all(isinstance(geo.get(n), Pt) for n in (P, X, Y)):
            continue
        co = circle_of(P)
        if not co:
            continue
        O, r = co
        n, f = geo[near], geo[far]
        ux, uy = n.x - f.x, n.y - f.y
        uu = math.hypot(ux, uy)
        if uu < 1e-9:
            continue
        ux, uy = ux / uu, uy / uu
        # THIÊN VỀ PHÍA TRÊN: cộng vector hướng lên để A nằm NỬA TRÊN (đỉnh) chứ không
        # rơi xuống cạnh/đáy — vẫn giữ thành phần ngang về phía 'near' nên AB<AC vẫn đúng.
        bx, by = ux, uy + 1.0
        bn = math.hypot(bx, by)
        if bn < 0.1:  # near ngay dưới far → bỏ thiên hướng, dùng hướng ngang
            bx, by, bn = ux, uy, 1.0
        bx, by = bx / bn, by / bn
        if r is None:
            r = math.hypot(n.x - O.x, n.y - O.y)
        tx, ty = O.x + r * bx, O.y + r * by  # trên đtròn: phía 'near' và NỬA TRÊN
        cmds.append(f"SetCoords({P},{tx:.6f},{ty:.6f})")
        changed = True

    return cmds, changed
