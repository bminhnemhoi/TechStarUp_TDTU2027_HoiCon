# Văn bản đồng ý · `guardian_alerts` · Báo cho con bác biết khi bác cần giúp

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Đây là trợ lý AI HỏiCon.
Báo cho con bác biết khi bác cần giúp.
Khi thấy dấu hiệu lạ, HỏiCon nhắn Zalo cho con hoặc người thân bác đã chọn, để họ gọi hỏi thăm.
Họ biết có cuộc gọi lạ (lúc nào, bao lâu), bác mở loại ứng dụng nào, chọn gì trên màn nhắc. Số điện thoại chỉ hiện 3 số cuối.
Họ xem lại các lần nhắc trên web, và nhận tóm tắt mỗi tuần. Họ được báo nếu HỏiCon bị tắt.
Khi nghi bác bị lừa, HỏiCon soạn sẵn tờ ghi sự việc để bác trình báo. HỏiCon không tự gửi cho cơ quan nào.
Cuộc gọi lạ giữ tối đa 90 ngày, các lần nhắc tối đa 12 tháng. HỏiCon không bán thông tin của bác.
Muốn ngừng báo, bác nhờ người cài HỏiCon cho bác. HỏiCon vẫn nhắc bác dừng lại, chỉ không báo con nữa. Bác chưa đồng ý cũng không sao.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- Nội dung tin, "3 số cuối", "15 phút": chữ app `disclosure_3_body`; spec 022, 023; heartbeat 15 phút (spec 029, `heartbeat.v1.json`).
- "90 ngày", "12 tháng sau khi xong": `docs/DATA-MODEL.md` §6 (`risk_events` 90 ngày; `incidents` đã đóng 12 tháng).
- "Xem lại trên web": spec 027 (`/incidents`, trace); đăng nhập bằng liên kết một lần qua Zalo.
- "Soạn sẵn tờ ghi sự việc để bác trình báo" (= hồ sơ vụ việc): spec 031 (`case_files`, `/incidents/[id]/case-file`); HỏiCon không tự gửi cho cơ quan nào.
- "Họ được báo nếu HỏiCon bị tắt", "nhận tóm tắt mỗi tuần": spec 032 (`weekly_digest`, `protection_lost`).

## Điểm chờ quyết
- **Minh/DPIA phải quyết (ghi chú (i) của spec 027):** việc người giám hộ XEM LẠI lịch sử trên web có thuộc `guardian_alerts` không? Bản nháp nói rõ là có. Nếu quyết là không, phải tách một mục đích mới (CLAUDE.md luật 7) và kiểm đồng ý ở các route đọc.
- Câu "Họ được báo nếu HỏiCon bị tắt" (22/10, gộp 031 + 032; ux-elder-reviewer đổi từ "máy bác hết được bảo vệ" vì nghe như bị hack) phụ thuộc ý I4 (MASTER-PLAN §1/§8): nếu Minh bác I4 thì 032 T008 bỏ cụm đó và tăng version. Văn bản vẫn là **bản nháp, chưa `released`** cho tới khi 032 merge (câu chỉ được nói khi mã làm thật).
- Người giám hộ thứ hai (T2) cũng nhận tin: chữ hiện nói "con bác hoặc người thân bác đã chọn". Minh xác nhận.
- Sửa theo `ux-elder-reviewer` (18/10): tách câu 30 từ (#9), nêu lý do của báo cáo định kỳ (#14), đưa việc xem lại trên web lên sát phần "họ biết gì" (#15), cùng câu hạn lưu với `core_protection` (#7), "không sao" (#27).
- Chữ app hiện tại còn nói "riêng ứng dụng tài chính thì kèm tên ứng dụng" và "phiên bản ứng dụng": bản này nói gọn "loại ứng dụng" (nên Minh xác nhận có cần nói rõ tên).
- Sửa theo `ux-elder-reviewer` (22/10, lượt 1): thêm "HỏiCon không tự gửi cho cơ quan nào" ngay trong văn bản (mức Chặn: trước đó ý này chỉ nằm ở ghi chú), "hồ sơ trình báo" → "tờ ghi sự việc để bác trình báo", "máy bác hết được bảo vệ" → "HỏiCon bị tắt", chủ ngữ "họ nhận tóm tắt mỗi tuần", bỏ "gọi tới hay đi" để giữ 160 từ. **Lệch so với chữ của 031 T011** (Opus soạn): cần Opus/Minh xác nhận. Còn mở: bác có tự tắt được báo con không (câu cuối nói phải nhờ người cài).
