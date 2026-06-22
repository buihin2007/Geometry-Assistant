"""KNOWLEDGE BASE — QUY ƯỚC ĐẶT HÌNH (layout/style conventions).

Đây là nơi DUY NHẤT để thêm quy ước vẽ hình. Nội dung chuỗi CONVENTIONS được nhồi
nguyên văn vào prompt của Planner. Mỗi quy ước là một gạch đầu dòng "•".

CÁCH THÊM QUY ƯỚC MỚI (develop dần):
  1. Thêm một dòng "• <Tên hình/tình huống>: <cách đặt tọa độ point_free>" vào CONVENTIONS.
  2. Viết rõ tọa độ cụ thể (vd B=(-3,-2), C=(3,-2)) để planner bắt chước chắc tay.
  3. Nếu quy ước cần ĐẢM BẢO TUYỆT ĐỐI (không phụ thuộc LLM), nói mình bake thành
     primitive (như rhombus_centered) thay vì chỉ để ở đây.
Quy ước ở đây là "mềm" (gợi ý cho LLM) — đo độ tuân thủ bằng scripts/eval_set.py.
"""

CONVENTIONS = """\
★ QUY ƯỚC ĐẶT HÌNH (đặt tọa độ point_free theo đúng các quy ước sau để hình "đúng kiểu",
cân đối; điểm phụ thuộc tự đi theo):
  • TỔNG QUÁT: đoạn/cạnh đáy/DÂY cung ĐẦU TIÊN đặt NẰM NGANG (∥ Ox, hai đầu cùng y),
    ĐỐI XỨNG qua Oy (x đối nhau: -a và a), và y ÂM. VD đáy/dây: (-3,-2) và (3,-2).
  • TAM GIÁC ABC: BC là ĐÁY ngang dưới (B=(-3,-2), C=(3,-2)); A là ĐỈNH ở TRÊN, y dương
    (vd A=(-1,3) lệch tùy đề; cân tại A thì A=(0,3) trên Oy). KHÔNG đặt A ở đáy.
  • ĐƯỜNG TRÒN có DÂY/CUNG BC: tâm O=(0,0); B,C đối xứng qua Oy và NẰM DƯỚI O (y âm),
    cách O vừa phải để BC không quá ngắn (đtròn bán kính ~5 thì B,C khoảng y=-4). Đường
    kính ⊥ BC nằm dọc Oy.
  • HÌNH THOI ABCD (không cho góc): dùng primitive rhombus_centered(p,q) — tâm O, chéo
    AC≡Ox, BD≡Oy, A,B kéo được.
  • Tránh tọa độ làm hình suy biến / thẳng hàng."""
