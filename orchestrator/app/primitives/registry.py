"""Thư viện primitive THCS (đặc tả PHẦN 1) — mỗi primitive là một TEMPLATE tất định
sinh lệnh GeoGebra. Lệnh tên tiếng Anh, ngoặc tròn.

NGUYÊN TẮC: cột "GeoGebra (nháp)" trong spec CHỈ là gợi ý — mọi template phải verify
trên applet thật (scripts/verify_primitives.py) rồi mới khóa. Hành vi đã verify ghi
chú ngay tại template:
  - Semicircle(M,N): cung nằm BÊN TRÁI vector M→N (M trái, N phải ⇒ nửa trên).
  - Intersect(line,circle) BẮT BUỘC có index (1/2); không index trả rác (0,0).
  - Rotate(P,90°,c)=ngược chiều kim đồng hồ; UnitPerpendicularVector=vuông trái (CCW).

build(args, out, aux) -> (commands, asserts):
  args : dict tên→(tên GeoGebra đã có | số literal | list tên cho variadic)
  out  : list tên đối tượng cần tạo (chính là tên GeoGebra dùng về sau)
  aux  : () -> tên phụ duy nhất bắt đầu "auxN" (tự ẩn ở render & applet)
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Primitive:
    name: str
    args: list[str]          # tên tham số (ref hoặc literal)
    n_out: int               # số output
    desc: str                # 1 dòng mô tả (cho menu planner)
    when: str                # khi nào dùng (cho menu planner)
    build: Callable          # (args, out, aux) -> (cmds, asserts)
    test: list[dict] = field(default_factory=list)  # plan tự chứa để verify
    literals: list[str] = field(default_factory=list)  # arg nào là số


def _others(vertex, a, b, c):
    return [p for p in (a, b, c) if p != vertex]


# ───────────────────────── A. Điểm & đối tượng cơ bản ─────────────────────────
def _point_free(ar, o, aux):
    return [f"{o[0]}=({ar['x']},{ar['y']})"], []


def _point_on_segment(ar, o, aux):
    return [f"{o[0]}={ar['A']}+{ar['t']}*({ar['B']}-{ar['A']})"], []


def _point_on_ray_beyond(ar, o, aux):
    return [f"{o[0]}={ar['P']}+{ar['t']}*({ar['Q']}-{ar['P']})"], []


def _point_on_object(ar, o, aux):
    return [f"{o[0]}=Point({ar['path']})"], []


def _midpoint(ar, o, aux):
    return [f"{o[0]}=Midpoint({ar['A']},{ar['B']})"], []


def _segment(ar, o, aux):
    return [f"{o[0]}=Segment({ar['A']},{ar['B']})"], []


def _line(ar, o, aux):
    return [f"{o[0]}=Line({ar['A']},{ar['B']})"], []


def _ray(ar, o, aux):
    return [f"{o[0]}=Ray({ar['A']},{ar['B']})"], []


def _distance(ar, o, aux):
    return [f"{o[0]}=Distance({ar['A']},{ar['B']})"], []


# ───────────────────────── B. Quan hệ đường thẳng ─────────────────────────
def _parallel_through(ar, o, aux):
    return [f"{o[0]}=Line({ar['P']},{ar['line']})"], [f"AreParallel({o[0]},{ar['line']})"]


def _perpendicular_through(ar, o, aux):
    return [f"{o[0]}=PerpendicularLine({ar['P']},{ar['line']})"], [
        f"ArePerpendicular({o[0]},{ar['line']})"
    ]


def _foot_of_perpendicular(ar, o, aux):
    # H = chân vuông góc; đoạn PH hiển thị (không có đường vô hạn).
    H, seg = o[0], o[1]
    return (
        [f"{H}=ClosestPoint({ar['line']},{ar['P']})", f"{seg}=Segment({ar['P']},{H})"],
        [f"ArePerpendicular(Line({ar['P']},{H}),{ar['line']})"],
    )


def _perpendicular_bisector(ar, o, aux):
    return [f"{o[0]}=PerpendicularBisector({ar['A']},{ar['B']})"], []


def _angle_bisector(ar, o, aux):
    return [f"{o[0]}=AngleBisector({ar['A']},{ar['B']},{ar['C']})"], []


def _intersect(ar, o, aux):
    # Giao đường-đường (1 nghiệm). index chỉ dùng khi có nhiều nghiệm.
    if "index" in ar:
        return [f"{o[0]}=Intersect({ar['obj1']},{ar['obj2']},{ar['index']})"], []
    return [f"{o[0]}=Intersect({ar['obj1']},{ar['obj2']})"], []


# ───────────────────────── C. Tam giác ─────────────────────────
def _triangle(ar, o, aux):
    return [f"{o[0]}=Polygon({ar['A']},{ar['B']},{ar['C']})"], []


def _triangle_equilateral(ar, o, aux):
    C, poly = o[0], o[1]
    return (
        [f"{C}=Rotate({ar['B']},60°,{ar['A']})", f"{poly}=Polygon({ar['A']},{ar['B']},{C})"],
        [f"AreEqual(Distance({ar['A']},{ar['B']}),Distance({ar['B']},{C}))",
         f"AreEqual(Distance({ar['A']},{ar['B']}),Distance({ar['A']},{C}))"],
    )


def _triangle_isosceles(ar, o, aux):
    C, poly = o[0], o[1]
    m, v = aux(), aux()
    return (
        [f"{m}=Midpoint({ar['A']},{ar['B']})",
         f"{v}=UnitPerpendicularVector(Vector({ar['A']},{ar['B']}))",
         f"{C}={m}+{ar['h']}*{v}",
         f"{poly}=Polygon({ar['A']},{ar['B']},{C})"],
        [f"AreEqual(Distance({C},{ar['A']}),Distance({C},{ar['B']}))"],
    )


def _triangle_right(ar, o, aux):
    # Góc vuông tại A; cạnh góc vuông AC dài h, vuông góc AB.
    C, poly = o[0], o[1]
    v = aux()
    return (
        [f"{v}=UnitPerpendicularVector(Vector({ar['A']},{ar['B']}))",
         f"{C}={ar['A']}+{ar['h']}*{v}",
         f"{poly}=Polygon({ar['A']},{ar['B']},{C})"],
        [f"ArePerpendicular(Line({ar['A']},{ar['B']}),Line({ar['A']},{C}))"],
    )


def _altitude(ar, o, aux):
    H, seg = o[0], o[1]
    o1, o2 = _others(ar["vertex"], ar["A"], ar["B"], ar["C"])
    L = aux()
    return (
        [f"{L}=PerpendicularLine({ar['vertex']},Line({o1},{o2}))",
         f"{H}=Intersect({L},Line({o1},{o2}))",
         f"{seg}=Segment({ar['vertex']},{H})"],
        [f"ArePerpendicular({L},Line({o1},{o2}))"],
    )


def _median(ar, o, aux):
    M, seg = o[0], o[1]
    o1, o2 = _others(ar["vertex"], ar["A"], ar["B"], ar["C"])
    return [f"{M}=Midpoint({o1},{o2})", f"{seg}=Segment({ar['vertex']},{M})"], []


def _angle_bisector_seg(ar, o, aux):
    D, seg = o[0], o[1]
    o1, o2 = _others(ar["vertex"], ar["A"], ar["B"], ar["C"])
    L = aux()
    return (
        [f"{L}=AngleBisector({o1},{ar['vertex']},{o2})",
         f"{D}=Intersect({L},Line({o1},{o2}))",
         f"{seg}=Segment({ar['vertex']},{D})"],
        [],
    )


def _midsegment(ar, o, aux):
    # Nối trung điểm AB và AC (song song BC). Trung điểm để hiện (có nhãn).
    M, N, seg = o[0], o[1], o[2]
    return (
        [f"{M}=Midpoint({ar['A']},{ar['B']})",
         f"{N}=Midpoint({ar['A']},{ar['C']})",
         f"{seg}=Segment({M},{N})"],
        [f"AreParallel(Line({M},{N}),Line({ar['B']},{ar['C']}))"],
    )


def _centroid(ar, o, aux):
    return [f"{o[0]}=Centroid(Polygon({ar['A']},{ar['B']},{ar['C']}))"], []


def _orthocenter(ar, o, aux):
    H = o[0]
    la, lb = aux(), aux()
    return (
        [f"{la}=PerpendicularLine({ar['A']},Line({ar['B']},{ar['C']}))",
         f"{lb}=PerpendicularLine({ar['B']},Line({ar['A']},{ar['C']}))",
         f"{H}=Intersect({la},{lb})"],
        [],
    )


def _incenter(ar, o, aux):
    I = o[0]
    b1, b2 = aux(), aux()
    return (
        [f"{b1}=AngleBisector({ar['B']},{ar['A']},{ar['C']})",
         f"{b2}=AngleBisector({ar['A']},{ar['B']},{ar['C']})",
         f"{I}=Intersect({b1},{b2})"],
        [],
    )


def _circumcenter(ar, o, aux):
    O = o[0]
    m1, m2 = aux(), aux()
    return (
        [f"{m1}=PerpendicularBisector({ar['A']},{ar['B']})",
         f"{m2}=PerpendicularBisector({ar['B']},{ar['C']})",
         f"{O}=Intersect({m1},{m2})"],
        [],
    )


# ───────────────────────── D. Đường tròn ─────────────────────────
def _circle_center_radius(ar, o, aux):
    return [f"{o[0]}=Circle({ar['O']},{ar['r']})"], []


def _circle_center_point(ar, o, aux):
    return [f"{o[0]}=Circle({ar['O']},{ar['A']})"], []


def _circle_through_3(ar, o, aux):
    return [f"{o[0]}=Circle({ar['A']},{ar['B']},{ar['C']})"], []


def _circumcircle(ar, o, aux):
    O, c = o[0], o[1]
    return (
        [f"{c}=Circle({ar['A']},{ar['B']},{ar['C']})", f"{O}=Center({c})"],
        [f"AreEqual(Distance({ar['A']},{O}),Radius({c}))"],
    )


def _incircle(ar, o, aux):
    I, c = o[0], o[1]
    b1, b2, r = aux(), aux(), aux()
    return (
        [f"{b1}=AngleBisector({ar['B']},{ar['A']},{ar['C']})",
         f"{b2}=AngleBisector({ar['A']},{ar['B']},{ar['C']})",
         f"{I}=Intersect({b1},{b2})",
         f"{r}=Distance({I},Line({ar['A']},{ar['B']}))",
         f"{c}=Circle({I},{r})"],
        [f"IsTangent(Line({ar['A']},{ar['B']}),{c})"],
    )


def _semicircle(ar, o, aux):
    # VERIFIED: cung nằm bên TRÁI vector M→N. Tâm = trung điểm.
    s, O = o[0], o[1]
    return [f"{s}=Semicircle({ar['M']},{ar['N']})", f"{O}=Midpoint({ar['M']},{ar['N']})"], []


def _arc(ar, o, aux):
    # VERIFIED: CircularArc(O,A,B) đi ngược chiều kim đồng hồ từ A đến B.
    return [f"{o[0]}=CircularArc({ar['O']},{ar['A']},{ar['B']})"], []


def _chord(ar, o, aux):
    return [f"{o[0]}=Segment({ar['A']},{ar['B']})"], []


def _diameter_point(ar, o, aux):
    return [f"{o[0]}=Reflect({ar['A']},{ar['O']})"], []


def _tangent_from_point(ar, o, aux):
    # out = [B, C, t1, t2] (tiếp điểm + 2 đoạn tiếp tuyến hiển thị). VERIFIED.
    B, C, t1, t2 = o[0], o[1], o[2], o[3]
    T = aux()
    return (
        [f"{T}=Tangent({ar['P']},{ar['c']})",
         f"{B}=Intersect({T}_1,{ar['c']})",
         f"{C}=Intersect({T}_2,{ar['c']})",
         f"{t1}=Segment({ar['P']},{B})",
         f"{t2}=Segment({ar['P']},{C})"],
        [f"IsTangent({T}_1,{ar['c']})", f"IsTangent({T}_2,{ar['c']})"],
    )


def _tangent_at_point(ar, o, aux):
    t = o[0]
    return [f"{t}=PerpendicularLine({ar['A']},Line(Center({ar['c']}),{ar['A']}))"], [
        f"IsTangent({t},{ar['c']})"
    ]


def _intersect_line_circle(ar, o, aux):
    # VERIFIED: PHẢI có index (1/2); không index trả rác. Mặc định 1.
    idx = ar.get("index", 1)
    return [f"{o[0]}=Intersect({ar['line']},{ar['c']},{idx})"], []


def _intersect_two_circles(ar, o, aux):
    idx = ar.get("index", 1)
    return [f"{o[0]}=Intersect({ar['c1']},{ar['c2']},{idx})"], []


def _second_intersection(ar, o, aux):
    # Giao điểm THỨ HAI của đường thẳng với đường tròn (tâm center) khi đã biết MỘT
    # giao điểm `known` trên đường tròn. Cách robust, KHÔNG dùng index (index của
    # Intersect đường-đường tròn rất không ổn định): hai đầu dây cung đối xứng qua
    # chân vuông góc hạ từ tâm xuống đường thẳng ⇒ P = đối xứng của known qua chân đó.
    P = o[0]
    foot = aux()
    return (
        [f"{foot}=ClosestPoint({ar['line']},{ar['center']})",
         f"{P}=Reflect({ar['known']},{foot})"],
        [f"AreEqual(Distance({P},{ar['center']}),Distance({ar['known']},{ar['center']}))"],
    )


def _point_on_circle(ar, o, aux):
    # Điểm KÉO ĐƯỢC trên đường tròn. param∈[0,1] = vị trí ban đầu theo góc (param*360°)
    # để lấy NHIỀU điểm phân biệt. Dùng Point(c)+SetCoords (KHÔNG Point(c,param) vì param
    # cố định làm điểm KHÔNG kéo được). SetCoords snap về đường tròn, vẫn kéo dọc được.
    P, c = o[0], ar["c"]
    if "param" in ar:
        return (
            [f"{P}=Point({c})",
             f"SetCoords({P},x(Center({c}))+Radius({c})*cos({ar['param']}*360°),"
             f"y(Center({c}))+Radius({c})*sin({ar['param']}*360°))"],
            [],
        )
    # Mặc định (không param): đặt ở ĐỈNH đường tròn (y = tâm + R) — quy ước "điểm/đỉnh
    # trên đường tròn ở phía trên". Vẫn kéo được (Point(c)+SetCoords).
    return (
        [f"{P}=Point({c})", f"SetCoords({P},x(Center({c})),y(Center({c}))+Radius({c}))"],
        [],
    )


def _point_on_arc(ar, o, aux):
    # Điểm KÉO ĐƯỢC trên đường tròn (tâm O, qua hai đầu mút cung), ĐẶT BAN ĐẦU Ở ĐỈNH
    # (điểm cao nhất, y = tâm + R) theo quy ước "điểm trên cung lớn / đỉnh ở phía trên".
    # KHÔNG dùng CircularArc(O,A,B) làm vị trí vì chiều CCW của nó có thể ra cung DƯỚI
    # → điểm rơi xuống đáy. Kéo được trên cả đường tròn; ràng buộc "sao cho" (nếu có)
    # sẽ tinh chỉnh sang đúng phía mà vẫn giữ nửa trên.
    E, O, A = o[0], ar["O"], ar["A"]
    c = aux()
    return (
        [f"{c}=Circle({O},{A})",
         f"{E}=Point({c})",
         f"SetCoords({E},x({O}),y({O})+Distance({O},{A}))"],
        [f"AreEqual(Distance({E},{O}),Distance({A},{O}))"],
    )


# ───────────────────────── E. Góc ─────────────────────────
def _angle_mark(ar, o, aux):
    return [f"{o[0]}=Angle({ar['A']},{ar['B']},{ar['C']})"], []


def _right_angle_mark(ar, o, aux):
    return [f"{o[0]}=Angle({ar['A']},{ar['B']},{ar['C']})"], []


def _inscribed_angle(ar, o, aux):
    return [f"{o[0]}=Angle({ar['A']},{ar['B']},{ar['C']})"], []


# ───────────────────────── F. Tứ giác & đa giác ─────────────────────────
def _polygon(ar, o, aux):
    pts = ",".join(ar["points"])
    return [f"{o[0]}=Polygon({pts})"], []


def _parallelogram(ar, o, aux):
    D, poly = o[0], o[1]
    return (
        [f"{D}={ar['A']}+({ar['C']}-{ar['B']})",
         f"{poly}=Polygon({ar['A']},{ar['B']},{ar['C']},{D})"],
        [f"AreParallel(Line({ar['A']},{ar['B']}),Line({D},{ar['C']}))"],
    )


def _parallelogram_named(ar, o, aux):
    # Hình bình hành theo ĐÚNG chuỗi thứ tự tên 'order' (4 tên, vòng quanh), 'new' = điểm
    # MỚI cần tính (một trong 4). Tất định: trong vòng, new = (đỉnh trước) + (đỉnh sau) −
    # (đỉnh đối). Planner CHỈ cần copy đúng thứ tự chữ + nói điểm nào mới (không tự suy luận
    # đỉnh đối). VD order=[A,P,B,C], new=P → trước A, sau B, đối C → P=A+B−C; Polygon(A,P,B,C).
    order = ar["order"]
    new = ar["new"]
    poly = o[1]
    i = order.index(new)
    bef, aft, opp = order[(i - 1) % 4], order[(i + 1) % 4], order[(i + 2) % 4]
    return (
        [f"{new}={bef}+{aft}-{opp}",
         f"{poly}=Polygon({','.join(order)})"],
        [f"AreParallel(Line({order[0]},{order[1]}),Line({order[3]},{order[2]}))",
         f"AreParallel(Line({order[1]},{order[2]}),Line({order[0]},{order[3]}))"],
    )


def _parallelogram_4th(ar, o, aux):
    # Dựng ĐIỂM MỚI là đỉnh thứ tư của hình bình hành theo ĐÚNG THỨ TỰ TÊN. Trong thứ
    # tự vòng, điểm mới NEW nằm giữa 'before' và 'after', đối diện 'opposite':
    #   …before → NEW → after → opposite…  ⇒  NEW = before + after − opposite
    # (hai đường chéo cắt nhau tại trung điểm). VD "ABPC hình bình hành, P mới":
    # before=B, after=C, opposite=A ⇒ P=B+C−A; Polygon(B,P,C,A) = đúng vòng ABPC.
    P, poly = o[0], o[1]
    bef, opp, aft = ar["before"], ar["opposite"], ar["after"]
    return (
        [f"{P}={bef}+{aft}-{opp}",
         f"{poly}=Polygon({bef},{P},{aft},{opp})"],
        [f"AreParallel(Line({bef},{P}),Line({opp},{aft}))",
         f"AreParallel(Line({P},{aft}),Line({bef},{opp}))"],
    )


def _rectangle(ar, o, aux):
    C, D, poly = o[0], o[1], o[2]
    v = aux()
    return (
        [f"{v}=UnitPerpendicularVector(Vector({ar['A']},{ar['B']}))",
         f"{C}={ar['B']}+{ar['h']}*{v}",
         f"{D}={ar['A']}+{ar['h']}*{v}",
         f"{poly}=Polygon({ar['A']},{ar['B']},{C},{D})"],
        [f"ArePerpendicular(Line({ar['A']},{ar['B']}),Line({ar['B']},{C}))"],
    )


def _square(ar, o, aux):
    # VERIFIED hướng: Rotate(... , -90°, ...) cho hình vuông lồi cùng phía.
    C, D, poly = o[0], o[1], o[2]
    return (
        [f"{C}=Rotate({ar['A']},-90°,{ar['B']})",
         f"{D}=Rotate({ar['B']},90°,{ar['A']})",
         f"{poly}=Polygon({ar['A']},{ar['B']},{C},{D})"],
        [f"AreEqual(Distance({ar['A']},{ar['B']}),Distance({ar['B']},{C}))",
         f"ArePerpendicular(Line({ar['A']},{ar['B']}),Line({ar['B']},{C}))"],
    )


def _rhombus(ar, o, aux):
    # Robust: planner chỉ cho HƯỚNG P của đỉnh thứ ba; primitive SNAP đỉnh C về đúng
    # khoảng cách |AB| ⇒ luôn là hình thoi, không phụ thuộc LLM tính tọa độ chính xác.
    C, D, poly = o[0], o[1], o[2]
    u = aux()
    return (
        [f"{u}=UnitVector(Vector({ar['B']},{ar['P']}))",
         f"{C}={ar['B']}+Distance({ar['A']},{ar['B']})*{u}",
         f"{D}={ar['A']}+({C}-{ar['B']})",
         f"{poly}=Polygon({ar['A']},{ar['B']},{C},{D})"],
        [f"AreEqual(Distance({ar['A']},{ar['B']}),Distance({ar['B']},{C}))",
         f"AreParallel(Line({ar['A']},{ar['B']}),Line({D},{C}))"],
    )


def _trapezoid(ar, o, aux):
    # Hình thang ABCD với AB // CD; D = C + 0.5*(A-B).
    D, poly = o[0], o[1]
    return (
        [f"{D}={ar['C']}+0.5*({ar['A']}-{ar['B']})",
         f"{poly}=Polygon({ar['A']},{ar['B']},{ar['C']},{D})"],
        [f"AreParallel(Line({ar['A']},{ar['B']}),Line({ar['C']},{D}))"],
    )


def _diagonal(ar, o, aux):
    return [f"{o[0]}=Segment({ar['P']},{ar['Q']})"], []


# ───────────────────────── G. Đối xứng ─────────────────────────
def _reflect_over_line(ar, o, aux):
    return [f"{o[0]}=Reflect({ar['obj']},{ar['line']})"], []


def _reflect_over_point(ar, o, aux):
    return [f"{o[0]}=Reflect({ar['obj']},{ar['O']})"], []


# ───────────────────────── H. Quay & chuyển góc ─────────────────────────
def _rotate_point(ar, o, aux):
    # Quay điểm P quanh center một góc 'angle' ĐỘ (literal). VERIFIED: +độ = ngược
    # chiều kim đồng hồ (CCW), khớp Rotate(P,θ°,center) của GeoGebra.
    return [f"{o[0]}=Rotate({ar['P']},{ar['angle']}°,{ar['center']})"], []


def _point_on_circle_angle_transport(ar, o, aux):
    # F trên đường tròn c sao cho ∠(from)(vertex)F = ∠(rA)(rB)(rC). 'vertex' phải nằm
    # trên c. Cách: quay tia (vertex→from) quanh vertex một góc bằng góc tham chiếu,
    # rồi lấy giao điểm THỨ HAI của tia với c (điểm còn lại chính là vertex). Lấy giao
    # thứ hai bằng đối xứng vertex qua chân vuông góc tâm→tia (robust, KHÔNG dùng index).
    # VERIFIED trên ggb-service: cả hai assert = 1 với tam giác ABC định hướng CCW.
    F = o[0]
    ang, rot, foot = aux(), aux(), aux()
    return (
        [f"{ang}=Angle({ar['rA']},{ar['rB']},{ar['rC']})",
         f"{rot}=Rotate({ar['from']},{ang},{ar['vertex']})",
         f"{foot}=ClosestPoint(Line({ar['vertex']},{rot}),Center({ar['c']}))",
         f"{F}=Reflect({ar['vertex']},{foot})"],
        [f"AreEqual(Distance({F},Center({ar['c']})),Radius({ar['c']}))",
         f"AreEqual(Angle({ar['from']},{ar['vertex']},{F}),{ang})"],
    )


# ───────────────────────── I. Đường tròn theo tiếp xúc ─────────────────────────
def _circle_tangent_to_line_at(ar, o, aux):
    # Đường tròn ĐI QUA P và TIẾP XÚC với 'line' tại điểm T (T nằm trên line).
    # Tâm O: nằm trên đường vuông góc line tại T (bán kính OT ⊥ line) VÀ trên trung
    # trực TP (cách đều T, P). O = giao hai đường đó; đường tròn = Circle(O,T).
    # VERIFIED trên ggb-service: IsTangent(line,c)=1, P thuộc c.
    O, c = o[0], o[1]
    perp, pb = aux(), aux()
    return (
        [f"{perp}=PerpendicularLine({ar['T']},{ar['line']})",
         f"{pb}=PerpendicularBisector({ar['T']},{ar['P']})",
         f"{O}=Intersect({perp},{pb})",
         f"{c}=Circle({O},{ar['T']})"],
        [f"IsTangent({ar['line']},{c})",
         f"AreEqual(Distance({O},{ar['P']}),Radius({c}))"],
    )


def _second_intersection_two_circles(ar, o, aux):
    # Giao điểm THỨ HAI của hai đường tròn khi đã biết MỘT giao điểm 'known'. Hai giao
    # điểm đối xứng nhau qua đường nối hai tâm ⇒ K = đối xứng known qua Line tâm-tâm.
    # Robust, KHÔNG dùng index (index giao 2 đường tròn rất không ổn định).
    K = o[0]
    ctr = aux()
    return (
        [f"{ctr}=Line(Center({ar['c1']}),Center({ar['c2']}))",
         f"{K}=Reflect({ar['known']},{ctr})"],
        [f"AreEqual(Distance({K},Center({ar['c1']})),Radius({ar['c1']}))",
         f"AreEqual(Distance({K},Center({ar['c2']})),Radius({ar['c2']}))"],
    )


# ───────────────────── J. Tứ giác chuyên & quay tổng quát ─────────────────────
def _rhombus_angle(ar, o, aux):
    # Hình thoi ABCD theo GÓC BAD cho trước: D=quay B quanh A góc 'angle' (⇒ |AD|=|AB|),
    # C=B+(D-A). Thứ tự A→B→C→D đi vòng (C đối A). VERIFIED.
    C, D, poly = o[0], o[1], o[2]
    A, B = ar["A"], ar["B"]
    return (
        [f"{D}=Rotate({B},{ar['angle']}°,{A})",
         f"{C}={B}+({D}-{A})",
         f"{poly}=Polygon({A},{B},{C},{D})"],
        [f"AreEqual(Distance({A},{B}),Distance({B},{C}))",
         f"AreEqual(Distance({A},{B}),Distance({A},{D}))"],
    )


def _isosceles_trapezoid(ar, o, aux):
    # Hình thang cân ABCD, AB là đáy lớn; CD ∥ AB ở độ cao h, dài lenCD, căn giữa
    # (đối xứng qua trung trực AB) ⇒ hai cạnh bên bằng nhau. VERIFIED.
    C, D, poly = o[0], o[1], o[2]
    A, B = ar["A"], ar["B"]
    n, u = aux(), aux()
    return (
        [f"{n}=UnitPerpendicularVector(Vector({A},{B}))",
         f"{u}=UnitVector(Vector({A},{B}))",
         f"{D}={A}+{ar['h']}*{n}+((Distance({A},{B})-{ar['lenCD']})/2)*{u}",
         f"{C}={D}+{ar['lenCD']}*{u}",
         f"{poly}=Polygon({A},{B},{C},{D})"],
        [f"AreParallel(Line({A},{B}),Line({C},{D}))",
         f"AreEqual(Distance({A},{D}),Distance({B},{C}))"],
    )


def _kite(ar, o, aux):
    # Hình diều ABCD trục AC: D đối xứng B qua đường AC ⇒ AB=AD, CB=CD. VERIFIED.
    D, poly = o[0], o[1]
    A, C, B = ar["A"], ar["C"], ar["B"]
    return (
        [f"{D}=Reflect({B},Line({A},{C}))",
         f"{poly}=Polygon({A},{B},{C},{D})"],
        [f"AreEqual(Distance({A},{B}),Distance({A},{D}))",
         f"AreEqual(Distance({C},{B}),Distance({C},{D}))"],
    )


def _cyclic_quadrilateral(ar, o, aux):
    # Tứ giác nội tiếp: 4 điểm trên đường tròn c tại 4 tham số t1<t2<t3<t4 (∈[0,1])
    # theo thứ tự vòng ⇒ đa giác lồi nội tiếp. VERIFIED (AreConcyclic).
    A, B, C, D, poly = o[0], o[1], o[2], o[3], o[4]
    c = ar["c"]
    return (
        [f"{A}=Point({c},{ar['t1']})",
         f"{B}=Point({c},{ar['t2']})",
         f"{C}=Point({c},{ar['t3']})",
         f"{D}=Point({c},{ar['t4']})",
         f"{poly}=Polygon({A},{B},{C},{D})"],
        [f"AreConcyclic({A},{B},{C},{D})"],
    )


def _circle_tangent_2lines_at_points(ar, o, aux):
    # Đường tròn tiếp xúc line1 tại P1 VÀ line2 tại P2: tâm = giao 2 đường vuông góc tại
    # P1, P2. (Chỉ tồn tại khi P1,P2 nhất quán; assert IsTangent bắt sai.) VERIFIED.
    O, c = o[0], o[1]
    e1, e2 = aux(), aux()
    return (
        [f"{e1}=PerpendicularLine({ar['P1']},{ar['line1']})",
         f"{e2}=PerpendicularLine({ar['P2']},{ar['line2']})",
         f"{O}=Intersect({e1},{e2})",
         f"{c}=Circle({O},{ar['P1']})"],
        [f"IsTangent({ar['line1']},{c})", f"IsTangent({ar['line2']},{c})"],
    )


def _tangent_other_than(ar, o, aux):
    # Tiếp tuyến từ P (ngoài c) KHÁC tiếp tuyến 'known': hai tiếp tuyến từ P đối xứng
    # qua đường P–tâm ⇒ t = đối xứng known qua Line(P,Center(c)). VERIFIED, không index.
    t = o[0]
    return (
        [f"{t}=Reflect({ar['known']},Line({ar['P']},Center({ar['c']})))"],
        [f"IsTangent({t},{ar['c']})"],
    )


def _circle_diameter(ar, o, aux):
    # Đường tròn đường kính AB: tâm = trung điểm AB, bán kính = |AB|/2. VERIFIED.
    O, c = o[0], o[1]
    return (
        [f"{O}=Midpoint({ar['A']},{ar['B']})",
         f"{c}=Circle({O},Distance({ar['A']},{ar['B']})/2)"],
        [f"AreEqual(Distance({O},{ar['A']}),Radius({c}))"],
    )


def _rotate(ar, o, aux):
    # Quay đối tượng bất kỳ (điểm/đoạn/đa giác) quanh center một góc 'angle' độ (+CCW).
    return [f"{o[0]}=Rotate({ar['obj']},{ar['angle']}°,{ar['center']})"], []


def _rhombus_centered(ar, o, aux):
    # Hình thoi ABCD theo QUY ƯỚC: tâm tại O, đường chéo AC ≡ Ox (A=(p,0),C=(-p,0)),
    # BD ≡ Oy (B=(0,q),D=(0,-q)). A,B là điểm TỰ DO (kéo được); C,D đối xứng qua O nên
    # tâm luôn ở O. p,q = nửa độ dài hai đường chéo. VERIFIED: 4 cạnh bằng, AC⊥BD.
    A, B, C, D, poly = o[0], o[1], o[2], o[3], o[4]
    return (
        [f"{A}=({ar['p']},0)", f"{B}=(0,{ar['q']})",
         f"{C}=Reflect({A},(0,0))", f"{D}=Reflect({B},(0,0))",
         f"{poly}=Polygon({A},{B},{C},{D})"],
        [f"AreEqual(Distance({A},{B}),Distance({B},{C}))",
         f"AreEqual(Distance({A},{B}),Distance({C},{D}))",
         f"AreEqual(Distance({A},{B}),Distance({D},{A}))"],
    )


# ───────────────────────── Bảng đăng ký ─────────────────────────
def _t(*stmts):
    return list(stmts)


def _s(op, args, out):
    return {"op": op, "args": args, "out": out}


# Khung test dùng lại
_ABC = [_s("point_free", {"x": 0, "y": 0}, ["A"]),
        _s("point_free", {"x": 6, "y": 0}, ["B"]),
        _s("point_free", {"x": 2, "y": 5}, ["C"]),
        _s("triangle", {"A": "A", "B": "B", "C": "C"}, ["tri"])]
_CIRC = [_s("point_free", {"x": 0, "y": 0}, ["O"]),
         _s("circle_center_radius", {"O": "O", "r": 3}, ["c"])]


PRIMITIVES: dict[str, Primitive] = {}


def reg(p: Primitive):
    PRIMITIVES[p.name] = p


# A
reg(Primitive("point_free", ["x", "y"], 1, "Điểm tự do tại tọa độ", "đặt điểm gốc",
              _point_free, [_s("point_free", {"x": 1, "y": 2}, ["P"])], ["x", "y"]))
reg(Primitive("point_on_segment", ["A", "B", "t"], 1, "Điểm trên đoạn AB tỷ lệ t∈(0,1)",
              "đề cho điểm trên đoạn có vị trí", _point_on_segment,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("point_on_segment", {"A": "A", "B": "B", "t": 0.35}, ["P"])], ["t"]))
reg(Primitive("point_on_ray_beyond", ["P", "Q", "t"], 1, "Điểm trên tia PQ vượt Q (t>1)",
              "kéo dài tia qua điểm", _point_on_ray_beyond,
              [_s("point_free", {"x": 0, "y": 0}, ["P"]), _s("point_free", {"x": 2, "y": 0}, ["Q"]),
               _s("point_on_ray_beyond", {"P": "P", "Q": "Q", "t": 1.6}, ["F"])], ["t"]))
reg(Primitive("point_on_object", ["path"], 1, "Điểm tự do trên path",
              "lấy điểm trên đối tượng không rõ vị trí", _point_on_object,
              _CIRC + [_s("point_on_object", {"path": "c"}, ["P"])]))
reg(Primitive("midpoint", ["A", "B"], 1, "Trung điểm AB", "trung điểm đoạn", _midpoint,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 2}, ["B"]),
               _s("midpoint", {"A": "A", "B": "B"}, ["M"])]))
reg(Primitive("segment", ["A", "B"], 1, "Đoạn thẳng AB", "nối hai điểm", _segment,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 0}, ["B"]),
               _s("segment", {"A": "A", "B": "B"}, ["s"])]))
reg(Primitive("line", ["A", "B"], 1, "Đường thẳng (vô hạn) qua A,B", "đề muốn 'đường thẳng'",
              _line, [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 1}, ["B"]),
                      _s("line", {"A": "A", "B": "B"}, ["l"])]))
reg(Primitive("ray", ["A", "B"], 1, "Tia gốc A qua B", "đề muốn 'tia'", _ray,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 1}, ["B"]),
               _s("ray", {"A": "A", "B": "B"}, ["r"])]))
reg(Primitive("distance", ["A", "B"], 1, "Độ dài đoạn (số)", "cần độ dài", _distance,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 3, "y": 4}, ["B"]),
               _s("distance", {"A": "A", "B": "B"}, ["d"])]))

# B
reg(Primitive("parallel_through", ["P", "line"], 1, "Đường qua P song song line",
              "kẻ song song", _parallel_through,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 0}, ["B"]),
               _s("line", {"A": "A", "B": "B"}, ["l"]), _s("point_free", {"x": 1, "y": 3}, ["P"]),
               _s("parallel_through", {"P": "P", "line": "l"}, ["d"])]))
reg(Primitive("perpendicular_through", ["P", "line"], 1, "Đường qua P vuông góc line",
              "kẻ vuông góc (đường vô hạn)", _perpendicular_through,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 0}, ["B"]),
               _s("line", {"A": "A", "B": "B"}, ["l"]), _s("point_free", {"x": 1, "y": 3}, ["P"]),
               _s("perpendicular_through", {"P": "P", "line": "l"}, ["d"])]))
reg(Primitive("foot_of_perpendicular", ["P", "line"], 2, "Chân vuông góc H + đoạn PH",
              "hạ vuông góc từ điểm xuống đường (hiện đoạn)", _foot_of_perpendicular,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("line", {"A": "A", "B": "B"}, ["l"]), _s("point_free", {"x": 2, "y": 4}, ["P"]),
               _s("foot_of_perpendicular", {"P": "P", "line": "l"}, ["H", "PH"])]))
reg(Primitive("perpendicular_bisector", ["A", "B"], 1, "Trung trực đoạn AB",
              "đường trung trực", _perpendicular_bisector,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("perpendicular_bisector", {"A": "A", "B": "B"}, ["d"])]))
reg(Primitive("angle_bisector", ["A", "B", "C"], 1, "Phân giác góc ABC (đỉnh B)",
              "tia phân giác của một góc", _angle_bisector,
              [_s("point_free", {"x": 4, "y": 0}, ["A"]), _s("point_free", {"x": 0, "y": 0}, ["B"]),
               _s("point_free", {"x": 3, "y": 3}, ["C"]),
               _s("angle_bisector", {"A": "A", "B": "B", "C": "C"}, ["d"])]))
reg(Primitive("intersect", ["obj1", "obj2"], 1, "Giao hai đối tượng (đường-đường 1 nghiệm; index nếu nhiều)",
              "giao điểm hai đối tượng", _intersect,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 4}, ["B"]),
               _s("line", {"A": "A", "B": "B"}, ["l1"]),
               _s("point_free", {"x": 0, "y": 4}, ["C"]), _s("point_free", {"x": 4, "y": 0}, ["D"]),
               _s("line", {"A": "C", "B": "D"}, ["l2"]),
               _s("intersect", {"obj1": "l1", "obj2": "l2"}, ["P"])]))

# C
reg(Primitive("triangle", ["A", "B", "C"], 1, "Tam giác ABC", "vẽ tam giác", _triangle,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("point_free", {"x": 2, "y": 5}, ["C"]),
               _s("triangle", {"A": "A", "B": "B", "C": "C"}, ["tri"])]))
reg(Primitive("triangle_equilateral", ["A", "B"], 2, "Tam giác đều trên cạnh AB",
              "tam giác đều", _triangle_equilateral,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("triangle_equilateral", {"A": "A", "B": "B"}, ["C", "tri"])]))
reg(Primitive("triangle_isosceles", ["A", "B", "h"], 2, "Tam giác cân đáy AB cao h",
              "tam giác cân", _triangle_isosceles,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("triangle_isosceles", {"A": "A", "B": "B", "h": 5}, ["C", "tri"])], ["h"]))
reg(Primitive("triangle_right", ["A", "B", "h"], 2, "Tam giác vuông tại A (AC⊥AB, AC=h)",
              "tam giác vuông", _triangle_right,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("triangle_right", {"A": "A", "B": "B", "h": 4}, ["C", "tri"])], ["h"]))
reg(Primitive("altitude", ["vertex", "A", "B", "C"], 2, "Đường cao từ đỉnh: chân H + đoạn",
              "kẻ đường cao", _altitude, _ABC + [
                  _s("altitude", {"vertex": "A", "A": "A", "B": "B", "C": "C"}, ["H", "hA"])]))
reg(Primitive("median", ["vertex", "A", "B", "C"], 2, "Trung tuyến từ đỉnh: trung điểm M + đoạn",
              "kẻ trung tuyến", _median, _ABC + [
                  _s("median", {"vertex": "A", "A": "A", "B": "B", "C": "C"}, ["M", "mA"])]))
reg(Primitive("angle_bisector_seg", ["vertex", "A", "B", "C"], 2,
              "Phân giác trong từ đỉnh cắt cạnh đối tại D + đoạn", "phân giác trong tam giác",
              _angle_bisector_seg, _ABC + [
                  _s("angle_bisector_seg", {"vertex": "A", "A": "A", "B": "B", "C": "C"}, ["D", "dA"])]))
reg(Primitive("midsegment", ["A", "B", "C"], 3, "Đường trung bình: trung điểm M,N + đoạn (∥ BC)",
              "đường trung bình tam giác", _midsegment, _ABC + [
                  _s("midsegment", {"A": "A", "B": "B", "C": "C"}, ["M", "N", "mid"])]))
reg(Primitive("centroid", ["A", "B", "C"], 1, "Trọng tâm", "trọng tâm G", _centroid,
              _ABC + [_s("centroid", {"A": "A", "B": "B", "C": "C"}, ["G"])]))
reg(Primitive("orthocenter", ["A", "B", "C"], 1, "Trực tâm (giao 2 đường cao)", "trực tâm H",
              _orthocenter, _ABC + [_s("orthocenter", {"A": "A", "B": "B", "C": "C"}, ["H"])]))
reg(Primitive("incenter", ["A", "B", "C"], 1, "Tâm nội tiếp (giao 2 phân giác)", "tâm nội tiếp I",
              _incenter, _ABC + [_s("incenter", {"A": "A", "B": "B", "C": "C"}, ["I"])]))
reg(Primitive("circumcenter", ["A", "B", "C"], 1, "Tâm ngoại tiếp (giao 2 trung trực)",
              "tâm ngoại tiếp O", _circumcenter, _ABC + [
                  _s("circumcenter", {"A": "A", "B": "B", "C": "C"}, ["O"])]))

# D
reg(Primitive("circle_center_radius", ["O", "r"], 1, "Đường tròn tâm O bán kính r",
              "đường tròn tâm-bán kính", _circle_center_radius,
              [_s("point_free", {"x": 0, "y": 0}, ["O"]),
               _s("circle_center_radius", {"O": "O", "r": 3}, ["c"])], ["r"]))
reg(Primitive("circle_center_point", ["O", "A"], 1, "Đường tròn tâm O qua A", "tâm + 1 điểm",
              _circle_center_point, [_s("point_free", {"x": 0, "y": 0}, ["O"]),
              _s("point_free", {"x": 3, "y": 0}, ["A"]),
              _s("circle_center_point", {"O": "O", "A": "A"}, ["c"])]))
reg(Primitive("circle_through_3", ["A", "B", "C"], 1, "Đường tròn qua 3 điểm", "qua 3 điểm",
              _circle_through_3, [_s("point_free", {"x": 0, "y": 0}, ["A"]),
              _s("point_free", {"x": 6, "y": 0}, ["B"]), _s("point_free", {"x": 2, "y": 5}, ["C"]),
              _s("circle_through_3", {"A": "A", "B": "B", "C": "C"}, ["c"])]))
reg(Primitive("circumcircle", ["A", "B", "C"], 2, "Đường tròn ngoại tiếp: tâm O + đường tròn c",
              "ngoại tiếp tam giác", _circumcircle, _ABC + [
                  _s("circumcircle", {"A": "A", "B": "B", "C": "C"}, ["O", "cc"])]))
reg(Primitive("incircle", ["A", "B", "C"], 2, "Đường tròn nội tiếp: tâm I + đường tròn c",
              "nội tiếp tam giác", _incircle, _ABC + [
                  _s("incircle", {"A": "A", "B": "B", "C": "C"}, ["I", "ic"])]))
reg(Primitive("semicircle", ["M", "N"], 2, "Nửa đường tròn đường kính MN (cung BÊN TRÁI M→N) + tâm O",
              "nửa đường tròn đường kính", _semicircle,
              [_s("point_free", {"x": -5, "y": 0}, ["M"]), _s("point_free", {"x": 5, "y": 0}, ["N"]),
               _s("semicircle", {"M": "M", "N": "N"}, ["s", "O"])]))
reg(Primitive("arc", ["O", "A", "B"], 1, "Cung tròn tâm O từ A đến B (ngược chiều kim đồng hồ)",
              "cung tròn", _arc, [_s("point_free", {"x": 0, "y": 0}, ["O"]),
              _s("point_free", {"x": 5, "y": 0}, ["A"]), _s("point_free", {"x": 0, "y": 5}, ["B"]),
              _s("arc", {"O": "O", "A": "A", "B": "B"}, ["a"])]))
reg(Primitive("chord", ["A", "B"], 1, "Dây cung (đoạn AB)", "dây cung", _chord,
              [_s("point_free", {"x": -3, "y": 0}, ["A"]), _s("point_free", {"x": 0, "y": 3}, ["B"]),
               _s("chord", {"A": "A", "B": "B"}, ["s"])]))
reg(Primitive("diameter_point", ["O", "A"], 1, "Điểm đối tâm của A qua O (đầu kia đường kính)",
              "đường kính từ 1 đầu", _diameter_point, [_s("point_free", {"x": 0, "y": 0}, ["O"]),
              _s("point_free", {"x": 3, "y": 1}, ["A"]),
              _s("diameter_point", {"O": "O", "A": "A"}, ["B"])]))
reg(Primitive("tangent_from_point", ["P", "c"], 4,
              "Hai tiếp tuyến từ điểm ngoài: tiếp điểm B,C + đoạn t1,t2", "tiếp tuyến từ điểm ngoài",
              _tangent_from_point, [_s("point_free", {"x": 0, "y": 0}, ["O"]),
              _s("circle_center_radius", {"O": "O", "r": 3}, ["c"]), _s("point_free", {"x": 8, "y": 1}, ["P"]),
              _s("tangent_from_point", {"P": "P", "c": "c"}, ["B", "C", "t1", "t2"])]))
reg(Primitive("tangent_at_point", ["A", "c"], 1, "Tiếp tuyến tại điểm A trên đường tròn",
              "tiếp tuyến tại tiếp điểm", _tangent_at_point,
              [_s("point_free", {"x": 0, "y": 0}, ["O"]), _s("circle_center_radius", {"O": "O", "r": 3}, ["c"]),
               _s("point_on_circle", {"c": "c"}, ["A"]),
               _s("tangent_at_point", {"A": "A", "c": "c"}, ["t"])]))
reg(Primitive("intersect_line_circle", ["line", "c"], 1,
              "Giao đường-đường tròn (BẮT BUỘC index 1/2)", "giao đường với đường tròn",
              _intersect_line_circle, _CIRC + [
                  _s("point_free", {"x": -5, "y": 0}, ["U"]), _s("point_free", {"x": 5, "y": 0}, ["V"]),
                  _s("line", {"A": "U", "B": "V"}, ["l"]),
                  _s("intersect_line_circle", {"line": "l", "c": "c", "index": 1}, ["P"])]))
reg(Primitive("intersect_two_circles", ["c1", "c2"], 1, "Giao hai đường tròn (index 1/2)",
              "hai đường tròn cắt nhau", _intersect_two_circles,
              [_s("point_free", {"x": 0, "y": 0}, ["O1"]), _s("circle_center_radius", {"O": "O1", "r": 3}, ["c1"]),
               _s("point_free", {"x": 4, "y": 0}, ["O2"]), _s("circle_center_radius", {"O": "O2", "r": 3}, ["c2"]),
               _s("intersect_two_circles", {"c1": "c1", "c2": "c2", "index": 1}, ["P"])]))
reg(Primitive("second_intersection", ["line", "center", "known"], 1,
              "Giao điểm THỨ HAI của đường thẳng với đường tròn tâm center, khi đã biết "
              "1 giao điểm known trên đường tròn (robust, không index)",
              "đường AB cắt (O) tại điểm mới mà A hoặc B đã thuộc (O)", _second_intersection,
              [_s("point_free", {"x": 0, "y": 0}, ["O"]),
               _s("point_free", {"x": 5, "y": 0}, ["N"]),
               _s("point_free", {"x": -3, "y": 6.4}, ["F"]),
               _s("line", {"A": "F", "B": "N"}, ["FN"]),
               _s("second_intersection", {"line": "FN", "center": "O", "known": "N"}, ["A"])]))
reg(Primitive("point_on_circle", ["c"], 1,
              "Điểm trên đường tròn (param∈[0,1] tùy chọn để lấy điểm phân biệt)",
              "lấy điểm trên đường tròn", _point_on_circle,
              _CIRC + [_s("point_on_circle", {"c": "c", "param": 0.2}, ["P"])]))
reg(Primitive("point_on_arc", ["O", "A", "B"], 1,
              "Điểm KÉO ĐƯỢC trên cung tròn A→B (tâm O, ngược chiều kim đồng hồ)",
              "lấy điểm DI ĐỘNG trên một cung xác định bởi hai đầu mút (bài cực trị/quỹ tích)",
              _point_on_arc,
              [_s("point_free", {"x": 0, "y": 0}, ["O"]),
               _s("circle_center_radius", {"O": "O", "r": 5}, ["c"]),
               _s("point_on_circle", {"c": "c", "param": 0.1}, ["A"]),
               _s("point_on_circle", {"c": "c", "param": 0.4}, ["B"]),
               _s("point_on_arc", {"O": "O", "A": "A", "B": "B"}, ["E"])]))

# E
reg(Primitive("angle_mark", ["A", "B", "C"], 1, "Ký hiệu góc ABC (đỉnh B)", "đánh dấu góc",
              _angle_mark, [_s("point_free", {"x": 4, "y": 0}, ["A"]), _s("point_free", {"x": 0, "y": 0}, ["B"]),
              _s("point_free", {"x": 3, "y": 3}, ["C"]),
              _s("angle_mark", {"A": "A", "B": "B", "C": "C"}, ["alpha"])]))
reg(Primitive("right_angle_mark", ["A", "B", "C"], 1, "Ký hiệu góc vuông tại B", "đánh dấu góc vuông",
              _right_angle_mark, [_s("point_free", {"x": 4, "y": 0}, ["A"]), _s("point_free", {"x": 0, "y": 0}, ["B"]),
              _s("point_free", {"x": 0, "y": 4}, ["C"]),
              _s("right_angle_mark", {"A": "A", "B": "B", "C": "C"}, ["beta"])]))
reg(Primitive("inscribed_angle", ["A", "B", "C"], 1, "Góc nội tiếp ABC", "góc nội tiếp",
              _inscribed_angle, [_s("point_free", {"x": 4, "y": 0}, ["A"]), _s("point_free", {"x": 0, "y": 0}, ["B"]),
              _s("point_free", {"x": 3, "y": 3}, ["C"]),
              _s("inscribed_angle", {"A": "A", "B": "B", "C": "C"}, ["gamma"])]))

# F
reg(Primitive("polygon", ["points"], 1, "Đa giác qua danh sách điểm", "đa giác tổng quát", _polygon,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 0}, ["B"]),
               _s("point_free", {"x": 4, "y": 3}, ["C"]), _s("point_free", {"x": 0, "y": 3}, ["D"]),
               _s("polygon", {"points": ["A", "B", "C", "D"]}, ["poly"])]))
reg(Primitive("parallelogram", ["A", "B", "C"], 2, "Hình bình hành ABCD (D=A+C−B)", "hình bình hành",
              _parallelogram, [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 5, "y": 0}, ["B"]),
              _s("point_free", {"x": 6, "y": 3}, ["C"]),
              _s("parallelogram", {"A": "A", "B": "B", "C": "C"}, ["D", "poly"])]))
reg(Primitive("parallelogram_named", ["order", "new"], 2,
              "Hình bình hành theo ĐÚNG chuỗi thứ tự tên (order=4 tên vòng quanh, new=điểm "
              "mới cần tính): tự tính điểm mới + vẽ đa giác đúng vòng. Planner chỉ copy thứ tự chữ.",
              "thêm điểm để 4 đỉnh THEO ĐÚNG THỨ TỰ CHỮ là hình bình hành (ABPC, APBC, AMBN…)",
              _parallelogram_named,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("point_free", {"x": 2, "y": 4}, ["C"]),
               _s("parallelogram_named", {"order": ["A", "P", "B", "C"], "new": "P"}, ["P", "poly"])]))
reg(Primitive("parallelogram_4th", ["before", "opposite", "after"], 2,
              "ĐIỂM thứ tư của hình bình hành theo ĐÚNG thứ tự tên: điểm mới giữa before&after, "
              "đối diện opposite (=before+after−opposite) + đa giác đúng vòng",
              "thêm điểm sao cho 4 đỉnh (theo đúng thứ tự chữ, vd ABPC) là hình bình hành",
              _parallelogram_4th,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("point_free", {"x": 2, "y": 4}, ["C"]),
               _s("parallelogram_4th", {"before": "B", "opposite": "A", "after": "C"}, ["P", "poly"])]))
reg(Primitive("rectangle", ["A", "B", "h"], 3, "Hình chữ nhật trên cạnh AB cao h", "hình chữ nhật",
              _rectangle, [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 5, "y": 0}, ["B"]),
              _s("rectangle", {"A": "A", "B": "B", "h": 3}, ["C", "D", "poly"])], ["h"]))
reg(Primitive("square", ["A", "B"], 3, "Hình vuông cạnh AB", "hình vuông", _square,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 0}, ["B"]),
               _s("square", {"A": "A", "B": "B"}, ["C", "D", "poly"])]))
reg(Primitive("rhombus", ["A", "B", "P"], 3,
              "Hình thoi ABCD trên cạnh AB; P = hướng đỉnh thứ ba (tự snap đúng cạnh)",
              "hình thoi", _rhombus,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 0}, ["B"]),
               _s("point_free", {"x": 6.4, "y": 3}, ["P"]),
               _s("rhombus", {"A": "A", "B": "B", "P": "P"}, ["C", "D", "poly"])]))
reg(Primitive("trapezoid", ["A", "B", "C"], 2, "Hình thang ABCD (AB∥CD)", "hình thang", _trapezoid,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("point_free", {"x": 5, "y": 3}, ["C"]),
               _s("trapezoid", {"A": "A", "B": "B", "C": "C"}, ["D", "poly"])]))
reg(Primitive("diagonal", ["P", "Q"], 1, "Đường chéo (đoạn PQ)", "đường chéo", _diagonal,
              [_s("point_free", {"x": 0, "y": 0}, ["P"]), _s("point_free", {"x": 4, "y": 3}, ["Q"]),
               _s("diagonal", {"P": "P", "Q": "Q"}, ["s"])]))

# G
reg(Primitive("reflect_over_line", ["obj", "line"], 1, "Đối xứng obj qua trục line", "đối xứng trục",
              _reflect_over_line, [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 0}, ["B"]),
              _s("line", {"A": "A", "B": "B"}, ["d"]), _s("point_free", {"x": 1, "y": 3}, ["P"]),
              _s("reflect_over_line", {"obj": "P", "line": "d"}, ["Pp"])]))
reg(Primitive("reflect_over_point", ["obj", "O"], 1, "Đối xứng obj qua tâm O", "đối xứng tâm",
              _reflect_over_point, [_s("point_free", {"x": 0, "y": 0}, ["O"]), _s("point_free", {"x": 3, "y": 1}, ["P"]),
              _s("reflect_over_point", {"obj": "P", "O": "O"}, ["Pp"])]))

# H — Quay & chuyển góc
reg(Primitive("rotate_point", ["P", "angle", "center"], 1,
              "Quay điểm P quanh center một góc 'angle' ĐỘ (dương = ngược chiều kim đồng hồ)",
              "quay một điểm quanh tâm theo góc SỐ cho trước (độ)", _rotate_point,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]),
               _s("point_free", {"x": 3, "y": 0}, ["B"]),
               _s("rotate_point", {"P": "B", "angle": 90, "center": "A"}, ["Bp"])], ["angle"]))
reg(Primitive("point_on_circle_angle_transport",
              ["vertex", "from", "c", "rA", "rB", "rC"], 1,
              "Điểm F trên đường tròn c sao cho ∠(from)(vertex)F = ∠(rA)(rB)(rC); "
              "vertex phải nằm trên c (quay tia vertex→from quanh vertex một góc bằng góc "
              "tham chiếu rồi cắt c)",
              "lấy điểm trên (cung/đường tròn) thỏa điều kiện một GÓC bằng góc cho trước",
              _point_on_circle_angle_transport,
              [_s("point_free", {"x": 0, "y": 5}, ["A"]),
               _s("point_free", {"x": -4, "y": 0}, ["B"]),
               _s("point_free", {"x": 6, "y": 0}, ["C"]),
               _s("midpoint", {"A": "B", "B": "C"}, ["M"]),
               _s("midpoint", {"A": "C", "B": "A"}, ["N"]),
               _s("midpoint", {"A": "A", "B": "B"}, ["P"]),
               _s("circle_through_3", {"A": "A", "B": "P", "C": "N"}, ["capn"]),
               _s("point_on_circle_angle_transport",
                  {"vertex": "A", "from": "P", "c": "capn", "rA": "M", "rB": "A", "rC": "C"},
                  ["F"])]))

# I — Đường tròn theo tiếp xúc
reg(Primitive("circle_tangent_to_line_at", ["T", "line", "P"], 2,
              "Đường tròn đi qua P và tiếp xúc với 'line' tại điểm T (T trên line): tâm O + đường tròn c",
              "đường tròn tiếp xúc một đường thẳng tại điểm cho trước và đi qua điểm khác",
              _circle_tangent_to_line_at,
              [_s("point_free", {"x": 0, "y": 5}, ["A"]),
               _s("point_free", {"x": -4, "y": 0}, ["B"]),
               _s("point_free", {"x": 6, "y": 0}, ["C"]),
               _s("orthocenter", {"A": "A", "B": "B", "C": "C"}, ["H"]),
               _s("line", {"A": "B", "B": "C"}, ["bc"]),
               _s("circle_tangent_to_line_at", {"T": "B", "line": "bc", "P": "H"}, ["O1", "c1"])]))
reg(Primitive("second_intersection_two_circles", ["c1", "c2", "known"], 1,
              "Giao điểm thứ hai của hai đường tròn c1,c2 khi đã biết 1 giao điểm 'known' "
              "(đối xứng known qua đường nối hai tâm; robust, không index)",
              "hai đường tròn cắt nhau tại điểm mới mà đã biết một giao điểm chung",
              _second_intersection_two_circles,
              [_s("point_free", {"x": 0, "y": 5}, ["A"]),
               _s("point_free", {"x": -4, "y": 0}, ["B"]),
               _s("point_free", {"x": 6, "y": 0}, ["C"]),
               _s("orthocenter", {"A": "A", "B": "B", "C": "C"}, ["H"]),
               _s("line", {"A": "B", "B": "C"}, ["bc"]),
               _s("circle_tangent_to_line_at", {"T": "B", "line": "bc", "P": "H"}, ["O1", "c1"]),
               _s("circle_tangent_to_line_at", {"T": "C", "line": "bc", "P": "H"}, ["O2", "c2"]),
               _s("second_intersection_two_circles", {"c1": "c1", "c2": "c2", "known": "H"}, ["K"])]))

# J — Tứ giác chuyên & quay tổng quát
reg(Primitive("rhombus_angle", ["A", "B", "angle"], 3,
              "Hình thoi ABCD theo GÓC BAD (độ) cho trước: đỉnh C, D + đa giác",
              "hình thoi khi đề cho số đo góc (vd góc BAD = 70°)", _rhombus_angle,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 6, "y": 0}, ["B"]),
               _s("rhombus_angle", {"A": "A", "B": "B", "angle": 70}, ["C", "D", "poly"])], ["angle"]))
reg(Primitive("isosceles_trapezoid", ["A", "B", "h", "lenCD"], 3,
              "Hình thang cân ABCD, AB đáy lớn, CD∥AB cao h dài lenCD căn giữa: C, D + đa giác",
              "hình thang cân", _isosceles_trapezoid,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 8, "y": 0}, ["B"]),
               _s("isosceles_trapezoid", {"A": "A", "B": "B", "h": 4, "lenCD": 4}, ["C", "D", "poly"])],
              ["h", "lenCD"]))
reg(Primitive("kite", ["A", "C", "B"], 2,
              "Hình diều ABCD trục AC (B cho trước, D đối xứng B qua AC): D + đa giác",
              "hình diều / tứ giác có trục đối xứng là đường chéo", _kite,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 0, "y": 6}, ["C"]),
               _s("point_free", {"x": 3, "y": 2}, ["B"]),
               _s("kite", {"A": "A", "C": "C", "B": "B"}, ["D", "poly"])]))
reg(Primitive("cyclic_quadrilateral", ["c", "t1", "t2", "t3", "t4"], 5,
              "Tứ giác ABCD nội tiếp đường tròn c (4 điểm tại 4 tham số ∈[0,1] tăng dần): A,B,C,D + đa giác",
              "tứ giác nội tiếp một đường tròn cho trước", _cyclic_quadrilateral,
              [_s("point_free", {"x": 0, "y": 0}, ["O"]),
               _s("circle_center_radius", {"O": "O", "r": 5}, ["c"]),
               _s("cyclic_quadrilateral", {"c": "c", "t1": 0.1, "t2": 0.35, "t3": 0.6, "t4": 0.85},
                  ["A", "B", "C", "D", "poly"])], ["t1", "t2", "t3", "t4"]))
reg(Primitive("circle_tangent_2lines_at_points", ["line1", "P1", "line2", "P2"], 2,
              "Đường tròn tiếp xúc line1 tại P1 và line2 tại P2: tâm O + đường tròn c",
              "đường tròn tiếp xúc hai đường thẳng tại hai điểm cho trước", _circle_tangent_2lines_at_points,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 4, "y": 3}, ["P1"]),
               _s("line", {"A": "A", "B": "P1"}, ["l1"]), _s("point_free", {"x": 4, "y": -3}, ["P2"]),
               _s("line", {"A": "A", "B": "P2"}, ["l2"]),
               _s("circle_tangent_2lines_at_points", {"line1": "l1", "P1": "P1", "line2": "l2", "P2": "P2"},
                  ["O", "c"])]))
reg(Primitive("tangent_other_than", ["P", "c", "known"], 1,
              "Tiếp tuyến từ P (ngoài c) khác tiếp tuyến 'known' đã biết (đối xứng known qua P–tâm)",
              "tiếp tuyến thứ hai từ một điểm ngoài khi đã biết một tiếp tuyến", _tangent_other_than,
              [_s("point_free", {"x": 0, "y": 0}, ["O"]),
               _s("circle_center_radius", {"O": "O", "r": 3}, ["c"]),
               _s("point_free", {"x": 8, "y": 1}, ["P"]),
               _s("tangent_from_point", {"P": "P", "c": "c"}, ["B", "Cc", "t1", "t2"]),
               _s("line", {"A": "P", "B": "B"}, ["known"]),
               _s("tangent_other_than", {"P": "P", "c": "c", "known": "known"}, ["t"])]))
reg(Primitive("circle_diameter", ["A", "B"], 2,
              "Đường tròn đường kính AB: tâm O (trung điểm) + đường tròn c",
              "đường tròn đường kính (vd đường kính AH)", _circle_diameter,
              [_s("point_free", {"x": -3, "y": 0}, ["A"]), _s("point_free", {"x": 3, "y": 1}, ["B"]),
               _s("circle_diameter", {"A": "A", "B": "B"}, ["O", "c"])]))
reg(Primitive("rotate", ["obj", "center", "angle"], 1,
              "Quay đối tượng bất kỳ quanh center một góc SỐ (độ, +ngược chiều kim đồng hồ)",
              "phép quay một đối tượng (điểm/đoạn/hình) theo góc cho trước", _rotate,
              [_s("point_free", {"x": 0, "y": 0}, ["A"]), _s("point_free", {"x": 3, "y": 0}, ["B"]),
               _s("segment", {"A": "A", "B": "B"}, ["s"]),
               _s("rotate", {"obj": "s", "center": "A", "angle": 90}, ["s2"])], ["angle"]))
reg(Primitive("rhombus_centered", ["p", "q"], 5,
              "Hình thoi ABCD QUY ƯỚC: tâm O, chéo AC≡Ox (nửa chéo p), BD≡Oy (nửa chéo q); "
              "A,B kéo được. Trả A,B,C,D + đa giác",
              "hình thoi ABCD không cho góc cụ thể (đặt theo quy ước tâm O, hai chéo trên trục)",
              _rhombus_centered,
              [_s("rhombus_centered", {"p": 4, "q": 2.5}, ["A", "B", "C", "D", "poly"])],
              ["p", "q"]))
