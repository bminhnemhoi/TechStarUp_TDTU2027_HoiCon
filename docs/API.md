# API HỏiCon `/v1`

> Trạng thái: **khung** (P0-05). Nguồn sự thật cuối cùng là OpenAPI do FastAPI sinh (`/openapi.json`) + JSON Schema
> trong `docs/schemas/`. Đổi API ⇒ cập nhật file này + `bash scripts/gen-api-client.sh` (client TS cho web).

## Xác thực
- Thiết bị (spec 020): `Authorization: Bearer <access_token>`; JWT HS256 ký bằng `HOICON_DEVICE_JWT_SECRET` (≥ 32 ký tự), sống **30 ngày**,
  claim `sub` (device_id), `family_id`, `member_id`, `role=protected`, `iss=hoicon`, `aud=hoicon-device`. Mỗi lần gọi còn đối chiếu DB
  (thiết bị tồn tại, chưa `revoked_at`) ⇒ thu hồi có hiệu lực ngay. Refresh token (32 byte ngẫu nhiên, DB chỉ giữ SHA-256) cấp cùng
  lúc; endpoint làm mới chưa có. Người giám hộ: magic link / action token một lần.
- Webhook Zalo: secret trong header `X-Bot-Api-Secret-Token` (so sánh hằng thời gian); chống trùng theo `message_id`
  (Zalo không có `update_id`).

## Thiết bị (app Lính gác)
| Method | Path | Ghi chú |
|---|---|---|
| POST | `/v1/pair` | **đã có** — đổi mã ghép đôi lấy token thiết bị (xem dưới) |
| POST | `/v1/auth/refresh` | |
| POST | `/v1/consents` | **đã có** — ghi thêm dòng đồng ý (xem dưới) |
| GET | `/v1/devices/me` | **đã có** — thông tin thiết bị + trạng thái đồng ý hiện tại (xem dưới) |
| GET | `/v1/config` | cấu hình, phiên bản luật, danh sách app ngân hàng |
| GET | `/v1/threat-list?since=` | tập `h1` bị gắn cờ (delta) |
| POST | `/v1/events` | **theo lô, idempotent** (id UUIDv7 từ máy) — schema `risk_event.v1.json` |
| POST | `/v1/incidents/{id}/answers` | trả lời câu hỏi nhanh E8 |
| POST | `/v1/incidents/{id}/ask-child` | nút "Hỏi con" |
| GET | `/v1/incidents/{id}/elder-view` | nội dung E9/E10 cho người cao tuổi |
| POST | `/v1/lookups` | tra cứu số/link/QR (đã băm/che) |
| POST | `/v1/drills/{id}/result` | |
| POST | `/v1/heartbeat` | trạng thái quyền, phiên bản |

### Ghép đôi, đồng ý, thiết bị (spec 020 — đã có)
Hợp đồng: `pair_request.v1.json` / `pair_response.v1.json`, `consent_record.v1.json`, `device_me.v1.json` (fixture `fixtures/*.v1.*.json`).

**`POST /v1/pair`** — không cần token. Thân: `code` (6 số), `app_version`/`rules_version` (`[0-9A-Za-z._+-]`, ≤ 32), `platform`, `device_label?` (máy chủ che số/email trước khi lưu).

| Mã | Khi nào |
|---|---|
| 200 | mã đúng, còn hạn 15 phút, chưa dùng: tạo `devices`, đánh dấu mã đã dùng (cùng giao dịch, `FOR UPDATE`), trả `pair_response` |
| 400 `{"detail": "Mã ghép đôi không tồn tại hoặc đã hết hạn"}` | mã sai / hết hạn / đã dùng — **cùng một câu** để không lộ mã nào tồn tại |
| 422 | thân sai hợp đồng (mã không đủ 6 số, trường lạ…) |
| 429 + `Retry-After` | quá 10 lần thử sai/15 phút từ một nguồn (IPv6 gộp theo /64), hoặc quá 60 lần/15 phút toàn hệ thống — chặn cả khi mã đúng (đánh đổi có chủ đích: kẻ lạ làm nghẽn ghép đôi tối đa 15 phút). Mỗi lần thử giữ chỗ ngay khi vào và trả lại nếu ghép được, nên loạt yêu cầu đồng thời không lách được ngưỡng. Đếm trong bộ nhớ (một tiến trình, ADR-002); sau reverse proxy chỉ ngưỡng toàn cục có tác dụng |
| 503 | chưa cấu hình khóa ký JWT thiết bị; mã KHÔNG bị tiêu thụ |

Thành viên được bảo vệ (`role=protected`) của gia đình được tạo ở lần ghép đầu và dùng lại ở các máy sau.

**`POST /v1/consents`** — cần token thiết bị. Thân `{"items": [...]}` (1–32 mục). Chặt hơn schema chung ở hai điểm: `channel` phải là `app`, và mỗi `purpose` chỉ một lần trong một lô. `family_id`/`member_id` lấy từ token, `recorded_at` do máy chủ đặt. Trả `{"status": "recorded", "count": N, "recorded_at": "<ISO>"}`. 401 không/sai token · 422 sai hợp đồng (cả lô không ghi) · 503 DB lỗi hoặc chưa cấu hình khóa ký. Không có PUT/PATCH/DELETE (405); trigger Postgres chặn sửa/xóa ở cấp CSDL. Rút đồng ý = gửi lại `purpose` với `granted=false`.

**`GET /v1/devices/me`** — cần token thiết bị. Trả `device` (id, gia đình, nền tảng, phiên bản, mốc thời gian; KHÔNG token/băm bí mật) và `consents`: dòng mới nhất của mỗi purpose.

## Người giám hộ
`/v1/families`, `/v1/incidents`, `POST /v1/incidents/{id}/decision`, `/v1/case-files`, `/v1/drills`, `/a/{token}` (web).

## Luồng SSE
`/v1/runs/{id}/stream` · `/v1/families/{id}/stream` · `/v1/demo/stream`

## Webhook & khác
`POST /webhooks/zalo/{bot_id}` · `/demo/*` · `/admin/*` · `/mcp/*` (FastMCP) · `GET /healthz`

### `POST /webhooks/zalo/{bot_id}` (spec 002 — đã có)
Hợp đồng thân: `docs/schemas/zalo_update.v1.json` (fixture `fixtures/zalo_update.v1.*.json`). Không thuộc `/v1`, không sinh client TS.

| Mã | Khi nào | Job được xếp? |
|---|---|---|
| 200 `{"ok": true}` | secret đúng; kể cả cập nhật không dùng được (ảnh, nhóm, tin của bot, thiếu `message_id`, thân thử của Zalo) | chỉ khi là tin chữ riêng tư dùng được: job `zalo_update`, khóa `zalo:{bot_id}:{message_id}` ⇒ gửi lại vẫn một job |
| 400 | thân không phải JSON | không |
| 401 | secret sai/thiếu | không |
| 404 | `bot_id` không phải bot đã cấu hình (chỉ trả lời sau khi xác thực) | không |
| 413 | thân > 64 KB | không |
| 503 | chưa cấu hình secret, thiếu khóa mã hóa, hoặc DB lỗi — **Zalo nên gửi lại**; không trả 200 rồi mất cập nhật | không |

Job KHÔNG mang Zalo ID thô, tên hiển thị hay chữ người gõ (DATA-MODEL §3b). Chạy riêng cho đường hầm (chỉ route này, không
`/docs`, `/openapi.json`, `/mcp`): `uvicorn hoicon.api.webhooks:app --port 18080 --loop asyncio:SelectorEventLoop`.
Đặt/xem/xóa webhook: `python -m hoicon.ops.zalo_webhook set|info|delete` (docs/setup/ACCOUNTS.md §3).
