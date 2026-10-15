# Research: Spec 002

> Mục nào ghi "CHƯA XÁC MINH" phải tra **tài liệu chính thức Zalo Bot Platform** (ghi URL + ngày tra) trước task phụ
> thuộc; không viết code theo trí nhớ. Kết quả chép vào `docs/spikes/P1-S3-zalo.md` §1.

## R1. Zalo Bot API — ĐÃ TRA 15/10/2026 (kết quả và nguồn: `docs/spikes/P1-S3-zalo.md` §1)
Tóm tắt kết quả: không có `update_id` (dùng `message_id`), không có nút bấm, hạn mức Basic 3 bot × 50 người × 3.000 tin/tháng
có trên trang sản phẩm, không có tài liệu giới hạn tốc độ hay cơ chế gửi lại webhook. Danh sách câu hỏi gốc giữ lại dưới đây.

Cần xác nhận:
- Định dạng cập nhật webhook: tên trường mã cập nhật (dùng làm khóa chống trùng), người gửi, văn bản, loại sự kiện.
- Gửi tin: tên phương thức, tham số `chat_id`/`text`, mã lỗi khi bị chặn hoặc chat không tồn tại.
- Nút bấm/bàn phím có hỗ trợ không; nếu có, dữ liệu callback trả về thế nào.
- `setWebhook` (`url`, `secret_token`), `getWebhookInfo`, `deleteWebhook`; header `X-Bot-Api-Secret-Token`.
- Giới hạn tốc độ, hạn mức 3 bot × 50 người × 3.000 tin/tháng (đếm tin gửi đi hay cả tin đến), điều khoản sử dụng
  cho cảnh báo tự động.

Đã biết (ADR-003, `check_keys.py`): base `https://bot-api.zaloplatforms.com/bot<TOKEN>/<method>`, có `getMe`.

## R2. Lưu `chat_id` (đề xuất D1)
- **Decision**: AES-256-GCM (`cryptography`), nonce 12 byte ngẫu nhiên, lưu `kid|nonce|ciphertext` (base64) ở
  `members.zalo_chat_enc`, khóa `HOICON_DATA_KEY_<kid>` (32 byte, `init_env` sinh) ngoài DB. Tra cứu bằng
  `members.zalo_user_hmac = HMAC(pepper[kid], "hoicon:zalo:v1:" + bot_id + ":" + user_id)`.
- **Rationale**: gửi được (giải mã khi gửi), DB lộ không lộ định danh; HMAC có tiền tố miền để không lẫn với băm số điện thoại.
- **Alternatives**: lưu thô (vi phạm luật 1); chỉ HMAC (không gửi được); mã hóa ở cột Postgres `pgcrypto` (khóa đi qua
  câu SQL — dễ lọt vào log).

## R3. Hạn mức
- **Decision**: đếm trên `messages_out` theo `(bot_id, quota_month)`; ngưỡng 80/95% cấu hình; nhóm tin sự cố
  (`fast_alert`, `detail`, `reminder`, `escalation`) không bị dừng ở 95%. Cảnh báo đội ở 80% = log WARNING + một dòng
  trong báo cáo vận hành (kênh cảnh báo đội thật thuộc 034).

## R4. Đo SC-001
- **Decision**: mốc 1 = `jobs.created_at` của `notify_guardian`; mốc 2 = lúc nhận phản hồi HTTP thành công từ Zalo ⇒
  ghi `messages_out.sent_at`; p50/p95 bằng truy vấn SQL; n ≥ 20 qua lệnh `python -m hoicon.agents.spike demo` lặp lại.
  Bấm giờ tay tới điện thoại ≥ 5 lần.

## R5. Kênh dự phòng
- **Decision mặc định**: trang hành động `/a/[token]` (spec 023) — ghi `messages_out.status = fallback_required`.
  Telegram chỉ khi Zalo thất bại về điều khoản/kỹ thuật (ADR-003) — quyết định trong ADR-010.
