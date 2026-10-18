# Văn bản đồng ý · `llm_processing` · Nhờ trí tuệ nhân tạo hiểu rõ hơn

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Đây là trợ lý AI HỏiCon.
Nhờ AI hiểu rõ hơn
Để hiểu tình huống của bác, HỏiCon có thể nhờ một dịch vụ AI (trí tuệ nhân tạo) ở nước ngoài đọc một bản tóm tắt ngắn.
Bản tóm tắt chỉ nói chuyện gì đang xảy ra, ví dụ có cuộc gọi lạ, bác mở ứng dụng ngân hàng. HỏiCon che số điện thoại, tên và số tài khoản trước khi gửi.
Nếu bác chưa đồng ý, HỏiCon không gửi bản tóm tắt cho dịch vụ AI và vẫn nhắc bác dừng lại bằng những câu viết sẵn. AI chỉ giúp lời nhắc kỹ hơn, không bao giờ làm lời nhắc bớt đi.
Bác đổi ý bất cứ lúc nào, chỉ cần nhờ người đã hướng dẫn bác cài HỏiCon.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- Che PII trước khi gọi LLM, nhà cung cấp ở nước ngoài, gói trả phí không dùng để huấn luyện: `docs/PRIVACY-DPIA.md` mục 2; CLAUDE.md luật 1, 5; `llm_router`.
- "Chỉ dùng câu soạn sẵn": `llm_router` rơi về mẫu soạn sẵn khi không có khóa/hết ngân sách; "không làm nhẹ đi": CLAUDE.md luật 5 (LLM chỉ nâng).

## Điểm chờ quyết
- **CHẶN TRƯỚC KHI DUYỆT:** mã hiện **không kiểm** đồng ý `llm_processing` ở đâu cả (chỉ có trong enum). Câu "Nếu bác không đồng ý, HỏiCon chỉ dùng câu soạn sẵn" chưa đúng với hành vi thật. Phải thực thi ở `llm_router` (thiếu đồng ý ⇒ rơi về mẫu) trước khi duyệt văn bản này.
- Xác nhận điều khoản của nhà cung cấp LLM thật sự cho phép câu "không dùng để dạy máy" ở gói đang dùng (chưa có khóa API, P0-08).
- Sửa theo `ux-elder-reviewer` (18/10): bỏ câu "không dùng để dạy máy" cho tới khi xác nhận điều khoản nhà cung cấp (#2); nói bản tóm tắt gồm gì; bỏ câu "xóa hết PII" tuyệt đối (che bằng máy có thể sót).
