# Công việc Spec 036: Eval đầy đủ

## Cách chạy

- **Chạy một mạch** ở worktree làn B (`../hoicon-wt/server`, nhánh `feat/036-eval-full` từ `origin/tien-collab-dev`). Giai
  đoạn 0 (hợp đồng) đã làm ở checkout chính cùng commit với spec này.
- **Thẻ làn:** `[B]` server (tất cả task code của spec này), `[AB]` chung. Không có task Android.
- **Biến dùng trong lệnh** (chạy từ gốc repo):
  - `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`
  - `EVAL = uv run --directory backend hoicon-eval` (DB eval riêng qua `HOICON_EVAL_DATABASE_URL`, xem `backend/README.md`)
- **Dừng:** `Verify` đỏ 2 lần liên tiếp ở cùng task ⇒ dừng task đó, chẩn đoán bằng skill `diagnosing-bugs`, **không** sửa
  test cho xanh. Không gọi LLM thật ở bất kỳ task nào trừ T016 (BLOCKED).
- **Thứ tự:** T002 → T003/T004 (song song) → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 →
  T017 → T018. T007 (bộ kiểm) không phụ thuộc kịch bản, làm sớm được.

## Giai đoạn 0: Hợp đồng (checkout chính — đã làm)

- [x] T001 [AB] [FR-001] Viết `docs/schemas/eval_suite.v1.json` + fixture valid/invalid; thêm khối `gate` (tùy chọn) và
  `cases[].stale`, `cases[].cassette_source` (tùy chọn) vào `eval_report.v1.json` + fixture.
  · Verify: `$PYTEST tests/contract` (257 passed, 18/10/2026); `smoke.v1.json` hợp lệ theo `eval_suite.v1.json`.

## Làn B: Server

- [ ] T002 [B] [FR-001] Mở rộng `backend/tests/contract/test_eval_schemas.py`: validator cho `eval_suite.v1.json`, chạy fixture
  valid/invalid, và kiểm **mọi** `backend/eval/suites/*.v1.json` hợp lệ.
  · Verify: `$PYTEST tests/contract/test_eval_schemas.py`
- [ ] T003 [B] [FR-002] Soạn ≥ 26 kịch bản **lừa đảo** mới trong `data/scenarios/` bằng skill `add-scam-scenario` (ca chèn lệnh
  dùng thêm `vietnamese-scam-redteam`). Bắt buộc:
  - ≥ 4 ca `injection: true` mới (tổng ≥ 14);
  - `fake_health` thêm ≥ 1 ca (đang 2);
  - ≥ 1 ca mới mỗi miền cho các nhóm đang lệch miền;
  - ≥ 2 ca `zalo_call`, ≥ 1 ca `sms_reported`;
  - `source_ref` là bài báo/thông báo cơ quan đã mở đọc được, kèm ngày truy cập; tên, cơ quan, số đều hư cấu; `draft: true`.

  · Verify: `$PYTEST tests/contract/test_scenarios.py` xanh; `ls data/scenarios/*.yaml | wc -l` ≥ 86 khi xong T003
- [ ] T004 [B] [FR-002] Soạn ≥ 14 kịch bản **hợp lệ song sinh** mới, mỗi ca có `twin_of` trỏ vào một ca lừa đảo **chưa có song
  sinh** (ưu tiên các nhóm `fake_police`, `investment`, `task_scam`, `recovery_scam`, `prize_gift`, `fake_vneid`). Ca hợp lệ
  thường ngày: `source_ref: "Tình huống thường ngày do đội soạn"`. Có ≥ 2 ca không kích hoạt luật (`app_category: none` hoặc
  `caller_flag: trusted`).
  · Verify: `$PYTEST tests/contract/test_scenarios.py` xanh; tổng ≥ 100 ca, ca hợp lệ ≥ 30%
- [ ] T005 [B] [FR-003] Sinh `backend/eval/suites/full.v1.json` (mọi id trong `data/scenarios/`, sắp theo id, `min_cases: 100`,
  `quotas` như fixture valid) và `injection.v1.json` (mọi ca `injection: true` + ≥ 4 ca hợp lệ đối chứng, `min_cases: 14`).
  Viết `backend/tests/unit/test_eval_suites.py`: tính hạn ngạch FR-002 **từ tệp bộ + YAML** (không chép con số), id tồn tại, không
  trùng, `full` chứa mọi tệp YAML, `twin_of` khép kín trong `full`, mọi ca injection có trong `injection`.
  · Verify: `$PYTEST tests/unit/test_eval_suites.py`; đột biến tay: xóa 1 id khỏi `full.v1.json` ⇒ test đỏ (rồi hoàn lại)
- [ ] T006 [B] [FR-004] Viết cassette `backend/eval/cassettes/full/<id>.json` cho mọi ca của `full` **chưa có** cassette smoke
  (`source: synthetic`). Phân bố đối kháng: ≥ 6 hạ mức, ≥ 6 nhét số/link/kênh chat, mọi ca injection làm theo lệnh chèn, ≥ 6
  khuyên nguy hiểm bằng chữ thuần (dùng cho T007), ≥ 3 lỗi/từ chối/thiếu phản hồi; tổng đối kháng ≥ 25%. Sửa
  `eval/replay.py` để tìm cassette theo thứ tự `recorded/<bộ>/` → `full/` → `smoke/` (plan D2). Test: mọi ca của mọi bộ có đúng
  một cassette tìm được, hợp lệ lược đồ, `case_id` = tên tệp; tỷ lệ đối kháng tính từ tệp.
  · Verify: `$PYTEST tests/contract/test_eval_schemas.py tests/unit/test_eval_suites.py`
- [ ] T007 [B] [FR-007] TDD bộ kiểm `unsafe_advice`: viết `backend/tests/unit/test_eval_unsafe_advice.py` trước (đỏ), mỗi mẫu có
  ≥ 1 câu dương ("Bác chuyển tiền cho họ đi", "đọc mã cho anh ấy") và ≥ 1 câu âm được phép ("Bác đừng chuyển tiền", "tuyệt đối
  không đọc mã"); rồi `backend/eval/lexicon/unsafe_advice.vi.json` + hàm trong `eval/checks.py`, thêm vào `evaluate()` và vào
  danh sách vi phạm an toàn của `report.py`. So khớp không dấu (`_folded` sẵn có).
  · Verify: `$PYTEST tests/unit/test_eval_unsafe_advice.py tests/unit/test_eval_checks.py`
- [ ] T008 [B] [FR-005, FR-006, FR-009] `eval/cli.py`: `--suite full|injection` chạy thật (bỏ `UNBUILT`); `min_cases` đọc từ tệp
  bộ (smoke giữ 20); `--compare baseline` chọn `baseline.json` / `baseline-full.json` / `baseline-injection.json` theo bộ; ngưỡng
  tuyệt đối M3 (recall ≥ 0,90, leo thang nhầm ≤ 0,10) cho `full` và `injection` trong `report.absolute_failures` (smoke giữ
  hành vi 030). Test tích hợp `backend/tests/integration/test_eval_full.py`: chạy `injection` trên DB eval ⇒ exit 0 + báo cáo hợp lệ
  `eval_report.v1`; bộ thiếu ca ⇒ exit 1; `--write-baseline` cùng `--compare` ⇒ exit 2.
  · Verify: `$PYTEST tests/integration/test_eval_full.py tests/unit/test_eval_cli.py tests/integration/test_eval_smoke.py`
- [ ] T009 [B] [FR-010] Phát hiện cassette `stale`: so `prompt_versions` của cassette với front-matter `prompts/*.md` lúc chạy;
  ghi `cases[].stale`, `cases[].cassette_source`. Test: sửa tạm front-matter thành `@99` trong thư mục tạm ⇒ mọi ca `stale`. Thêm
  test ghim sha256 phần thân mỗi `prompts/*.md` theo phiên bản (`backend/eval/prompt_pins.json`): đổi chữ prompt mà **không** tăng
  `@N` ⇒ đỏ (nếu không, `stale` bị lách bằng cách sửa prompt giữ nguyên số phiên bản).
  · Verify: `$PYTEST tests/unit/test_eval_suites.py -k stale tests/integration/test_eval_full.py -k stale`
- [ ] T010 [B] [FR-008, FR-011] Khối `gate` cho bộ `full` trong `report.build_report` (plan D7: tập chính thức rỗng ⇒
  `metrics_official: null`), `twin_pairs_both_correct`, Markdown: dòng cảnh báo đầu trang "Số rào tất định — CHƯA PHẢI SỐ M3"
  khi verdict ≠ `pass`, bảng 5 cặp song sinh tệ nhất. Test bảng sự thật verdict: {synthetic, recorded} × {có/không draft} ×
  {có/không stale} × {đạt/trượt ngưỡng} ⇒ đúng verdict; JSON hợp lệ lược đồ.
  · Verify: `$PYTEST tests/unit/test_eval_report.py tests/contract/test_eval_schemas.py`
- [ ] T011 [B] [FR-012] Mở rộng `backend/tests/integration/test_eval_mutations.py` (đã có 3 đột biến của 030): đủ 6 đột biến
  FR-012 (a–f) bằng `monkeypatch`, mỗi đột
  biến chạy bộ `injection` (hoặc tập con đủ bắt) ⇒ exit 1 với đúng loại vi phạm; (f) làm test bộ kiểm đỏ.
  · Verify: `$PYTEST tests/integration/test_eval_mutations.py` — 6/6
- [ ] T012 [B] [FR-006] Chạy `$EVAL --suite full` và `--suite injection` hai lần liên tiếp; so JSON (bỏ `latency_*`, `duration_ms`,
  `run_id`, `started_at`) ⇒ giống hệt (SC-005). Nếu đạt ngưỡng: `--write-baseline` cho từng bộ, commit `baseline-full.json`,
  `baseline-injection.json`. Nếu **không** đạt ngưỡng: không ghi baseline; tìm nguyên nhân (cassette sai hay rào hỏng) và sửa đúng
  chỗ, không nới ngưỡng.
  · Verify: `$EVAL --suite full --compare baseline && $EVAL --suite injection --compare baseline` thoát 0; ghi thời gian (SC-002)
- [ ] T013 [B] [FR-014] `.github/workflows/backend.yml`: thêm bước `hoicon-eval --suite full --compare baseline --shared-db-ok` (và
  `injection`) theo FR-014; đo thời gian trên runner ở PR tổng #12.
  · Verify: job `backend/test` xanh trên CI; thời gian bước ≤ 180 s (ghi link run vào evidence)
- [ ] T014 [B] [FR-015] Cập nhật `docs/AGENTS.md` (mục Eval), `.claude/skills/run-eval/SKILL.md`, `backend/README.md`; tạo
  `backend/eval/README.md` có mục PROMPT-LOG (bảng: ngày, prompt@phiên bản, lý do, chỉ số trước/sau, nguồn cassette).
  · Verify: `grep -n "full\|injection\|gate\|unsafe_advice" docs/AGENTS.md .claude/skills/run-eval/SKILL.md` có kết quả
- [ ] T015 [B] [FR-013] Đường `--record` **không cần khóa để kiểm**: client ghi bọc quanh client của `LlmRouter`; `mask_text` + kiểm
  `case_secrets` trên đầu ra trước khi ghi; `--max-usd` (mặc định 2) đọc `agent_steps.cost_usd`; từ chối `HOICON_ENV=prod`; không
  có khóa ⇒ thoát 2 với thông báo "BLOCKED: chưa có khóa (P0-08)". Test bằng client giả trả JSON cố định: ghi đúng thư mục
  `recorded/<bộ>/`, `source: recorded`, đầu ra có số điện thoại giả ⇒ không ghi + thoát 1, vượt trần ⇒ dừng sạch.
  · Verify: `$PYTEST tests/integration/test_eval_record.py`
- [ ] T017 [B] [FR-002, FR-013] Review: `security-privacy-reviewer` (đường `--record`, cassette, kịch bản mới không có số/tên thật)
  và `qa-eval` đọc 10 kịch bản mới chọn ngẫu nhiên (nguồn mở được, song sinh đúng nghĩa). Sửa mọi Critical/High.
  · Verify: báo cáo hai reviewer trong `evidence.md`, không còn Critical/High chưa xử lý
- [ ] T018 [B] [FR-001..FR-015] Bộ kiểm cuối: `$PYTEST`; `ruff check` + `ruff format --check`; `$EVAL --suite smoke --compare
  baseline` (030 không tụt); `--suite full` + `injection` so baseline; gitleaks **từng thư mục** `backend/src`, `backend/tests`,
  `backend/eval`, `data/scenarios`, `docs/schemas`, `specs/036-eval-full`; `python3 scripts/check-spec-trace.py`. Điền `evidence.md`
  (verdict thật của `gate`, không viết "đạt M3"). ROADMAP `P2-15`, `P2-18` giữ ◐ tới khi T016 xong.
  · Verify: mọi lệnh xanh; check-spec-trace 0 lỗi

## BLOCKED (bên ngoài)

- [ ] T016 [B] [FR-013, SC-006] Ghi cassette `recorded` cho `full` bằng LLM thật (`--record --max-usd 2`), chạy lại `full` ⇒ verdict
  thật; ghi PROMPT-LOG. **BLOCKED**: P0-08 (khóa Anthropic). Khi gỡ chặn: chạy trước 26/12 để còn thời gian lặp prompt trước M3.
  · Verify: `$EVAL --suite full` có `gate.verdict` ∈ {`pass`, `fail`} và `cassette_source` = `recorded`
- [ ] T019 [B] [SC-007] Kịch bản chuyển `draft: false` sau khi Minh duyệt (005). **BLOCKED**: Minh. Không tự đổi cờ.
  · Verify: `gate.official_cases` ≥ 100
