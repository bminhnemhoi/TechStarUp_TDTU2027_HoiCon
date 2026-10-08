# API HỏiCon `/v1`

> Trạng thái: **khung** (P0-05). Nguồn sự thật cuối cùng là OpenAPI do FastAPI sinh (`/openapi.json`) + JSON Schema
> trong `docs/schemas/`. Đổi API ⇒ cập nhật file này + `bash scripts/gen-api-client.sh` (client TS cho web).

## Xác thực
- Thiết bị: JWT ngắn hạn + refresh token (cấp khi ghép đôi). Người giám hộ: magic link / action token một lần.
- Webhook Zalo: secret theo bot trong header; chống trùng theo message id.

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
