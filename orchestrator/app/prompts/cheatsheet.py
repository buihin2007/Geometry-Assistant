# Cheatsheet lệnh GeoGebra mức 1 (THCS lớp 7–9) — nhồi vào system prompt Generator.
# Mọi tên lệnh ở đây cần verify trên GeoGebra thật (PLAN §7.2 / §11).

CHEATSHEET = """\
LỆNH DỰNG GEOGEBRA MỨC 1 (chỉ dùng các lệnh dưới đây, đúng cú pháp):

ĐIỂM & ĐOẠN:
- Điểm tự do:           A=(0,0)
- Đoạn thẳng:           s=Segment(A,B)
- Đường thẳng:          l=Line(A,B)
- Tia:                  r=Ray(A,B)
- Trung điểm:           M=Midpoint(A,B)
- Giao điểm:            P=Intersect(obj1,obj2)   (đường/đoạn/đường tròn)
- Điểm gần nhất:        H=ClosestPoint(Line(B,C),A)   (chân đường vuông góc)

ĐA GIÁC:
- Tam giác:             tri=Polygon(A,B,C)

QUAN HỆ ĐƯỜNG:
- Đường song song:      p=Line(A,l)            (qua A, song song l)
- Đường vuông góc:      n=PerpendicularLine(A,l)
- Trung trực:           m=PerpendicularBisector(A,B)
- Phân giác trong:      bi=AngleBisector(B,A,C)   (phân giác góc tại đỉnh A)

TAM GIÁC — ĐIỂM ĐẶC BIỆT:
- Trọng tâm:            G=Centroid(tri)
- Tâm ngoại tiếp:       O=Center(Circle(A,B,C))   (hoặc giao 2 trung trực)
- Trực tâm: dựng bằng giao 2 đường cao:
                        ha=PerpendicularLine(A,Line(B,C))
                        hb=PerpendicularLine(B,Line(A,C))
                        Hh=Intersect(ha,hb)
- Tâm nội tiếp: dựng bằng giao 2 phân giác:
                        bi1=AngleBisector(B,A,C)
                        bi2=AngleBisector(A,B,C)
                        I=Intersect(bi1,bi2)

ĐƯỜNG TRÒN:
- Tâm + bán kính:       c=Circle(O,3)
- Tâm + qua điểm:       c=Circle(O,A)
- Qua 3 điểm (ngoại tiếp): c=Circle(A,B,C)
- Nội tiếp tam giác (sau khi có I):
                        r=Distance(I,Line(A,B))
                        incirc=Circle(I,r)

TIẾP TUYẾN (RẤT QUAN TRỌNG — KHÔNG dùng Line(A,B) cho tiếp tuyến!):
- "Đường tròn (O) có hai tiếp tuyến AB, AC từ điểm A ngoài đường tròn":
  A là điểm NGOÀI đường tròn (OA > bán kính); AB, AC là tiếp tuyến; B, C là TIẾP ĐIỂM.
  Trình tự ĐÚNG:
                        O=(0,0)
                        circ=Circle(O,3)
                        A=(8,1)                  # đảm bảo OA > 3
                        auxT=Tangent(A,circ)     # tạo auxT_1, auxT_2 (đường vô hạn, PHỤ)
                        B=Intersect(auxT_1,circ) # tiếp điểm
                        C=Intersect(auxT_2,circ)
                        tAB=Segment(A,B)         # tiếp tuyến HIỂN THỊ là đoạn A→tiếp điểm
                        tAC=Segment(A,C)
  (auxT_1, auxT_2 tên bắt đầu "aux" nên TỰ ĐỘNG ẨN — chỉ hiện đoạn tАB, tАC.)
- "Tiếp tuyến tại điểm M cho trước trên đường tròn (O)": vuông góc bán kính OM tại M:
                        auxt=PerpendicularLine(M,Line(O,M))
                        # rồi vẽ đoạn hữu hạn nếu cần, ẩn auxt như quy tắc dưới.

═══ QUY TẮC BẮT BUỘC: ẨN ĐƯỜNG VÔ HẠN TRUNG GIAN (chống nét thừa) ═══
Khi dùng Line / PerpendicularLine / PerpendicularBisector / AngleBisector / Tangent
CHỈ để LẤY GIAO ĐIỂM (đề thực ra cần một ĐOẠN hữu hạn để hiển thị: đường cao, trung
tuyến, phân giác trong tam giác, tiếp tuyến...), thì BẮT BUỘC:
  1. Đặt tên đối tượng vô hạn bắt đầu bằng "aux" (vd aux1, auxH, auxT) → sẽ TỰ ẨN.
  2. Lấy giao điểm bằng Intersect(...).
  3. Vẽ Segment nối hai điểm hữu hạn cần hiển thị (đây mới là đối tượng chính).
Ví dụ ĐƯỜNG CAO AH từ A xuống BC (KHÔNG để PerpendicularLine kéo dài tràn ra ngoài):
                        aux_h=PerpendicularLine(A,Line(B,C))
                        H=Intersect(aux_h,Line(B,C))
                        AH=Segment(A,H)
NGOẠI LỆ: nếu đề THỰC SỰ muốn vẽ một ĐƯỜNG THẲNG đầy đủ ("vẽ đường thẳng d",
"đường thẳng xy") thì giữ Line bình thường, KHÔNG đặt tên aux, KHÔNG ẩn.

═══ BIẾN THỂ CÁCH DIỄN ĐẠT (map về cùng cách dựng) ═══
- "đường cao AH" = "kẻ AH vuông góc BC" = "hạ đường vuông góc từ A xuống BC"
  = "AH ⊥ BC" → pattern đường cao (aux_h + Segment).
- "trung tuyến AM" = "nối A với trung điểm M của BC" → M=Midpoint(B,C); Segment(A,M).
- "phân giác góc A" = "tia phân giác của góc BAC" → AngleBisector(B,A,C) (ẩn nếu chỉ
  cần đoạn trong tam giác).
- "đường trung trực của AB" = "đường vuông góc tại trung điểm AB" → PerpendicularBisector(A,B).
- "tiếp tuyến" LUÔN map về Tangent(...), KHÔNG BAO GIỜ Line(A,B).
- "(O;R)" / "(O)" = đường tròn tâm O. "nội tiếp"/"ngoại tiếp" xem mục đường tròn.

KHOẢNG CÁCH / GÓC:
- Khoảng cách:          d=Distance(A,B)  hoặc Distance(I,Line(A,B))
- Góc:                  α=Angle(B,A,C)

QUY ƯỚC BẮT BUỘC:
- KHÔNG đoán tọa độ cho đối tượng phụ thuộc. Chỉ đặt tọa độ cho điểm TỰ DO.
- Đặt 2–3 điểm tự do ở vị trí "đẹp" để hình cân đối, ví dụ tam giác:
  A=(0,0)  B=(6,0)  C=(2,5)   (tránh tam giác quá nhọn/tù/suy biến).
- Mỗi lệnh một dòng, có tên ở vế trái (label=...) khi cần tham chiếu lại.
- Tên đối tượng dùng chữ Latin (A,B,C,O,I,H,M...). Nhãn hiển thị để GeoGebra lo.
"""
