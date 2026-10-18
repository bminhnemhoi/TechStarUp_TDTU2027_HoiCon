# Kế hoạch Spec 012: Hạ tầng VPS

## 1. Kiến trúc

```
Internet ─80/443─▶ caddy ─┬─ /v1/*, /webhooks/zalo/*, /healthz, /readyz ─▶ backend :18000 ─▶ postgres :5432
                          └─ còn lại ────────────────────────────────────▶ web :3100        (mạng `db`, internal)
        /mcp/*, /docs, /redoc, /openapi.json ─▶ 404 tại Caddy
```
Ba mạng docker: `api` (caddy, backend; có egress, backend gọi Zalo/Anthropic), `web` (caddy, web; `internal: true`) và `db`
(postgres, backend; `internal: true`). Chỉ Caddy có `ports:`. Web không có đường tới backend/Postgres/Internet, nên chiếm được web
không bỏ qua được các chặn ở Caddy (review bảo mật 012 M-1).

## 2. Quyết định

| # | Quyết định | Lý do | Phương án đã bỏ |
|---|---|---|---|
| D1 | Một tên miền cho web + API; `/v1/*` đi thẳng tới backend, không qua rewrite của Next | SSE không qua thêm một bước; cookie phiên và kiểm `Origin` (027) cùng nguồn; Android dùng cùng gốc | Hai tên miền (cần CORS, cookie chéo nguồn) |
| D2 | `/mcp/*`, `/docs`, `/redoc`, `/openapi.json` trả 404 tại Caddy | MCP `threat` đóng mặc định nhưng không cần mở ra Internet (003 giao 012 quyết); tài liệu API lộ bề mặt | Mở `/mcp` có token |
| D3 | `HOICON_ENV`, `ZALO_MODE`, `RUN_WORKER`, `WEB_BASE_URL`, `DATABASE_URL` ép cố định trong compose | Không thể chạy prod ở chế độ dev vì quên/gõ sai (034 FR-006) | Đọc tất cả từ tệp biến |
| D4 | Compose chỉ truyền biến mà dịch vụ dùng; khóa sao lưu chỉ ở máy chủ | Giảm hậu quả khi lộ container ứng dụng | `env_file` nguyên tệp |
| D5 | Sao lưu đi tới Postgres qua **IP container** trên mạng docker (`backup-vps.sh`) | Công cụ 034 cần kết nối từ máy chủ để xuất snapshot; không muốn mở cổng Postgres | Mở `127.0.0.1:5432` (mạng `internal` không cho `ports:`); viết lại công cụ sao lưu chạy trong container |
| D6 | Migrate chạy **trước** khi nạp container mới, sau một bản sao lưu bắt buộc khi DB đã có dữ liệu | Migration chỉ đi tới; nếu hỏng thì có bản để khôi phục | Migrate khi khởi động backend |
| D7 | `/readyz` qua Caddy là điều kiện duy nhất để coi rollout xong | `compose --wait` chỉ biết healthcheck nội bộ; cần kiểm cả Caddy + chứng chỉ + định tuyến | Chỉ tin `compose --wait` |
| D8 | Ghi log lỗi và log truy cập cùng một bộ lọc (`(redact_logs)`) | Log lỗi của Caddy in cả `request` với URI và header (đã thấy khi gây 502) | Chỉ lọc log truy cập |
| D9 | Giữ web ở chế độ `next start` (ảnh ≈ 1,4 GB) | Không đổi `next.config.ts`; chỉ tốn đĩa | `output: "standalone"` / build nhiều tầng (để sau) |
| D11 | Mount thư mục `infra/caddy` + `caddy reload` trong deploy; khai báo tường minh site `http://<tên miền>` | Mount từng tệp giữ inode cũ sau `git pull`; máy chủ :80 tự tạo của Caddy không nhận `servers { timeouts }` | Mount tệp; để Caddy tự tạo :80 |
| D10 | Không áp `roles.sql` ở prod ở lần này | LangGraph `setup()` chạy DDL nên cần role chủ; chưa kiểm `hoicon_app` chạy được app | Áp ngay (có thể làm app không khởi động) |

## 3. Tệp

`infra/compose.prod.yml`, `infra/caddy/Caddyfile`, `infra/env.prod.example`, `backend/Dockerfile`, `apps/web/Dockerfile`,
`.dockerignore`, `scripts/deploy-vps.sh`, `scripts/backup-vps.sh`, `scripts/lib/envfile.sh`, `docs/setup/VPS-DEPLOYMENT.md`;
`backend/pyproject.toml` (khai báo `pyyaml`, `jsonschema` là phụ thuộc chính vì `domain/drill.py` import lúc chạy).

## 4. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Let's Encrypt giới hạn tần suất khi cấu hình sai | Kiểm DNS trước; `--check` không đụng máy; thử với `*.localhost` (chứng chỉ nội bộ) |
| Bản sao lưu chỉ nằm trên VPS | Ghi rõ là BLOCKED; cần quyết nơi lưu ngoài máy |
| Mất khóa (pepper, dữ liệu, sao lưu) | Tài liệu đòi cất ngoài VPS; script từ chối khóa trùng nhau |
| Ảnh web lớn, build tốn RAM | Ghi trong tài liệu; VPS < 2 GB cần swap |
