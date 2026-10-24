# Công việc Spec 031: Hồ sơ vụ việc

## Cách chạy

- **Chạy một mạch** ở worktree làn B (`../hoicon-wt/server`, nhánh `feat/031-case-file`). Giai đoạn 0 đã làm ở checkout chính.
- **Thẻ làn:** `[B-api]` = `backend/**`, `data/case_file/**`; `[B-web]` = `apps/web/**`; `[A]` Android (một task ghim sha);
  `[AB]` chung.
- **Biến:** `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache` · `WEB = pnpm --dir apps/web` ·
  `GRADLE = ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/opt/android-studio/jbr PATH="/opt/android-studio/jbr/bin:$PATH" ./apps/android/gradlew -p apps/android`
- **Số migration:** số kế tiếp sau head lúc thi công (`uv run --directory backend alembic heads`); 032 cũng thêm migration ⇒ ai
  merge sau thì đổi `down_revision` và ghi vào evidence.
- **Dừng:** `Verify` đỏ 2 lần ⇒ dừng task, chẩn đoán, không sửa test cho xanh. Không gọi LLM thật (test dùng `ReplayClient` /
  client giả).

## Giai đoạn 0: Hợp đồng (checkout chính — đã làm)

- [x] T001 [AB] [FR-001] Viết `docs/schemas/case_file.v1.json`, `case_file_action.v1.json` + fixture (2+3 valid, 7+3 invalid).
  · Verify: jsonschema trên mọi fixture (valid hợp lệ, invalid bị từ chối, 18/10/2026)

## Nhóm [B-api]

- [x] T002 [B-api] [FR-001] `backend/tests/contract/test_case_file_schemas.py` chạy fixture hai lược đồ.
  · Verify: `$PYTEST tests/contract/test_case_file_schemas.py`
- [x] T003 [B-api] [FR-002] Migration bảng `case_files` theo FR-002 + model `CaseFile` + `tests/integration/test_schema_<số>.py`
  (CHECK trạng thái, UNIQUE `incident_id`, CASCADE khi xóa sự cố/gia đình, SET NULL khi xóa thành viên).
  · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head && $PYTEST tests/integration/test_schema_<số>.py`
- [x] T004 [B-api] [FR-004, FR-011] `services/case_file_service.py::build_content(incident_id)` tất định: câu cố định mới ở
  `agents/texts.py` (nhãn transition, lý do, luật, câu hỏi/đáp E8, `local_fields`), hướng dẫn từ
  `data/case_file/report_guidance.vi.yaml` (`approved: false` ⇒ câu chung FR-011). Test TDD (viết trước, đỏ): kết quả hợp lệ
  `case_file.v1#/$defs/content`; không chứa `case_secrets` của sự cố seed; thiếu `verifications` ⇒ mảng rỗng; R2 ⇒ `caller_last3:
  null` nếu không có cuộc gọi.
  Thêm `COPY data/case_file /app/data/case_file` vào `backend/Dockerfile` (ảnh 012 chỉ chép các thư mục `data/` được liệt kê) và kiểm
  trong `scripts/tests/test_deploy_vps.py`.
  · Verify: `$PYTEST tests/unit/test_case_file_content.py && python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py`
- [x] T005 [B-api] [FR-005] Đoạn tóm tắt: prompt `agents/prompts/case_file.md` (front-matter `case_file@1`, mở đầu nêu "không đưa
  số, link, tên"), lời gọi `llm_router` hồ sơ `strong`, output có cấu trúc `{summary}`; lọc bằng `_UNSAFE_SUMMARY` (+ `unsafe_advice`
  nếu 036 đã merge), dài > 600 ⇒ mẫu. Test: client giả trả câu sạch ⇒ `summary_source = llm`; trả số/link/lời khuyên nguy hiểm ⇒
  `template`; quá hạn ⇒ `template`; không khóa ⇒ `template`.
  · Verify: `$PYTEST tests/unit/test_case_file_summary.py`
- [x] T006 [B-api] [FR-003, FR-006] Đồ thị: nút `case_file` + interrupt `await_case_approval` + cạnh theo plan §3; điều kiện bỏ qua
  (`is_drill`, cờ `sim`, eval); tin Zalo mẫu `case_file` (D7, `urgent=True`, khóa `{incident}:msg:case_file`, công khai AI, nhãn
  không áp cho diễn tập vì diễn tập không tới đây); nhãn nút cho topology của 033 nếu đã merge. Test
  `tests/integration/test_case_file_graph.py`: `scam` ⇒ 1 dòng `draft` + 1 tin; `safe`/`no_response` ⇒ 0; diễn tập `scam` ⇒ 0;
  chạy lại resume ⇒ không nhân bản tin hay dòng; `kill -9` giả (dựng lại runtime) ⇒ vẫn chờ đúng interrupt; tin mở đầu "Đây là trợ
  lý AI HỏiCon".
  · Verify: `$PYTEST tests/integration/test_case_file_graph.py tests/integration/test_incident_graph.py`
- [x] T007 [B-api] [FR-007] `GET/POST /v1/guardian/incidents/{id}/case-file` trong `api/routers/guardian.py`: phiên `hc_guardian`,
  gia đình khác ⇒ 404, `require_same_origin` cho POST, bảng chuyển trạng thái FR-007 (sai ⇒ 409), `approve`/`discard` resume đồ
  thị, `mark_sent`/`discard` đóng sự cố qua `IncidentService.transition()` (actor `guardian`). Test `test_api_case_file.py`: mọi cặp
  chuyển (SC-004), thân có trường lạ ⇒ 422, sai Origin ⇒ 403, gia đình khác ⇒ 404, quét phản hồi không có `case_secrets`.
  · Verify: `$PYTEST tests/integration/test_api_case_file.py tests/integration/test_guardian_incidents.py`
- [x] T008 [B-api] [FR-008] Job `case_autoclose` hằng ngày (đăng ký như job `retention` của 034): `case_open` không hoạt động 30
  ngày ⇒ resume `{"case_action": "discard", "actor": "system"}` nếu còn `draft`, rồi `closed` (actor `system`). Test đồng hồ giả: 29
  ngày ⇒ giữ; 31 ngày ⇒ đóng; hồ sơ `approved` ⇒ giữ `approved`, sự cố vẫn đóng.
  · Verify: `$PYTEST tests/integration/test_case_autoclose.py`
- [x] T009 [B-api] [FR-009] Hạn lưu + xóa: kiểm `case_files` bị xóa theo sự cố 12 tháng sau `closed_at` (CASCADE trong
  `retention_service`), và theo `purge_service` khi xóa gia đình. Bổ sung `DATA-MODEL.md` §6.
  · Verify: `$PYTEST tests/integration/test_retention.py tests/integration/test_purge_family.py`
- [x] T010 [B-api] [FR-013] `tests/integration/test_case_file_scenarios.py`: với ≥ 5 kịch bản lừa đảo (≥ 2 chèn lệnh) — dựng sự cố
  seed thật (UUID, gia đình demo), chạy đồ thị với `ReplayClient` của cassette smoke/full, quyết định `scam` ⇒ `case_file`; kiểm
  `content` hợp lệ lược đồ, không chứa `eval.cases.case_secrets(case)`, có `ai_label`; tin Zalo mở đầu công khai AI. Rồi hồi quy:
  `hoicon-eval --suite smoke --compare baseline` không đổi chỉ số.
  · Verify: `$PYTEST tests/integration/test_case_file_scenarios.py && uv run --directory backend hoicon-eval --suite smoke --compare baseline`
- [x] T011 [B-api] [FR-012] Văn bản đồng ý **gộp 031 + 032**. **Bản duy nhất (chốt 23/10/2026, Wave 4): `guardian_alerts`
  `2026.10-v4`, sha256 `afd2491512d6ecd7b89ff62cac56a54e8c6429ff741fdd440ca5f86ec6a2b72a`, `draft`, 160 từ, `consent_texts check` đạt**
  — là bản làn B đã sửa theo `ux-elder-reviewer` (mức Chặn: thiếu "HỏiCon không tự gửi cho cơ quan nào"; "máy bác hết được bảo vệ"
  nghe như bị hack), **thay** bản Opus soạn 22/10. Làn B giữ `manifest.json` (không đổi chữ khi chưa có quyết định mới); làn A đồng bộ
  chuỗi theo đúng sha này (T014). Câu phụ thuộc I4 là "Họ được báo nếu HỏiCon bị tắt." — Minh bác I4 ⇒ 032 T008 bỏ câu đó (còn 153 từ).
  > Đây là trợ lý AI HỏiCon.
  > Báo cho con bác biết khi bác cần giúp.
  > Khi thấy dấu hiệu lạ, HỏiCon nhắn Zalo cho con hoặc người thân bác đã chọn, để họ gọi hỏi thăm.
  > Họ biết có cuộc gọi lạ (lúc nào, bao lâu), bác mở loại ứng dụng nào, chọn gì trên màn nhắc. Số điện thoại chỉ hiện 3 số cuối.
  > Họ xem lại các lần nhắc trên web, và nhận tóm tắt mỗi tuần. Họ được báo nếu HỏiCon bị tắt.
  > Khi nghi bác bị lừa, HỏiCon soạn sẵn tờ ghi sự việc để bác trình báo. HỏiCon không tự gửi cho cơ quan nào.
  > Cuộc gọi lạ giữ tối đa 90 ngày, các lần nhắc tối đa 12 tháng. HỏiCon không bán thông tin của bác.
  > Muốn ngừng báo, bác nhờ người cài HỏiCon cho bác. HỏiCon vẫn nhắc bác dừng lại, chỉ không báo con nữa. Bác chưa đồng ý cũng không sao.
  · Verify: `$PYTEST tests/contract/test_consent_texts.py && uv run --directory backend python -m hoicon.ops.consent_texts check`
- [x] T012 [B-api] [FR-001, FR-014] `bash scripts/gen-api-client.sh`; `docs/API.md`, `docs/AGENTS.md` (nhánh `case_file`),
  `docs/PRIVACY-DPIA.md` (hồ sơ, ô tự điền).
  · Verify: `bash scripts/gen-api-client.sh && $WEB typecheck`

## Nhóm [B-web]

- [x] T013 [B-web] [FR-010] Trang `src/app/incidents/[id]/case-file/page.tsx` theo FR-010 (dùng `guardian-ui`, xác nhận trước khi
  duyệt/bỏ, in sau khi duyệt, ô tự điền ngoài form, không `localStorage`, câu "HỏiCon không tự gửi cho cơ quan nào"), CSS `@media
  print`, link từ `incidents/[id]`. Playwright `e2e/case-file.spec.ts` trên sự cố seed `case_open`: duyệt ⇒ hiện nút in; bỏ ⇒ sự cố
  đóng; điền ô tự điền rồi duyệt + in ⇒ `page.on("request")` không thấy giá trị nào trong URL/thân (SC-003); axe 0 lỗi; ảnh
  360/1280 px và bản in (`page.pdf` hoặc `emulateMedia print`).
  · Verify: `$WEB e2e case-file a11y`

## Nhóm [A]

- [x] T014 [A] [FR-012] Sau T011: đồng bộ chuỗi `guardian_alerts` trên Android theo văn bản gộp 031 + 032 (một lần cho cả hai
  spec — 032 T010 không lặp lại trừ khi chữ đổi), `res/values/consent_texts.xml` + `ConsentLedger.VERSION` theo `manifest.json`
  (cùng cách của 011 T018, Wave 2); chụp E4 ở 100% + 200% trên `hc-api36`, `ux-elder-reviewer` (160 từ ở 200%).
  · Verify: `$GRADLE :app:testDebugUnitTest --tests '*ConsentManifestPinTest*' :app:testDebugUnitTest :app:lintDebug`
  (`ConsentTextsPinTest` đã được thay bằng `ConsentManifestPinTest` ở Wave 2)

## Rà soát & nghiệm thu

- [x] T015 [AB] [FR-014] `security-privacy-reviewer` (lược đồ, content, ô tự điền, tin Zalo, hạn lưu) và `ux-elder-reviewer` (câu
  chữ trang + tin + văn bản đồng ý). Sửa mọi Chặn/Critical/High.
  · Verify: báo cáo trong `evidence.md`, không còn mục chặn chưa xử lý
- [ ] T016 [AB] [FR-001..FR-014] Bộ kiểm cuối: `$PYTEST`; `ruff`; `$WEB typecheck lint build e2e`; eval smoke so baseline; gitleaks
  **từng thư mục** `backend/src`, `backend/tests`, `apps/web/src`, `docs/schemas`, `docs/legal`, `data/case_file`,
  `specs/031-case-file`; `check-spec-trace`. Điền `evidence.md`; ROADMAP `P2-16` ◐ (☑ khi SC-007 có người thật hoặc Minh chấp nhận).
  · Verify: mọi lệnh xanh; check-spec-trace 0 lỗi

## BLOCKED (bên ngoài)

- [ ] T017 [AB] [SC-007] Một người giám hộ thí điểm duyệt + in hồ sơ của một sự cố **demo** (gia đình `is_demo`, dữ liệu hư cấu —
  không dùng diễn tập, D6), nói lại nội dung. **BLOCKED**: thí điểm (029 giai đoạn 2).
  · Verify: ghi chú phỏng vấn ngắn trong `evidence.md`
- [ ] T018 [B-api] [FR-011] Minh duyệt `report_guidance.vi.yaml` (`approved: true`) kèm nguồn chính thức. **BLOCKED**: Minh.
  · Verify: test "bản prod chỉ hiện hướng dẫn đã duyệt" xanh với `approved: true`

## Wave 4 (23/10/2026) — FR-015 hướng dẫn trình báo lên web; plan D11 (`fast`)

Hợp đồng đã có: `case_file.v1.guidance` (tùy chọn, `approved=false` ⇒ `steps` rỗng) + fixture. Test đỏ trước.

- [x] T019 [B-api] [FR-015] `case_file_service.load_guidance()` (đọc YAML một lần, kiểm cấu trúc lúc khởi động) + route GET hồ sơ gửi
  `guidance`. Test `tests/integration/test_api_case_file.py`: tệp `approved: false` ⇒ `steps == []`, có `fallback_vi`; tệp thử
  `approved: true` (monkeypatch đường dẫn) ⇒ đủ bước đúng thứ tự; phản hồi hợp lệ `case_file.v1`; không có dãy ≥ 4 chữ số trong
  `guidance`. Sửa `spec.md` FR-005 đã ghi `fast` — không đổi mã router. Sinh lại client TS.
  · Verify: `$PYTEST tests/integration/test_api_case_file.py tests/contract -q && bash scripts/gen-api-client.sh && $WEB typecheck`
- [ ] T020 [B-web] [FR-015] Trang `src/app/incidents/[id]/case-file/page.tsx`: khối "Các bước nên làm" (danh sách có số thứ tự khi
  `approved`, chỉ câu chung khi chưa duyệt), nằm ngoài vùng in dữ kiện vụ việc; in (`@media print`) vẫn gồm khối này ở cuối.
  Playwright `e2e/case-file.spec.ts` hai fixture (chưa duyệt / đã duyệt), axe 0 lỗi, ảnh 390/1440; `ux-elder-reviewer` đọc chữ.
  Phụ thuộc T019. · Verify: `$WEB typecheck && $WEB lint && $WEB e2e case-file a11y`
