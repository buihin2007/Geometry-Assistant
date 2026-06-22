"""ĐỊNH HƯỚNG TỔNG QUÁT (deterministic): xoay + (có thể) lật toàn hình để ĐOẠN NỀN
(dây/đường kính/đáy) nằm NGANG ở DƯỚI và APEX (điểm trên cung/đỉnh) ở TRÊN.

Đây là phép biến hình CỨNG (rigid: quay quanh gốc + lật dọc) áp lên TỌA ĐỘ tuyệt đối
trong danh sách lệnh — bảo toàn MỌI quan hệ (chỉ xoay/lật một cấu hình hợp lệ). Áp cho
các loại lệnh có tọa độ/góc tuyệt đối:
  • điểm tự do  X=(a,b)
  • SetCoords(P,a,b)  (literal — vd repair ràng buộc)
  • point_on_circle: SetCoords(...cos(θ*360°)...) → dịch góc θ
Các điểm dẫn xuất (Midpoint/Intersect/Reflect/CircularArc…) tự đi theo.
"""
import math
import re

_FREE = re.compile(r"^(\w+)\s*=\s*\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)\s*$")
_SETC = re.compile(r"^SetCoords\(\s*(\w+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)\s*$")
_ANG = re.compile(r"(-?[\d.]+)\s*\*\s*360°")


def _points(objects):
    return {
        o["name"]: (float(o["x"]), float(o["y"]))
        for o in objects
        if (o.get("type") or "").lower() == "point" and o.get("x") is not None
    }


def apply_orientation(commands: list[str], base, apex: str, objects: list[dict]) -> list[str]:
    """Trả danh sách lệnh đã định hướng (hoặc nguyên gốc nếu thiếu dữ liệu)."""
    pts = _points(objects)
    P, Q = base
    if not all(n in pts for n in (P, Q, apex)):
        return commands
    px, py = pts[P]
    qx, qy = pts[Q]
    beta = math.atan2(qy - py, qx - px)  # hướng base hiện tại
    # CHỈ DÙNG PHÉP QUAY (không lật gương) để bảo toàn chiều cung/định hướng — lật gương
    # không đổi được chiều CircularArc/Semicircle (topo) và không dịch điểm trên trục lật.
    gamma = -beta  # quay base về ngang

    def rotate(x, y, g):
        c, s = math.cos(g), math.sin(g)
        return x * c - y * s, x * s + y * c

    # apex phải ở TRÊN trung điểm base; nếu chưa → quay THÊM 180° (vẫn là phép quay).
    _, amy = rotate((px + qx) / 2, (py + qy) / 2, gamma)
    _, ary = rotate(*pts[apex], gamma)
    if ary < amy:
        gamma += math.pi

    def tp(x, y):
        return rotate(x, y, gamma)

    gamma_deg = math.degrees(gamma)

    def tang(theta_deg):  # góc tuyệt đối cộng thêm góc quay
        return theta_deg + gamma_deg

    out = []
    for cmd in commands:
        m = _FREE.match(cmd.strip())
        if m:
            x, y = tp(float(m.group(2)), float(m.group(3)))
            out.append(f"{m.group(1)}=({x:.6f},{y:.6f})")
            continue
        m = _SETC.match(cmd.strip())
        if m:
            x, y = tp(float(m.group(2)), float(m.group(3)))
            out.append(f"SetCoords({m.group(1)},{x:.6f},{y:.6f})")
            continue
        if "*360°" in cmd:  # point_on_circle: dịch góc tuyệt đối
            out.append(_ANG.sub(lambda mm: f"{tang(float(mm.group(1)) * 360):.4f}°", cmd))
            continue
        out.append(cmd)
    return out
