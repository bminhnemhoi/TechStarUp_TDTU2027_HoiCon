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
| POST | `/v1/events` | **đã có** — lô 1–50 sự kiện, idempotent theo id UUIDv7 từ máy (xem dưới) |
| GET | `/v1/incidents/{id}` | **đã có** — chi tiết sự cố + lịch sử chuyển trạng thái (xem dưới) |
| GET | `/v1/families/{id}/incidents` | **đã có** — danh sách sự cố của gia đình (xem dưới) |
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

### Sự kiện & sự cố (spec 021 — đã có)
Hợp đồng: `events_batch.v1.json` (+ `risk_event.v1.json`), `events_result.v1.json`, `incident.v1.json` (fixture `fixtures/*.v1.*.json`).

**`POST /v1/events`** — cần token thiết bị. Thân `{"events": [RiskEvent × 1–50]}`, khớp CHẶT `risk_event.v1.json` (trường lạ, kể cả số điện thoại thô, là lỗi). `family_id`/`device_id` lấy từ token. Một lô = một giao dịch: lưu sự kiện (`ON CONFLICT (id) DO NOTHING` ⇒ gửi lại cả lô hoặc từng sự kiện đều vô hại), rồi mỗi sự kiện MỚI đi qua `IncidentService.correlate_event`. Trả `{"accepted", "duplicates", "incident_id", "incident_opened"}`.

| Mã | Khi nào |
|---|---|
| 200 | đã xử lý (kể cả khi toàn bộ là trùng: `accepted = 0`) |
| 401 | không/sai token, thiết bị bị thu hồi |
| 422 | thân sai hợp đồng — cả lô không ghi gì. Thông báo chỉ nêu vị trí + loại lỗi, KHÔNG lặp lại giá trị đã gửi. Chuỗi tự do bị ràng buộc: `app.package` dạng gói Android, `app_version`/`rules_version` dạng phiên bản (số đầu ≤ 4 chữ số, hậu tố build tùy chọn như `0.1.0-20261016`), mỗi thành phần tối đa 8 chữ số nên số điện thoại không lọt vào; số nguyên có cận trên (`duration_s` ≤ 86400, `timing.*_ms` ≤ 3.600.000); cờ boolean phải là `true/false` thật |
| 429 + `Retry-After` | thiết bị gửi quá 30 lô/phút (đếm trong bộ nhớ, một tiến trình) |
| 503 + `Retry-After` | chưa cấu hình pepper băm số điện thoại (không lưu gì), hoặc chờ khóa thiết bị quá 3 giây (lô không ghi gì, app gửi lại được) |

Mở/liên kết sự cố (FR-008): sự kiện loại `banking_app_foreground`/`flagged_number_call`/`sideload_detected`/`ask_child_pressed` hoặc `rule_floor ≥ high` mở sự cố `detected` nếu thiết bị chưa có sự cố đang mở; mọi sự kiện sau đó liên kết vào sự cố đang mở (cùng thiết bị, cùng loại thật/diễn tập, cùng `drill_id`) **còn hoạt động trong 600 giây gần nhất** (mốc = sự kiện cuối của sự cố, hoặc lúc mở nếu chưa có), và `rule_floor` cao hơn thì NÂNG `rule_floor` + `level` (không bao giờ hạ). Sự cố im lặng quá 600 giây không nhận thêm: sự kiện mới tạo sự cố MỚI (sự cố cũ giữ nguyên trạng thái; đưa nó ra khỏi `detected` thuộc bộ hẹn giờ/tác tử). Sự cố đã kết thúc không mở lại — sự kiện mới tạo sự cố mới. Số gọi đến chỉ lưu `HMAC(pepper, h1)` + 3 số cuối (ADR-006); h1 không vào DB hay log. Chưa có giới hạn kích thước thân ở tầng ứng dụng (FastAPI đọc thân trước khi xác thực) — cần giới hạn ở Caddy khi mở ra Internet.

**`GET /v1/incidents/{id}`** — cần token thiết bị; chỉ sự cố của gia đình mình, sự cố nhà khác trả 404 (không lộ sự tồn tại). Trả `incident.v1.json` kèm `transitions` (cũ → mới).
**`GET /v1/families/{id}/incidents?limit=`** — `id` phải là gia đình của token (nhà khác ⇒ 404); mới nhất trước, `limit` 1–100 (mặc định 20), bản tóm tắt không có `transitions`. Người giám hộ đọc qua `/a/{token}` (spec 022), không qua các route này.

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
