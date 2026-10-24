# Công việc Spec 037: Gia cố phần còn lại

> **Đã đối soát 24/10/2026 (kiến trúc sư):** bản của làn B được giữ làm gốc vì mã đã thi công theo nó; bổ sung từ bản kiến trúc sư ở cuối `tasks.md` (T013–T016).

## Cách chạy

- **Làn B một mạch** (`feat/037-hardening-rest`): chỉ `backend/**`, `infra/**`, `scripts/**`. `[A]` (Crashlytics) để làn A khi có Firebase.
  Làn B không sửa `docs/` — task `[Docs]` ghi sẵn nội dung cho người có quyền.
- **Thứ tự**: T001 → T002 → T003 → T004 (an toàn trước) → T005–T007 → T008 → T009 → T010. Test đỏ trước ở mọi task đổi hành vi.
- **Biến dùng trong lệnh**: `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`.
- **Dừng**: `Verify` đỏ 2 lần ⇒ dừng task, chẩn đoán (`diagnosing-bugs`); cần đổi `docs/schemas` ⇒ dừng, báo Opus.

## Nhóm [B]

- [x] T001 [B] [FR-001, SC-001] Test đỏ trước `backend/tests/integration/test_consent_manifest_enforcement.py`: ở `consent_strict=True`,
  `POST /v1/consents` với (purpose, version, sha) ngoài manifest ⇒ 422, 0 dòng ghi; trong manifest ⇒ 200; `consent_strict=False` ⇒ nhận như cũ.
  Rồi sửa `api/routers/consents.py` + `config.py` (`consent_strict`, mặc định `true` khi `env == "prod"`). Thân lỗi không nêu sha mong đợi.
  · Verify: `$PYTEST tests/integration/test_consent_manifest_enforcement.py tests/integration/test_api_consents.py`
- [x] T002 [B] [FR-002, SC-002] Test đỏ trước `test_send_checks_consent.py`: sự cố mở khi còn `guardian_alerts`, rồi rút ⇒ job `notify_guardian`
  đã xếp (cả `reminder`, `escalation`, bản tin tuần của Coach, tổng kết diễn tập, hồ sơ vụ việc) **không** tới `deliver`
  (client Zalo giả đếm 0). Sửa: payload mang `protected_member_id` (`incident_graph.notify`, `coach_service`, `drill_service._queue_debrief`,
  `case_file`), `channels/guardian.py::send_to_guardian` đọc `consent_gate` trước `deliver`; job cũ chưa có khóa ⇒ tra qua `incident_id`/`family_id`.
  Tin **cảnh báo khẩn giai đoạn 1** đã xếp trước khi rút vẫn không gửi sau khi rút (nguyên tắc: đồng ý là điều kiện lúc gửi).
  · Verify: `$PYTEST tests/integration/test_send_checks_consent.py tests/integration/test_notify_guardian.py tests/integration/test_consent_enforcement.py`
- [x] T003 [B] [FR-003] Chính sách link cũ sau khi rút `guardian_alerts` (đề xuất D2, hằng số `WITHDRAWN_DECISION_POLICY`): test đỏ trước —
  `GET /action/{token}` ⇒ "liên kết hết hạn" không kèm nhãn/mức/tóm tắt; `POST …/decision` vẫn ghi quyết định và đóng sự cố nhưng trả thân tối thiểu
  (không `state`/`outcome`); `POST /incidents/{id}/decision` cùng quy tắc; đã đồng ý ⇒ như cũ. Nếu thân tối thiểu vi phạm `incident_decision`/`action_view`
  ⇒ **DỪNG, báo Opus** (đổi hợp đồng).
  · Verify: `$PYTEST tests/integration/test_guardian_alert.py tests/integration/test_guardian_reply.py tests/integration/test_withdrawn_links.py`
- [x] T004 [B] [FR-004, SC-003] `tests/integration/test_idor_matrix.py`: liệt kê route từ `app.routes` (có `{id}`/token hoặc phụ thuộc xác thực), mỗi ô chạy
  3 kiểu token (gia đình khác / sai audience / gia đình đã xóa); kỳ vọng cùng mã 404 (hoặc 401 khi không xác thực) cho "không có" và "không thuộc nhà". Danh sách route
  được miễn (công khai) nằm trong test, kèm lý do. Ô nào đỏ ⇒ sửa route (không nới test).
  · Verify: `$PYTEST tests/integration/test_idor_matrix.py` + in số ô (tổng/đạt) vào `evidence.md`
- [x] T005 [B] [FR-005] Giới hạn tần suất `POST /v1/consents` theo thiết bị (cửa sổ trượt, 429 + `Retry-After`; mẫu `_retry_after` của `events.py`). Test đỏ trước.
  · Verify: `$PYTEST tests/integration/test_api_consents.py tests/integration/test_consents_rate_limit.py`
- [x] T006 [B] [FR-005] `jobs/queue.py`: log lỗi chỉ tên lớp lỗi, không `exc_info` kèm tham số SQL (test: lỗi chứa chuỗi `0900000001` trong tham số ⇒ không có trong log);
  fixture dùng số `0912345678` đổi sang số hư cấu đã đăng ký trong `tests/`.
  · Verify: `$PYTEST tests/unit/test_queue_logging.py` và `gitleaks dir backend/tests`
- [x] T007 [B] [FR-005] `ops/backup.py`: khóa con theo tệp (HKDF, `salt` 16 byte ngẫu nhiên trong phần đầu tệp, có phiên bản định dạng); đọc được định dạng cũ.
  Test `tests/unit/test_backup_subkeys.py`: hai tệp cùng khóa chính ⇒ khóa con khác nhau; bản cũ (fixture sinh bằng mã trước khi đổi) khôi phục khớp manifest; sửa 1 byte ⇒ lỗi.
  · Verify: `$PYTEST tests/unit/test_backup_subkeys.py tests/integration/test_backup_restore.py`
- [x] T008 [B] [FR-006, SC-004] `ops/privacy_report.py` + `tests/unit/test_privacy_report.py`: in bảng dữ liệu ↔ mục đích ↔ hạn lưu sinh từ `Base.metadata` + ánh xạ ở một tệp Python;
  quét số điện thoại thô (mẫu của hook `guard-privacy`) trong `backend/src`, `backend/tests`, `data`; chạy `consent_texts check`; đếm dòng nghi PII trong `jobs.payload`/`agent_steps` (chỉ đếm).
  Đột biến: thêm bảng giả vào metadata không ánh xạ ⇒ thoát khác 0.
  · Verify: `$PYTEST tests/unit/test_privacy_report.py && uv run --directory backend python -m hoicon.ops.privacy_report`
- [x] T009 [B] [FR-007, SC-005] Rà soát bảo mật cuối: gọi `security-privacy-reviewer` đọc diff từ `main` (toàn codebase) + mục 1 của spec; sửa hết Critical/High; Medium ghi chủ + ngày.
  Quét phụ thuộc bằng `osv-scanner` hoặc `uv pip audit` nếu có (không có ⇒ `UNAVAILABLE`, ghi rõ).
  · Verify: báo cáo trong `evidence.md` không còn Critical/High chưa xử lý
- [ ] T010 [B] Chạy bộ kiểm đầy đủ: `$PYTEST`, `ruff check` + `format --check`, `hoicon-eval --suite smoke --compare baseline --shared-db-ok` và `--suite full --compare baseline-full`,
  `check-spec-trace`, gitleaks từng thư mục, `alembic heads` = 1; điền `evidence.md` (SC-001…SC-006).
  · Verify: lệnh thoát 0; `python3 scripts/check-spec-trace.py`

## Nhóm [A] / [Docs]

- [ ] T011 [A] [FR-008, SC-006] ★ **Chờ Minh** (MASTER-PLAN §8 mục 13; đề xuất: chưa dùng Crashlytics, đo bằng Android vitals — T015). Crashlytics: SDK + mục đích đồng ý mới (`consent-copy`, luật 7) + `play-policy`. **BLOCKED**: chưa có Firebase (W0-3/P0-08). Tiêu chí gỡ chặn:
  project Firebase + `google-services.json` ngoài git. Không tạo tệp giả; SC-006 ghi "chưa đo".
- [ ] T012 [Docs] [FR-009] **Người có quyền sửa `docs/`**: `PRIVACY-DPIA.md` thêm (a) bảng dữ liệu của `privacy_report` (T008), (b) độ trễ đệm đồng ý ≤ 60 giây khi đồng ý đổi từ kênh khác,
  (c) chính sách link cũ (T003); `docs/setup/BACKUP.md` thêm định dạng khóa con (T007). **BLOCKED**: ngoài quyền làn B.

## Đối soát kiến trúc sư 24/10/2026 (bổ sung từ bản của kiến trúc sư)

Bỏ: task [A] xử lý `consent_withdrawn` trên Android (đã có từ spec 034: `OutboxSender`, `PairingApiClient`); "sổ xóa" (không có yêu cầu
nào cần, karpathy: không làm trước). Quyết định cho các câu làn B hỏi:
- **#5 (FR-003)**: giữ D2 (ghi quyết định, thân tối thiểu) làm mặc định vì đây là đường an toàn; Minh có thể đổi ⇒ §8 mục 14.
- **#6**: hạn mức `/v1/consents` tính theo tiến trình là đủ vì ADR-002 chạy một worker API; ghi một câu vào `plan.md` D-mục hạn mức, không thêm Redis.
- **#8**: bản sao lưu v1 trùng nonce: rủi ro thấp (khóa 256 bit, ít tệp), không tái mã hóa; bản mới đã dùng khóa con (T007).

- [ ] T013 [B] [FR-001] Test hợp đồng `backend/tests/contract/test_error_schema.py` cho `docs/schemas/error.v1.json` (đã có, kiến trúc sư 23/10):
  chạy fixture valid/invalid; enum `purpose` == mục đích trong `backend/src/hoicon/consent_texts/manifest.json`; thân 403 `consent_withdrawn`
  của `routers/events.py` và `routers/devices.py` khớp lược đồ. · Verify: `$PYTEST tests/contract/test_error_schema.py -q`
- [x] T014 [B] [FR-005] `ops restore`: một khối lỗi (`BackupError`) ⇒ bỏ **cả lượt**, DB đích không đổi (một giao dịch). Test đỏ trước: tệp sửa 1 byte ở khối giữa
  ⇒ số dòng mọi bảng trước = sau. · Verify: `$PYTEST tests/integration/test_backup_restore.py -q -k atomic`
- [ ] T015 [AB] [FR-008] `docs/setup/STABILITY.md`: đọc độ ổn định ở Android vitals (Play Console), ngưỡng hành vi xấu của Play, cách ghi vào báo cáo thí điểm.
  SC-006 BLOCKED tới Play Console (W0-3). Người có quyền `docs/setup` làm. · Verify: review
- [ ] T016 [B] Chạy lại T010 sau T013–T014. · Verify: như T010
