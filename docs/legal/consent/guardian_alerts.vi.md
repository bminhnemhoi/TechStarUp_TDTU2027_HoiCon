# Văn bản đồng ý · `guardian_alerts` · Báo cho con bác biết khi bác cần giúp

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Đây là trợ lý AI HỏiCon.
Báo cho con bác biết khi bác cần giúp
Khi thấy dấu hiệu đáng ngờ, HỏiCon gửi tin qua Zalo cho con bác hoặc người thân bác đã chọn, để họ gọi hỏi thăm bác.
Họ biết có cuộc gọi lạ, gọi tới hay gọi đi, lúc nào và bao lâu. Họ biết bác vừa mở loại ứng dụng nào và chọn gì trên màn nhắc. Số điện thoại chỉ hiện 3 số cuối.
Họ cũng xem lại được các lần nhắc này trên trang web của HỏiCon.
Để nhắc bác nếu lỡ tắt, thỉnh thoảng HỏiCon báo họ biết bác còn bật các quyền bảo vệ không.
HỏiCon giữ thông tin về từng cuộc gọi lạ tối đa 90 ngày, ghi chép các lần nhắc dừng lại tối đa 12 tháng. HỏiCon không bán thông tin của bác.
Bác tắt được bất cứ lúc nào. Bác chưa đồng ý cũng không sao.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- Nội dung tin, "3 số cuối", "15 phút": chữ app `disclosure_3_body`; spec 022, 023; heartbeat 15 phút (spec 029, `heartbeat.v1.json`).
- "90 ngày", "12 tháng sau khi xong": `docs/DATA-MODEL.md` §6 (`risk_events` 90 ngày; `incidents` đã đóng 12 tháng).
- "Xem lại trên web": spec 027 (`/incidents`, trace); đăng nhập bằng liên kết một lần qua Zalo.

## Điểm chờ quyết
- **Minh/DPIA phải quyết (ghi chú (i) của spec 027):** việc người giám hộ XEM LẠI lịch sử trên web có thuộc `guardian_alerts` không? Bản nháp nói rõ là có. Nếu quyết là không, phải tách một mục đích mới (CLAUDE.md luật 7) và kiểm đồng ý ở các route đọc.
- Người giám hộ thứ hai (T2) cũng nhận tin: chữ hiện nói "con bác hoặc người thân bác đã chọn". Minh xác nhận.
- Sửa theo `ux-elder-reviewer` (18/10): tách câu 30 từ (#9), nêu lý do của báo cáo định kỳ (#14), đưa việc xem lại trên web lên sát phần "họ biết gì" (#15), cùng câu hạn lưu với `core_protection` (#7), "không sao" (#27).
- Chữ app hiện tại còn nói "riêng ứng dụng tài chính thì kèm tên ứng dụng" và "phiên bản ứng dụng": bản này nói gọn "loại ứng dụng" (nên Minh xác nhận có cần nói rõ tên).
