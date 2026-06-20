Sửa ba vấn đề trong Agent Generator (sinh lệnh GeoGebra) và pipeline liên quan. Đọc hết cả ba phần trước khi sửa vì chúng dùng chung một cơ chế (chuẩn hóa cheatsheet + ẩn đối tượng phụ).

---

## VẤN ĐỀ 1 — Tiếp tuyến dựng sai (cát tuyến thay vì tiếp tuyến)

Đề "Vẽ đường tròn O có 2 tiếp tuyến AB và AC" hiện cho ra AB, AC chỉ là đường thẳng qua các điểm cho trước (cát tuyến cắt đường tròn), không tiếp xúc. Điều kiện tiếp xúc chưa từng được dựng.

**Sửa logic dựng:**
- Diễn giải chuẩn "đường tròn (O) có hai tiếp tuyến AB và AC": A là điểm **ngoài** đường tròn; AB, AC là hai tiếp tuyến kẻ từ A; B, C là **tiếp điểm** trên đường tròn.
- Trình tự đúng: dựng đường tròn O trước → đặt A ngoài đường tròn (đảm bảo khoảng cách OA > bán kính) → dùng `Tangent(A, circ)` lấy hai tiếp tuyến → B, C = giao của mỗi tiếp tuyến với đường tròn (tiếp điểm) → vẽ đoạn AB, AC từ kết quả đó. KHÔNG dùng `Line(A,B)` với B, C đặt tùy ý.
- Thêm mẫu này vào cheatsheet + golden example set. Bổ sung biến thể "tiếp tuyến tại một điểm cho trước trên đường tròn" (vuông góc với bán kính tại tiếp điểm, dùng `PerpendicularLine` qua điểm đó với bán kính — nhưng nhớ áp luôn quy tắc ẩn-đường-vô-hạn ở Vấn đề 2 bên dưới).

**Validator — thêm kiểm tra tiếp xúc xác định:**
- Với mọi đối tượng đề gọi là "tiếp tuyến": kiểm tra khoảng cách từ tâm đường tròn tới đường thẳng đó ≈ bán kính (dung sai nhỏ). Không thỏa → lỗi, feed lại Generator.
- Tổng quát: thêm kiểm tra cho các quan hệ đề nêu rõ tên (tiếp xúc, nội tiếp, ngoại tiếp, vuông góc, thẳng hàng).

**Reviewer:** prompt review phải kiểm tra quan hệ ĐỀ NÊU TÊN có thực sự đúng không (tiếp tuyến chạm đúng 1 điểm; nội/ngoại tiếp; song song; vuông góc...), không chỉ "trông giống hình đúng dạng".

---

## VẤN ĐỀ 2 — Đường nét thừa: dùng Line vô hạn cho thứ phải là Segment hữu hạn

Quan sát: đề "vẽ tam giác ABC có 3 đường cao" cho ra 3 đường thẳng vuông góc (`PerpendicularLine`) kéo dài tràn ra ngoài tam giác ở cả hai đầu, thay vì là đoạn thẳng từ đỉnh đến chân đường cao trên cạnh đối diện. Cùng một lớp lỗi sẽ gặp ở: trung trực, phân giác hiển thị tràn cạnh, đường kính/bán kính vẽ thừa, v.v. — bất kỳ chỗ nào dùng `Line`/`PerpendicularLine`/`LineBisector`/`AngleBisector` chỉ để LẤY GIAO ĐIỂM nhưng đề thực ra cần một đoạn hữu hạn để hiển thị.

**Cách sửa — đúng theo hướng người dùng đề xuất, làm thành quy tắc chuẩn trong Generator:**

1. Dựng đối tượng vô hạn (Line/PerpendicularLine/LineBisector/AngleBisector...) như bình thường để tính giao điểm — đây là bước trung gian, đặt tên rõ là phụ (vd prefix `aux_` hoặc hậu tố `_line`).
2. Lấy giao điểm cần thiết bằng `Intersect(...)`.
3. Dựng **Segment** nối hai điểm hữu hạn cần hiển thị (ví dụ đỉnh → chân đường cao) làm đối tượng HIỂN THỊ chính.
4. **Ẩn đối tượng phụ vô hạn**: dùng `SetVisibleInView(aux_line, 1, false)` (hoặc lệnh ẩn tương đương của GeoGebra) ngay sau khi đã lấy xong giao điểm từ nó. Đối tượng phụ vẫn tồn tại trong construction (để giữ phụ thuộc/tính toán đúng) nhưng không vẽ ra.

Ví dụ áp dụng cho "đường cao AH từ A xuống BC":
```
aux_line=PerpendicularLine(A,Line(B,C))
H=Intersect(aux_line,Line(B,C))
AH=Segment(A,H)
SetVisibleInView(aux_line,1,false)
```

**Cập nhật cheatsheet:** liệt kê rõ ràng đây là PATTERN BẮT BUỘC mỗi khi dùng các lệnh sinh đối tượng vô hạn (Line, PerpendicularLine, LineBisector/trung trực, AngleBisector/phân giác) mà mục đích thực chất là một đoạn/tia hữu hạn trong hình (đường cao, trung trực đoạn AB hiển thị trong phạm vi hợp lý, phân giác trong tam giác...). Trường hợp đề thực sự muốn vẽ một ĐƯỜNG THẲNG đầy đủ (ví dụ "vẽ đường thẳng d") thì giữ nguyên không ẩn — chỉ áp quy tắc ẩn khi đối tượng vô hạn chỉ đóng vai trò công cụ trung gian.

**Cập nhật Technical Validator:** thêm kiểm tra cảnh báo (không cần chặn cứng) khi construction cuối cùng còn đối tượng `Line`/`PerpendicularLine`/`LineBisector`/`AngleBisector` đang ở trạng thái hiển thị (visible) NHƯNG có điểm hữu hạn phụ thuộc nó đã được dựng (dấu hiệu nó chỉ nên là công cụ trung gian bị quên ẩn) — feed cảnh báo này cho Generator như một vòng sửa "làm gọn hình" trước khi trả kết quả cuối.

**Test hồi quy:** "vẽ tam giác abc có 3 đường cao" phải cho ra hình chỉ còn tam giác + 3 đoạn đường cao bên trong tam giác (cộng điểm chân đường cao + trực tâm nếu có), không còn đường nào tràn ra ngoài cạnh.

---

## VẤN ĐỀ 3 — App chỉ nhận diện tốt đề cơ bản, yếu với đề biến thể/phức tạp hơn

**Chẩn đoán trước khi sửa mù:** đây không phải một bug đơn lẻ mà là vấn đề độ phủ. Trước khi code, hãy:
1. Thu thập ví dụ cụ thể về loại đề bị nhận diện sai/kém (xin người dùng cung cấp thêm 5-10 đề đã thử mà kết quả không như ý, nếu có) để biết đang yếu ở khâu nào: từ vựng hình học bị thiếu trong cheatsheet? cấu trúc câu phức (nhiều mệnh đề phụ thuộc liên tiếp) làm model lạc hướng? hay model (Gemini Flash free tier) không đủ mạnh cho đề nhiều bước?

**Các hướng cải thiện cụ thể (áp dụng song song):**

1. **Mở rộng cheatsheet + golden example set** với nhiều BIẾN THỂ cách diễn đạt cho cùng một khái niệm hình học (vd "đường cao", "đường vuông góc hạ từ...", "kẻ AH ⊥ BC" đều phải map về cùng pattern dựng). Hiện golden set còn mỏng — đây là đòn bẩy rẻ và hiệu quả nhất, ưu tiên làm trước.

2. **Tách bước "phân tích đề" khỏi bước "sinh lệnh"** nếu đề có nhiều mệnh đề phụ thuộc liên tiếp (kiểu "lấy P trên... rồi từ P kẻ... cắt tại Q rồi từ Q..."): thêm một bước trung gian trong Generator buộc model liệt kê tuần tự từng đối tượng cần dựng (dạng danh sách: tên, loại, phụ thuộc vào gì) TRƯỚC khi xuất lệnh GeoGebra thật. Tách suy luận cấu trúc khỏi việc nhớ cú pháp giúp giảm lỗi ở đề nhiều bước.

3. **Cho phép cấu hình model riêng cho đề phức tạp:** nếu xác nhận nguyên nhân là model free tier (Gemini Flash) không đủ sức với đề nhiều bước, thêm khả năng chọn model mạnh hơn qua biến môi trường đã có sẵn (`GENERATOR_MODEL`) mà không cần sửa code — kiểm tra xem cấu hình này đã hoạt động đúng trong orchestrator chưa.

4. **Log lại các đề fail (kèm lý do fail) để xây bộ test hồi quy mở rộng dần** — mỗi lần người dùng báo một đề bị nhận diện sai, sau khi sửa, thêm đề đó vào danh sách test, tránh sửa xong một trường hợp lại làm hỏng trường hợp khác.

**Không làm:** không cần xây pipeline RAG scrape đề từ internet ở giai đoạn này — chưa đúng chỗ, ưu tiên cheatsheet + golden set đã verify trước (xem lý do ở phần thảo luận trước đó nếu cần tham khảo).

---

## Tiêu chí hoàn thành chung

- Đề tiếp tuyến: AB, AC thực sự tiếp xúc đường tròn (khoảng cách tâm–đường thẳng = bán kính); Validator tự bắt được nếu sai.
- Đề "tam giác có 3 đường cao": hình chỉ hiện đoạn đường cao bên trong tam giác, không còn đường vuông góc kéo dài tràn ra ngoài. Áp dụng quy tắc ẩn-đối-tượng-phụ tương tự cho mọi trường hợp dùng Line/PerpendicularLine/LineBisector/AngleBisector làm công cụ trung gian.
- Golden example set được mở rộng với các biến thể diễn đạt + ví dụ nhiều bước, có ghi chú đã verify trên GeoGebra applet thật.
- Có cơ chế (log + danh sách test) để tiếp tục phát hiện và vá các đề bị nhận diện kém theo thời gian, thay vì sửa một lần rồi thôi.
