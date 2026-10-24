# Công việc Spec 028: Diễn tập nhận biết lừa đảo v1

## Cách chạy

- Chạy một mạch. Giai đoạn 0 làm ở checkout chính và merge trước, sau đó làn B (`../hoicon-wt/server`) và làn A
  (`../hoicon-wt/android`) chạy song song, rồi gom ở giai đoạn Z.
- **Thẻ làn:** `[B]` server, `[A]` Android, `[AB]` chung.
- **Biến dùng trong lệnh:**
  - `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`
  - `GRADLE = ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/opt/android-studio/jbr PATH="/opt/android-studio/jbr/bin:$PATH" ./apps/android/gradlew -p apps/android`
- **Số migration:** migration mang số kế tiếp sau head lúc thi công (`uv run --directory backend alembic heads`). Nếu 026
  chưa merge thì không được dùng `0007` mà 026 đã giữ chỗ trong plan của nó. Khi đó lấy số kế tiếp và ghi vào evidence.

## Giai đoạn 0: Hợp đồng & nội dung

- [x] T001 [AB] [FR-001] Viết `docs/schemas/drill_script.v1.json`, `drill_offer.v1.json` và `drill_result.v1.json` theo
  plan §4, kèm fixture `valid`/`invalid`. Fixture invalid phải có:
  - 3 lựa chọn ở một bước;
  - `choice_id` là chữ "x1";
  - `drill_offer` có `is_drill=false`;
  - `drill_result` có trường `note`.

  · Verify: `$PYTEST tests/contract/test_drill_schemas.py`
- [x] T002 [AB] [FR-010] Soạn 3 tệp `data/drills/*.yaml` (giả công an, giả nhân viên ngân hàng, "con cháu cần tiền gấp"),
  `approved: false`, tên cơ quan hư cấu. Dùng skill `add-scam-scenario` hoặc `vietnamese-scam-redteam` để soạn và
  `ux-elder-reviewer` để duyệt câu chữ.
  · Verify: như T003
- [x] T003 [AB] [FR-001] [FR-010] Viết `backend/tests/contract/test_drill_schemas.py`. Test kiểm:
  - mọi tệp `data/drills/*.yaml` khớp schema;
  - không chuỗi nào chứa dãy ≥ 4 chữ số liền (trừ `caller_last3_fictional`);
  - không chứa từ cấm (danh sách cơ quan thật + tên tổ chức trong `bank_apps.vn.json`);
  - mỗi bước có đúng 1 lựa chọn đúng;
  - debrief không có cụm nào trong `PANIC_PHRASES`.

  · Verify: `$PYTEST tests/contract/test_drill_schemas.py`

## Làn B: Server

- [x] T004 [B] [FR-002] Viết migration bảng `drills` theo spec FR-002 (CHECK trạng thái, khung giờ từ 30 phút tới 4 giờ,
  chỉ mục) và cập nhật `db/models.py`.
  · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head`
- [x] T005 [B] [FR-002] Viết `backend/tests/integration/test_schema_<số>.py`: các CHECK, xóa gia đình thì xóa dây chuyền,
  và không cột nào chứa văn bản tự do.
  · Verify: `$PYTEST tests/integration/test_schema_<số>.py`
- [x] T006 [B] [FR-004] Viết `backend/src/hoicon/domain/drill.py` (nạp YAML qua schema, chấm điểm tất định) và
  `services/drill_service.py` (`schedule`, `offer`, `record_result`, `expire`, bảng cạnh `ALLOWED`, khóa theo gia đình
  bằng `_lock`).
  · Verify: `$PYTEST tests/unit/test_drill_scoring.py tests/integration/test_api_drills.py`
- [x] T007 [B] [FR-004] Viết `backend/tests/unit/test_drill_scoring.py`. Các ca:
  - đúng hết ⇒ `passed`;
  - một sai ⇒ `failed`;
  - mã lựa chọn lạ ⇒ lỗi;
  - thứ tự bước sai ⇒ lỗi;
  - máy chủ chấm lại, bỏ qua điểm do máy gửi.

  · Verify: như T006
- [x] T008 [B] [FR-003] Thêm bước chặn cờ diễn tập trong `api/routers/events.py` (plan D2), log `warning` không có PII.
  Sửa các test cũ gửi `is_drill=true` cho tạo dòng `drills` hợp lệ trước (`test_api_events.py`, `test_api_incidents.py`,
  `test_incident_service.py` nếu đi qua API) và ghi số test đã sửa vào evidence.
  · Verify: `$PYTEST tests/integration/test_drill_flag_guard.py tests/integration/test_api_events.py tests/integration/test_api_incidents.py`
- [x] T009 [B] [FR-003] Viết `backend/tests/integration/test_drill_flag_guard.py` với ma trận:
  - không có bài;
  - bài của nhà khác;
  - bài `scheduled` (chưa `in_progress`);
  - bài đã hết hạn;
  - `occurred_at` ngoài khung giờ;
  - bài đúng.

  Mọi ca sai ⇒ sự cố `is_drill=false` và cảnh báo gửi đi như thật; ca đúng ⇒ `is_drill=true`, tin có `[DIỄN TẬP]`.
  · Verify: như T008
- [x] T010 [B] [FR-005] Viết `api/routers/drills.py`: `GET /v1/drills/offer` và `POST /v1/drills/{id}/result`, JWT thiết
  bị, hạn mức 30 lần/giờ/thiết bị. Gắn vào `api/main.py`.
  · Verify: `$PYTEST tests/integration/test_api_drills.py`
- [x] T011 [B] [FR-004] [FR-005] [FR-006] Viết `backend/tests/integration/test_api_drills.py`. Các ca:
  - `schedule`: chưa đồng ý, bài thứ 3 trong tháng, khung giờ quá khứ, khung > 4 giờ, kịch bản chưa duyệt khi
    `HOICON_ENV=prod` ⇒ đều bị từ chối;
  - `offer` chỉ trả bài trong khung giờ;
  - `declined` thì không có tin;
  - `completed` ⇒ máy chủ chấm lại ⇒ `passed`/`failed`, đúng 1 job `notify_guardian` có câu công khai AI + `[DIỄN TẬP]`
    + `is_drill=true`;
  - gửi lặp ⇒ 200, gửi khác nội dung ⇒ 409;
  - bài của nhà khác ⇒ 404;
  - quét DB không có văn bản tự do.

  · Verify: như T010
- [x] T012 [B] [FR-006] [FR-007] Thêm `texts.drill_debrief(...)` (qua `_message`, nên tự có câu công khai và nhãn diễn tập), job
  `drill_expire` (đăng ký trong `incident_handlers` hoặc chạy theo lịch của worker), và lệnh ops `ops/drills.py`
  (`schedule`, `list`, `cancel`; chặn chạy khi `HOICON_ENV=prod` nếu không có `--confirm`).
  · Verify: `$PYTEST tests/integration/test_api_drills.py tests/unit/test_drill_scoring.py`
- [x] T013 [B] [FR-012] Sinh lại client TS; cập nhật `docs/API.md` và `docs/DATA-MODEL.md`.
  · Verify: `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck`

## Làn A: Android

- [x] T014 [A] [FR-009] Viết `DrillEngine.kt` (JVM thuần): bước kế, chấm điểm, `red_flags` cần nhắc. Viết test JVM dùng
  fixture `data/drills` qua `hoicon.schemasDir` (theo mẫu test hợp đồng hiện có của app).
  · Verify: `$GRADLE :app:testDebugUnitTest`
- [x] T015 [A] [FR-008] Viết `DrillApiClient.kt` (mẫu `ElderApiClient`). Trong `HeartbeatWorker`: hỏi bài khi
  `mayShare()` đúng **và** đã có đồng ý `drills`; có bài thì hiện thông báo kênh "Luyện tập" (mức ưu tiên mặc định,
  không full-screen); không hiện khi cửa sổ rủi ro đang mở. Test: không đồng ý ⇒ không hỏi; cửa sổ mở ⇒ hoãn; lỗi mạng
  ⇒ không sập.
  · Verify: `$GRADLE :app:testDebugUnitTest`
- [x] T016 [A] [FR-009] Viết `DrillResultWorker` (cần mạng, backoff, `KEEP` theo `drill_id`). Test ánh xạ 2xx/409/4xx/5xx
  và mất mạng.
  · Verify: `$GRADLE :app:testDebugUnitTest`
- [x] T017 [A] [FR-009] Viết `ui/DrillScreen.kt` và `DrillActivity.kt` (`exported=false`), dùng skill `ui-screen`:
  - 4 màn (lời mời, bước, debrief, đã dừng);
  - token `drill.*`, `[DIỄN TẬP]` + biểu tượng `school` cố định ở đầu;
  - `Speaker` đọc lời người gọi và debrief;
  - 2 nút ≥ 64dp, nút phụ "Dừng luyện tập";
  - 200% vẫn thấy đủ nút (nút ghim, nội dung cuộn).

  · Verify: `$GRADLE :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`
- [x] T018 [A] [FR-009] Chụp ảnh 4 màn ở 100% và 200% trên AVD `hc-api36`, lưu `~/hoicon-evidence/028-drills/`. Gửi
  `ux-elder-reviewer` và sửa hết mục chặn. Kiểm manifest không có quyền mới.
  · Verify: ảnh đủ 8 tệp; `git diff --stat -- apps/android/app/src/main/AndroidManifest.xml` chỉ thêm khai báo `DrillActivity`

## Giai đoạn Z: Gom & nghiệm thu

- [x] T019 [AB] [FR-012] E2E trên AVD `hc-api36` với backend dev và Zalo mock:
  - `ops drills schedule` (khung 30 phút bắt đầu ngay);
  - ép `HeartbeatWorker` chạy ngay (`adb shell cmd jobscheduler run` hoặc broadcast debug sẵn có);
  - nhận thông báo, làm hết bài;
  - tắt mạng rồi bật lại để thử gửi lại;
  - tin `[DIỄN TẬP]` có trong `messages_out` mock.

  Ghi các mốc thời gian.
  · Verify: log E2E trong evidence có đủ các mốc
- [x] T020 [AB] [FR-012] Review độc lập bằng `security-privacy-reviewer` (FR-003, đồng ý, nội dung hư cấu, quyền
  Android). Sửa hết Critical/High.
  · Verify: báo cáo không còn Critical/High chưa xử lý
- [x] T021 [AB] [FR-011] (P2, chỉ khi 027 đã merge) Thêm `POST /v1/guardian/drills` + trang `/drills` trên web người giám
  hộ (đặt lịch, lịch sử, nhãn `[DIỄN TẬP]`), dùng chung `DrillService.schedule`, có test Playwright. Nếu 027 chưa merge
  thì đánh BLOCKED và ghi vào evidence.
  Hợp đồng **có từ 24/10/2026**: `guardian_drill_request.v1.json`, `guardian_drill_list.v1.json` (+ fixture; lỗi 422 `{detail: <mã DrillRefused>}`).
  Thêm test hợp đồng vào `tests/contract/test_drill_schemas.py`; sinh lại client TS.
  · Verify: `$PYTEST tests/contract/test_drill_schemas.py tests/integration/test_api_drills.py && pnpm --dir apps/web e2e drills`
- [x] T022 [AB] [FR-012] Chạy đủ bộ lệnh kiểm:
  - `$PYTEST`; `ruff check` và `ruff format --check`;
  - `$GRADLE :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`;
  - `hoicon-eval --suite smoke --compare baseline` (hồi quy, vì D2 đổi đường sự kiện);
  - gitleaks **từng thư mục**: `backend/src`, `backend/tests`, `apps/android/app/src`, `docs/schemas`, `data/drills`,
    `specs/028-drills`;
  - `python3 scripts/check-spec-trace.py`.

  Cập nhật `docs/DESIGN-SYSTEM.md` (E11) và ROADMAP "Ghi chú" (chỉ số PILOT-PROTOCOL ★, lựa chọn B để sau, chờ Minh duyệt
  3 kịch bản). Điền `evidence.md`. Đặt `P2-13` ◐ cho tới khi Minh duyệt kịch bản.
  · Verify: mọi lệnh xanh; `python3 scripts/check-spec-trace.py` ⇒ 0 lỗi

## Wave 2 (18/10/2026 — tồn đọng Wave 1)

- [x] T023 [A] [FR-008] Màn đồng ý `drills` **đúng lúc** trên Android (review bảo mật 028, Medium #1; 011 `privacy-audit`: "không ai
  được mời"). Cần 011 T018 xong trước (chuỗi `drills` theo `docs/legal/consent/drills.vi.md` v3).
  - Đường vào: một hàng phụ (không phải hành động chính thứ ba) trên E6 "Đang bảo vệ": "Luyện tập nhận biết lừa đảo cùng con", vùng
    chạm ≥ 64dp; E6 vẫn ≤ 2 hành động chính.
  - Màn đồng ý: chữ của `drills.vi.md` (đọc to được), hai nút "Đồng ý luyện tập" / "Để sau"; đã đồng ý thì màn hiện "Ngừng luyện
    tập" (rút đồng ý, ghi dòng `granted=false`).
  - `ConsentLedger`: thêm `drills` vào `granted`/`texts` (nếu không, `changes()` tự sinh dòng **rút** đồng ý — ghi chú evidence 028
    mục 1); ghi qua `ConsentSync` như các mục đích khác, sha khớp `manifest.json`.
  - Test JVM: đồng ý ⇒ `changes()` có đúng một dòng `drills` granted với `version`/`sha256` của manifest; rút ⇒ một dòng
    `granted=false`; các mục đích khác không đổi.
  - E2E AVD `hc-api36`: đồng ý trên máy ⇒ `ops drills schedule` thành công (trước đó trả `consent_required`) ⇒ nhận lời mời; rút ⇒
    lịch mới bị từ chối. Ảnh 100% + 200%; `ux-elder-reviewer` 0 Chặn.

  · Verify: `$GRADLE :app:testDebugUnitTest :app:lintDebug`; log E2E + ảnh + báo cáo reviewer trong `evidence.md`;
  `python3 scripts/emu-scenario.py --avd hc-api36 --scenario fake_police` vẫn ĐẠT
- T021 giữ **P2** (web `/drills`, cần 027 — 027 đã merge nên không còn BLOCKED; làm sau 033 nếu còn thời gian, không chặn ☑ của
  P2-13 vì FR-011 là P2).

## Lượt 9 (nhà điều phối 24/10/2026)
- [ ] T022 [B-api][B-web] [FR-011] Hợp đồng `guardian_drill_list.v1` có thêm `elders` (`member_id`, `alias`, `drills_consent`) và `scripts`
  (`id`, `title`, `summary`) — GET luôn gửi. Bỏ cách tạm (lấy người nhận từ sự cố, 3 kịch bản viết cứng ở web); biểu mẫu `/drills` dùng hai danh sách
  này; chưa đồng ý `drills` ⇒ nút tắt + câu giải thích. Sinh lại client TS. · Verify: `$PYTEST tests/contract/test_drill_schemas.py tests/integration/test_api_drills.py -q && pnpm --dir apps/web e2e drills`
