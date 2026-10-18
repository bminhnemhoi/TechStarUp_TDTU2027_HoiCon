# Công việc Spec 026: Tác tử xác minh, tra cứu E10 & danh sách đe dọa trên máy

## Cách chạy

- **Chạy một mạch.** Giai đoạn 0 làm ở checkout chính và merge trước. Sau đó làn B (`../hoicon-wt/server`) và làn A
  (`../hoicon-wt/android`) chạy song song. Giai đoạn Z gom lại. Không có task nào chờ duyệt tay.
- **Một ngoại lệ:** ADR-011 ở trạng thái "Đề xuất". Nếu Tiến chưa chấp nhận thì vẫn thi công theo ADR-011 (dừng giữa
  chừng tốn hơn), và evidence ghi rõ trạng thái đó.
- **Thẻ làn:** `[B]` server, `[A]` Android, `[AB]` chung. Mỗi task phải chạy dòng `Verify` thấy xanh rồi mới sang task kế.
- **Biến dùng trong lệnh** (chạy từ gốc repo):
  - `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`
  - `GRADLE = ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/opt/android-studio/jbr PATH="/opt/android-studio/jbr/bin:$PATH" ./apps/android/gradlew -p apps/android`

## Giai đoạn 0: Hợp đồng & quyết định (checkout chính)

- [x] T001 [AB] [FR-003] Viết `docs/adr/ADR-011-danh-sach-de-doa-bucket.md` ở trạng thái **Đề xuất**: bối cảnh (dò ngược
  h1), ba phương án A/B/C, công thức k-ẩn danh và tỉ lệ khớp nhầm, `bucket_enc`, chính sách chọn `bucket_bits`, hệ quả.
  Không sửa thân ADR-006.
  · Verify: `grep -c "Đề xuất" docs/adr/ADR-011-danh-sach-de-doa-bucket.md`
- [x] T002 [AB] [FR-001] Viết `docs/schemas/lookup_request.v1.json`, `lookup_result.v1.json` và `threat_list.v1.json`
  theo plan §6. Thêm `lookups` vào enum `purpose` của `consent_record.v1.json`. Viết fixture `valid`/`invalid` cho cả 3
  schema; fixture invalid phải có đủ các lỗi liệt kê ở plan §6.
  · Verify: `$PYTEST tests/contract/test_lookup_schemas.py tests/contract/test_pairing_schemas.py`
- [x] T003 [AB] [FR-001] Viết `backend/tests/contract/test_lookup_schemas.py`. Test kiểm valid qua, invalid trượt, và
  câu `disclaimer` của mọi fixture valid mở đầu bằng "Đây là trợ lý AI HỏiCon.".
  · Verify: như T002

## Làn B: Server

- [x] T004 [B] [FR-002] Viết migration `backend/migrations/versions/20261016_0007_verification_lookups.py` theo plan §5
  và cập nhật `db/models.py` (`Verification`, `ThreatIndicator.bucket_enc`, CHECK của `consents`).
  · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head`
- [x] T005 [B] [FR-002] Viết `backend/tests/integration/test_schema_0007.py`. Test kiểm:
  - các CHECK (`actor`, `kind`, `via`, `verdict`, hex, `last3`);
  - UNIQUE một phần cho `via='call'`;
  - xóa gia đình thì xóa dây chuyền;
  - consent `lookups` ghi được;
  - không cột nào có tên chứa `h1`, `phone` hay `url`.
  - hạ cấp rồi nâng cấp lại khi đã có dòng consent `lookups`: trigger chặn DELETE nên CHECK cũ phải dựng bằng `NOT VALID`.

  · Verify: `$PYTEST tests/integration/test_schema_0007.py`
- [x] T006 [B] [FR-003] Viết `backend/src/hoicon/domain/threat_bucket.py`:
  - `bucket24(h1)`;
  - `shift(bucket24, bits)`;
  - `encrypt_bucket(bucket24, value_hmac, kid=None)` và `decrypt_bucket(...)`, dùng lại `_aead` của `domain/pii.py`,
    AAD `hoicon:threat:bucket:v1:<kid>:<value_hmac>`.
  · Verify: `$PYTEST tests/unit/test_threat_bucket.py`
- [x] T007 [B] [FR-003] Viết `backend/tests/unit/test_threat_bucket.py`. Các ca:
  - vectơ cố định (h1 → bucket24);
  - `shift` ở 16/22/24 bit;
  - mã hóa rồi giải mã cho lại giá trị cũ;
  - tráo bản mã giữa hai `value_hmac` thì giải mã hỏng;
  - sai kid thì báo lỗi;
  - bản mã không chứa bucket dạng rõ.

  · Verify: như T006
- [x] T008 [B] [FR-003] Sửa `ops/threat_list.py` để ghi `bucket_enc` khi nạp và khi nạp lại. In ra số dòng thiếu
  `bucket_enc`. Không in h1, HMAC hay bucket. Bổ sung test vào bộ test hiện có của loader.
  · Verify: `$PYTEST tests/integration/test_threat_indicators.py`
- [x] T009 [B] [FR-004] Viết `backend/src/hoicon/services/verification_service.py`:
  - `verify_phone` dùng lại `lookup_h1`;
  - `verify_url` (chuẩn hóa IDNA, bỏ đường dẫn/truy vấn/thông tin đăng nhập, áp bảng ở plan §4);
  - `record(...)`;
  - các hằng `DISCLAIMER`, `REASONS` và bảng sàn nâng mức.

  Không gọi LLM.
  · Verify: `$PYTEST tests/unit/test_verification_rules.py`
- [x] T010 [B] [FR-004] Viết `backend/tests/unit/test_verification_rules.py`. Các ca:
  - toàn bộ các dòng của bảng plan §4;
  - `phone` không bao giờ ra `safe` (lặp với mọi `confidence`);
  - URL có `user:pass@`, truy vấn chứa số điện thoại hư cấu: không phần nào lọt vào kết quả hay vào thứ được băm
    (chỉ host);
  - IDN tiếng Việt;
  - mọi câu `reasons` không chứa cụm nào trong `PANIC_PHRASES` (`eval/checks.py`).

  · Verify: như T009
- [x] T011 [B] [FR-006] Thêm `IncidentService.raise_level(session, incident_id, level, reason)`: chỉ nâng, tăng
  `version`, không ghi `incident_transitions`, giữ `_lock`. Sự cố không ở `GUARDIAN_DECIDABLE` thì trả về mà không làm gì.
  Viết test trong `tests/integration/test_incident_service.py` cho các ca: không hạ, không vượt khi đã quyết, gọi đồng
  thời.
  · Verify: `$PYTEST tests/integration/test_incident_service.py`
- [x] T012 [B] [FR-005] [FR-006] Viết `backend/src/hoicon/api/routers/lookups.py` với `POST /v1/lookups`:
  - nhận JWT thiết bị hoặc JWT người giám hộ;
  - kiểm consent `lookups`;
  - advisory lock rồi đếm hạn mức (plan D3);
  - kiểm `incident_id` cùng gia đình;
  - gọi `raise_level`;
  - xếp job `graph_resume {"evidence"}` với khóa `{incident_id}:evidence`, chỉ khi người tra là thiết bị và kết luận là
    `dangerous`.

  Gắn router vào `api/main.py`.
  · Verify: `$PYTEST tests/integration/test_api_lookups.py`
- [x] T013 [B] [FR-005] [FR-006] Viết `backend/tests/integration/test_api_lookups.py`. Các ca:
  - số trong danh sách và số không có;
  - URL `.apk`;
  - 401;
  - 403 khi chưa có đồng ý;
  - 404 khi `incident_id` của nhà khác;
  - 422 với `kind=account` và với trường `number`;
  - 429: ở lần thứ 21 trong giờ (thiết bị), lần thứ 61 trong giờ (người giám hộ), và hạn mức gia đình; kèm một test gọi
    đồng thời 25 request mà chỉ 20 lọt;
  - nâng mức sự cố chỉ đi lên;
  - job `evidence` chỉ một lần mỗi sự cố, và không có khi người tra là người giám hộ;
  - quét DB và `caplog` không thấy h1, URL hay host.

  · Verify: như T012
- [x] T014 [B] [FR-009] Viết `backend/src/hoicon/services/threat_list_service.py` (dựng ảnh chụp, `version`, cache 5
  phút, bỏ dòng `is_demo` khi `HOICON_ENV=prod`, bỏ dòng hết hạn hoặc thiếu `bucket_enc`) và route
  `GET /v1/threat-list?since=`: JWT thiết bị, trả `304` khi trùng phiên bản, hạn mức 24 lần/ngày. Thêm cấu hình
  `threat_bucket_bits` (mặc định 22, giới hạn 16–24) vào `config.py`.
  · Verify: `$PYTEST tests/integration/test_threat_list.py`
- [x] T015 [B] [FR-009] Viết `backend/tests/integration/test_threat_list.py`. Các ca:
  - payload khớp `threat_list.v1`;
  - giải mã `buckets_b64` ra đúng tập bucket đã sắp xếp, không trùng;
  - không có h1, HMAC hay last3 trong phản hồi;
  - `304` khi gọi lại với `since`;
  - dòng hết hạn thì biến mất khỏi ảnh chụp;
  - bản prod bỏ dòng `is_demo`;
  - 401 và 429.

  · Verify: như T014
- [x] T016 [B] [FR-008] Trong `api/routers/events.py`, khi `_start_graph` chạy thì ghi một dòng `verifications`
  (`actor=system`, `via=call`, kết luận theo bảng plan §4) từ kết quả `prepare_event`, dùng `ON CONFLICT DO NOTHING`.
  Giữ nguyên kiểm tra "payload `start_graph` không mang h1". Thêm test vào `tests/integration/test_api_elder.py` hoặc
  `tests/integration/test_api_events.py`.
  · Verify: `$PYTEST tests/integration/test_api_events.py tests/integration/test_api_elder.py`
- [x] T017 [B] [FR-007] Sửa `agents/incident_graph.py`:
  - thêm node `verification` giữa `risk_scorer` và `intervention`: đọc `verifications` của sự cố, rescore bằng `max()`,
    gọi `raise_level`, ghi `step` (không có HMAC); lượt eval/demo thì bỏ qua DB;
  - `await_guardian` nhận resume `{"evidence": id}`: sự cố chưa quyết thì gửi
    `notify(state, "evidence", texts.guardian_evidence(...))`, rồi quay lại chờ.

  Thêm `texts.guardian_evidence(alias, kind, last3, is_drill)`, dùng `_message` nên tự có câu công khai AI và nhãn diễn tập.
  · Verify: `$PYTEST tests/integration/test_graph_verification.py tests/integration/test_incident_graph.py tests/integration/test_graph_durable.py`
- [x] T018 [B] [FR-007] Viết `backend/tests/integration/test_graph_verification.py`. Các ca:
  - sự cố có dòng `dangerous` thì mức thành `critical` trong state **và** trong `incidents.level`;
  - không có dòng xác minh nào thì mức không đổi;
  - mức không bao giờ dưới `rule_floor`;
  - mức do `risk_scorer` nâng được ghi xuyên về `incidents.level`;
  - `evidence` khi đang chờ: đúng 1 job `notify_guardian` có câu công khai AI, và bộ hẹn giờ không bị dời;
  - `evidence` lần hai: không có tin mới;
  - `evidence` sau khi người giám hộ đã quyết: không gửi;
  - sự cố diễn tập: tin có nhãn `[DIỄN TẬP]`.

  · Verify: như T017
- [x] T019 [B] [FR-013] Chạy `hoicon-eval --suite smoke --compare baseline`. Nếu lệch thì sửa code, **không** ghi đè
  baseline.
  · Verify: `uv run --directory backend hoicon-eval --suite smoke --compare baseline --database-url postgresql+psycopg://hoicon:hoicon_dev@127.0.0.1:15432/hoicon --shared-db-ok`

## Làn A: Android

- [x] T020 [A] [FR-003] [FR-010] Viết `apps/android/rules/src/main/kotlin/vn/hoicon/rules/ThreatBucketIndex.kt` (JVM
  thuần): `bucket(h1, bits)`, `fromPacked(bytes, bits)` (kiểm `count × 3`, đã sắp xếp, bits trong khoảng 16–24),
  `contains(h1)`. Viết test JVM:
  - vectơ khớp với `test_threat_bucket.py`;
  - packed hỏng thì báo lỗi;
  - p99 `contains` ≤ 5 ms trên 100.000 bucket;
  - tỉ lệ khớp nhầm trên 100.000 h1 hư cấu nằm trong ±30% của `N/2^b`.

  · Verify: `$GRADLE :rules:test`
- [x] T021 [A] [FR-010] Đưa Room `sentinel.db` lên v2: xóa `threat_hashes`, thêm `ThreatSnapshotEntity` (một dòng) và
  `ThreatSnapshotDao`. Viết `Migration(1, 2)`, xuất `app/schemas/.../2.json`. Không dùng `fallbackToDestructiveMigration`
  vì nó xóa luôn outbox đang chờ gửi.
  - App hiện chưa có Robolectric, `room-testing` hay thư mục `androidTest`, nên test migration chạy dạng instrumentation
    trên AVD `hc-api36`: thêm `androidx.room:room-testing` + `androidx.test.ext:junit` (chỉ `androidTestImplementation`;
    lý do: đây là cách duy nhất kiểm migration bằng schema đã xuất).
  - Viết `app/src/androidTest/.../SentinelMigrationTest.kt` dùng `MigrationTestHelper`, chứng minh `outbox_events` còn
    nguyên sau 1→2.
  · Verify: `$GRADLE :app:testDebugUnitTest` và (máy ảo `hc-api36` đang chạy) `$GRADLE :app:connectedDebugAndroidTest`
- [x] T022 [A] [FR-010] Viết `ThreatSyncWorker` trong `work/Workers.kt`:
  - chạy định kỳ 12 giờ, và một lần khi mở app hoặc ghép đôi xong (`KEEP`), cần mạng, backoff;
  - `GET /v1/threat-list?since=`, `304` thì chỉ cập nhật `fetched_at`;
  - kiểm hợp lệ, ghi Room, rồi `ThreatBucketIndex` swap (`@Volatile`).

  Nạp chỉ mục khi tiến trình khởi động ở `SentinelServices`, ngoài main thread. `LocalLists.isFlagged` dùng chỉ mục, giữ
  h1 demo cứng của bản debug. Test: phản hồi hỏng thì giữ ảnh cũ; `304`; chưa nạp xong thì trả `false`.
  · Verify: `$GRADLE :app:testDebugUnitTest`
- [x] T023 [A] [FR-011] Viết `data/remote/LookupApiClient.kt` theo mẫu `ElderApiClient`: dựng thân theo
  `lookup_request.v1`, đọc `lookup_result.v1`, ánh xạ lỗi 401/403/429/5xx/mất mạng. Viết test với fixture hợp đồng; số
  thô không xuất hiện trong thân request hay trong log.
  · Verify: `$GRADLE :app:testDebugUnitTest`
- [x] T024 [A] [FR-011] Màn đồng ý đúng lúc cho mục đích `lookups`: chuỗi tiếng Việt mới, ghi qua `ConsentLedger` với
  `text_sha256`. Không buộc đồng ý lại các mục đích đã có (test). Chạy skill `consent-copy` nếu đã có trong repo; nếu
  chưa có thì ghi vào evidence.
  · Verify: `$GRADLE :app:testDebugUnitTest`
- [x] T025 [A] [FR-011] Viết `ui/LookupScreen.kt` (nhập số), `ui/LookupResultScreen.kt` (5 trạng thái: nguy hiểm, cảnh
  báo, chưa có thông tin, an toàn [chỉ bản xem trước], mất mạng) và `LookupActivity.kt` (`exported=false`).
  - Dùng token `risk.*`, luôn kèm biểu tượng + chữ.
  - Chữ ≥ 20sp, nút ≥ 64dp, 200% vẫn thấy đủ hai nút (nút ghim đáy, nội dung cuộn).
  - `Speaker` đọc câu công khai AI và kết luận.
  - Mất mạng thì kết luận từ `ThreatBucketIndex`.
  - Thêm nút phụ "Kiểm tra số hay đường link" trên E6.

  Dùng skill `ui-screen`.
  · Verify: `$GRADLE :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`
- [x] T026 [A] [FR-011] Chụp ảnh E10 trên AVD `hc-api36` ở cỡ chữ 100% và 200% cho 5 trạng thái, lưu tại
  `~/hoicon-evidence/026-verification-threat/`. Gửi `ux-elder-reviewer` và sửa hết mục chặn. Đo từ lúc bấm tới lúc có kết
  quả (SC-001) qua log mốc thời gian, nối backend dev.
  · Verify: ảnh có đủ 10 tệp; báo cáo reviewer không còn mục chặn
- [x] T027 [A] [FR-012] (P3) Viết `domain/qr/VietQrParser.kt` (EMVCo TLV, CRC, GUID `A000000727`, tag 59) kèm test JVM
  với payload hư cấu. Thêm "Quét mã QR" bằng Google Code Scanner (tra phiên bản bằng `documentation-lookup`, nêu lý do
  thêm thư viện, không thêm quyền `CAMERA`, ẩn nút khi không có GMS). Thêm "Dán đường link" (bỏ truy vấn/mảnh/thông tin
  đăng nhập trên máy trước khi gửi). VietQR chỉ hiện trên máy, không gửi gì lên máy chủ.
  · Verify: `$GRADLE :app:testDebugUnitTest :app:lintDebug && grep -c "android.permission.CAMERA" apps/android/app/src/main/AndroidManifest.xml` (phải là 0)

## Giai đoạn Z: Gom & nghiệm thu (checkout chính)

- [x] T028 [AB] [FR-013] E2E trên máy ảo: `python3 scripts/emu-scenario.py --avd hc-api36 --scenario fake_police` rồi
  chạy lại với `--avd hc-api34`. Backend dev có seed demo đã nạp lại để có `bucket_enc`. Kiểm số hư cấu
  `flagged_caller` khớp bucket qua đồng bộ thật (không chỉ qua h1 cứng của bản debug), và SafePause hiện biến thể
  `critical`.
  · Verify: cả hai AVD đều ĐẠT trong log của script
- [x] T029 [AB] [FR-013] Chạy `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck`. Cập nhật:
  - `docs/API.md` (`/v1/lookups`, `/v1/threat-list`);
  - `docs/DATA-MODEL.md` (`verifications`, `bucket_enc`, Room v2 thay `threat_hashes`, hạn lưu);
  - `docs/AGENTS.md` (node `verification` không LLM, `evidence`);
  - `docs/DESIGN-SYSTEM.md` (E10);
  - ROADMAP "Ghi chú" (`verifying`/`rescore` chưa dùng; `account` để dành).

  · Verify: `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck`
- [x] T030 [AB] [FR-013] Review độc lập bằng `security-privacy-reviewer` (PII, manifest, đồng ý, `bucket_enc`, hạn mức).
  Sửa mọi mục Critical/High và ghi kết quả vào evidence.
  · Verify: báo cáo reviewer không còn Critical/High chưa xử lý
- [ ] T031 [AB] [FR-013] Chạy đủ bộ lệnh kiểm:
  - `$PYTEST`;
  - `ruff check` và `ruff format --check` (`--cache-dir /tmp/ruff_cache src/ tests/`);
  - `$GRADLE :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`;
  - gitleaks **từng thư mục**: `backend/src`, `backend/tests`, `apps/android/app/src`, `apps/android/rules/src`,
    `docs/schemas`, `docs/adr`, `specs/026-verification-threat`;
  - eval smoke so baseline;
  - `python3 scripts/check-spec-trace.py`.

  Sau đó điền `evidence.md` bằng số thật có nguồn, và đặt ROADMAP `P2-11` ở ◐ (☑ chỉ khi có số máy thật hoặc Minh chấp
  nhận số máy ảo).
  · Verify: mọi lệnh trên xanh; `python3 scripts/check-spec-trace.py` ⇒ 0 lỗi

## Wave 2 (18/10/2026 — tồn đọng Wave 1)

- [ ] T032 [A] [FR-011] Bỏ chuỗi giống số điện thoại khỏi chú thích trong **mã sản phẩm** (CLAUDE.md luật 1–2: số hư cấu chỉ ở
  `tests/` hoặc `data/`): `data/lookup/LookupChecker.kt:37` (`"0912345678a"`) ⇒ mô tả bằng lời ("một số gõ kèm chữ cái thừa ở
  cuối"); cùng loại ở `apps/android/rules/src/main/kotlin/vn/hoicon/rules/PiiMasker.kt:14` (ví dụ dạng `+84 …`, `091-…`, `(028) …`)
  ⇒ mô tả các dạng phân cách bằng lời. Ví dụ cụ thể, nếu cần, chuyển vào test (`src/test/`) dùng số trong `data/fixtures/phones.json`.
  Không đổi hành vi.
  · Verify: `grep -rnE "(\+?84|0)[35789][0-9]{8}|(\+?84|0)[35789][0-9][ .-]?[0-9]{3}[ .-]?[0-9]{3,4}|\(0[0-9]{2}\) ?[0-9]{4}" apps/android/app/src/main apps/android/rules/src/main apps/android/demobank/src/main`
  không còn kết quả; `$GRADLE :rules:test :app:testDebugUnitTest`
