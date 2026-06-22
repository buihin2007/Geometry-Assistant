"""Compiler tất định: plan (DSL JSON) → lệnh GeoGebra + asserts (đặc tả PHẦN 2).
KHÔNG có LLM ở đây. Tên trong plan = tên GeoGebra (dùng trực tiếp).

- validate_plan: kiểm op tồn tại, tham chiếu hợp lệ, ràng buộc tham số, out duy nhất,
  thứ tự không vòng (dùng-trước-định-nghĩa). Chạy TRƯỚC compile.
- compile_plan: bung từng primitive ra lệnh + assert; sinh tên phụ "auxN" tự ẩn.
"""
from .registry import PRIMITIVES


class PlanError(Exception):
    pass


# Ràng buộc tham số literal (PHẦN 2, luật 3).
def _check_params(op: str, args: dict, errors: list[str]):
    def num(key):
        v = args.get(key)
        return v if isinstance(v, (int, float)) else None

    if op == "point_on_segment":
        t = num("t")
        if t is None or not (0 < t < 1):
            errors.append(f"point_on_segment.t phải ∈ (0,1), nhận {args.get('t')}")
    if op == "point_on_ray_beyond":
        t = num("t")
        if t is None or not (t > 1):
            errors.append(f"point_on_ray_beyond.t phải > 1, nhận {args.get('t')}")
    if op == "circle_center_radius":
        r = num("r")
        if r is None or not (r > 0):
            errors.append(f"circle_center_radius.r phải > 0, nhận {args.get('r')}")
    if op in ("triangle_isosceles", "triangle_right", "rectangle"):
        h = num("h")
        if h is None or not (h > 0):
            errors.append(f"{op}.h phải > 0, nhận {args.get('h')}")
    if op in ("intersect", "intersect_line_circle", "intersect_two_circles") and "index" in args:
        idx = args["index"]
        if idx not in (1, 2):
            errors.append(f"{op}.index phải là 1 hoặc 2, nhận {idx}")


def _refs(args: dict) -> list[str]:
    """Các giá trị là THAM CHIẾU (string) — gồm cả phần tử trong list 'points'."""
    out = []
    for v in args.values():
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            out.extend(x for x in v if isinstance(x, str))
    return out


def validate_plan(plan: list[dict]) -> list[str]:
    errors: list[str] = []
    known: set[str] = set()
    for i, st in enumerate(plan):
        op = st.get("op")
        args = st.get("args", {}) or {}
        out = st.get("out", []) or []
        tag = f"[#{i} {op}]"

        if op in ("RAW", "REQUIRE", "ORIENT"):
            # RAW: escape hatch. REQUIRE: ràng buộc "sao cho". ORIENT: gợi ý định hướng
            # (base/apex) cho hậu xử lý xoay-lật. Không sinh lệnh — bỏ qua ở đây.
            continue
        if op not in PRIMITIVES:
            errors.append(f"{tag} op không có trong menu primitive")
            continue
        prim = PRIMITIVES[op]

        # tham chiếu hợp lệ (string args phải đã định nghĩa trước, HOẶC là tên output
        # của chính bước này — vd 'order' của parallelogram_named chứa tên điểm mới).
        for ref in _refs(args):
            if ref not in known and ref not in out:
                errors.append(f"{tag} tham chiếu `{ref}` chưa được định nghĩa trước đó")

        # ràng buộc tham số
        _check_params(op, args, errors)

        # số output khớp
        if len(out) != prim.n_out:
            errors.append(f"{tag} cần {prim.n_out} output, nhận {len(out)}")

        # out duy nhất
        for name in out:
            if name in known:
                errors.append(f"{tag} tên output `{name}` trùng (đã dùng)")
            known.add(name)

    return errors


def valid_prefix(plan: list[dict]) -> tuple[list[dict], str | None]:
    """Tiền tố HỢP LỆ tối đa của plan + mô tả bước hỏng đầu tiên (fail gọn §6).

    Dừng ở statement đầu tiên: là RAW / op ngoài menu / tham chiếu chưa định nghĩa /
    sai số output. Trả (các statement dựng được, mô tả bước không dựng được hoặc None).
    """
    known: set[str] = set()
    prefix: list[dict] = []
    for st in plan:
        op = st.get("op")
        args = st.get("args", {}) or {}
        out = st.get("out", []) or []
        if op in ("REQUIRE", "ORIENT"):
            prefix.append(st)  # không phải bước dựng, giữ nguyên trong prefix
            continue
        if op == "RAW":
            note = (args.get("note") or "thao tác ngoài thư viện").strip()
            return prefix, f"bước '{note}' (chưa có primitive tương ứng)"
        if op not in PRIMITIVES:
            return prefix, f"phép dựng '{op}' chưa được hỗ trợ"
        bad_ref = next((r for r in _refs(args) if r not in known), None)
        if bad_ref is not None:
            return prefix, f"bước {op} cần '{bad_ref}' nhưng nó chưa dựng được"
        if len(out) != PRIMITIVES[op].n_out:
            return prefix, f"bước {op} sai số đối tượng tạo ra"
        for name in out:
            known.add(name)
        prefix.append(st)
    return prefix, None


def extract_constraints(plan: list[dict]) -> list[dict]:
    """Lấy các ràng buộc 'sao cho' planner trích ra: op REQUIRE với {rel,lhs,rhs}.
    rel ∈ lt|gt|le|ge|eq. lhs/rhs là biểu thức verifier đọc được (Distance/Angle/số)."""
    out = []
    for st in plan:
        if st.get("op") != "REQUIRE":
            continue
        a = st.get("args", {}) or {}
        if a.get("rel") and a.get("lhs") and a.get("rhs"):
            out.append({"rel": a["rel"], "lhs": a["lhs"], "rhs": a["rhs"]})
    return out


def extract_orient(plan: list[dict]) -> dict | None:
    """Lấy gợi ý ĐỊNH HƯỚNG: op ORIENT với {base:[P,Q], apex:R}. Dùng cho hậu xử lý
    xoay base về ngang-dưới, lật apex lên trên (giữ nguyên quan hệ)."""
    for st in plan:
        if st.get("op") != "ORIENT":
            continue
        a = st.get("args", {}) or {}
        base = a.get("base")
        apex = a.get("apex")
        if isinstance(base, list) and len(base) == 2 and apex:
            return {"base": [str(base[0]), str(base[1])], "apex": str(apex)}
    return None


def compile_plan(plan: list[dict]) -> tuple[list[str], list[str]]:
    """Trả (commands, asserts). Gọi sau khi validate_plan sạch (hoặc bỏ qua RAW)."""
    commands: list[str] = []
    asserts: list[str] = []
    counter = {"n": 0}

    def aux() -> str:
        counter["n"] += 1
        return f"aux{counter['n']}"

    for st in plan:
        op = st.get("op")
        if op == "RAW" or op not in PRIMITIVES:
            continue
        prim = PRIMITIVES[op]
        cmds, asr = prim.build(st.get("args", {}) or {}, st.get("out", []) or [], aux)
        commands.extend(cmds)
        asserts.extend(asr)

    return commands, asserts
