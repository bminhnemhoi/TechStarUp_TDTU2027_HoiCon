# API HỏiCon `/v1`

> Trạng thái: **khung** (P0-05). Nguồn sự thật cuối cùng là OpenAPI do FastAPI sinh (`/openapi.json`) + JSON Schema
> trong `docs/schemas/`. Đổi API ⇒ cập nhật file này + `bash scripts/gen-api-client.sh` (client TS cho web).

## Xác thực
- Thiết bị: JWT ngắn hạn + refresh token (cấp khi ghép đôi). Người giám hộ: magic link / action token một lần.
- Webhook Zalo: secret trong header `X-Bot-Api-Secret-Token` (so sánh hằng thời gian); chống trùng theo `message_id`
  (Zalo không có `update_id`).

## Thiết bị (app Lính gác)
| Method | Path | Ghi chú |
|---|---|---|
| POST | `/v1/pair` | đổi mã ghép đôi lấy token thiết bị |
| POST | `/v1/auth/refresh` | |
| POST | `/v1/consents` | ghi thêm dòng đồng ý (purpose, granted, consent_version, text_sha256) |
| GET | `/v1/config` | cấu hình, phiên bản luật, danh sách app ngân hàng |
| GET | `/v1/threat-list?since=` | tập `h1` bị gắn cờ (delta) |
| POST | `/v1/events` | **theo lô, idempotent** (id UUIDv7 từ máy) — schema `risk_event.v1.json` |
| POST | `/v1/incidents/{id}/answers` | trả lời câu hỏi nhanh E8 |
| POST | `/v1/incidents/{id}/ask-child` | nút "Hỏi con" |
| GET | `/v1/incidents/{id}/elder-view` | nội dung E9/E10 cho người cao tuổi |
| POST | `/v1/lookups` | tra cứu số/link/QR (đã băm/che) |
| POST | `/v1/drills/{id}/result` | |
| POST | `/v1/heartbeat` | trạng thái quyền, phiên bản |

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
