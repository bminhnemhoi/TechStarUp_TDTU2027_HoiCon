# Công việc Spec 012: Hạ tầng VPS (làn B)

Viết ngược sau khi hạ tầng đã dựng (xem `spec.md`). Task đã tick đã chạy `Verify` xanh (kết quả và số đo ở `evidence.md`).
Biến: `UT = python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py` ·
`GRADLE = ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/opt/android-studio/jbr PATH="/opt/android-studio/jbr/bin:$PATH" ./apps/android/gradlew -p apps/android`.
**Thẻ làn** (thêm 18/10): T001–T014, T017, T019 là `[B]`; T015, T016, T018 là `[A]`. Tệp biến thử là tệp GIẢ sinh bằng
`openssl rand` (không phải khóa thật).

## Giai đoạn 1: Ảnh container
- [x] T001 [FR-006] `backend/Dockerfile` (uv, Python 3.12, uid 10001, bố cục như repo) + `.dockerignore`; khai báo `pyyaml`,
  `jsonschema` là phụ thuộc chính (`domain/drill.py` import lúc chạy).
  · Verify: `docker build -f backend/Dockerfile -t hoicon-backend:t .` rồi chạy ảnh với `--read-only --cap-drop ALL`:
  import `hoicon.api.main`, nạp 3 kịch bản diễn tập, `alembic heads` = 0010 (head).
- [x] T002 [FR-006] `apps/web/Dockerfile` (Node 22, `next start`, người dùng `node`).
  · Verify: `docker build -f apps/web/Dockerfile -t hoicon-web:t .` rồi chạy `--read-only`: `/login` 200, `/nope` 404, header riêng tư còn.

## Giai đoạn 2: Compose và Caddy
- [x] T003 [FR-001, FR-010] `infra/compose.prod.yml` + `infra/env.prod.example`.
  · Verify: `$UT` (lớp `ComposeInvariants`: chỉ Caddy có cổng, mạng `db` internal, ENV/ZALO ép, khóa sao lưu ∉ container, rootfs chỉ đọc, giới hạn tài nguyên).
- [x] T004 [FR-002, FR-003, FR-004, FR-005] `infra/caddy/Caddyfile` (HTTPS, định tuyến, ẩn `/mcp /docs /redoc /openapi.json`,
  SSE không đệm, header, trần thân, bộ lọc nhật ký cho logger mặc định và logger site).
  · Verify: `caddy validate` + `caddy fmt --diff` trong ảnh `caddy:2.10.2-alpine`; `$UT` (lớp `CaddyfileInvariants`); thử lách đường ẩn trên stack thật.

## Giai đoạn 3: Script vận hành
- [x] T005 [FR-007] `scripts/deploy-vps.sh` + `scripts/lib/envfile.sh`.
  · Verify: `$UT` (lớp `DeployCheck`); `shellcheck -x -P SCRIPTDIR`; chạy thật lần đầu và lần hai; 4 ca hỏng (thiếu biến, `/readyz` không 200, backend unhealthy, migrate hỏng) ⇒ thoát 1, không "XONG".
- [x] T006 [FR-008] `scripts/backup-vps.sh` (đi qua IP container, khóa sao lưu chỉ cho tiến trình sao lưu).
  · Verify: lần triển khai thứ hai (sao lưu trước migrate, tệp 0600) rồi `bash scripts/backup-vps.sh restore-check` ĐẠT.
- [x] T007 [FR-009] `docs/setup/VPS-DEPLOYMENT.md` (cài đặt, bí mật, triển khai, kiểm, webhook, nhật ký, cập nhật/quay lui, sao lưu, sự cố, đã kiểm/chưa kiểm).
  · Verify: các lệnh `ops` trong mục 9 chạy được trong container (`pilot`, `data`, `devices`, `threat_list`, `zalo_webhook --help`).
- [x] T008 [FR-001..FR-008] `scripts/tests/test_deploy_vps.py` (15 test) + kiểm độ nhạy bằng đột biến.
  · Verify: `$UT` xanh; 11/11 đột biến làm test đỏ.
- [x] T009 [FR-002, FR-004, FR-005] Review `security-privacy-reviewer` cho `infra/`; sửa High + Medium.
  · Verify: báo cáo reviewer trong `evidence.md`; `$UT` + `caddy validate` xanh sau khi sửa.

## Wave 2 (18/10/2026 — từ `/speckit-analyze`: việc làm được ngay, trước đây bị gộp vào BLOCKED)

- [ ] T016 [A] [FR-011] buildType `demo` (kế thừa `release`: R8, `BuildConfig.DEBUG = false`; khác `release` ở `applicationIdSuffix
  ".demo"`, nhãn app "HỏiCon (demo)", địa chỉ máy chủ demo qua `-PhoiconApiBaseUrl` https) cho video và gian trưng bày; thêm baseline
  profile (`androidx.baselineprofile` + `profileinstaller`: nêu lý do thêm thư viện — O3 của MASTER-PLAN, khởi động nguội) cho
  `CallScreeningService` → `RiskWindowService` → `SafePauseActivity`. `release-gate.sh` chạy được trên AAB `demo`.
  · Verify: `$GRADLE :app:assembleDemo :app:bundleRelease && bash scripts/release-gate.sh <aab release>` thoát 0;
  `aapt2 dump badging` của APK demo có `vn.hoicon.sentinel.demo`
- [ ] T017 [B] [FR-001] Thử `roles.sql` trên **DB dev**: chạy `AsyncPostgresSaver.setup()` + `alembic upgrade head` bằng role chủ, rồi
  chạy API + worker dưới `hoicon_app`; ghi quyền thiếu (nếu có) và sửa `roles.sql`. Quyết định ghi vào plan (D10 cập nhật).
  · Verify: `HOICON_DATABASE_URL=<url hoicon_app> uv run --directory backend pytest tests/integration/test_db_roles.py` xanh (không
  bị bỏ qua); API dev dưới `hoicon_app` qua `/readyz` 200 và một lượt `scripts/e2e-m1.sh` phần máy chủ ĐẠT
- [ ] T018 [A] [FR-011, SC-009] Đo lại khởi động nguội trên AVD `hc-api36` và `hc-api34` với bản `release`/`demo` (R8 + baseline
  profile): thời gian từ cuộc gọi tới `CallScreeningService.onScreenCall` khi app đã bị `am force-stop` (hạn của Telecom 5 s), và
  `app_foreground → pause_shown` (`emu-scenario.py --scenario fake_police --runs 10 --prep kill`). So với số debug cũ. Ghi "máy ảo ≠
  máy thật"; số máy thật vẫn ở 001 (FTL, BLOCKED).
  · Verify: bảng p50/p95 hai AVD × hai bản trong `evidence.md`; `onScreenCall` p95 < 5 s
- [ ] T019 [B] [FR-005, FR-009] Review L-10: địa chỉ IP khách trong log Caddy/uvicorn — đặt hạn giữ log (`roll_keep_for` của Caddy,
  `max-size`/`max-file` của driver log Docker), ghi mục đích + hạn lưu vào `docs/PRIVACY-DPIA.md` và `docs/DATA-MODEL.md` §6.
  · Verify: `python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py` (thêm kiểm `roll_keep_for` trong Caddyfile và giới
  hạn log trong compose); `caddy validate` trong ảnh `caddy:2.10.2-alpine`

## BLOCKED (cần VPS, tên miền hoặc tài khoản thật)
- [ ] T010 [FR-007, SC-008] VPS thật + DNS + chứng chỉ Let's Encrypt thật; `https://<tên-miền>/healthz` 200; đo thời gian build/khôi phục. **BLOCKED**: chưa có VPS/tên miền.
  · Verify: `bash scripts/deploy-vps.sh` trên VPS rồi `curl -fsS https://<tên-miền>/readyz`.
- [ ] T011 [FR-002] Bot Zalo thật + `setWebhook` + một tin thử đầu–cuối. **BLOCKED**: W0-3 (token bot), cần T010.
  · Verify: `hc exec backend python -m hoicon.ops.zalo_webhook set --url https://<tên-miền>` rồi `info`.
- [ ] T012 [FR-008] Bật `hoicon-backup.timer` trên VPS và chép bản sao lưu ra ngoài máy. **BLOCKED**: cần T010 và quyết định nơi lưu.
  · Verify: bản sao lưu xuất hiện ở nơi lưu ngoài máy; `restore-check` hằng tuần đạt.
- [ ] T013 [B] [FR-001] Áp `infra/postgres/roles.sql` ở **prod** theo cách đã thử ở T017. **BLOCKED**: cần T010 (VPS) và T017.
  · Verify: ứng dụng khởi động và qua `/readyz` dưới `hoicon_app` trên VPS; `test_db_roles.py` xanh.
- [ ] T014 [FR-009] Giám sát bên ngoài gọi `/readyz` mỗi phút và báo về điện thoại đội. **BLOCKED**: cần T010.
- [ ] T015 [A] [FR-011] AAB **đã ký** lên Play internal testing + Google Group tester (P1-08). **BLOCKED**: Play Console (W0-3) và
  khóa ký (Tiến tự giữ, Claude không đọc keystore). Bản release có R8 đã có (commit `3129dd3`, 029 T011).
  · Verify: Play Console hiện bản `0.3.0 (3)` ở kênh internal; một tester cài được
