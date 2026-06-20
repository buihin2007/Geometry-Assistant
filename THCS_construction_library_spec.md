# Đặc tả thư viện dựng hình THCS (primitive + planner DSL + coverage)

> Tài liệu nền để feed cho Claude Code, thay thế cách "LLM → lệnh GeoGebra thô" bằng kiến trúc **thư viện primitive đã verify + planner + compiler tất định**. Mục tiêu: phủ MỌI cấu hình hình học phẳng cấp THCS một cách bền vững, đo được.

## Nguyên lý

Mọi đề THCS là một **chuỗi thao tác dựng cơ bản** nối tiếp. Số khối dựng cơ bản (primitive) là **hữu hạn** (~50), nhưng ghép lại phủ **vô hạn** đề. Luồng:

```
Đề (tiếng Việt)
   → PLANNER (LLM)  : phân rã thành plan = chuỗi lời gọi primitive (DSL/JSON)
   → VALIDATOR plan : kiểm tra tham chiếu, ràng buộc tham số
   → COMPILER (code): bung mỗi primitive ra lệnh GeoGebra từ template đã verify  ← KHÔNG có LLM
   → GeoGebra render
   → VALIDATOR quan hệ (Python, đọc tọa độ): kiểm tiếp xúc/vuông góc/thuộc...
```

LLM chỉ làm việc ở mức "chọn primitive nào, nối ra sao" (đáng tin), không viết cú pháp GeoGebra (dễ sai). Lỗi cú pháp tiêu biến vì lệnh đến từ template đã khóa.

**Quy ước chung cho mọi primitive:**
- Mỗi primitive khi implement phải: (a) emit lệnh GeoGebra đã **verify trên applet thật**; (b) **tự ẩn** đối tượng phụ vô hạn dùng làm công cụ trung gian (`SetVisibleInView(...,false)`); (c) **bật nhãn** cho các điểm/đối tượng hiển thị có tên; (d) trả ra các output có tên để bước sau tham chiếu.
- Tên lệnh GeoGebra **dùng tiếng Anh, ngoặc tròn** (không ngoặc vuông, không tên tiếng Việt).
- Cột "GeoGebra (nháp)" bên dưới là gợi ý — **bắt buộc verify lại** khi implement, đặc biệt chỉ số `Intersect` và hướng `Semicircle`.

---

# PHẦN 1 — Thư viện primitive THCS (~50 khối)

## A. Điểm & đối tượng cơ bản

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|---|
| `point_free` | x, y | P | Điểm tự do tại tọa độ | `P=(x,y)` |
| `point_on_segment` | A, B, t∈(0,1) | P | Điểm trên đoạn AB theo tỷ lệ t (khác hai đầu) | `P=A+t*(B-A)` |
| `point_on_ray_beyond` | P, Q, t>1 | F | Điểm trên tia PQ, vượt qua Q | `F=P+t*(Q-P)` |
| `point_on_object` | path | P | Điểm tự do trên path (đoạn/đường/đường tròn/cung) — khi đề KHÔNG cho vị trí cụ thể | `P=Point(path)` |
| `midpoint` | A, B | M | Trung điểm | `M=Midpoint(A,B)` |
| `segment` | A, B | s | Đoạn thẳng | `s=Segment(A,B)` |
| `line` | A, B | l | Đường thẳng (vô hạn) — chỉ khi đề thực sự muốn "đường thẳng" | `l=Line(A,B)` |
| `ray` | A, B | r | Tia gốc A qua B | `r=Ray(A,B)` |
| `distance` | A, B | d | Độ dài đoạn (giá trị số) | `d=Distance(A,B)` |

## B. Quan hệ đường thẳng

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|---|
| `parallel_through` | P, line | l | Đường qua P song song line | `l=Line(P,line)` |
| `perpendicular_through` | P, line | l (aux, tự ẩn nếu là công cụ) | Đường qua P vuông góc line | `l=PerpendicularLine(P,line)` |
| `foot_of_perpendicular` | P, line | H, seg PH | Chân vuông góc + đoạn từ P (ẩn đường vô hạn) | `H=ClosestPoint(line,P)` → `Segment(P,H)` |
| `perpendicular_bisector` | A, B | l (aux, tự ẩn nếu là công cụ) | Trung trực đoạn AB | `l=PerpendicularBisector(A,B)` |
| `angle_bisector` | A, B, C | l | Phân giác góc ABC (đỉnh B) | `l=AngleBisector(A,B,C)` |
| `intersect` | obj1, obj2, [index] | P | Giao điểm (index khi có nhiều nghiệm) | `P=Intersect(obj1,obj2[,n])` |
| `intersect_pick_side` | obj1, obj2, side | P | Giao điểm + lọc theo nửa mặt phẳng (vd y≥y0) trong Python | (full circle Intersect + filter) |

## C. Tam giác

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|---|
| `triangle` | A, B, C | poly | Tam giác | `poly=Polygon(A,B,C)` |
| `triangle_equilateral` | A, B | C, poly | Tam giác đều trên cạnh AB | verify (dựng C bằng quay 60° / giao 2 đường tròn) |
| `triangle_isosceles` | base A,B, height h | C, poly | Tam giác cân đáy AB | `C=Midpoint(A,B)+h*UnitPerp...` verify |
| `triangle_right` | A, B (cạnh huyền/góc vuông) | C, poly | Tam giác vuông | verify |
| `altitude` | vertex, A, B, C | H (chân), seg | Đường cao từ đỉnh (ẩn đường vô hạn) | `PerpendicularLine`→`Intersect`→`Segment` |
| `median` | vertex, A, B, C | M, seg | Trung tuyến từ đỉnh tới trung điểm cạnh đối | `M=Midpoint(...)`→`Segment(vertex,M)` |
| `angle_bisector_seg` | vertex, A, B, C | D, seg | Phân giác trong từ đỉnh, cắt cạnh đối tại D (ẩn đường vô hạn) | `AngleBisector`→`Intersect`→`Segment` |
| `midsegment` | A, B, C (2 cạnh) | seg | Đường trung bình (nối trung điểm 2 cạnh) | 2×`Midpoint`→`Segment` |
| `centroid` | A, B, C | G | Trọng tâm | `G=Centroid(Polygon(A,B,C))` |
| `orthocenter` | A, B, C | H | Trực tâm (giao 2 đường cao) | giao 2 `PerpendicularLine` |
| `incenter` | A, B, C | I | Tâm nội tiếp (giao 2 phân giác) | giao 2 `AngleBisector` |
| `circumcenter` | A, B, C | O | Tâm ngoại tiếp (giao 2 trung trực) | giao 2 `PerpendicularBisector` |

## D. Đường tròn

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|---|
| `circle_center_radius` | O, r | c | Đường tròn tâm O bán kính r | `c=Circle(O,r)` |
| `circle_center_point` | O, A | c | Tâm O đi qua A | `c=Circle(O,A)` |
| `circle_through_3` | A, B, C | c | Qua 3 điểm | `c=Circle(A,B,C)` |
| `circumcircle` | A, B, C | O, c | Đường tròn ngoại tiếp tam giác | `c=Circle(A,B,C)`, `O=Center(c)` |
| `incircle` | A, B, C | I, c, tiếp điểm | Đường tròn nội tiếp | `incenter`→ r=`Distance(I,Line(A,B))`→`Circle(I,r)` |
| `semicircle` | M, N | s, O | Nửa đường tròn đường kính MN | `s=Semicircle(M,N)`, `O=Midpoint(M,N)` (verify hướng) |
| `arc` | O, A, B | a | Cung tròn | `a=CircularArc(O,A,B)` verify |
| `chord` | A, B (trên c) | s | Dây cung | `s=Segment(A,B)` |
| `diameter_point` | O, A, c | B | Điểm đối tâm của A qua O (đầu kia đường kính) | `B=Reflect(A,O)` |
| `tangent_from_point` | P (ngoài c), c | t1, t2, tiếp điểm B, C | Hai tiếp tuyến từ điểm ngoài | `Tangent(P,c)`→`Intersect(t_i,c)` |
| `tangent_at_point` | A (trên c), c | t | Tiếp tuyến tại A (⊥ bán kính OA) | `PerpendicularLine(A,Line(Center(c),A))` |
| `intersect_line_circle` | line, c, [index/side] | P (1 hoặc 2) | Giao đường–đường tròn, chọn nghiệm đúng | `Intersect(line,c[,n])` + lọc |
| `intersect_two_circles` | c1, c2, [index] | P1, P2 | Giao hai đường tròn | `Intersect(c1,c2[,n])` |
| `point_on_circle` | c, [param] | P | Điểm trên đường tròn | `Point(c)` |

## E. Góc (ký hiệu/hiển thị)

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|---|
| `angle_mark` | A, B, C | α | Ký hiệu góc ABC (đỉnh B) | `α=Angle(A,B,C)` |
| `right_angle_mark` | A, B, C | — | Ký hiệu góc vuông tại B | `Angle(A,B,C)` (GeoGebra tự hiện ô vuông khi 90°) |
| `inscribed_angle` | A, B, C trên c | α | Góc nội tiếp (chỉ là angle_mark trên đường tròn) | `Angle(A,B,C)` |

## F. Tứ giác & đa giác

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|---|
| `polygon` | P1..Pn | poly | Đa giác tổng quát | `Polygon(P1,...,Pn)` |
| `parallelogram` | A, B, C | D, poly | Hình bình hành (D = A+C−B) | `D=A+(C-B)`→`Polygon(A,B,C,D)` |
| `rectangle` | A, B, h | C, D, poly | Hình chữ nhật trên cạnh AB, cao h | verify (dựng vuông góc) |
| `square` | A, B | C, D, poly | Hình vuông cạnh AB | verify |
| `rhombus` | A, B, C | D, poly | Hình thoi | verify |
| `trapezoid` | A, B, C, D | poly | Hình thang (1 cặp cạnh song song) | dựng D song song AB qua C |
| `diagonal` | P, Q (đỉnh đối) | s | Đường chéo | `s=Segment(P,Q)` |

## G. Đối xứng (THCS lớp 8)

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|---|
| `reflect_over_line` | obj, line | obj' | Đối xứng trục | `Reflect(obj,line)` |
| `reflect_over_point` | obj, O | obj' | Đối xứng tâm | `Reflect(obj,O)` |

## H. Tiện ích hiển thị (do compiler gọi, planner thường không gọi trực tiếp)

| Primitive | Inputs | Mô tả | GeoGebra (nháp) |
|---|---|---|---|
| `hide` | obj | Ẩn đối tượng phụ vô hạn | `SetVisibleInView(obj,1,false)` |
| `show_label` | obj | Bật nhãn | `ShowLabel(obj,true)` |
| `set_style` | obj, color/line | Màu/nét (nhấn mạnh đoạn chính so với phụ) | `SetColor`, `SetLineStyle` |

> Tổng ~50 primitive. Backlog implement = build + verify từng cái. Đây cũng là đơn vị "skill" đúng nghĩa: mỗi primitive verify một lần, ghép lại phủ mọi đề.

---

# PHẦN 2 — Đặc tả Planner DSL

## Vai trò
Planner (LLM) nhận đề + **danh sách primitive (menu đóng)** → xuất một **plan**. Planner KHÔNG được tự bịa primitive ngoài menu, KHÔNG xuất lệnh GeoGebra thô.

## Định dạng máy (canonical): JSON
LLM xuất một mảng "statements". Mỗi statement:

```json
{
  "op": "point_on_segment",
  "args": { "A": "M", "B": "O", "t": 0.35 },
  "out": ["P"]
}
```

- `op`: tên primitive, PHẢI thuộc menu.
- `args`: object; giá trị là **tên output đã định nghĩa trước đó** (string) hoặc **literal số** (cho t, r, h...).
- `out`: danh sách tên đối tượng tạo ra; tên điểm theo đúng đề (M, N, O, P, Q...).

## Dạng đọc cho người (tương đương, để review)
```
point_on_segment(A=M, B=O, t=0.35) -> P
```

## Ví dụ plan đầy đủ — bài nửa đường tròn
```json
[
  {"op":"point_free","args":{"x":-5,"y":0},"out":["M"]},
  {"op":"point_free","args":{"x":5,"y":0},"out":["N"]},
  {"op":"semicircle","args":{"M":"M","N":"N"},"out":["s","O"]},
  {"op":"point_on_segment","args":{"A":"M","B":"O","t":0.35},"out":["P"]},
  {"op":"perpendicular_through","args":{"P":"P","line":"MN"},"out":["d"]},
  {"op":"intersect_line_circle","args":{"line":"d","c":"s"},"out":["Q"]},
  {"op":"point_on_ray_beyond","args":{"P":"P","Q":"Q","t":1.6},"out":["F"]},
  {"op":"segment","args":{"A":"F","B":"N"},"out":["FN"]},
  {"op":"intersect_line_circle","args":{"line":"FN","c":"s"},"out":["A"]},
  {"op":"line","args":{"A":"M","B":"A"},"out":["MA"]},
  {"op":"intersect","args":{"obj1":"MA","obj2":"d"},"out":["E"]},
  {"op":"line","args":{"A":"N","B":"E"},"out":["NE"]},
  {"op":"intersect_line_circle","args":{"line":"NE","c":"s","index":2},"out":["K"]}
]
```
(Lưu ý: `MN` cần được tạo trước hoặc cho `perpendicular_through` nhận trực tiếp hai điểm M,N — chuẩn hóa khi implement.)

## Luật validate plan (chạy trước compiler, deterministic)
1. **Op tồn tại**: mọi `op` phải có trong menu primitive. Nếu không → reject (hoặc escape hatch).
2. **Tham chiếu hợp lệ**: mọi giá trị args dạng string phải là một `out` đã định nghĩa ở statement trước, hoặc tên điểm gốc đã khai báo.
3. **Ràng buộc tham số**:
   - `point_on_segment.t` ∈ (0,1).
   - `point_on_ray_beyond.t` > 1.
   - `circle_center_radius.r` > 0.
   - `tangent_from_point`: P phải ngoài đường tròn (kiểm sau khi compile, qua validator quan hệ).
4. **Tên output duy nhất**: không trùng tên đã dùng.
5. **Thứ tự không vòng**: mỗi đối tượng dùng trước khi được định nghĩa → lỗi (đặc biệt chặn kiểu `d=Line(P,Q)` trong khi Q phụ thuộc d).

## Prompt cho Planner
- Inject **menu primitive** (tên + chữ ký input/output + 1 dòng mô tả + khi nào dùng).
- Inject 3–5 **few-shot plan** mẫu (gồm bài nhiều bước như trên).
- Yêu cầu xuất **JSON hợp lệ duy nhất**, không kèm giải thích.
- Quy tắc chọn primitive: đề nói "điểm trên đoạn/tia có mô tả vị trí" → `point_on_segment`/`point_on_ray_beyond`; "lấy điểm trên..." không vị trí cụ thể → `point_on_object`; "tiếp tuyến từ A" → `tangent_from_point`; "nửa đường tròn" → `semicircle`; v.v.

## Escape hatch
Nếu đề cần thao tác chưa có primitive: planner đánh dấu `{"op":"RAW","args":{"note":"..."}}`, hệ chuyển sang sinh lệnh thô (pipeline cũ) + validate + **log** để bổ sung primitive mới sau. Mỗi RAW là một mục backlog.

---

# PHẦN 3 — Coverage checklist (bộ test THCS)

Mỗi mục = một cấu hình + đề test chuẩn + primitive cần. Theo dõi cột Trạng thái (☐ chưa / ◐ một phần / ☑ pass). Đây vừa là thước đo độ phủ, vừa là backlog primitive, vừa là test hồi quy.

## Nhóm 1 — Đường, đoạn, góc cơ bản
| ID | Cấu hình | Đề test | Primitive cần | TT |
|---|---|---|---|---|
| B01 | Đoạn & trung điểm | "Vẽ đoạn AB và trung điểm M" | segment, midpoint | ☐ |
| B02 | Đường vuông góc qua điểm | "Vẽ đường thẳng d, điểm A ngoài d, kẻ AH⊥d" | foot_of_perpendicular | ☐ |
| B03 | Đường song song qua điểm | "Qua A kẻ đường song song với d" | parallel_through | ☐ |
| B04 | Trung trực đoạn | "Vẽ trung trực của đoạn AB" | perpendicular_bisector | ☐ |
| B05 | Phân giác góc | "Vẽ tia phân giác góc xOy" | angle_bisector | ☐ |

## Nhóm 2 — Tam giác & đường/điểm đặc biệt
| ID | Cấu hình | Đề test | Primitive cần | TT |
|---|---|---|---|---|
| T01 | Tam giác thường | "Vẽ tam giác ABC" | triangle | ☐ |
| T02 | Tam giác cân / đều / vuông | "Vẽ tam giác ABC cân tại A" / "đều" / "vuông tại A" | triangle_isosceles/equilateral/right | ☐ |
| T03 | Một đường cao | "Tam giác ABC, kẻ đường cao AH" | altitude | ☐ |
| T04 | Ba đường cao + trực tâm | "Tam giác ABC có 3 đường cao, xác định trực tâm H" | altitude×3, orthocenter | ☐ |
| T05 | Trung tuyến + trọng tâm | "Ba trung tuyến, trọng tâm G" | median×3, centroid | ☐ |
| T06 | Phân giác trong | "Phân giác góc A cắt BC tại D" | angle_bisector_seg | ☐ |
| T07 | Trung trực ba cạnh + tâm ngoại | "Tâm đường tròn ngoại tiếp O" | perpendicular_bisector, circumcenter | ☐ |
| T08 | Đường trung bình | "Đường trung bình MN của tam giác" | midsegment | ☐ |
| T09 | Tâm nội tiếp | "Đường tròn nội tiếp tâm I" | incircle | ☐ |

## Nhóm 3 — Đường tròn
| ID | Cấu hình | Đề test | Primitive cần | TT |
|---|---|---|---|---|
| C01 | Đường tròn tâm–bán kính | "Vẽ đường tròn tâm O bán kính 3" | circle_center_radius | ☐ |
| C02 | Ngoại tiếp tam giác | "Tam giác ABC nội tiếp đường tròn tâm O" | circumcircle | ☐ |
| C03 | Dây & đường kính | "Đường tròn (O), dây AB, đường kính CD" | chord, diameter_point | ☐ |
| C04 | Góc nội tiếp / ở tâm | "Góc nội tiếp BAC chắn cung BC" | inscribed_angle | ☐ |
| C05 | Tiếp tuyến từ điểm ngoài | "Từ A ngoài (O) kẻ hai tiếp tuyến AB, AC" | tangent_from_point | ☐ |
| C06 | Tiếp tuyến tại một điểm | "Tiếp tuyến của (O) tại điểm A trên đường tròn" | tangent_at_point | ☐ |
| C07 | Hai đường tròn cắt nhau | "Hai đường tròn (O) và (O') cắt nhau tại A, B" | circle, intersect_two_circles | ☐ |
| C08 | Nửa đường tròn | "Nửa đường tròn đường kính MN" | semicircle | ☐ |
| C09 | Cung & tiếp tuyến-dây | "Cung AB, tiếp tuyến tại A và dây AB" | arc, tangent_at_point, chord | ☐ |

## Nhóm 4 — Tứ giác
| ID | Cấu hình | Đề test | Primitive cần | TT |
|---|---|---|---|---|
| Q01 | Hình bình hành + chéo | "Hình bình hành ABCD, hai đường chéo cắt nhau tại O" | parallelogram, diagonal, intersect | ☐ |
| Q02 | Hình chữ nhật | "Vẽ hình chữ nhật ABCD" | rectangle | ☐ |
| Q03 | Hình vuông | "Vẽ hình vuông ABCD" | square | ☐ |
| Q04 | Hình thoi | "Hình thoi ABCD, hai đường chéo" | rhombus, diagonal | ☐ |
| Q05 | Hình thang | "Hình thang ABCD (AB // CD)" | trapezoid | ☐ |
| Q06 | Tứ giác nội tiếp | "Tứ giác ABCD nội tiếp đường tròn" | polygon, circle_through_3/point_on_circle | ☐ |

## Nhóm 5 — Đối xứng
| ID | Cấu hình | Đề test | Primitive cần | TT |
|---|---|---|---|---|
| S01 | Đối xứng trục | "Vẽ điểm A' đối xứng với A qua đường thẳng d" | reflect_over_line | ☐ |
| S02 | Đối xứng tâm | "Vẽ A' đối xứng với A qua điểm O" | reflect_over_point | ☐ |

## Nhóm 6 — Tổng hợp nhiều bước (config thi)
| ID | Cấu hình | Đề test | Primitive cần | TT |
|---|---|---|---|---|
| X01 | Nửa đường tròn nhiều bước | (Bài MN/P/Q/F/A/E/K đầy đủ) | semicircle, point_on_segment, perpendicular_through, intersect_line_circle, point_on_ray_beyond, line, intersect | ☐ |
| X02 | Tam giác + đường cao + đường tròn | "Tam giác ABC, đường cao AH, đường tròn đường kính AH" | altitude, semicircle/circle | ☐ |
| X03 | Tiếp tuyến + tính chất | "Từ A kẻ 2 tiếp tuyến AB, AC tới (O); OA cắt BC tại H" | tangent_from_point, line, intersect | ☐ |

> Mở rộng dần: mỗi đề thực tế người dùng báo fail → thêm một dòng vào nhóm phù hợp, gắn primitive cần, đưa vào test hồi quy. Khi mọi dòng ☑, hệ phủ trọn THCS theo nghĩa đo được.

---

# Lộ trình implement (gợi ý cho Claude Code)

1. **Compiler + 10 primitive nhóm A,B,C cơ bản** (point_*, segment, line, perpendicular/foot, triangle, altitude, median, midpoint) — verify từng cái trên applet. Test bằng B01–B05, T01, T03, T05.
2. **Planner DSL + validator plan**, chạy được các đề nhóm 1–2. Inject menu + few-shot.
3. **Nhóm D (đường tròn)**: circle_*, circumcircle, incircle, semicircle, tangent_*. Test C01–C09 — đây là chỗ gỡ lỗi tiếp tuyến & nửa đường tròn tận gốc.
4. **Nhóm F, G** (tứ giác, đối xứng). Test Q*, S*.
5. **Escape hatch + log**, rồi chạy bộ X (tổng hợp) gồm bài nửa đường tròn — giờ chỉ là ghép primitive đã verify.
6. **Validator quan hệ (Python)** cho tiếp xúc/vuông góc/thuộc, và **fail gracefully** (hình một phần có nhãn + báo bước fail).

# Tiêu chí thành công tổng thể
- Khâu sinh lệnh tất định: không còn lỗi cú pháp GeoGebra từ LLM.
- Mọi mục coverage checklist đạt ☑ (hoặc có primitive tương ứng đã verify).
- Đề nhiều bước = ghép primitive, dựng trong 1 vòng, đúng quan hệ, đủ nhãn.
- Cấu hình mới chỉ tốn: thêm 1 primitive (verify 1 lần) + 1 dòng coverage.
