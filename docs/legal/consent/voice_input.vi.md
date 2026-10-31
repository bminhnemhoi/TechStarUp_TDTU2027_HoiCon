# Văn bản đồng ý · `voice_input` · Nói với HỏiCon thay vì bấm nút

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Đây là trợ lý AI HỏiCon.
Nói với HỏiCon thay vì bấm nút
Bác có thể nói "có", "không" hay "không biết" thay vì bấm nút. Điện thoại chỉ nghe khi bác bấm nút nói.
Để đổi lời bác thành chữ, điện thoại dùng dịch vụ của Android, do Google làm. Dịch vụ này có thể gửi tiếng của bác ra ngoài điện thoại. HỏiCon không ghi âm và chỉ nhận lại chữ.
Bác chưa đồng ý cũng không sao. Bác cứ bấm nút như bình thường.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- "Nút bấm là chính", dùng `SpeechRecognizer` vi-VN của Android: `specs/004-voice-vi/spec.md`.

## Điểm chờ quyết
- **CHẶN TRƯỚC KHI DUYỆT:** chưa có tính năng trả lời bằng giọng nói trong app (004 mới đo). Chưa có mã nào ghi/kiểm đồng ý `voice_input`.
- Cần xác nhận kỹ thuật sau khi 004 có số đo: nhận dạng chạy trên máy hay gửi âm thanh tới Google (câu "có thể do Google xử lý" là cách nói thận trọng, phải sửa cho đúng sự thật), và HỏiCon thật sự chỉ nhận chữ.
- Sửa theo `ux-elder-reviewer` (18/10): bỏ "không giữ lại tiếng nói" (Google có thể giữ), nói thẳng dịch vụ có thể gửi tiếng ra ngoài (#3). Vẫn phải sửa lại cho đúng khi 004 cho biết nhận dạng chạy trên máy hay ngoài máy.
