"""Verifier quan hệ DETERMINISTIC bằng Python, đọc TỌA ĐỘ từ render (upgrade_plan §5).

Đánh giá các assert quan hệ (cùng "ngôn ngữ" biểu thức như assert GeoGebra:
IsTangent, AreEqual(Distance(...),Radius(...)), ArePerpendicular, AreCollinear,
AreConcurrent, AreConcyclic, Angle...) NHƯNG tính trực tiếp từ tọa độ điểm / tâm-bán
kính đường tròn / phương trình đường thẳng — KHÔNG nhờ boolean GeoGebra.

Trả về cho mỗi assert: True (thỏa) / False (không thỏa) / None (chưa kết luận được →
caller fallback sang kết quả GeoGebra). "None thay vì đoán" để KHÔNG loại oan hình đúng.

Hình học lấy từ render["objects"]: point {x,y}; circle/conic {cx,cy,r}; line/segment/
ray/vector {eq} (chuỗi phương trình GeoGebra, parse ở đây).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

_TOL = 1e-6


class Inconclusive(Exception):
    """Không đủ dữ liệu / cú pháp ngoài phạm vi → trả None cho assert đó."""


# ───────────────────────── kiểu giá trị ─────────────────────────
@dataclass
class Pt:
    x: float
    y: float


@dataclass
class Ln:
    a: float
    b: float
    c: float  # a x + b y = c, (a,b) đã chuẩn hoá đơn vị


@dataclass
class Cir:
    cx: float
    cy: float
    r: float


# ───────────────────────── parse đường thẳng ─────────────────────────
def _parse_line_eq(eq: str) -> Ln:
    """ "f: 4x + 3y = 25" / "y = 1.5x - 2" / "x = 4" → Ln(a,b,c) chuẩn hoá."""
    if not eq or "=" not in eq:
        raise Inconclusive(f"line eq lạ: {eq!r}")
    s = eq.split(":", 1)[1] if ":" in eq else eq
    lhs, rhs = s.split("=", 1)

    def f(expr: str, X: float, Y: float) -> float:
        e = expr.replace(" ", "")
        if not e:
            return 0.0
        # chèn '*' cho phép nhân ẩn: 4x→4*x, 1.5y→1.5*y, )x→)*x
        e = re.sub(r"(?<=[0-9.\)])(?=[xy(])", "*", e)
        try:
            return float(eval(e, {"__builtins__": {}}, {"x": X, "y": Y}))  # noqa: S307
        except Exception as ex:
            raise Inconclusive(f"không eval được '{expr}': {ex}")

    def g(X: float, Y: float) -> float:
        return f(lhs, X, Y) - f(rhs, X, Y)

    c0 = g(0.0, 0.0)
    a = g(1.0, 0.0) - c0
    b = g(0.0, 1.0) - c0
    n = math.hypot(a, b)
    if n < 1e-12:
        raise Inconclusive("đường thẳng suy biến khi parse")
    return Ln(a / n, b / n, -c0 / n)  # a x + b y = -c0


# ───────────────────────── bảng đối tượng ─────────────────────────
def _names(name: str):
    """Tên gốc + alias bỏ ngoặc subscript: GeoGebra lưu 'aux1_{1}' còn assert dùng
    'aux1_1' → đăng ký cả hai để tra cứu khớp."""
    alias = name.replace("_{", "_").replace("}", "")
    return {name, alias}


def build_geometry(objects: list[dict]) -> dict[str, object]:
    geo: dict[str, object] = {}
    for o in objects:
        name = o.get("name")
        if not name or not o.get("defined", True):
            continue
        t = (o.get("type") or "").lower()
        try:
            val = None
            if t == "point" and o.get("x") is not None:
                val = Pt(float(o["x"]), float(o["y"]))
            elif t in ("circle", "conic") and o.get("r") is not None:
                val = Cir(float(o["cx"]), float(o["cy"]), float(o["r"]))
            elif t in ("line", "segment", "ray", "vector") and o.get("eq"):
                val = _parse_line_eq(o["eq"])
            elif o.get("value") is not None:
                val = float(o["value"])  # numeric/angle (radian) cho AreEqual
            if val is not None:
                for n in _names(name):
                    geo[n] = val
        except Inconclusive:
            continue
    return geo


# ───────────────────────── tokenizer + parser biểu thức ─────────────────────────
_TOKEN = re.compile(r"\s*([A-Za-z_]\w*|\d+\.?\d*|°|[(),*/+\-])")


def _tokenize(s: str) -> list[str]:
    toks, pos = [], 0
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            if s[pos].isspace():
                pos += 1
                continue
            raise Inconclusive(f"ký tự lạ: {s[pos]!r}")
        toks.append(m.group(1))
        pos = m.end()
    return toks


class _Parser:
    def __init__(self, toks: list[str]):
        self.t = toks
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, tok):
        if self.next() != tok:
            raise Inconclusive(f"thiếu {tok!r}")

    def parse(self):
        node = self.expr()
        if self.peek() is not None:
            raise Inconclusive("token thừa")
        return node

    def expr(self):
        node = self.term()
        while self.peek() in ("+", "-"):
            op = self.next()
            node = (op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek() in ("*", "/"):
            op = self.next()
            node = (op, node, self.factor())
        return node

    def factor(self):
        tok = self.peek()
        if tok == "-":
            self.next()
            return ("neg", self.factor())
        if tok == "(":
            self.next()
            node = self.expr()
            self.expect(")")
            return node
        if tok is None:
            raise Inconclusive("hết token")
        self.next()
        if re.fullmatch(r"\d+\.?\d*", tok):
            val = float(tok)
            if self.peek() == "°":
                self.next()
                val = math.radians(val)
            return ("num", val)
        if re.fullmatch(r"[A-Za-z_]\w*", tok):
            if self.peek() == "(":
                self.next()
                args = []
                if self.peek() != ")":
                    args.append(self.expr())
                    while self.peek() == ",":
                        self.next()
                        args.append(self.expr())
                self.expect(")")
                return ("call", tok, args)
            return ("name", tok)
        raise Inconclusive(f"token lạ: {tok!r}")


# ───────────────────────── đánh giá ─────────────────────────
def _ccw_angle(b: Pt, a: Pt, c: Pt) -> float:
    """Góc ∠(a)(b)(c) tại đỉnh b, ngược chiều kim đồng hồ từ ba→bc, [0,2π) — khớp GeoGebra."""
    a1 = math.atan2(a.y - b.y, a.x - b.x)
    a2 = math.atan2(c.y - b.y, c.x - b.x)
    d = a2 - a1
    while d < 0:
        d += 2 * math.pi
    while d >= 2 * math.pi:
        d -= 2 * math.pi
    return d


def _line_through(p: Pt, q: Pt) -> Ln:
    a, b = q.y - p.y, p.x - q.x
    n = math.hypot(a, b)
    if n < 1e-12:
        raise Inconclusive("Line từ hai điểm trùng")
    a, b = a / n, b / n
    return Ln(a, b, a * p.x + b * p.y)


def _dist_pt_line(p: Pt, l: Ln) -> float:
    return abs(l.a * p.x + l.b * p.y - l.c)


class _Eval:
    def __init__(self, geo: dict[str, object]):
        self.geo = geo

    def ev(self, node):
        tag = node[0]
        if tag == "num":
            return node[1]
        if tag == "neg":
            return -self.ev(node[1])
        if tag in ("+", "-", "*", "/"):
            x, y = self.ev(node[1]), self.ev(node[2])
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise Inconclusive("toán số học trên không-phải-số")
            if tag == "+":
                return x + y
            if tag == "-":
                return x - y
            if tag == "*":
                return x * y
            return x / y if abs(y) > 1e-15 else float("inf")
        if tag == "name":
            if node[1] not in self.geo:
                raise Inconclusive(f"không có đối tượng {node[1]}")
            return self.geo[node[1]]
        if tag == "call":
            return self.call(node[1], [self.ev(a) for a in node[2]])
        raise Inconclusive("node lạ")

    def call(self, fn: str, a: list):
        if fn == "Distance":
            p, q = a
            if isinstance(p, Pt) and isinstance(q, Pt):
                return math.hypot(p.x - q.x, p.y - q.y)
            if isinstance(p, Pt) and isinstance(q, Ln):
                return _dist_pt_line(p, q)
            if isinstance(p, Ln) and isinstance(q, Pt):
                return _dist_pt_line(q, p)
            raise Inconclusive("Distance kiểu lạ")
        if fn == "Radius":
            (c,) = a
            if isinstance(c, Cir):
                return c.r
            raise Inconclusive("Radius không phải đường tròn")
        if fn == "Center":
            (c,) = a
            if isinstance(c, Cir):
                return Pt(c.cx, c.cy)
            raise Inconclusive("Center không phải đường tròn")
        if fn == "Midpoint":
            p, q = a
            return Pt((p.x + q.x) / 2, (p.y + q.y) / 2)
        if fn == "Line":
            p, q = a
            return _line_through(p, q)
        if fn == "Angle":
            x, v, c = a
            return _ccw_angle(v, x, c)
        # ---- predicate → bool ----
        if fn == "AreEqual":
            x, y = a
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                return abs(x - y) <= _TOL * (1 + max(abs(x), abs(y)))
            if isinstance(x, Pt) and isinstance(y, Pt):
                return math.hypot(x.x - y.x, x.y - y.y) <= _TOL
            raise Inconclusive("AreEqual kiểu lạ")
        if fn == "IsTangent":
            l, c = (a if isinstance(a[0], Ln) else (a[1], a[0]))
            if isinstance(l, Ln) and isinstance(c, Cir):
                return abs(_dist_pt_line(Pt(c.cx, c.cy), l) - c.r) <= _TOL * (1 + c.r)
            raise Inconclusive("IsTangent kiểu lạ")
        if fn in ("ArePerpendicular", "AreParallel"):
            l1, l2 = a
            if not (isinstance(l1, Ln) and isinstance(l2, Ln)):
                raise Inconclusive("cần hai đường thẳng")
            d1 = (-l1.b, l1.a)
            d2 = (-l2.b, l2.a)
            dot = d1[0] * d2[0] + d1[1] * d2[1]
            cross = d1[0] * d2[1] - d1[1] * d2[0]
            return abs(dot) <= _TOL if fn == "ArePerpendicular" else abs(cross) <= _TOL
        if fn == "AreCollinear":
            p, q, r = a
            cross = (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)
            n = math.hypot(q.x - p.x, q.y - p.y) * math.hypot(r.x - p.x, r.y - p.y)
            return abs(cross) <= _TOL * (n if n > 0 else 1)
        if fn == "AreConcurrent":
            l1, l2, l3 = a
            p = _intersect(l1, l2)
            return _dist_pt_line(p, l3) <= _TOL * 10
        if fn == "AreConcyclic":
            p1, p2, p3, p4 = a
            cir = _circle_through(p1, p2, p3)
            return abs(math.hypot(p4.x - cir.cx, p4.y - cir.cy) - cir.r) <= _TOL * 10 * (1 + cir.r)
        raise Inconclusive(f"hàm chưa hỗ trợ: {fn}")


def _intersect(l1: Ln, l2: Ln) -> Pt:
    det = l1.a * l2.b - l2.a * l1.b
    if abs(det) < 1e-12:
        raise Inconclusive("hai đường song song, không giao")
    x = (l1.c * l2.b - l2.c * l1.b) / det
    y = (l1.a * l2.c - l2.a * l1.c) / det
    return Pt(x, y)


def _circle_through(a: Pt, b: Pt, c: Pt) -> Cir:
    d = 2 * (a.x * (b.y - c.y) + b.x * (c.y - a.y) + c.x * (a.y - b.y))
    if abs(d) < 1e-12:
        raise Inconclusive("ba điểm thẳng hàng, không có đường tròn")
    ux = ((a.x**2 + a.y**2) * (b.y - c.y) + (b.x**2 + b.y**2) * (c.y - a.y) + (c.x**2 + c.y**2) * (a.y - b.y)) / d
    uy = ((a.x**2 + a.y**2) * (c.x - b.x) + (b.x**2 + b.y**2) * (a.x - c.x) + (c.x**2 + c.y**2) * (b.x - a.x)) / d
    return Cir(ux, uy, math.hypot(a.x - ux, a.y - uy))


def evaluate_assert(expr: str, geo: dict[str, object]) -> bool | None:
    """True/False nếu kết luận được, None nếu không (→ fallback GeoGebra)."""
    try:
        node = _Parser(_tokenize(expr)).parse()
        result = _Eval(geo).ev(node)
        return bool(result) if isinstance(result, (bool, int, float)) else None
    except Inconclusive:
        return None
    except Exception:
        return None


def verify_relations(asserts: list[str], objects: list[dict]) -> dict[str, bool | None]:
    """Map expr → verdict Python (True/False/None)."""
    geo = build_geometry(objects)
    return {expr: evaluate_assert(expr, geo) for expr in asserts}
