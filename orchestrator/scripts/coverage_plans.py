"""Coverage checklist THCS chạy TẤT ĐỊNH (không LLM) — đo độ phủ thư viện primitive
+ compiler + validator quan hệ. Miễn nhiễm quota LLM; dùng làm regression cố định.
Mỗi mục là một plan viết tay (đúng thứ tự phụ thuộc) cho một cấu hình trong PHẦN 3.

Chạy:  GGB_SERVICE_URL=http://localhost:8081 ./.venv/Scripts/python -u -m scripts.coverage_plans
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ggb_client import GgbClient
from app.primitives.compiler import validate_plan, compile_plan
from app.agents.validator import validate


def s(op, args, out):
    return {"op": op, "args": args, "out": out}


P = lambda x, y, n: s("point_free", {"x": x, "y": y}, [n])
TRI = [P(0, 0, "A"), P(6, 0, "B"), P(2, 5, "C"), s("triangle", {"A": "A", "B": "B", "C": "C"}, ["tri"])]

CASES = {
 "B01 đoạn+trung điểm": [P(0,0,"A"),P(6,2,"B"),s("segment",{"A":"A","B":"B"},["AB"]),s("midpoint",{"A":"A","B":"B"},["M"])],
 "B02 AH⊥d": [P(-2,0,"U"),P(6,0,"V"),s("line",{"A":"U","B":"V"},["d"]),P(2,4,"A"),s("foot_of_perpendicular",{"P":"A","line":"d"},["H","AH"])],
 "B03 song song qua A": [P(-2,0,"U"),P(6,0,"V"),s("line",{"A":"U","B":"V"},["d"]),P(1,3,"A"),s("parallel_through",{"P":"A","line":"d"},["e"])],
 "B04 trung trực AB": [P(0,0,"A"),P(6,0,"B"),s("perpendicular_bisector",{"A":"A","B":"B"},["d"])],
 "B05 phân giác xOy": [P(5,0,"X"),P(0,0,"O"),P(3,4,"Y"),s("angle_bisector",{"A":"X","B":"O","C":"Y"},["d"])],
 "T01 tam giác": TRI,
 "T02 cân tại A": [P(0,0,"A"),P(6,0,"B"),s("triangle_isosceles",{"A":"A","B":"B","h":5},["C","tri"])],
 "T03 đường cao AH": TRI+[s("altitude",{"vertex":"A","A":"A","B":"B","C":"C"},["H","AH"])],
 "T04 3 đường cao+trực tâm": TRI+[
    s("altitude",{"vertex":"A","A":"A","B":"B","C":"C"},["Ha","ha"]),
    s("altitude",{"vertex":"B","A":"A","B":"B","C":"C"},["Hb","hb"]),
    s("altitude",{"vertex":"C","A":"A","B":"B","C":"C"},["Hc","hc"]),
    s("orthocenter",{"A":"A","B":"B","C":"C"},["Hh"])],
 "T05 3 trung tuyến+G": TRI+[
    s("median",{"vertex":"A","A":"A","B":"B","C":"C"},["Ma","ma"]),
    s("median",{"vertex":"B","A":"A","B":"B","C":"C"},["Mb","mb"]),
    s("median",{"vertex":"C","A":"A","B":"B","C":"C"},["Mc","mc"]),
    s("centroid",{"A":"A","B":"B","C":"C"},["G"])],
 "T06 phân giác trong→D": TRI+[s("angle_bisector_seg",{"vertex":"A","A":"A","B":"B","C":"C"},["D","dA"])],
 "T07 tâm ngoại tiếp": TRI+[s("circumcenter",{"A":"A","B":"B","C":"C"},["O"])],
 "T08 đường trung bình": TRI+[s("midsegment",{"A":"A","B":"B","C":"C"},["Mm","Nn","mid"])],
 "T09 nội tiếp tâm I": TRI+[s("incircle",{"A":"A","B":"B","C":"C"},["I","ic"])],
 "C01 đtròn tâm-bk": [P(0,0,"O"),s("circle_center_radius",{"O":"O","r":3},["c"])],
 "C02 ngoại tiếp": TRI+[s("circumcircle",{"A":"A","B":"B","C":"C"},["O","cc"])],
 "C03 dây+đường kính": [P(0,0,"O"),s("circle_center_radius",{"O":"O","r":4},["c"]),
    s("point_on_circle",{"c":"c","param":0.1},["A"]),s("point_on_circle",{"c":"c","param":0.4},["B"]),s("chord",{"A":"A","B":"B"},["AB"]),
    s("point_on_circle",{"c":"c","param":0.7},["Cp"]),s("diameter_point",{"O":"O","A":"Cp"},["Dp"]),s("segment",{"A":"Cp","B":"Dp"},["CD"])],
 "C04 góc nội tiếp": [P(0,0,"O"),s("circle_center_radius",{"O":"O","r":4},["c"]),
    s("point_on_circle",{"c":"c","param":0.1},["A"]),s("point_on_circle",{"c":"c","param":0.45},["B"]),s("point_on_circle",{"c":"c","param":0.8},["Cp"]),
    s("inscribed_angle",{"A":"B","B":"A","C":"Cp"},["alpha"])],
 "C05 2 tiếp tuyến": [P(0,0,"O"),s("circle_center_radius",{"O":"O","r":3},["c"]),P(8,1,"A"),
    s("tangent_from_point",{"P":"A","c":"c"},["B","Cc","tAB","tAC"])],
 "C06 tiếp tuyến tại A": [P(0,0,"O"),s("circle_center_radius",{"O":"O","r":3},["c"]),
    s("point_on_circle",{"c":"c"},["A"]),s("tangent_at_point",{"A":"A","c":"c"},["t"])],
 "C07 hai đtròn cắt": [P(0,0,"O1"),s("circle_center_radius",{"O":"O1","r":3},["c1"]),
    P(4,0,"O2"),s("circle_center_radius",{"O":"O2","r":3},["c2"]),
    s("intersect_two_circles",{"c1":"c1","c2":"c2","index":1},["A"]),
    s("intersect_two_circles",{"c1":"c1","c2":"c2","index":2},["B"])],
 "C08 nửa đường tròn": [P(-5,0,"M"),P(5,0,"N"),s("semicircle",{"M":"M","N":"N"},["semi","O"])],
 "Q01 hbh+2 chéo": [P(0,0,"A"),P(5,0,"B"),P(6,3,"C"),s("parallelogram",{"A":"A","B":"B","C":"C"},["D","poly"]),
    s("diagonal",{"P":"A","Q":"C"},["AC"]),s("diagonal",{"P":"B","Q":"D"},["BD"]),
    s("intersect",{"obj1":"AC","obj2":"BD"},["O"])],
 "Q02 hình chữ nhật": [P(0,0,"A"),P(5,0,"B"),s("rectangle",{"A":"A","B":"B","h":3},["C","D","poly"])],
 "Q03 hình vuông": [P(0,0,"A"),P(4,0,"B"),s("square",{"A":"A","B":"B"},["C","D","poly"])],
 "Q04 hình thoi+chéo": [P(0,0,"A"),P(4,0,"B"),P(6,3,"Pd"),s("rhombus",{"A":"A","B":"B","P":"Pd"},["C","D","poly"]),
    s("diagonal",{"P":"A","Q":"C"},["AC"]),s("diagonal",{"P":"B","Q":"D"},["BD"])],
 "Q05 hình thang": [P(0,0,"A"),P(6,0,"B"),P(5,3,"C"),s("trapezoid",{"A":"A","B":"B","C":"C"},["D","poly"])],
 "S01 đối xứng trục": [P(-2,0,"U"),P(6,0,"V"),s("line",{"A":"U","B":"V"},["d"]),P(1,3,"A"),
    s("reflect_over_line",{"obj":"A","line":"d"},["Ap"])],
 "S02 đối xứng tâm": [P(0,0,"O"),P(3,1,"A"),s("reflect_over_point",{"obj":"A","O":"O"},["Ap"])],
 # auxMN, auxd: công cụ trung gian (tự ẩn); chỉ hiện đoạn PQ.
 "X01 nửa đtròn nhiều bước": [P(-5,0,"M"),P(5,0,"N"),s("semicircle",{"M":"M","N":"N"},["semi","O"]),
    s("point_on_segment",{"A":"M","B":"O","t":0.35},["Pp"]),s("line",{"A":"M","B":"N"},["auxMN"]),
    s("perpendicular_through",{"P":"Pp","line":"auxMN"},["auxd"]),s("intersect_line_circle",{"line":"auxd","c":"semi","index":1},["Q"]),
    s("segment",{"A":"Pp","B":"Q"},["PQ"])],
 # OA, BC vẽ thành ĐOẠN (đúng đề) thay vì đường vô hạn → không nét thừa.
 "X03 tiếp tuyến+OA∩BC": [P(0,0,"O"),s("circle_center_radius",{"O":"O","r":3},["c"]),P(8,1,"A"),
    s("tangent_from_point",{"P":"A","c":"c"},["B","Cc","tAB","tAC"]),s("segment",{"A":"O","B":"A"},["OA"]),
    s("segment",{"A":"B","B":"Cc"},["BC"]),s("intersect",{"obj1":"OA","obj2":"BC"},["H"])],
}


async def main() -> int:
    c = GgbClient(os.environ.get("GGB_SERVICE_URL", "http://localhost:8081"))
    npass = npart = nfail = 0
    for name, plan in CASES.items():
        errs = validate_plan(plan)
        if errs:
            print(f"☐ fail   {name}: plan invalid → {errs}", flush=True); nfail += 1; continue
        cmds, asr = compile_plan(plan)
        try:
            r = await c.render(cmds, ["png"], checks=asr)
        except Exception as e:
            print(f"☐ fail   {name}: render {e}", flush=True); nfail += 1; continue
        v = validate(cmds, r)
        if not v.ok or not r.get("pngBase64"):
            print(f"☐ fail   {name}: {v.errors}", flush=True); nfail += 1
        elif v.warnings:
            print(f"◐ warn   {name}: {v.warnings}", flush=True); npart += 1
        else:
            chk = sum(1 for x in r.get("checkResults", []) if x.get("value") == 1)
            tot = len(r.get("checkResults", []))
            print(f"☑ pass   {name}  (asserts {chk}/{tot})", flush=True); npass += 1
    print(f"\n☑ {npass}  ◐ {npart}  ☐ {nfail}  / {len(CASES)} mục", flush=True)
    return 1 if nfail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
