import re
from dataclasses import dataclass, field

# Technical Validator (PLAN §6.2) — DETERMINISTIC, không phải LLM.
# Đọc kết quả render từ Node và phát hiện lỗi cứng:
#  - lệnh báo lỗi (evalCommand false)
#  - đối tượng undefined
#  - suy biến: tam giác diện tích ≈ 0, bán kính ≤ 0, điểm trùng
#  - assert quan hệ đề-nêu-tên không thỏa (tiếp tuyến, nội tiếp, vuông góc...)
# Ngoài ra cảnh báo (không chặn) khi còn nét thừa: đường vô hạn trung gian chưa ẩn.

DEGENERATE_AREA_EPS = 1e-6
DEGENERATE_RADIUS_EPS = 1e-9

# Lệnh sinh đối tượng VÔ HẠN — nếu chỉ dùng làm trung gian (có điểm Intersect phụ
# thuộc) mà vẫn hiển thị thì là nét thừa (PLAN Vấn đề 2).
INFINITE_CMDS = ("Line", "PerpendicularLine", "PerpendicularBisector", "LineBisector",
                 "AngleBisector", "Tangent")
INFINITE_TYPES = ("line",)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def feedback_text(self) -> str:
        return "\n".join(f"- {e}" for e in self.errors + self.warnings)


def _assigned_name(command: str) -> str | None:
    # "tAB=Segment(A,B)" -> "tAB"; bỏ khoảng trắng, lấy vế trái trước dấu '='.
    m = re.match(r"\s*([A-Za-z_]\w*)\s*=", command)
    return m.group(1) if m else None


def _base(name: str) -> str:
    # "auxT_{1}" -> "auxt" (bỏ subscript, lowercase) để so khớp tên.
    return re.sub(r"_\{?.*$", "", str(name)).lower()


def _seg_cross(p, q, r, s) -> bool:
    """Hai đoạn pq, rs có cắt nhau ở điểm TRONG (proper intersection) không."""
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = cr(p, q, r), cr(p, q, s)
    d3, d4 = cr(r, s, p), cr(r, s, q)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def _point_xy(objects: list[dict]) -> dict:
    """name (kể cả alias bỏ ngoặc subscript) → (x,y) cho các điểm có tọa độ."""
    m = {}
    for o in objects:
        if (o.get("type") or "").lower() == "point" and o.get("x") is not None:
            xy = (float(o["x"]), float(o["y"]))
            n = o["name"]
            m[n] = xy
            m[n.replace("_{", "_").replace("}", "")] = xy
    return m


def _check_quad_order(commands: list[str], objects: list[dict]) -> list[str]:
    """Mọi Polygon 4 đỉnh phải đi VÒNG QUANH (đa giác đơn): cạnh đối không cắt nhau.
    Thứ tự sai (vd ABCD bắt chéo) ⇒ 'đường chéo' thành AD/BC thay vì AC/BD."""
    errors = []
    pts = _point_xy(objects)
    for cmd in commands:
        m = re.search(r"=\s*Polygon\(([^)]*)\)", cmd)
        if not m:
            continue
        names = [a.strip() for a in m.group(1).split(",")]
        if len(names) != 4 or not all(n in pts for n in names):
            continue
        a, b, c, d = (pts[n] for n in names)
        # đa giác đơn ⟺ cạnh đối (AB,CD) và (BC,DA) KHÔNG cắt nhau
        if _seg_cross(a, b, c, d) or _seg_cross(b, c, d, a):
            errors.append(
                f"Tứ giác {''.join(names)} SAI THỨ TỰ ĐỈNH (các cạnh cắt nhau). Đỉnh phải đi "
                f"vòng quanh {names[0]}→{names[1]}→{names[2]}→{names[3]}; đường chéo là "
                f"{names[0]}{names[2]} và {names[1]}{names[3]}. Đặt lại tọa độ/đỉnh cho đúng vòng."
            )
    return errors


def validate(commands: list[str], render: dict) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    # 1) Lệnh báo lỗi trực tiếp.
    for st in render.get("perCommandStatus", []):
        if not st.get("ok"):
            errors.append(
                f"Lệnh #{st['index']+1} `{st['command']}` lỗi: "
                f"{st.get('error') or 'không dựng được'}"
            )

    # 2) Đối tượng undefined (cú pháp đúng nhưng quan hệ không dựng được,
    #    vd Circle(A,-3), Intersect hai đường song song).
    objects = render.get("objects", [])
    for o in objects:
        if not o.get("defined", True):
            errors.append(
                f"Đối tượng `{o['name']}` (type {o.get('type') or '?'}) bị undefined "
                "— quan hệ không dựng được, xem lại lệnh tạo nó."
            )

    # 3) Suy biến theo giá trị số.
    by_name = {o["name"]: o for o in objects}
    for o in objects:
        otype = (o.get("type") or "").lower()
        val = o.get("value")
        if val is None:
            continue
        if otype in ("triangle", "polygon") and abs(val) < DEGENERATE_AREA_EPS:
            errors.append(
                f"Tam giác/đa giác `{o['name']}` có diện tích ≈ 0 "
                "— ba điểm thẳng hàng. Đặt lại tọa độ điểm tự do cho không thẳng hàng."
            )
        if otype in ("circle", "conic") and val <= DEGENERATE_RADIUS_EPS:
            errors.append(
                f"Đường tròn `{o['name']}` bán kính ≤ 0 — không hợp lệ."
            )

    # 4) Assert quan hệ ĐỀ NÊU TÊN (tiếp tuyến/nội tiếp/vuông góc/thẳng hàng...).
    #    Node đã đánh giá bằng lệnh boolean GeoGebra (IsTangent, AreCollinear...).
    #    value: 1 = đúng, 0 = SAI quan hệ, null = không tính được (assert hỏng).
    for chk in render.get("checkResults", []) or []:
        val = chk.get("value")
        expr = chk.get("expr")
        if val == 0:
            errors.append(
                f"Quan hệ `{expr}` KHÔNG thỏa — hình dựng sai quan hệ đề yêu cầu. "
                "Dựng lại đúng quan hệ (vd dùng Tangent(...) cho tiếp tuyến, "
                "Circle(A,B,C) cho ngoại tiếp)."
            )
        elif val is None:
            warnings.append(
                f"Không kiểm chứng được quan hệ `{expr}` (assert sai cú pháp hoặc "
                "tham chiếu đối tượng không tồn tại)."
            )

    # 5) Thứ tự đỉnh tứ giác (đa giác đơn) — bắt lỗi "ABCD bắt chéo" làm AC/BD không
    #    còn là đường chéo. Đọc tọa độ điểm từ render (đã export hình học).
    errors.extend(_check_quad_order(commands, objects))

    # (Đã bỏ cảnh báo "nét thừa" cho đường vô hạn hiển thị: đường do ĐỀ NÊU TÊN — như
    #  "đường thẳng d" — cần được HIỆN. Việc ẩn công cụ trung gian do planner quyết
    #  định qua quy ước đặt tên aux*, không ép ở validator.)

    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)
