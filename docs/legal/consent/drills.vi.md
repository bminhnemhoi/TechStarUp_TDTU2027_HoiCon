# Văn bản đồng ý · `drills` · Tập nhận biết lừa đảo, không có thật

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Đây là trợ lý AI HỏiCon.
Tập nhận biết lừa đảo (chỉ là diễn tập)
HỏiCon xin phép thỉnh thoảng mời bác tập nhận biết cuộc gọi lừa đảo. Tối đa 2 lần mỗi tháng, chỉ trong khung giờ con bác đã đặt, và HỏiCon báo trước cho bác.
Đó là cuộc gọi giả. Tên cơ quan và số điện thoại đều bịa ra, và trên màn hình luôn có chữ "ĐÂY LÀ DIỄN TẬP".
Bác từ chối hay dừng giữa chừng bất cứ lúc nào cũng không sao. HỏiCon không báo đó như một vụ lừa đảo thật.
Con bác sẽ biết bác đã chọn gì ở từng bước, để cùng trò chuyện với bác chứ không phải để chấm điểm.
Bác chưa đồng ý cũng không sao.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- "Tối đa 2 lần mỗi tháng": `specs/028-drills` (`DrillService.schedule`, tính theo tháng giờ VN); `docs/PILOT-PROTOCOL.md`.
- "Khung giờ đã đồng ý", "ĐÂY LÀ DIỄN TẬP", "lưu bác chọn gì và kết quả": spec 028 (`drills.answers` chỉ lưu mã lựa chọn, `score`); tin tổng kết gửi người giám hộ có nhãn [DIỄN TẬP].
- "Con bác gọi hỏi thăm": `docs/PILOT-PROTOCOL.md` (debrief).

## Điểm chờ quyết
- Mục đích `drills` hiện được máy chủ kiểm khi mời diễn tập (028), nhưng Android chưa có màn xin đồng ý này (chưa có chuỗi/`ConsentLedger.DRILLS`).
- "Bác và con bác đã đồng ý khung giờ": hiện khung giờ do người giám hộ/đội đặt khi lên lịch (`ops drills schedule`); chưa có bước người cao tuổi đồng ý từng khung giờ. Minh quyết có cần không.
- Sửa theo `ux-elder-reviewer` (18/10): "khung giờ con bác đã đặt" cho đúng thực tế (khung giờ do người giám hộ/đội đặt, #6); tiêu đề dễ đọc to hơn (#30); bỏ giọng "chấm điểm" (#12). Nếu sau này có bước người cao tuổi đồng ý từng khung giờ, sửa lại câu này.
- "Báo trước cho bác": hiện lời mời hiện trong khung giờ; cần xác nhận có báo trước thật (028).
