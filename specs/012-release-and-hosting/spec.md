# Spec 012: Phát hành và hosting (phần hạ tầng VPS — làn B)

**Mã ROADMAP**: `P2-04` (VPS + Caddy + `compose.prod.yml` + bot Zalo thí điểm) và `P1-09` (VPS + tên miền + Caddy);
phần Android `P1-08` (Play internal testing) là **làn A** · **Làn**: B (`infra/**`, `scripts/**`, `backend/Dockerfile`,
`apps/web/Dockerfile`, `docs/setup/**`) · **Cột mốc**: mở khóa giai đoạn 2 của `029-pilot-kit` và các mục BLOCKED của
`034-hardening-core` · **Nhánh**: `feat/012-release-and-hosting` (commit `29bd228`) · **Luật**: CLAUDE.md luật 1, 5, 9;
ADR-002 (một tiến trình API + worker), ADR-004 (Postgres 17 + pgvector).

> **Spec viết ngược (18/10/2026).** Hạ tầng đã được dựng và thử trước khi thư mục spec này tồn tại; tài liệu này ghi lại
> đúng cái đã làm để có truy vết `spec → task → bằng chứng`. Mọi tiêu chí còn đòi VPS, tên miền, Let's Encrypt, bot Zalo
> thật hoặc tài khoản Play Console đều ghi **BLOCKED**, không tính là đạt.

---

## 1. Bối cảnh

Trước 012 không có gì chạy được ngoài máy dev: không có ảnh container, không có reverse proxy, nên các spec khác phải hoãn
phần "chạy trên VPS": 003 (MCP `threat` "chưa mở ra Internet — 012 quyết"), 025 (`: ping` qua Caddy), 027 (che
`/login/*` và `/a/*` trong nhật ký, ghi chú ROADMAP), 034 (lịch sao lưu, nơi lưu ngoài máy, áp role DB ở prod), 029
(giai đoạn 2).

| Thành phần | Hiện trạng trước 012 | Hệ quả |
|---|---|---|
| Ảnh container | Không có `Dockerfile` | Không triển khai được |
| Reverse proxy / HTTPS | Không có | Webhook Zalo cần HTTPS công khai; trình duyệt và Android cần HTTPS |
| Sao lưu | `scripts/backup.sh` (034) kết nối Postgres **từ máy chủ** | Ở prod Postgres không có cổng nào xuất ra ⇒ không chạy được |
| Cấu hình prod | `backend/.env.example` cho dev | Dễ chạy nhầm `HOICON_ENV=dev` ở máy chủ thật |

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-12.1 | **P1** | Là đội vận hành, tôi dựng được HỏiCon lên một VPS bằng một lệnh và chỉ coi là xong khi `/readyz` qua HTTPS trả 200 |
| US-12.2 | **P1** | Là người giám hộ, tôi mở liên kết Zalo trên điện thoại qua HTTPS; token trong liên kết không để lại dấu vết trong nhật ký máy chủ |
| US-12.3 | **P1** | Là đội vận hành, dữ liệu gia đình không thể bị truy cập từ Internet ngoài các đường API đã định, và mỗi lần nâng cấp luôn có bản sao lưu trước khi đổi schema |
| US-12.4 | **P2** | Là đội phát triển, tôi nâng cấp và quay lui được mà không mất dữ liệu |

## 3. Yêu cầu chức năng

- **(FR-001)** `infra/compose.prod.yml` gồm `postgres` (pgvector pg17, không `ports:`, mạng `internal`, healthcheck
  `pg_isready`), `backend`, `web`, `caddy`; giới hạn CPU/RAM từng dịch vụ; `HOICON_ENV=prod` và `HOICON_ZALO_MODE=live`
  **ép cố định** (không đọc từ tệp biến).
- **(FR-002)** `infra/caddy/Caddyfile`: HTTPS tự động (Let's Encrypt); `/v1/*`, `/webhooks/zalo/*`, `/healthz`, `/readyz` →
  backend; còn lại → web; `/mcp/*`, `/docs`, `/redoc`, `/openapi.json` **không** tới được từ Internet (404).
- **(FR-003)** Luồng SSE `/v1/runs/*/stream` qua Caddy không bị đệm hay nén (`flush_interval -1`, `X-Accel-Buffering: no`).
- **(FR-004)** Header bảo mật trên mọi phản hồi: HSTS, `nosniff`, `X-Frame-Options`, CSP, `Permissions-Policy`,
  `Referrer-Policy` (không ghi đè giá trị Next đặt cho trang có token), bỏ `Server`; trần thân yêu cầu ở cửa vào.
- **(FR-005)** Nhật ký proxy (cả truy cập lẫn lỗi) che token một lần trong đường dẫn (`/login/<token>`, `/a/<token>`,
  `/v1/action/<token>`) và bỏ `Cookie`, `Authorization`, `X-Bot-Api-Secret-Token`, `Referer`, `Set-Cookie`.
- **(FR-006)** `backend/Dockerfile`, `apps/web/Dockerfile`: người dùng không đặc quyền, bố cục giữ như repo (mã tìm
  `data/` và `docs/schemas/` theo đường dẫn tương đối); container chạy rootfs chỉ đọc, bỏ mọi capability.
- **(FR-007)** `scripts/deploy-vps.sh`: kiểm từng biến bắt buộc (PEPPER, DATA_KEY, BACKUP_KEY, DEVICE_JWT_SECRET, …) và
  quyền tệp, chỉ in **tên** biến; sao lưu trước khi migrate khi DB đã có dữ liệu; `alembic upgrade head` *trước* khi nạp
  container mới; chỉ báo xong khi `/readyz` qua Caddy trả đúng 200; mọi lỗi thoát mã 1 kèm hướng dẫn, không báo "XONG".
- **(FR-008)** `scripts/backup-vps.sh`: sao lưu mã hóa và `restore-check` trên Postgres của prod (đi qua IP container trên
  mạng docker, không mở cổng); khóa sao lưu không nằm trong container ứng dụng; có mẫu lịch hằng ngày.
- **(FR-009)** `docs/setup/VPS-DEPLOYMENT.md`: hướng dẫn từ VPS trắng tới chạy, cập nhật, quay lui, sao lưu, sự cố, và mục
  "đã kiểm / chưa kiểm / giới hạn".
- **(FR-010)** `infra/env.prod.example` chỉ chứa khóa rỗng và hướng dẫn sinh khóa; tệp thật `infra/.env.prod` bị `.gitignore`.
- **(FR-011)** *[Làn A]* buildType `demo`/`release` (R8, tắt log chẩn đoán, baseline profile), AAB lên Play internal testing +
  Google Group, đo khởi động nguội. `release` + R8 đã có (commit `3129dd3`, 029 T011); phần còn lại: T015 (BLOCKED Play Console),
  T016 (`demo` + baseline profile), T018 (đo AVD). Xem `specs/029-pilot-kit/evidence.md` (SC-003 `release-block`).
  *(Sửa 18/10 theo `/speckit-analyze`: MASTER-PLAN §3 đặt P1-08 trong 012, nên FR-011 thuộc phạm vi spec này, làn A.)*

## 4. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Triển khai một lệnh | Từ DB trống và lần hai: `/readyz` qua Caddy = 200, `zalo_mode: live`, web `/login` = 200; lần hai lũy đẳng | chạy `deploy-vps.sh` |
| **(SC-002)** | Cô lập | Postgres: 0 cổng xuất ra, không ra được Internet; backend/web không `ports:`; backend uid ≠ 0, rootfs chỉ đọc; khóa sao lưu ∉ môi trường container backend | `docker port`, thử kết nối, `touch`, liệt kê tên biến |
| **(SC-003)** | Đóng cửa | `/mcp/*`, `/docs`, `/redoc`, `/openapi.json` ⇒ 404 qua Caddy; reviewer độc lập không tìm được cách lách | `curl` + `security-privacy-reviewer` |
| **(SC-004)** | SSE không đệm | Sự kiện tới trình duyệt đúng nhịp phát (không gộp lô) | upstream giả phát 4 sự kiện cách 0,5 s |
| **(SC-005)** | Nhật ký sạch | 0 token/cookie/khóa trong nhật ký truy cập **và** lỗi của Caddy | yêu cầu thật + lỗi 502 cố ý, grep giá trị |
| **(SC-006)** | Thất bại an toàn | Thiếu/sai biến, `/readyz` không 200, backend unhealthy, migrate hỏng ⇒ thoát 1, kèm hướng dẫn, không "XONG"; sao lưu hỏng ⇒ không migrate | 4 ca hỏng cố ý |
| **(SC-007)** | Sao lưu → khôi phục | Sao lưu mã hóa tạo tệp 0600; `restore-check` khớp manifest + trigger bất biến | `backup-vps.sh`, `restore-check` |
| **(SC-008)** | VPS thật | Chứng chỉ Let's Encrypt thật, `https://<tên-miền>/healthz` = 200, `setWebhook` Zalo đạt, đo thời gian build/khôi phục | **BLOCKED** (VPS, tên miền, bot Zalo thật) |
| **(SC-009)** | Android phát hành | AAB lên Play internal testing (**BLOCKED** Play Console, W0-3); khởi động nguội đo lại trên AVD: `onScreenCall` p95 < 5 s (T018) | AVD + Play Console |

## 5. Ngoài phạm vi

Giám sát/cảnh báo ngoài (uptime), chép sao lưu ra ngoài máy, áp `infra/postgres/roles.sql` ở prod
(cần chạy `AsyncPostgresSaver.setup()` bằng role chủ trước — mục #8 review 034), tự động cập nhật bản vá hệ điều hành,
nhiều bản backend song song (hạn mức đếm trong bộ nhớ, ADR-002).
