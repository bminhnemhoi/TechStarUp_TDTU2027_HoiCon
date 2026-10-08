# ADR-001: Phát hiện & dừng an toàn bằng luật tất định trên máy, không LLM

- Trạng thái: **Chấp nhận** · 08/10/2026
- Liên quan: ARCHITECTURE §3, CLAUDE.md luật 3–5

## Bối cảnh
Kẻ gian thường giữ máy nạn nhân trong cuộc gọi và hối thúc chuyển tiền trong vài phút. Khoảnh khắc cần can thiệp là
lúc người cao tuổi **mở app ngân hàng/ví khi đang (hoặc vừa) nghe số lạ**. Mạng có thể chập chờn; LLM có độ trễ 1–10 s,
có thể lỗi hoặc bị prompt injection. Chính sách Google Play và cam kết riêng tư không cho đọc SMS, nhật ký cuộc gọi,
nội dung cuộc gọi hay dùng Accessibility.

## Quyết định
- Trên máy chỉ dùng **luật tất định** trong module JVM thuần `:rules`:
  - R0 liên hệ tin cậy → không làm gì;
  - R1 đang/vừa gọi số lạ hoặc số bị gắn cờ + mở app ngân hàng/ví → sàn `high` (`critical` nếu số bị gắn cờ hoặc gọi > 5 phút);
  - R2 cài app ngoài Play ≤ 30 phút sau cuộc gọi lạ → `critical`;
  - R4 số bị gắn cờ gọi đến → gắn nhãn + thông báo.
- Đường **phát hiện → SafePause** chạy hoàn toàn offline, không LLM, mục tiêu p95 ≤ 3 s; âm thanh thu sẵn/TTS trên máy.
- Máy gửi `rule_floor` lên máy chủ; LLM chỉ được **nâng** mức (bất biến `level >= rule_floor`).
- Tín hiệu: CallScreeningService (vai trò), trạng thái cuộc gọi, UsageStats (quyền đặc biệt), hiển thị trên app khác.

## Hệ quả
- (+) Hoạt động khi mất mạng / máy chủ chết; dễ kiểm thử (hàng trăm ca unit trong vài giây); giải thích được cho BGK
  và người dùng; qua được review quyền của Play.
- (−) Không hiểu nội dung cuộc gọi ⇒ có báo nhầm (con cháu gọi bằng số mới…) — giảm bằng liên hệ tin cậy, câu hỏi
  nhanh E8, nút "tiếp tục" giữ 3 s. Không bắt được lừa đảo không đi qua cuộc gọi + app ngân hàng (ngoài phạm vi MVP).
- (−) Phụ thuộc giới hạn nền của từng hãng ⇒ FGS trong cửa sổ rủi ro + heartbeat.

## Phương án đã loại
- Phân loại cuộc gọi bằng LLM/STT trên máy: cần ghi âm cuộc gọi (bị cấm, rủi ro pháp lý), nặng, chậm.
- Accessibility để đọc màn hình app ngân hàng: vi phạm chính sách Play cho mục đích này, rủi ro bảo mật.
- Gửi mọi tín hiệu lên máy chủ để quyết định: phụ thuộc mạng, chậm, nhiều dữ liệu cá nhân hơn.
