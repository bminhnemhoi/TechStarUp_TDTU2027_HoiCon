# Data model delta: Spec 002 (migration 0003)

Nguồn: `docs/DATA-MODEL.md` §2. Chỉ ghi phần **tạo mới / khác** — chờ Minh duyệt D1, D2 (ADR-010) trước khi viết migration.

| Bảng | Cột (spec này tạo) | Khác DATA-MODEL |
|---|---|---|
| `families` | id, display_name, region, plan, created_at, is_demo | không |
| `members` | id, family_id, role, alias, address_form, guardian_rank, **zalo_user_hmac**, **zalo_hmac_kid**, **zalo_chat_enc**, **zalo_bot_id**, locale, created_at | **D1**: thay `zalo_user_ref (HMAC)` bằng HMAC tra cứu + `chat_id` mã hóa + bot đã ghép |
| `pairing_codes` | id, family_id, code_hash, expires_at, used_at | không (thêm `role_hint`? — không, YAGNI) |
| `messages_out` | id, family_id, incident_id, **member_id**, channel, bot_id, template_id, status, quota_month, sent_at, error, **job_key** | thêm `member_id` (biết người nhận để ánh xạ phản hồi) + `job_key` unique (gửi đúng một lần) |

- `messages_out.status`: `queued | sent | held_quota | failed | fallback_required`.
- Ràng buộc: unique `(family_id, guardian_rank)` khi `role = guardian`; unique `(zalo_bot_id, zalo_user_hmac)`;
  index `messages_out (bot_id, quota_month, status)`.
- Hạn lưu: theo DATA-MODEL §6; `zalo_chat_enc` xóa khi rút đồng ý/xóa gia đình (job retention ở 034).
- Spec 020 thêm: `devices`, `consents`, `trusted_contacts`, `action_tokens` (migration sau 0003).
