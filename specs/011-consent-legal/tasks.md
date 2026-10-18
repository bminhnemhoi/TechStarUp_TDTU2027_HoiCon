# Công việc Spec 011: Văn bản đồng ý, DPIA rút gọn, quy trình thí điểm

`PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`. Tick một task chỉ khi `Verify` đã chạy xanh.

## Giai đoạn 1: Lõi kiểm tra (đỏ trước)
- [x] T001 [FR-009, FR-010] Viết `backend/tests/contract/test_consent_texts.py` (đỏ vì chưa có văn bản/mô-đun) và
  `backend/src/hoicon/ops/consent_texts.py` (trích chữ, chuẩn hóa, sha256, manifest, `problems()`, CLI `check|write`);
  gồm cả test "DPIA nhắc đủ mọi mục đích" và "PILOT-PROTOCOL có đủ mục" (dùng ở T004/T005).
  · Verify: `$PYTEST tests/contract/test_consent_texts.py` đỏ đúng lý do (thiếu văn bản) trước khi có văn bản
- [x] T002 [FR-002, FR-003] Test bất biến phiên bản trên dữ liệu giả (`released`), test chuẩn hóa/sha256.
  · Verify: `$PYTEST tests/contract/test_consent_texts.py -k "released or normal or sha"`

## Giai đoạn 2: Văn bản
- [x] T003 [FR-001, FR-004, FR-005, FR-006] Soạn 10 tệp `docs/legal/consent/<purpose>.vi.md` + `README.md`, rồi
  `python -m hoicon.ops.consent_texts write` sinh `manifest.json`.
  · Verify: `$PYTEST tests/contract/test_consent_texts.py` xanh; `python -m hoicon.ops.consent_texts check` thoát 0
- [x] T004 [FR-007] Hoàn thiện `docs/PRIVACY-DPIA.md` (giữ phần quy trình đã cài đặt của 034).
  · Verify: test "DPIA nhắc đủ mọi mục đích" xanh
- [x] T005 [FR-008] Hoàn thiện `docs/PILOT-PROTOCOL.md`.
  · Verify: test "PILOT-PROTOCOL có đủ mục" xanh

## Giai đoạn 3: Rà soát và nghiệm thu
- [x] T006 [FR-005, FR-006] Chạy skill `privacy-audit` (mã ↔ chữ ↔ DPIA) và `ux-elder-reviewer` cho văn bản; sửa mục chặn/High.
  **Giới hạn:** chữ đã sửa; 3 văn bản (`llm_processing`, `voice_input`, `pilot_research`) vẫn CHẶN phát hành vì mã chưa thực thi lời hứa (xem `evidence.md`).
  · Verify: báo cáo ghi vào `evidence.md`; test xanh sau sửa
- [x] T007 [FR-011] Liệt kê (không sửa) chỗ Android hard-code chuỗi đồng ý cần đồng bộ cho làn A vào `evidence.md`.
  · Verify: `grep` các tệp Android liệt kê; không có thay đổi dưới `apps/android/`
- [x] T008 [FR-009] Kiểm độ nhạy bằng đột biến (đổi 1 ký tự, xóa 1 tệp, đổi enum, bỏ banner, thêm số điều luật).
  · Verify: mọi đột biến làm test đỏ
- [x] T009 [FR-001..FR-011] Bộ kiểm cuối: ruff, pytest toàn bộ, `hoicon-eval --suite smoke --compare baseline --shared-db-ok`,
  `check-spec-trace`, gitleaks `backend infra specs docs`; điền `evidence.md`; ROADMAP `P1-06` ở ◐.
  **Ghi chú:** `gitleaks dir backend` báo 4 phát hiện CHỈ ở tệp cấu hình cục bộ của máy dev (bị `.gitignore`, không nằm trong git;
  `backend/src`, `tests`, `migrations`, `eval` sạch); eval chạy trên DB `hoicon_eval` riêng (không cần `--shared-db-ok`).
  · Verify: mọi lệnh xanh

## BLOCKED
- [ ] T010 [FR-004, SC-007] Minh duyệt văn bản (`draft` → `approved`, ghi `released` khi đưa cho người thật). **BLOCKED**: Minh.
- [ ] T011 [SC-008] Người cao tuổi thật đọc thử, ghi chỗ khó hiểu. **BLOCKED**: cần thí điểm (029 giai đoạn 2).
- [ ] T012 [FR-011] *Làn A:* đồng bộ chuỗi Android với văn bản đã duyệt và nâng `ConsentLedger.VERSION`. **BLOCKED**: sau T010.
