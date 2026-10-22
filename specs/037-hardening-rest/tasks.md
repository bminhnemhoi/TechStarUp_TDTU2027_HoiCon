# Tasks: 037 — Gia cố phần còn lại

**Chế độ chạy**: tự hành một mạch (MASTER-PLAN §2.6). `[B]` = `backend/**`, `[A]` = `apps/android/**`. Test đỏ trước. `$PYTEST` =
`uv run --directory backend pytest`; `$GRADLE` = `apps/android/gradlew -p apps/android`. **Dừng** khi Verify đỏ 2 lần liên tiếp
(`diagnosing-bugs`), hoặc khi cần quyết định Crashlytics (★ Minh, MASTER-PLAN §8 mục 13).

## Hợp đồng (checkout chính, làm trước khi tách làn)
- [x] T001 [AB] [FR-002, FR-004] *(kiến trúc sư, checkout chính — luật 1 §5)* Thêm mã `consent_withdrawn` (kèm `purpose`) và `unknown_consent_text` vào hợp đồng mới `docs/schemas/error.v1.json`
  (`{error, purpose?}`; hiện mã đã dùng ở `routers/events.py`, `routers/devices.py`) + fixture valid/invalid. **Xong 23/10** (3 valid ĐẠT, 4 invalid bị từ chối khi kiểm bằng `jsonschema` Draft 2020-12). Test hợp
  đồng `backend/tests/contract/test_error_schema.py` (chạy fixture + enum `purpose` == mục đích trong `manifest.json`) viết ở T002.
  · Verify: `$PYTEST tests/contract -q` (sau T002)

## Làn B
- [ ] T002 [B] [FR-001, FR-002] Test hợp đồng `tests/contract/test_error_schema.py` (T001) + test đỏ `tests/integration/test_consent_at_send.py`: 7 loại mẫu (`fast_alert`, `detail`, `reminder`,
  `escalation`, `evidence`, `case_file`, `coach_weekly`/`protection_*`) + tổng kết diễn tập: rút đồng ý ⇒ `skipped_consent`, 0 dòng
  `messages_out`, 0 lời gọi client Zalo; cấp lại ⇒ đi; `is_demo`/`sim` ⇒ hành vi cũ. · Verify (đỏ): `$PYTEST tests/integration/test_consent_at_send.py -q`
- [ ] T003 [B] [FR-001] Hiện thực D1/D2 (`protected_member_id` trong payload, tra theo `incident_id` khi thiếu). · Verify: T002 xanh +
  `$PYTEST -q` + `hoicon-eval --suite smoke --compare baseline --shared-db-ok` exit 0
- [ ] T004 [B] [FR-002, FR-004, FR-005] Test đỏ rồi hiện thực: thân 403 thống nhất ở route thiết bị; `POST /v1/consents` kiểm
  manifest (D3; `prod` chỉ `released`); 30/giờ/thiết bị (D4). · Verify: `$PYTEST tests/integration/test_api_consents.py -q` (SC-003)
- [ ] T005 [B] [FR-006] Sổ xóa (D5) + `ops restore` chạy lại `purge_family`; test khôi phục bản cũ trên DB tạm (cách của 012 T020).
  · Verify: `$PYTEST tests/integration/test_backup_restore.py -q` (SC-004)
- [ ] T006 [B] [FR-007] HKDF khóa phụ theo tệp cho sao lưu (đọc được bản cũ), bỏ `exc_info` ở `queue.py`, đổi fixture số.
  · Verify: `$PYTEST tests/integration/test_backup_restore.py tests/unit/test_queue_logging.py -q` (tệp sau là mới) + `rg -n "0912345678" backend` rỗng

## Làn A
- [ ] T007 [A] [FR-003] Test đỏ rồi hiện thực: `consent_withdrawn` ⇒ trạng thái riêng, dừng worker mục đích đó, không thử lại; E6 câu
  mới (`ux-elder-reviewer`, ảnh 100/200% `hc-api36`). Phụ thuộc T001, T004. · Verify: `$GRADLE :app:testDebugUnitTest :app:lintDebug` (SC-002)

## Chung
- [ ] T008 [AB] [FR-008] `docs/setup/STABILITY.md` (Android vitals: đọc ở đâu, ngưỡng của Play, ghi vào báo cáo thí điểm). SC-006
  BLOCKED tới Play Console (W0-3). · Verify: review
- [ ] T009 [AB] [FR-009] Rà soát cuối trước 06/01: `privacy-audit`, `security-privacy-reviewer` toàn codebase + ma trận IDOR,
  `gitleaks dir` (cấu hình `.gitleaks.toml`), `osv-scanner` cho `backend/uv.lock` và `apps/web/pnpm-lock.yaml`; sửa mọi Critical/High.
  · Verify: báo cáo 0 Critical/High chưa xử lý (SC-005)
- [ ] T010 [AB] [FR-001..FR-009] Cổng + `evidence.md` (SC-001…006) + dòng P2-20 ROADMAP (người tích hợp).
  · Verify: `$PYTEST -q`; `$GRADLE :rules:test :app:testDebugUnitTest :app:lintDebug`; `python3 scripts/check-spec-trace.py`
- [ ] T011 [AB] [FR-008] **★ CHỜ MINH (§8 mục 13)** — chỉ khi duyệt Crashlytics: mục đích đồng ý mới + văn bản (skill
  `consent-copy`), DPIA, SDK bật sau đồng ý, Play data safety. Chưa duyệt ⇒ không làm, ghi trong evidence. · Verify: `consent_texts check`

Thứ tự: T001 → (B: T002 → T003 → T004 → T005 → T006) ‖ (A: T007 sau T004) → T008 → T009 → T010.
