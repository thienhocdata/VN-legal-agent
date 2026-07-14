# Phạm vi corpus đất đai V1

Mốc kiểm chứng: **15/07/2026**. Phạm vi này áp dụng cho 10 gói nghiệp vụ trong `package-registry.json`.

## Quy tắc bao phủ

1. Trục hiện hành dùng toàn văn hợp nhất mới nhất nếu có, đồng thời giữ văn bản gốc và văn bản sửa đổi để truy vết theo thời gian.
2. Nhánh lịch sử bắt buộc trước mắt là Luật Đất đai 2013 và các sửa đổi ảnh hưởng trực tiếp. Luật 1987, 1993 và 2003 chưa thuộc V1; agent phải báo thiếu nguồn nếu câu hỏi đòi mốc đó.
3. Văn bản liên ngành chỉ bắt buộc khi nó có thể thay đổi kết luận của một trong 10 gói: dân sự, hôn nhân gia đình, công chứng, nhà ở, kinh doanh bất động sản, tín dụng và bảo đảm, tố tụng/thi hành án, khiếu nại/hành chính, quy hoạch/xây dựng, thuế/phí.
4. TP.HCM sau sắp xếp được quản lý theo một địa bàn mới nhưng có ba vùng quy tắc tiền nhiệm. Agent phải xác định phường/xã và vùng tiền nhiệm trước khi áp dụng quy định tách thửa còn chuyển tiếp.
5. Bảng giá, bản đồ quy hoạch và lớp không gian được lưu nguyên bản nhưng nhập vào lớp dữ liệu có cấu trúc/geospatial, không embedding như điều luật thông thường.
6. Án lệ chỉ lấy nguồn chính thức và được gắn taxonomy vấn đề. Không thu thập đại trà mọi bản án.

## Nguồn bị loại khỏi tập bắt buộc V1

- Tài liệu điều tra, đánh giá, cải tạo chất lượng đất chuyên ngành không làm thay đổi 10 nghiệp vụ người dùng đã chốt.
- Giáo trình, bài báo, blog và bản tổng hợp thương mại; chỉ dùng để tìm đầu mối, không dùng làm bằng chứng kết luận.
- Văn bản đã bị thay thế trong luồng hiện hành; chỉ giữ ở lớp lịch sử với khoảng hiệu lực rõ ràng.
- Văn bản chưa có hiệu lực tại ngày 15/07/2026, gồm Thông tư 22/2026/TT-BNNMT và Nghị định 281/2026/NĐ-CP, được theo dõi nhưng không được retrieval như luật hiện hành.

## Điều kiện tuyên bố một gói hoàn thành

Một gói chỉ `ready` khi toàn bộ nguồn bắt buộc có artifact chính thức, hash, toàn văn kiểm định, quan hệ sửa đổi/thay thế, khoảng hiệu lực và kiểm tra retrieval. Tải được PDF chỉ là `artifact_downloaded_unverified`, tuyệt đối không đồng nghĩa hoàn thành.
