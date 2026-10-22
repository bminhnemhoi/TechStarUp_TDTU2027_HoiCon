# Kế hoạch Spec 012: Hạ tầng VPS

## 0. Kiểm theo hiến chương (bổ sung 18/10/2026 khi rà `/speckit-analyze`)

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Nhật ký proxy che token một lần, bỏ cookie/Authorization/Referer; IP khách có hạn giữ (T019) |
| V. Hợp đồng | Không đổi API; `compose.prod.yml` ép `HOICON_ENV=prod`, `ZALO_MODE=live` |
| VII. Bằng chứng | Mọi tiêu chí cần VPS/tên miền/Play Console ghi BLOCKED; số máy ảo ghi "máy ảo ≠ máy thật" |
| VIII. Ít code | Caddy + Compose, không orchestrator; tái dùng `backup.sh` của 034 |
| IX. Chặn phát hành | Bản Android phát hành phải qua `release-gate.sh` (029) + T019 của 011 (văn bản hứa điều mã chưa làm) |

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
| D10 | Không áp `roles.sql` ở prod ở lần này | LangGraph `setup()` chạy DDL nên cần role chủ; chưa kiểm `hoicon_app` chạy được app | Áp ngay (có thể làm app không khởi động) |
| D11 | Mount thư mục `infra/caddy` + `caddy reload` trong deploy; khai báo tường minh site `http://<tên miền>` | Mount từng tệp giữ inode cũ sau `git pull`; máy chủ :80 tự tạo của Caddy không nhận `servers { timeouts }` | Mount tệp; để Caddy tự tạo :80 |

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

## 5. Rà soát `/speckit-analyze` (18/10/2026, Opus — spec viết ngược sau khi đã dựng)

Đối chiếu `spec.md` ↔ `plan.md` ↔ `tasks.md` ↔ MASTER-PLAN §3 (Đợt 2) ↔ mã (`infra/`, `apps/android/app/build.gradle.kts`,
commit `3129dd3`). Phủ FR: 11/11 FR có task. **0 CRITICAL, 1 HIGH (đã sửa), 4 MEDIUM, 2 LOW.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| B1 | HIGH | T015 gộp ba việc làm được ngay (buildType `demo`, baseline profile, đo khởi động nguội trên AVD) vào một task BLOCKED vì Play Console — trái MASTER-PLAN §2.5 (BLOCKED chỉ cho phần cần bên ngoài). AC "đo lại khởi động nguội (hạn sàng lọc 5 s của Telecom)" của MASTER-PLAN không có task chạy được | Tách: T015 chỉ còn tải AAB đã ký (BLOCKED), T016 `demo` + baseline profile, T018 đo AVD |
| B2 | MEDIUM | T013 (`roles.sql`) BLOCKED "cần quyết định + thử trên DB dev" — DB dev có sẵn, không phải chặn bên ngoài | T017 thử trên DB dev ngay; T013 chỉ còn áp ở prod (BLOCKED VPS) |
| B3 | MEDIUM | Spec FR-011 ghi "ngoài phạm vi làn B" và mục 5 liệt kê phần Android là ngoài phạm vi, trong khi MASTER-PLAN đặt P1-08 trong 012; ROADMAP P1-08/P1-09 vẫn ☐ dù 012 đã có | Sửa FR-011, mục 5, SC-009; ROADMAP P1-08/P1-09 ◐ có link 012 |
| B4 | MEDIUM | `plan.md` thiếu bảng kiểm hiến chương; D10 đứng sau D11 | Thêm mục 0; sắp lại D10/D11 |
| B5 | MEDIUM | L-10 (IP khách trong log, DPIA chưa nêu mục đích/hạn) chỉ nằm trong evidence, không có task | T019 |
| B6 | LOW | Task không có thẻ làn | Thêm ghi chú thẻ làn ở đầu `tasks.md`; thẻ cho task mới |
| B7 | LOW | L-2, L-5, L-9, L-12 còn mở (Low) | Giữ ở `evidence.md`; L-9 phải kiểm trên VPS thật trước khi đặt AAAA (T010) |

Ghi nhận cho spec khác: 033 thêm cổng `HOICON_SIM_ENABLED` — `compose.prod.yml` **không** được đặt biến này (033 T003 có test).


## Wave 4 (23/10/2026)

| # | Quyết định | Lý do | Hệ quả |
|---|---|---|---|
| D12 | Thử `roles.sql` (T017) trên **một Postgres tạm, dùng một lần** (`pgvector/pgvector:pg17`, cổng 15433, xóa sau khi xong), không trên DB dev | Role `hoicon_app` trên DB dev có mật khẩu do người khác đặt; không được đổi nó. Trên DB mới role chưa có ⇒ `test_db_roles.py` tự tạo role + mật khẩu tạm sinh ngẫu nhiên và chạy đủ (không bị bỏ qua) | Không phụ thuộc mật khẩu nào có sẵn; kết quả áp được cho prod (cùng ảnh Postgres với `compose.dev.yml`) |
| D13 | **Giữ baseline profile viết tay** (`baseline-prof.txt` + `profileinstaller`), không thêm plugin `androidx.baselineprofile` + mô-đun macrobenchmark | Số đo AVD bản `demo`: sàng lọc nguội p95 64–214 ms, rất xa hạn 5 s của Telecom; plugin cần mô-đun mới + máy để sinh hồ sơ và không có số cho thấy cần (Hiến chương VIII) | Rủi ro: hồ sơ viết tay lặng lẽ mất tác dụng khi đổi tên gói/lớp ⇒ T021 thêm kiểm "mọi mẫu khớp ≥ 1 lớp". **Xem lại khi** số máy thật (001, FTL) có `onScreenCall` p95 > 2 s hoặc E7 p95 > 2,5 s |
