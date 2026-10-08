# ADR-003: Kênh người giám hộ là Zalo Bot Platform, dự phòng bằng trang hành động web

- Trạng thái: **Chấp nhận** (xác nhận lại sau spike P1-S3) · 08/10/2026

## Bối cảnh
Con cháu ở Việt Nam dùng Zalo hằng ngày; cài thêm app riêng làm giảm tỷ lệ kích hoạt. Zalo Bot Platform cho phép bot
gửi/nhận tin với người đã tương tác, có webhook và nút bấm; giới hạn ở gói hiện tại khoảng **3 bot × 50 người dùng,
3.000 tin/tháng**, điều khoản có thể đổi. ZNS (template trả phí) cần doanh nghiệp đã xác minh.

## Quyết định
- Người giám hộ ghép đôi bằng `/start <mã>` với bot; cảnh báo giai đoạn 1 theo **mẫu soạn sẵn** (mục tiêu ≤ 10 s),
  nút [Gọi Mẹ] [Đã liên lạc – an toàn] [Nghi lừa đảo] [Xem chi tiết]; không có nút ⇒ trả lời 1/2/3.
- Webhook `POST /webhooks/zalo/{bot_id}`: kiểm secret, chống trùng theo message id, trả 200 ngay, xử lý trong job.
- Mọi tin đi qua `messages_out` + bộ kiểm hạn mức: cảnh báo ở 80%, dừng bản tin tuần ở 95%, cảnh báo sự cố luôn
  được ưu tiên. Chia gia đình thí điểm qua 3 bot.
- Dự phòng: magic link `/a/[token]` (web, web push) có cùng các hành động; Telegram nếu P1-S3 thất bại.

## Yêu cầu bảo mật bắt buộc cho code Zalo (review 08/10/2026)
Zalo Bot API đặt **token trên đường dẫn URL** (`https://bot-api.zaloplatforms.com/bot<TOKEN>/<method>`), nên:
- Mọi lời gọi đi qua **một** `ZaloClient`; logger `httpx` đặt mức WARNING; thêm `logging.Filter` thay `/bot[^/]+/`
  bằng `/bot***/`; lỗi HTTP gói thành `ZaloError(status)` **không mang URL** (`raise … from None`).
- Trace/OTel/Sentry (nếu dùng) phải scrub `url.full` và không ghi biến cục bộ của frame.
- `setWebhook` chạy bằng script `hoicon.ops.zalo_webhook` (chỉ in Đạt/Lỗi) — không ai dựng lệnh curl chứa token.
- Đường hầm dev chỉ phơi **route webhook** (app con), không phơi `/docs`, `/openapi.json`, `/mcp/*`.
- Webhook kiểm `X-Bot-Api-Secret-Token` bằng so sánh hằng thời gian (`hmac.compare_digest`).

## Hệ quả
- (+) Không cần app cho người giám hộ; quen thuộc; demo được ở gian.
- (−) Hạn mức giới hạn quy mô thí điểm (~150 người giám hộ) — đủ cho Vòng 2/chung kết; gian chung kết dùng web push
  cho khách, Zalo chỉ cho ~40 khách đầu.
- (−) Phụ thuộc nền tảng bên thứ ba ⇒ không lưu Zalo ID thô (HMAC), theo dõi điều khoản.
