import json
import re
from ..llm.base import LLMProvider
from ..primitives.menu import build_menu

# Planner (LLM) — đặc tả PHẦN 2. Nhận đề + MENU đóng → xuất PLAN (JSON statements).
# KHÔNG viết lệnh GeoGebra thô; chỉ chọn primitive & nối tham chiếu.

FEWSHOT = """\
VÍ DỤ 1 — "Vẽ tam giác ABC, kẻ đường cao AH":
[
 {"op":"point_free","args":{"x":0,"y":0},"out":["A"]},
 {"op":"point_free","args":{"x":6,"y":0},"out":["B"]},
 {"op":"point_free","args":{"x":2,"y":5},"out":["C"]},
 {"op":"triangle","args":{"A":"A","B":"B","C":"C"},"out":["tri"]},
 {"op":"altitude","args":{"vertex":"A","A":"A","B":"B","C":"C"},"out":["H","AH"]}
]

VÍ DỤ 2 — "Từ A ngoài (O) kẻ hai tiếp tuyến AB, AC":
[
 {"op":"point_free","args":{"x":0,"y":0},"out":["O"]},
 {"op":"circle_center_radius","args":{"O":"O","r":3},"out":["circ"]},
 {"op":"point_free","args":{"x":8,"y":1},"out":["A"]},
 {"op":"tangent_from_point","args":{"P":"A","c":"circ"},"out":["B","C","tAB","tAC"]}
]

VÍ DỤ 3 — bài nửa đường tròn NHIỀU BƯỚC (chú ý second_intersection cho A và K vì
N là đầu đường kính nên N ĐÃ THUỘC nửa đường tròn):
"Nửa đtròn tâm O đk MN; P trên MO; d qua P ⊥ MN cắt (O) tại Q; F trên tia PQ ngoài
(O); FN cắt (O) tại A; MA cắt d tại E; NE cắt (O) tại điểm thứ hai K."
[
 {"op":"point_free","args":{"x":-5,"y":0},"out":["M"]},
 {"op":"point_free","args":{"x":5,"y":0},"out":["N"]},
 {"op":"semicircle","args":{"M":"M","N":"N"},"out":["semi","O"]},
 {"op":"point_on_segment","args":{"A":"M","B":"O","t":0.4},"out":["P"]},
 {"op":"line","args":{"A":"M","B":"N"},"out":["MN"]},
 {"op":"perpendicular_through","args":{"P":"P","line":"MN"},"out":["d"]},
 {"op":"intersect_line_circle","args":{"line":"d","c":"semi","index":1},"out":["Q"]},
 {"op":"point_on_ray_beyond","args":{"P":"P","Q":"Q","t":1.5},"out":["F"]},
 {"op":"line","args":{"A":"F","B":"N"},"out":["FN"]},
 {"op":"second_intersection","args":{"line":"FN","center":"O","known":"N"},"out":["A"]},
 {"op":"line","args":{"A":"M","B":"A"},"out":["MA"]},
 {"op":"intersect","args":{"obj1":"MA","obj2":"d"},"out":["E"]},
 {"op":"line","args":{"A":"N","B":"E"},"out":["NE"]},
 {"op":"second_intersection","args":{"line":"NE","center":"O","known":"N"},"out":["K"]}
]

VÍ DỤ 4 — ĐIỀU KIỆN GÓC trên đường tròn (∠PAF = ∠MAC) → point_on_circle_angle_transport.
Đỉnh góc A đã thuộc đường tròn (APN); F là điểm trên đường tròn sao cho góc ∠PAF
bằng góc tham chiếu ∠MAC. KHÔNG dùng point_on_object (điểm tự do, sai vị trí).
"Tam giác nhọn ABC (AB<AC); M,N,P trung điểm BC,CA,AB; trên cung nhỏ PN của đường
tròn (APN) lấy F sao cho ∠PAF=∠MAC; D = giao của AM và trung trực AB."
[
 {"op":"point_free","args":{"x":0,"y":5},"out":["A"]},
 {"op":"point_free","args":{"x":-4,"y":0},"out":["B"]},
 {"op":"point_free","args":{"x":6,"y":0},"out":["C"]},
 {"op":"triangle","args":{"A":"A","B":"B","C":"C"},"out":["tri"]},
 {"op":"midpoint","args":{"A":"B","B":"C"},"out":["M"]},
 {"op":"midpoint","args":{"A":"C","B":"A"},"out":["N"]},
 {"op":"midpoint","args":{"A":"A","B":"B"},"out":["P"]},
 {"op":"circle_through_3","args":{"A":"A","B":"P","C":"N"},"out":["capn"]},
 {"op":"point_on_circle_angle_transport","args":{"vertex":"A","from":"P","c":"capn","rA":"M","rB":"A","rC":"C"},"out":["F"]},
 {"op":"line","args":{"A":"A","B":"M"},"out":["AM"]},
 {"op":"perpendicular_bisector","args":{"A":"A","B":"B"},"out":["tt"]},
 {"op":"intersect","args":{"obj1":"AM","obj2":"tt"},"out":["D"]}
]

VÍ DỤ 5 — ĐƯỜNG TRÒN TIẾP XÚC đường thẳng tại điểm + GIAO THỨ HAI hai đường tròn:
"Tam giác ABC nhọn, AB<AC, trực tâm H. (O1) đi qua H và tiếp xúc BC tại B; (O2) đi
qua H và tiếp xúc BC tại C. (O1),(O2) cắt nhau tại điểm thứ hai K."
[
 {"op":"point_free","args":{"x":0,"y":5},"out":["A"]},
 {"op":"point_free","args":{"x":-4,"y":0},"out":["B"]},
 {"op":"point_free","args":{"x":6,"y":0},"out":["C"]},
 {"op":"triangle","args":{"A":"A","B":"B","C":"C"},"out":["tri"]},
 {"op":"orthocenter","args":{"A":"A","B":"B","C":"C"},"out":["H"]},
 {"op":"line","args":{"A":"B","B":"C"},"out":["bc"]},
 {"op":"circle_tangent_to_line_at","args":{"T":"B","line":"bc","P":"H"},"out":["O1","c1"]},
 {"op":"circle_tangent_to_line_at","args":{"T":"C","line":"bc","P":"H"},"out":["O2","c2"]},
 {"op":"second_intersection_two_circles","args":{"c1":"c1","c2":"c2","known":"H"},"out":["K"]}
]
"""


def _make_system() -> str:
    return f"""\
Bạn là PLANNER dựng hình THCS. Nhận đề tiếng Việt → xuất PLAN: mảng JSON các bước,
mỗi bước gọi MỘT primitive trong MENU dưới đây. TUYỆT ĐỐI:
- CHỈ dùng op có trong MENU. KHÔNG viết lệnh GeoGebra thô. KHÔNG bịa op.
- args: giá trị là TÊN output đã định nghĩa ở bước trước (string) HOẶC số literal
  (x,y,t,r,h,index). out: danh sách tên đối tượng tạo ra (đặt tên theo đề: A,B,C,O,M...).
- Đặt điểm gốc bằng point_free với tọa độ "đẹp", cân đối, tam giác không suy biến
  (vd A=(0,0), B=(6,0), C=(2,5)). Điểm phụ thuộc để primitive tự tính, KHÔNG tự đoán.
- Quy tắc chọn: "điểm trên đoạn/tia có vị trí"→point_on_segment/point_on_ray_beyond;
  "lấy điểm trên..." không vị trí→point_on_object/point_on_circle; "tiếp tuyến từ điểm
  ngoài"→tangent_from_point; "tiếp tuyến tại điểm trên đường tròn"→tangent_at_point;
  "đường cao/trung tuyến/phân giác trong"→altitude/median/angle_bisector_seg; "nửa
  đường tròn"→semicircle. Giao đường-đường tròn PHẢI có index (1 hoặc 2).
- GIAO ĐIỂM THỨ HAI (RẤT QUAN TRỌNG cho đề dài): khi đề nói "đường thẳng AB cắt
  đường tròn (O) tại <điểm mới>" mà A HOẶC B ĐÃ THUỘC (O) (là điểm trước đó dựng trên
  (O): tiếp điểm, đầu đường kính, điểm trên cung...), thì đường AB cắt (O) ở 2 chỗ:
  ngay tại điểm-đã-thuộc và tại điểm-mới. KHÔNG dùng intersect_line_circle với index
  (index không ổn định). DÙNG: second_intersection(line=AB, center=O, known=<đầu mút
  đã thuộc (O)>) → <điểm mới>. center là TÂM đường tròn (vd O của nửa đường tròn).
  Ví dụ: "FN cắt (O) tại A" với N đã thuộc (O) ⇒ second_intersection(FN, O, N)→A.
  "NE cắt (O) tại điểm thứ hai K" với N thuộc (O) ⇒ second_intersection(NE, O, N)→K.
  LƯU Ý: M và N (hai đầu ĐƯỜNG KÍNH) LUÔN thuộc nửa đường tròn; mọi điểm đã dựng trên
  cung/đường tròn cũng vậy. Nên BẤT KỲ "đường thẳng (qua M/N hoặc qua điểm trên (O))
  cắt (O) tại <điểm>" ĐỀU là second_intersection — KHÔNG cần đề ghi chữ "thứ hai".
  CHỈ dùng intersect_line_circle khi KHÔNG đầu mút nào thuộc (O) (vd d⊥MN cắt (O) tại Q).
- CHỐNG NÉT THỪA: đường vô hạn chỉ dùng làm CÔNG CỤ trung gian (KHÔNG được đề nhắc
  tên) → đặt tên bắt đầu "aux" để tự ẩn. NHƯNG nếu ĐỀ GỌI TÊN đường đó (vd "đường
  thẳng d", "đường thẳng xy") thì GIỮ tên đề cho, để HIỆN bình thường, KHÔNG aux.
- Lấy NHIỀU điểm phân biệt trên cùng đường tròn: point_on_circle có param∈[0,1] khác nhau.
- ĐIỀU KIỆN GÓC trên đường tròn: "lấy điểm F trên (đường tròn/cung) sao cho ∠XYF = ∠UVW"
  (đỉnh Y đã thuộc đường tròn) → point_on_circle_angle_transport(vertex=Y, from=X,
  c=<đường tròn>, rA=U, rB=V, rC=W). Phải dựng đường tròn TRƯỚC (vd circle_through_3 /
  circumcircle). TUYỆT ĐỐI KHÔNG dùng point_on_object cho điểm có ràng buộc GÓC (đó là
  điểm tự do, sai vị trí). Quay một điểm theo góc SỐ độ cho trước → rotate_point.
- ĐƯỜNG TRÒN TIẾP XÚC đường thẳng TẠI một điểm: "đường tròn đi qua P và tiếp xúc với
  (đường) tại điểm T" → tạo line trước rồi circle_tangent_to_line_at(T=<tiếp điểm>,
  line=<đường>, P=<điểm đi qua>) → [tâm, đường tròn]. KHÔNG dùng circle_through_3 (sẽ
  sai, tâm sập về điểm khác). GIAO THỨ HAI hai đường tròn đã biết 1 giao điểm chung →
  second_intersection_two_circles(c1, c2, known=<giao điểm đã biết>); KHÔNG dùng
  intersect_two_circles với index (không ổn định).
- TỨ GIÁC (dựng-đúng-định-nghĩa, KHÔNG tự đoán tọa độ 4 đỉnh; thứ tự A→B→C→D vòng quanh):
  "hình thoi ABCD góc BAD = X°"→rhombus_angle(A,B,angle=X); "hình thoi" không cho góc→
  rhombus(A,B,P) (P là điểm hướng đỉnh thứ ba). "hình bình hành"→parallelogram; "hình
  chữ nhật"→rectangle; "hình vuông"→square; "hình thang cân"→isosceles_trapezoid(A,B,h,
  lenCD) (AB đáy lớn, chọn lenCD<|AB|); "hình thang" thường→trapezoid; "hình diều / 2 cặp
  cạnh kề bằng, trục là đường chéo AC"→kite(A,C,B); "tứ giác ABCD nội tiếp (O)"→
  cyclic_quadrilateral(c, t1<t2<t3<t4 ∈[0,1]).
- TIẾP TUYẾN/ĐƯỜNG TRÒN chuyên: "đường tròn tiếp xúc 2 đường tại 2 điểm cho trước"→
  circle_tangent_2lines_at_points(line1,P1,line2,P2); "tiếp tuyến thứ hai/khác từ điểm
  ngoài"→tangent_other_than(P,c,known=<tiếp tuyến đã biết>); "đường tròn đường kính AB"→
  circle_diameter(A,B). Quay đối tượng theo góc số→rotate(obj,center,angle).
- Nếu đề cần thao tác KHÔNG có trong menu: xuất đúng một bước {{"op":"RAW","args":{{"note":"<mô tả>"}},"out":[]}}.

MENU PRIMITIVE (đóng):
{build_menu()}

ĐỊNH DẠNG OUTPUT: chỉ JSON mảng statements, không markdown, không giải thích.

{FEWSHOT}
"""


def _extract_json_array(text: str):
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


class Planner:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.system = _make_system()

    async def plan(
        self, problem: str, feedback: str | None = None, prev_plan: list | None = None
    ) -> list[dict]:
        if feedback and prev_plan is not None:
            user = (
                f'Đề: "{problem}"\n\n'
                f"Plan trước:\n{json.dumps(prev_plan, ensure_ascii=False)}\n\n"
                f"Vấn đề cần sửa:\n{feedback}\n\nTrả về PLAN JSON ĐÃ SỬA (đầy đủ)."
            )
        else:
            user = f'Đề: "{problem}"\n\nTrả về PLAN JSON.'
        raw = await self.provider.complete_text(self.system, user)
        plan = _extract_json_array(raw)
        if not isinstance(plan, list):
            raise ValueError(f"Planner trả không phải mảng: {raw[:200]}")
        return plan

    @staticmethod
    def is_raw(plan: list[dict]) -> bool:
        return any(st.get("op") == "RAW" for st in plan)
