# Bằng chứng nghiệm thu Spec 012: Hạ tầng VPS (làn B)

- **Trạng thái**: hạ tầng đã dựng và thử trên máy dev (17–18/10/2026), review bảo mật độc lập xong và đã sửa Medium. **Chưa chạy trên
  VPS thật**: Let's Encrypt thật, tên miền, bot Zalo thật, chép sao lưu ra ngoài máy và phần Android (làn A) đều BLOCKED.
- **Spec viết ngược** sau khi hạ tầng có (commit `29bd228`); các sửa sau review nằm ở nhánh `feat/w1-server`.
- **Môi trường**: Linux CachyOS, Docker Compose 5.6, stack thử trong project compose riêng `hoicon-prodtest2` (tên miền `hoicon.localhost`,
  chứng chỉ nội bộ của Caddy, khóa GIẢ sinh bằng `openssl`), Postgres dev `hoicon-db` không bị đụng tới.
- **Nguồn số**: máy dev, một lần đo mỗi mục; thời gian build/khôi phục không đại diện cho VPS. Chưa chạy: CI trên PR, Windows, VPS thật.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 triển khai một lệnh | `/readyz` qua Caddy = 200, `zalo_mode: live`, `/login` = 200; lần hai lũy đẳng | `scripts/deploy-vps.sh` chạy 6 lần (DB trống, DB có dữ liệu, sau mỗi sửa) | Mọi lần xanh: `{"status":"ok","db":"up","zalo_mode":"live"}`, `/login` 200, `/docs` `/redoc` `/openapi.json` `/mcp/threat/` 404. Lần đầu (build lạnh) 1 phút 42 giây; lần chạy lại có sao lưu trước migrate 11 giây; migration 0001 → 0010 | ĐẠT (máy dev) |
| SC-002 cô lập | Postgres 0 cổng ra host, không ra Internet; web không tới backend/Postgres/Internet; backend uid ≠ 0, rootfs chỉ đọc; khóa sao lưu ∉ container | `docker port`, kết nối thử từ trong container, `touch`, liệt kê tên biến, `test_deploy_vps.py` | Postgres: không cổng, không ra Internet. Web: `EAI_AGAIN` khi tới `backend`/`postgres`, `ENETUNREACH` khi ra Internet. Backend: uid 10001, ghi `/app` bị từ chối, ra Internet được; 0 biến `BACKUP_KEY` trong container | ĐẠT |
| SC-003 đóng cửa | `/mcp/*`, `/docs`, `/redoc`, `/openapi.json` ⇒ 404; reviewer không lách được | 33 biến thể tự thử (hoa/thường, `//`, `%2f`, `%6d`, `..`, `%2e%2e`, `;`) + reviewer thử ≈ 35 biến thể khác (kể cả HTTP/3 suy luận) | Tất cả 404 ở Caddy hoặc rơi vào web (Next 404), không biến thể nào tới backend. Reviewer: ĐẠT | ĐẠT |
| SC-004 SSE không đệm | Sự kiện tới đúng nhịp phát | upstream giả phát 4 sự kiện cách 0,5 s qua Caddy | +8 / +508 / +1008 / +1508 ms, `X-Accel-Buffering: no`, không nén. **Chỉ với upstream giả**; backend thật mới thử tới 401 không token | MỘT PHẦN |
| SC-005 nhật ký sạch | 0 token/cookie/khóa trong log truy cập **và** log lỗi Caddy | yêu cầu thật có `Cookie`/`Authorization`/`Referer`, lỗi 502 cố ý, `//login/<token>` | 0 lần lộ sau sửa. Trước sửa: `Refresh: 0;url=/login/<token>` của Next lọt vào log (đã bỏ `Refresh`/`Content-Location`) | ĐẠT |
| SC-006 thất bại an toàn | Thiếu/sai biến, `/readyz` không 200, backend unhealthy, migrate hỏng, Caddyfile hỏng ⇒ thoát 1 kèm hướng dẫn, không "XONG"; sao lưu hỏng ⇒ không migrate | 5 ca hỏng cố ý | Cả 5 thoát mã 1, 0 dòng "XONG". Caddyfile hỏng: `caddy reload` lỗi, Caddy vẫn phục vụ cấu hình cũ (`/readyz` 200). Sao lưu hỏng (chọn nhầm Postgres): script dừng trước migrate | ĐẠT |
| SC-007 sao lưu → khôi phục | Tệp mã hóa 0600; `restore-check` khớp manifest + trigger bất biến | `backup-vps.sh` rồi `restore-check` trên Postgres của stack prod | Tệp 70.007 byte, 24 bảng, 12 dòng khớp manifest, trigger `ALWAYS` còn nguyên, DB tạm đã xóa; khôi phục 0,48 s (tổng 0,72 s) trên dữ liệu rất nhỏ | ĐẠT (máy dev) |
| SC-008 VPS thật | Let's Encrypt thật, `https://<tên miền>/healthz` 200, đo build/khôi phục | — | Chưa có VPS/tên miền | BLOCKED |
| SC-009 Android phát hành | AAB lên Play internal testing; đo khởi động nguội | — | Làn A; Play Console (W0-3) | BLOCKED |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py` | 26 test OK (6 kiểm biến, 11 bất biến compose, 9 Caddyfile) |
| Đột biến hạ tầng (`compose.prod.yml`, `Caddyfile`, `deploy-vps.sh`) | 19/19 làm test đỏ; tệp khôi phục nguyên vẹn sau mỗi lần |
| `shellcheck -x -P SCRIPTDIR` trên 4 script | sạch |
| `caddy validate` + `caddy fmt --diff` trong ảnh `caddy:2.10.2-alpine` | `Valid configuration`, đúng định dạng |
| `docker build` backend (463 MB, 59 s), web (1,4 GB, 64 s) | xanh; chạy `--read-only --cap-drop ALL` import được app, nạp 3 kịch bản diễn tập, `alembic heads` = 0010 |
| Ma trận 4 ca hỏng + Caddyfile hỏng | xem SC-006 |
| `uv run --directory backend pytest` | 2059 passed, 21 skipped (role `hoicon_app` đã có sẵn trên DB dev nên `test_db_roles.py` tự bỏ qua) |

## Review độc lập (`security-privacy-reviewer`, 18/10/2026)

**0 Critical, 0 High, 2 Medium, 12 Low.** Đã chạy Caddy/uvicorn thật với bộ lọc log thật; không đọc `.env`. Kết luận 10 mục: 1, 2, 3, 4, 7, 9
(kích thước thân) ĐẠT; 5 ĐẠT có điều kiện; 6 ĐẠT một phần; 8 lỗi nhẹ.

**Đã sửa:**
- **M-1** web cùng mạng với backend và backend tin `X-Forwarded-For` từ mọi nguồn ⇒ tách mạng `web` (`internal`) khỏi `api`; chỉ Caddy cùng mạng `api`
  với backend. Test: web không chung mạng với backend/Postgres, `api` = {backend, caddy}.
- **M-2** không timeout kết nối ⇒ `read_header 10s`, `read_body 30s`, `idle 2m`, tiêu đề ≤ 16 KB; RAM Caddy 128 → 192 MB.
- L-1 regex che token chịu `//login/…`; bỏ `Location`; L-3 bỏ khóa Gemini khỏi container; L-4 lỗi SQL không kèm câu lệnh trong log Postgres;
  L-6 `backup.sh` dùng `--frozen --no-dev`; L-7 khóa/bí mật chỉ ký tự an toàn (Compose cắt `$`, ` #`); L-8 deploy kiểm 404 cho `/docs /redoc /openapi.json /mcp/threat/`; L-11 bỏ `X-Powered-By`.

**Tìm thêm khi kiểm lại sau sửa (không thuộc báo cáo reviewer):**
- `Refresh: 0;url=/login/<token>` của Next lọt vào log Caddy khi gọi `//login/<token>` ⇒ bỏ `Refresh`, `Content-Location`.
- Cổng 80 do Caddy tự tạo **không nhận** `servers { timeouts }` (Slowloris không bị ngắt sau 25 s) ⇒ khai báo site `http://<tên miền>` tường minh; giờ ngắt đúng 10,0 s.
- Mount **từng tệp** Caddyfile giữ inode cũ sau `git pull` và deploy không nạp lại ⇒ mount thư mục + `caddy reload` trong deploy.

**Để lại (chưa sửa, cần quyết hoặc cần VPS thật):**
- **L-2** `/readyz` công khai và chạm DB mỗi lần gọi (theo yêu cầu giám sát bên ngoài; có thể đệm 5–10 giây hoặc chỉ mở `/healthz`).
- **L-5** ảnh ghim theo tag chứ không theo digest, Postgres chưa `cap_drop`, chưa `pids_limit`, Caddy chạy root (đã `cap_drop ALL`).
- **L-9** (suy luận) IPv6 + userland-proxy của Docker có thể gộp mọi khách IPv6 thành một IP ở giới hạn ghép đôi: kiểm trên VPS thật trước khi đặt bản ghi AAAA.
- **L-10** địa chỉ IP khách nằm trong log Caddy/uvicorn: DPIA chưa nêu mục đích và hạn lưu của log IP.
- **L-12** khóa sao lưu nằm cùng máy với bản sao lưu: chỉ có tác dụng khi bản sao được chép ra ngoài (BLOCKED T012).
- Chưa đặt `docs_url=None` khi `HOICON_ENV=prod` ở `main.py` (lớp phòng thủ thứ hai); Caddy đang là lớp duy nhất.
- Chưa có reviewer đọc lại các bản sửa trên.

## Còn mở (không đánh ☑)

T010–T015 trong `tasks.md`: VPS + DNS + Let's Encrypt thật; bot Zalo thật + `setWebhook`; bật `hoicon-backup.timer` và chép sao lưu ra ngoài máy;
áp `roles.sql` ở prod; giám sát `/readyz`; phần Android (`specs/029-pilot-kit/evidence.md`).

## Android: buildType `demo`, baseline profile, đo khởi động nguội (Làn A Wave 3, 22/10/2026) — T016, T018

**T016 (mã).** `apps/android/app/build.gradle.kts`: buildType `demo` = `initWith(release)` (R8, `BuildConfig.DEBUG = false`, tắt nhật ký chẩn đoán) +
`applicationIdSuffix ".demo"`; nhãn "HỏiCon (demo)" ở `src/demo/res/values/strings.xml`; địa chỉ máy chủ demo từ `-PhoiconApiBaseUrl` chỉ nhận
`https://` (http ⇒ rơi về `https://api.hoicon.vn`, như `release`). Không có khóa phát hành ⇒ ký bằng khóa debug của SDK để cài thẳng lên máy ảo
(không tải lên Play được). Baseline profile: thêm `androidx.profileinstaller:1.4.0` (đã có trong cache Gradle, nhẹ) và
`src/main/baseline-prof.txt` **viết tay** bằng ký tự đại diện cho đường nóng `sensing/**` → `pause/**` → `domain/rules/**` → `SafePauseScreen` →
`:rules`. **Lệch task:** không dùng plugin `androidx.baselineprofile` + mô-đun macrobenchmark (cần máy thật/máy ảo để sinh hồ sơ và thêm mô-đun); hồ sơ
viết tay đủ để AGP biên dịch vào AAB (`BUNDLE-METADATA/.../baseline.prof` 7 852 byte, `baseline.profm` 1 025 byte) nhưng **chưa được sinh bằng đo thật** ⇒ cần
Opus quyết có nâng lên plugin sinh hồ sơ không. Sửa kèm: `scripts/release-gate.sh` và `scripts/tests/test_release_gate.py` còn gọi
`ConsentTextsPinTest` (Wave 2 đã thay bằng `ConsentManifestPinTest`) nên cổng TRƯỢT "No tests found"; đã đổi tên.

| Kiểm | Kết quả |
|---|---|
| `gradlew :app:assembleDemo :app:bundleRelease :app:bundleDemo --no-configuration-cache` | thành công |
| `aapt2 dump badging` APK demo | `package: name='vn.hoicon.sentinel.demo' versionCode='3' versionName='0.3.0'`, `application-label:'HỏiCon (demo)'` |
| `bash scripts/release-gate.sh app-release.aab` | thoát 0: quyền cấm ĐẠT (17 quyền, 2 dịch vụ), debuggable tắt, R8 959/3 941 lớp (24%) rút gọn, không HC_TIMING/HC_SPIKE, cleartext chặn, có "Đây là trợ lý AI HỏiCon", `ConsentManifestPinTest` ĐẠT |
| `bash scripts/release-gate.sh app-demo.aab` | thoát 0, cùng kết quả |
| `python3 -m unittest discover -s scripts/tests` | OK |

**T018 (đo).** Máy ảo, **không phải máy thật** (số máy thật vẫn ở 001, FTL, BLOCKED). `hc-api34` khởi động nguội (`emu-start.sh --cold`) ngay trước khi đo. Cùng
một máy ảo, cùng phiên: bản debug hiện tại so với bản `demo` (R8 + hồ sơ). Mỗi lần: `am force-stop` → cuộc gọi giả (`adb emu gsm call`) → đọc log
Telecom. "Sàng lọc" = từ `CallScreeningServiceFilter ... <gói> scheduled` tới `SCREENING_COMPLETED` (app đã bị dừng, tiến trình nguội); "tới
FILTERING_COMPLETED" = hết bộ lọc của Telecom. Hạn của Telecom là 5 s.

| AVD | Bản | n | Sàng lọc p50 / p95 (ms) | Tới FILTERING_COMPLETED p50 / p95 (ms) | `am start -W` MainActivity nguội (ms, 10 lần: min – max, trung vị) |
|---|---|---|---|---|---|
| hc-api36 | debug | 10 | 230 / 353 | 246 / 388 | 1143 – 1403, ≈ 1252 |
| hc-api36 | **demo** | 10 | **51 / 64** | **67 / 96** | 760 – 1204, ≈ 906 |
| hc-api34 | debug | 10 | 280 / 1105 | 296 / 1125 | 1249 – 1703, ≈ 1295 |
| hc-api34 | **demo** | 9 (1 lần thiếu mốc log) | **121 / 214** | **187 / 425** | 736 – 949, ≈ 826 |

- **Hạn 5 s của Telecom:** `onScreenCall` (sàng lọc) p95 ≤ 214 ms trên bản `demo`, đạt với biên rất rộng ở cả hai AVD. SC-009 phần đo AVD: ĐẠT (số máy ảo).
- **`app_foreground → pause_shown` không đo được trên bản `demo`:** mốc `HC_TIMING` bị R8/`BuildConfig.DEBUG=false` loại khỏi bản phát hành (đúng chủ ý của
  release-gate). Phần SafePause ở bản debug (cùng phiên, `emu-scenario.py --scenario fake_police`, n = 10): xem `specs/010-design-system/evidence.md` mục Wave 3.
- **Không tách được phần của baseline profile:** khác biệt debug → demo gồm R8, không còn `debuggable` và hồ sơ; profileinstaller chỉ áp hồ sơ lúc chạy đầu/dexopt
  nền nên một lần cài mới trên máy ảo chưa chắc đã hưởng. Không kết luận "hồ sơ làm nhanh X ms".
- Một lần chạy đầu của bản demo trên hc-api34 thiếu mốc Telecom (n = 9): không điều tra thêm.
- Một lần `emu-start.sh --cold` đầu tiên của `hc-api34` rơi kết nối ngay sau khi lên (adb `offline`); khởi động lại một lần là ổn.
## Wave 3 (làn B)

- **T019 ĐẠT:** log Caddy ra stdout nên hạn giữ do driver Docker (`max-size 10m × max-file 5` mỗi dịch vụ, test `test_every_service_has_bounded_logs`);
  `roll_keep_for` chỉ dùng được khi ghi ra tệp nên KHÔNG áp dụng (lệch so với chữ của task, hạn theo dung lượng chứ không theo ngày — **cần Opus** nếu muốn hạn theo ngày).
  Đã ghi mục đích + hạn vào `docs/PRIVACY-DPIA.md` §2 và `docs/DATA-MODEL.md` §6. Verify: `unittest test_deploy_vps` 28 OK; `caddy validate` (`caddy:2.10.2-alpine`) Valid.
- **T017 BLOCKED:** role `hoicon_app` đã có sẵn trên DB dev với mật khẩu do người khác đặt; chạy API/worker dưới role này cần mật khẩu hoặc đặt lại mật khẩu (tôi không đổi).
  Tiến: cho phép đặt mật khẩu tạm hoặc tự chạy `HOICON_DATABASE_URL=<url hoicon_app> pytest tests/integration/test_db_roles.py`.

## Wave 5 — T017 (đường thử không phụ thuộc mật khẩu `hoicon_app`), làn B, 23/10/2026

- **T017 ĐẠT** (bằng Postgres tạm thay vì DB dev): `scripts/try-roles.sh` dựng container `pgvector/pgvector:pg17` riêng (cổng 15433, xóa khi xong, mật khẩu sinh ngẫu nhiên mỗi lần) nên không đụng role `hoicon_app` có sẵn ở DB dev. Các bước và kết quả: (1) `alembic upgrade head` + `open_checkpointer` (setup) bằng role chủ; (2) `roles.sql` áp 3 lần (trước/sau setup, chạy lại được); (3) API dưới `hoicon_app` — `/healthz` và **`/readyz` 200**; (4) `tests/integration/test_db_roles.py` **21 passed, 0 bỏ qua**; (5) `scripts/lib/roles_smoke.py`: một lượt đồ thị demo + checkpoint + job dưới `hoicon_app` (`agent_runs=1 jobs=3`, chạy tới `ask_elder`).
- **Phát hiện thật:** dưới `hoicon_app`, `AsyncPostgresSaver.setup()` báo `InsufficientPrivilege` (DDL) ⇒ worker không mở được runtime ("chưa mở được runtime, thử lại sau 1 s", lặp mãi). SỬA: `open_checkpointer` bỏ qua đúng lỗi này (log info), lỗi khác vẫn ném (2 test `test_checkpointer_privileges.py`). Thứ tự áp ở prod ghi vào chú thích `roles.sql`: migration + setup bằng role chủ → `roles.sql` → đổi URL.
- **Không làm:** phần `scripts/e2e-m1.sh` dưới `hoicon_app` — các test của nó dọn dữ liệu bằng cách tắt trigger (cần role chủ), nên chạy dưới `hoicon_app` sẽ đỏ vì lý do không liên quan; thay bằng bước (5). **Cần Opus:** cập nhật `plan.md` D10 ("không áp roles.sql ở prod") — nay đã thử được, quyết định áp là của Tiến/Minh. T013 (áp ở prod) vẫn BLOCKED bởi T010 (VPS).

## Wave 6 — T020 (làn B, 24/10/2026)

- **T020 ĐẠT**: c584bea đã đáp ứng gần đủ (Postgres tạm, `roles.sql` ×3, `/readyz` 200 dưới `hoicon_app`, `test_db_roles` không bỏ qua, một lượt đồ thị + job). Thiếu: `ALTER DEFAULT PRIVILEGES` (Medium #8 của 034).
  Test đỏ trước (`test_a_table_added_by_a_later_migration_is_usable_without_rerunning_the_script`: `permission denied for table zz_012_later`), rồi thêm `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hoicon_app` vào `roles.sql`.
  `scripts/try-roles.sh` chạy lại: `test_db_roles.py` **22 passed, 0 skipped**; `/readyz` 200; `agent_runs=1 jobs=3`; `docker ps -a | grep -c hoicon-db-t017` = 0.
- Lệch chữ task: sự kiện thử qua `POST /v1/events` KHÔNG làm (cần JWT thiết bị); thay bằng một lượt đồ thị + job dưới `hoicon_app` (`roles_smoke.py`). Tên container là `hoicon-db-t017` chứ không phải `hoicon-roles-try`.
- Lưu ý: sổ chỉ-ghi-thêm MỚI (nếu có) phải thêm tay vào hai dòng REVOKE, vì quyền mặc định cấp cả UPDATE/DELETE.
