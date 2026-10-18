# Văn bản đồng ý · `lookups` · Nhờ HỏiCon kiểm tra giúp bác

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Đây là trợ lý AI HỏiCon.
Nhờ HỏiCon kiểm tra giúp bác
Khi bác nhờ, HỏiCon kiểm tra số điện thoại hay đường link xem có trong danh sách cảnh báo lừa đảo không.
HỏiCon không gửi số đầy đủ, chỉ gửi 3 số cuối và một mã thay cho số. Với đường link, HỏiCon chỉ gửi địa chỉ trang web, bỏ phần có thông tin riêng của bác.
HỏiCon không bao giờ nói một số là "an toàn". Chưa có trong danh sách chỉ nghĩa là chưa có thông tin. Còn băn khoăn, bác gọi hỏi con bác trước khi làm theo.
Mỗi lần kiểm tra được ghi lại tối đa 90 ngày để không bị kẻ xấu lợi dụng. HỏiCon không bán thông tin của bác.
Nếu con bác đang được báo về một cuộc gọi lạ và kết quả đáng lo, con bác sẽ biết bác vừa kiểm tra.
Bác chưa đồng ý cũng không sao.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- Chữ app hiện tại `lookups_consent_*` (spec 026); 90 ngày: `docs/DATA-MODEL.md` §6 (`verifications`); "không bao giờ nói an toàn": spec 026.
- "Báo thêm cho con bác": `IncidentService.raise_level` + tin người giám hộ khi có sự cố mở (spec 026).

## Điểm chờ quyết
- Người giám hộ trên web chưa có đường ghi đồng ý `lookups` (ghi chú (e) của spec 027): họ gọi tra cứu sẽ bị 403. Chưa có văn bản riêng cho người giám hộ.
- Máy chủ chưa kiểm đồng ý theo phiên bản/sha256 (chỉ kiểm bản ghi mới nhất `granted`).
- Sửa theo `ux-elder-reviewer` (18/10): bỏ "dãy ký tự đại diện", "đường dẫn", "dấu chấm hỏi" (#10, #20); thêm việc để làm tiếp (#22); chữ "chống lạm dụng" đổi giọng (#22).
- Chữ app hiện tại nói con bác chỉ biết "3 số cuối hoặc một đường link": bản này nói gọn, Minh xác nhận có cần giữ chi tiết.
