# Đánh giá tác động xử lý dữ liệu cá nhân (DPIA rút gọn)

> Trạng thái: **khung** (P0-05) — hoàn thiện ở P1-06, trước khi thí điểm. Căn cứ: Luật Bảo vệ dữ liệu cá nhân
> 91/2025/QH15, Nghị định 356/2025, Nghị định 330/2026 (xử phạt thiếu nhật ký đồng ý), Luật Trí tuệ nhân tạo 134/2025/QH15.

## Cần điền
1. Mô tả xử lý: dữ liệu nào, mục đích (enum `consents.purpose`), cơ sở pháp lý (đồng ý), hạn lưu (DATA-MODEL §6).
2. Luồng dữ liệu: máy → máy chủ (VN/VPS) → nhà cung cấp LLM (nước ngoài: **chỉ dữ liệu đã che PII**, gói trả phí không
   dùng để huấn luyện) → Zalo.
3. Dữ liệu nhạy cảm: không thu nội dung cuộc gọi/SMS/danh bạ; số điện thoại chỉ ở dạng băm (ADR-006).
   - `CallScreeningService` được gọi cho cả cuộc gọi **đến và đi** tới số không có trong danh bạ ⇒ DPIA phải ghi cả
     hai chiều (review bảo mật 09/10).
   - `h1` là SHA-256 không muối trên không gian ~10⁹ số ⇒ coi là **dữ liệu cá nhân đã bí danh hóa**, không phải ẩn
     danh; lưu trên máy phải mã hóa (Room + Tink AEAD, P2-05), không để trong SharedPreferences dạng rõ như bản spike.
   - Log chẩn đoán (tên gói ngân hàng + 3 số cuối + mức rủi ro) chỉ có ở bản debug.
4. Quyền chủ thể: xem, rút đồng ý (E12), xóa/xuất (`data_requests`), thời hạn phản hồi.
5. Rủi ro & biện pháp: rò rỉ DB, prompt injection, báo nhầm gây hoảng, lạm dụng diễn tập, người giám hộ lạm quyền.
6. Công khai AI: "Đây là trợ lý AI HỏiCon" + trang `/ai`.
7. Thí điểm: chỉ người ≥ 18 tuổi; văn bản đồng ý có phiên bản (`docs/legal/consent/`).
