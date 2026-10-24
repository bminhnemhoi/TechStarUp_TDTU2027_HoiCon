# Tasks 038 — Cài đặt & quyền riêng tư (E12)

**Chế độ**: tự hành một mạch. `[A]` = `apps/android/**`; `[B]` = `backend/**`. Test đỏ trước. `$PYTEST` = `uv run --directory backend pytest`;
`$GRADLE` = `apps/android/gradlew -p apps/android`. Dừng khi Verify đỏ 2 lần liên tiếp.

- [x] T001 [AB] [FR-003, FR-004] *(kiến trúc sư)* `docs/schemas/data_request.v1.json` + fixture valid/invalid. · Verify: kiểm fixture bằng jsonschema
- [x] T002 [B] [FR-004] Test hợp đồng + test đỏ `tests/integration/test_api_data_requests.py`: chỉ thiết bị `protected`; lũy đẳng; 3/ngày; được phép khi đã rút
  đồng ý; ghi `requested_via='app'`; xếp tin báo (mở đầu công khai AI) trước `purge_family` chỉ khi còn `guardian_alerts` (đã rút ⇒ 0 tin); purge xong ⇒ token cũ 401/403. Rồi hiện thực.
  · Verify: `$PYTEST tests/contract tests/integration/test_api_data_requests.py tests/integration/test_purge_family.py -q`
- [ ] T003 [A] [FR-001, FR-002] E12 trong `PermissionsScreen.kt`: thẻ mỗi mục đích; "Tắt" + xác nhận cho mục không gắn quyền ⇒ `ConsentLedger` ghi `granted=false`.
  Test đơn vị + Compose đỏ trước. · Verify: `$GRADLE :app:testDebugUnitTest :app:lintDebug`
- [ ] T004 [A] [FR-003] `PrivacyDeleteScreen.kt` (giữ 3 giây, offline ⇒ không xóa cục bộ) + client `POST /v1/data-requests` + xóa cục bộ + về E1.
  · Verify: `$GRADLE :app:testDebugUnitTest` (test client với MockWebServer: 200/202, offline, 429)
- [ ] T005 [A] [FR-005, SC-002, SC-003, SC-004] Máy ảo hc-api36 + backend dev: đi hết E12 ⇒ xóa ⇒ `data_requests.done`; tắt `overlay_pause` rồi `fake_police --runs 3`;
  ảnh 100/200% + `ux-elder-reviewer` 0 Chặn/Cao. · Verify: evidence.md (lệnh + kết quả)
- [ ] T006 [AB] Bộ kiểm cuối ($PYTEST, ruff, Gradle, check-spec-trace) + evidence SC-001…SC-004. · Verify: lệnh thoát 0
