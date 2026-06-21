# Plan nâng cấp: THCS → Thi vào 10 chuyên Toán

> Nối tiếp `THCS_construction_library_spec.md`. Mục tiêu: phủ tin cậy các cấu hình **thi vào 10 chuyên Toán** (THCS nâng cao), KHÔNG nhắm HSG/olympiad. Mô hình: **Claude Haiku** làm planner mặc định, **escalate sang Sonnet** khi verify fail. Tài liệu để feed Claude Code.

## 0. Nguyên tắc (không đổi)
Kiến trúc vẫn là: **Planner (LLM) → plan DSL → Validator plan → Compiler tất định (template primitive đã verify) → GeoGebra → Verifier quan hệ (Python)**. "Lên chuyên" = mở rộng thư viện primitive + nâng planner + siết verify, KHÔNG đập đi làm lại. Thứ tự bắt buộc: **hoàn thiện engine + primitive THCS trước**, rồi phủ thêm phần chuyên lên trên.

> ⚠️ Cập nhật cấu hình: provider LLM thực tế đang dùng là **Anthropic Claude (Haiku)**, không phải Gemini như bản plan gốc. Sửa lại biến môi trường/đặc tả cho khớp (xem §4).

---

## 1. SỬA GỐC TỨ GIÁC (ưu tiên cao nhất)

**Triệu chứng:** "hình thoi ABCD" cho ra tứ giác có AB=6 nhưng AD≈8.94 (cạnh không bằng nhau), đỉnh C sai vị trí, không vẽ thành đa giác kín. Nguyên nhân: pipeline để model **tự đoán tọa độ 4 đỉnh**, không ép ràng buộc định nghĩa.

**Nguyên tắc sửa:** mỗi loại tứ giác là một **primitive dựng-đúng-theo-định-nghĩa**, nhận tham số tối thiểu rồi **tính** các đỉnh còn lại theo công thức đảm bảo toán học. Quy ước chung:
- **Thứ tự đỉnh A→B→C→D đi vòng quanh** (C đối diện A, không kề A). Đây là chỗ bug C sai vị trí.
- **Vẽ thành `Polygon(A,B,C,D)` kín**, bật nhãn 4 đỉnh.
- Tham số góc/tỷ lệ do LLM chọn hợp lý theo đề (vd "góc BAD < 90°" → góc nhọn).

| Primitive | Inputs | Cách dựng (đỉnh còn lại) | Đảm bảo |
|---|---|---|---|
| `parallelogram` | A, B, D | `C = B + (D - A)` | 2 cặp cạnh song song & bằng |
| `rhombus` | A, B, góc θ (<90° nếu đề yêu cầu) | `D = Rotate(B, θ, A)` (quay B quanh A góc θ → \|AD\|=\|AB\|); `C = B + (D - A)` | 4 cạnh bằng nhau, đúng góc BAD |
| `rectangle` | A, B, h | n = vector đơn vị ⊥ AB; `D = A + h*n`; `C = B + h*n` | 4 góc vuông |
| `square` | A, B | như rectangle với `h = \|AB\|` | vuông |
| `trapezoid` | A, B, h, lenCD, offset | đặt CD song song AB ở độ cao h: `D = A + h*n + offset*û_AB`; `C = D + lenCD*û_AB` | AB ∥ CD |
| `isosceles_trapezoid` | A, B, h, lenCD | đối xứng qua trung trực AB | cân |
| `kite` | A, C (trục), B, D đối xứng | B, D đối xứng qua đường AC | 2 cặp cạnh kề bằng |
| `cyclic_quadrilateral` | 4 điểm trên một đường tròn | đặt 4 điểm bằng `Point(circle)` rồi `Polygon` | nội tiếp |

**GeoGebra (nháp, verify):** dùng phép toán điểm (`C=B+(D-A)`) và `Rotate(<điểm>,<góc>,<tâm>)`. Ví dụ rhombus:
```
A=(0,0); B=(6,0)
D=Rotate(B, 70°, A)
C=B+(D-A)
poly=Polygon(A,B,C,D)
```
→ verify: \|AB\|=\|BC\|=\|CD\|=\|DA\|, góc BAD = 70°, ABCD đi đúng vòng. Đây là test bắt buộc cho mọi primitive tứ giác.

**Test hồi quy tứ giác:** mỗi loại một đề ("Vẽ hình thoi ABCD góc BAD nhọn", "hình vuông ABCD", "hình chữ nhật", "hình thang cân ABCD"). Verifier (Python) kiểm số đo cạnh/góc đúng định nghĩa.

---

## 2. GÓI PRIMITIVE MỞ RỘNG THI-CHUYÊN (~15, thêm trên nền THCS)

Đề thi vào 10 chuyên hay dùng các dựng hình sau (không có ở THCS cơ bản):

| Primitive | Inputs | Outputs | Mô tả | GeoGebra (nháp, verify) |
|---|---|---|---|---|
| `circle_tangent_2lines_at_points` | line1, P1, line2, P2 | O, c | Đường tròn tiếp xúc 2 đường tại 2 điểm cho trước (bài hình thoi) | O = giao 2 đường ⊥ tại P1, P2; `c=Circle(O,P1)` |
| `second_intersection` | line/circle, c, knownP | P2 | Giao điểm thứ hai, loại điểm đã biết | `Intersect(obj,c,2)` + lọc ≠ knownP |
| `tangent_other_than` | P (ngoài c), c, knownTangent/knownPoint | t | Tiếp tuyến từ P khác tiếp tuyến đã biết | `Tangent(P,c)` → chọn cái ≠ known |
| `tangent_at_point` | A (trên c), c | t | Tiếp tuyến tại A (⊥ bán kính) | `PerpendicularLine(A,Line(Center(c),A))` |
| `tangent_from_point` | P, c | t1,t2, tiếp điểm | Hai tiếp tuyến từ điểm ngoài | `Tangent(P,c)` → `Intersect` |
| `reflect_over_line` | obj, line | obj' | Đối xứng trục | `Reflect(obj,line)` |
| `reflect_over_point` | obj, O | obj' | Đối xứng tâm | `Reflect(obj,O)` |
| `rotate` | obj, center, angle | obj' | Phép quay | `Rotate(obj,angle,center)` |
| `line_intersection_extended` | line1, line2 | P | Giao 2 đường thẳng (kể cả kéo dài) | `Intersect(line1,line2)` |
| `parallel_through` / `perpendicular_through` | P, line | l | Đường song song/vuông góc qua P | (đã có ở THCS) |
| `projection` | P, line | H | Hình chiếu vuông góc của P lên line | `ClosestPoint(line,P)` |
| `circle_diameter` | A, B | c | Đường tròn đường kính AB | `c=Circle(Midpoint(A,B), Distance(A,B)/2)` |
| `arc` | O, A, B | a | Cung tròn | `CircularArc(O,A,B)` (verify) |
| `point_on_line_condition` | line, điều kiện | P | Điểm trên đường thoả điều kiện đơn giản (vd cách điểm cho trước 1 khoảng) | nội suy / `Intersect` với đường tròn phụ |

**Lưu ý chọn nhánh (rất quan trọng ở đề chuyên):** các đề chuyên đầy "giao điểm thứ hai", "tiếp tuyến khác...". `second_intersection` và `tangent_other_than` phải triển khai chắc (loại đúng điểm/đường đã biết bằng so sánh tọa độ trong Python, không phó mặc chỉ số GeoGebra).

---

## 3. NÂNG CẤP PLANNER: phân rã có cấu trúc

Đề chuyên có chuỗi phụ thuộc sâu (10–20 đối tượng). Bắt planner làm **2 bước** thay vì xuất plan thẳng:

**Bước 3a — Phân tích đề thành bảng đối tượng** (intermediate representation). LLM xuất danh sách, mỗi đối tượng:
```json
{ "name": "Q", "type": "point", "defined_by": "giao của đường thẳng CM và đường thẳng AB", "depends_on": ["C","M","A","B"] }
```
**Bước 3b — Sắp thứ tự topo + map sang primitive** → plan DSL như spec gốc.

Tách "hiểu cấu trúc đề" khỏi "viết plan" giảm mạnh lỗi ở đề sâu — đây là chỗ Haiku hay lạc nếu phải làm một phát. Validator kiểm: mọi `depends_on` được định nghĩa trước, không phụ thuộc vòng.

---

## 4. CHIẾN LƯỢC HAI TẦNG MODEL (Haiku → Sonnet)

- **Mặc định: Claude Haiku** cho cả phân tích đề + lập plan (rẻ, đủ cho phần lớn đề).
- **Escalate sang Sonnet** khi: plan của Haiku **fail verify** (lỗi dựng hoặc quan hệ không thoả) sau hết vòng sửa. Chỉ request đó dùng Sonnet → giữ chi phí thấp, không chặn trần năng lực ở bài khó.
- Cấu hình env (sửa lại cho khớp Anthropic, bỏ Gemini):
```
LLM_PROVIDER=anthropic
PLANNER_MODEL=claude-haiku-4-5-20251001
PLANNER_ESCALATION_MODEL=claude-sonnet-4-6
REVIEWER_MODEL=claude-haiku-4-5-20251001   # vision review
ESCALATE_ON_VERIFY_FAIL=true
MAX_FIX_ROUNDS=3
MAX_LLM_CALLS_PER_REQUEST=10
```

---

## 5. VERIFICATION MẠNH (deterministic, Python — đọc tọa độ ra)

Sau khi compile + render, đọc tọa độ/giá trị từ GeoGebra và kiểm **mọi quan hệ đề nêu tên**. KHÔNG tiêm lệnh boolean vào GeoGebra (lỗi `IsOnSegment` cũ). Bộ quan hệ cần phủ ở mức chuyên:

| Quan hệ | Cách kiểm (Python) |
|---|---|
| Thuộc đoạn/đường | khoảng cách điểm–đường ≈ 0 (và trong đoạn nếu cần) |
| Tiếp xúc | khoảng cách tâm–đường = bán kính |
| Vuông góc / song song | tích vô hướng / tích chéo của vector chỉ phương |
| Thẳng hàng (3 điểm) | diện tích tam giác ≈ 0 |
| Đồng quy (3 đường) | 3 giao điểm đôi một trùng nhau |
| Đồng viên (4 điểm) | 4 điểm cùng cách một tâm / định thức đồng viên ≈ 0 |
| Bằng nhau (cạnh/góc) | so sánh độ dài / số đo trong dung sai |
| Đúng định nghĩa hình | (tứ giác) cạnh & góc theo §1 |

Quan hệ nào không thoả → feed lại planner (và escalate nếu cần). Đồng quy/đồng viên đặc biệt quan trọng vì đề chuyên hay xoay quanh chúng.

---

## 6. FAIL GỌN + CHẶN PHẠM VI

- Đề vượt thi-vào-10-chuyên (olympiad, cần phép phụ sáng tạo, hoặc dùng quan hệ chưa có primitive): planner đánh dấu escape; hệ trả **hình phần dựng được (có nhãn) + thông báo "vượt phạm vi / chưa dựng được bước X"**, KHÔNG trả hình vỡ.
- Mỗi escape là một mục backlog (cân nhắc thêm primitive hay không).

---

## 7. CÁC BƯỚC CÒN LẠI (thứ tự build cho Claude Code)

1. **Sửa gốc tứ giác (§1)** — làm trước vì là lỗi rõ nhất & cấu hình chuyên hay dùng. Verify từng primitive tứ giác.
2. **Hoàn thiện engine primitive THCS** còn lại (từ spec gốc): compiler tất định + primitive nhóm A–G, verify từng cái. Đây là nền, chưa xong thì chưa lên chuyên.
3. **Planner phân rã cấu trúc (§3)** + validator plan (không phụ thuộc vòng).
4. **Verifier quan hệ mạnh (§5)** trong Python, tách khỏi lỗi dựng.
5. **Gói primitive mở rộng chuyên (§2)** — circle_tangent_2lines, second_intersection, tangent_other_than, rotate, reflect, projection...
6. **Hai tầng model (§4)** + escalation theo verify.
7. **Fail gọn + chặn phạm vi (§6)**.
8. **Mở rộng coverage (§8)** + chạy như test hồi quy.

---

## 8. COVERAGE CHECKLIST — bổ sung cấu hình thi-chuyên

(Thêm vào checklist THCS gốc. TT: ☐/◐/☑)

### Tứ giác (ưu tiên — đang hỏng)
| ID | Cấu hình | Đề test | Primitive | TT |
|---|---|---|---|---|
| QC01 | Hình thoi góc nhọn | "Hình thoi ABCD, góc BAD < 90°" | rhombus | ☐ |
| QC02 | Hình vuông | "Hình vuông ABCD, hai đường chéo cắt tại O" | square, diagonal, intersect | ☐ |
| QC03 | Hình chữ nhật | "Hình chữ nhật ABCD" | rectangle | ☐ |
| QC04 | Hình thang cân | "Hình thang cân ABCD (AB ∥ CD)" | isosceles_trapezoid | ☐ |
| QC05 | Tứ giác nội tiếp | "Tứ giác ABCD nội tiếp (O)" | cyclic_quadrilateral | ☐ |

### Đường tròn & tiếp tuyến nâng cao
| ID | Cấu hình | Đề test | Primitive | TT |
|---|---|---|---|---|
| KC01 | Đường tròn tiếp xúc 2 cạnh tại 2 điểm | "(O) tiếp xúc AB, AD tại B, D" | circle_tangent_2lines_at_points | ☐ |
| KC02 | Tiếp tuyến khác / giao điểm thứ hai | "Tiếp tuyến qua R khác RD; NE cắt (O) tại điểm thứ hai K" | tangent_other_than, second_intersection | ☐ |
| KC03 | Đường tròn đường kính | "Đường tròn đường kính AH" | circle_diameter | ☐ |

### Tổng hợp nhiều bước (chuyên)
| ID | Cấu hình | Đề test | TT |
|---|---|---|---|
| XC01 | Hình thoi + cát tuyến + giao điểm | (Bài hình thoi ABCD / M / Q / N / R đầy đủ) | ☐ |
| XC02 | Nửa đường tròn nhiều bước | (Bài MN/P/Q/F/A/E/K) | ☐ |
| XC03 | Đối xứng + đường tròn | "Lấy A' đối xứng A qua O, chứng minh A' thuộc..." (chỉ phần dựng) | ☐ |

---

## 9. Tiêu chí thành công
- Mọi primitive tứ giác dựng **đúng định nghĩa** (cạnh/góc verify được), vẽ đa giác kín, đỉnh đúng thứ tự — bài hình thoi chạy đúng.
- Đề chuyên nhiều bước = ghép primitive đã verify, planner phân rã cấu trúc dựng đúng chuỗi, Haiku lo phần lớn, Sonnet gánh số ít bài khó.
- Verifier bắt được mọi quan hệ đề nêu (gồm đồng quy/đồng viên); không còn "không lỗi đỏ nhưng sai quan hệ".
- Đề vượt tầm → fail gọn có nhãn + thông báo, không hình vỡ.
- Mọi mục coverage (THCS + chuyên) tiến tới ☑; cấu hình mới chỉ tốn thêm 1 primitive (verify 1 lần) + 1 dòng coverage.
```
