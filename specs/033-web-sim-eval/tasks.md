# Công việc Spec 033: Web `/sim`, `/trace`, `/eval`

## Cách chạy

- **Chạy một mạch** ở worktree làn B (`../hoicon-wt/server`, nhánh `feat/033-web-sim-eval`). Giai đoạn 0 (hợp đồng) đã làm ở
  checkout chính cùng commit với spec này.
- **Thẻ làn:** `[B-api]` = `backend/**`; `[B-web]` = `apps/web/**`; `[AB]` chung. Không có task Android. Làm hết nhóm `[B-api]`
  của P1 trước, sinh client TS, rồi mới sang `[B-web]`. **Wave 3 (22/10):** thứ tự hai làn ở MASTER-PLAN §5 "Wave 3"; nếu Tiến
  duyệt đề xuất nới quyền ở đó thì `[B-web]` do **làn A** làm (chỉ `apps/web/**`, nhánh `feat/033-web-sim-eval-web`): T012 bắt đầu
  được ngay từ fixture `docs/schemas/fixtures/graph_topology.v1.valid.json`, T013–T015 sau `[B-api]` T011. Chưa duyệt ⇒ giữ như cũ.
- **Ưu tiên:** P1 = `/sim` + `/trace` (T002–T009, T011–T015, T017–T019). P3 = `/eval` (T010, T016): làm sau cùng; trễ thì đánh
  ✂ theo danh sách cắt của ROADMAP, ghi vào evidence, không làm vòng.
- **Biến dùng trong lệnh** (từ gốc repo):
  - `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`
  - `WEB = pnpm --dir apps/web`
  - Playwright cần API cổng 18000 + web 3100 chạy với `HOICON_SIM_ENABLED=true` và gia đình demo (`ops guardian_link --seed`).
- **Dừng:** `Verify` đỏ 2 lần liên tiếp ⇒ dừng task, chẩn đoán (`diagnosing-bugs`), không sửa test cho xanh. Không gọi LLM
  thật (mọi test dùng `llm: "replay"`; `live` chỉ thử không có khóa ⇒ `fallback`).

## Giai đoạn 0: Hợp đồng (checkout chính — đã làm)

- [x] T001 [AB] [FR-001] Viết `docs/schemas/{sim_run_request,sim_run,sim_scenarios,graph_topology}.v1.json` + fixture valid/invalid
  (dùng `$ref` tới `incident.v1#/$defs/state`, `elder_question.v1`, `scenario.v1#/properties/category`).
  · Verify: jsonschema + `referencing` trên mọi fixture (8 valid hợp lệ, 15 invalid bị từ chối, 18/10/2026); `$PYTEST tests/contract`
  257 passed

## Nhóm [B-api]

- [ ] T002 [B-api] [FR-001] `backend/tests/contract/test_sim_schemas.py`: chạy fixture của 4 lược đồ với `Registry` (mẫu
  `test_drill_schemas.py`).
  · Verify: `$PYTEST tests/contract/test_sim_schemas.py`
- [ ] T003 [B-api] [FR-002, FR-003] `config.py`: `sim_enabled: bool = False` (biến `HOICON_SIM_ENABLED`); `api/routers/sim.py` với
  phụ thuộc chung: cổng tắt ⇒ 404; phiên `hc_guardian` bắt buộc; gia đình không `is_demo` ⇒ 404; lệnh ghi có
  `require_same_origin`. `ops guardian_link --seed` tạo thêm **một thiết bị demo** cho gia đình demo (sự kiện cần `device_id`) nếu
  chưa có. Test `tests/integration/test_api_sim.py` (phần cổng): tắt ⇒ 404 mọi route; gia đình thật ⇒ 404; thiếu phiên ⇒ 401;
  sai `Origin` ⇒ 403. Kiểm `infra/compose.prod.yml` **không** đặt `HOICON_SIM_ENABLED` (test hạ tầng có sẵn ở `scripts/tests`).
  · Verify: `$PYTEST tests/integration/test_api_sim.py -k gate && python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py`
- [ ] T004 [B-api] [FR-004] Cờ `sim` trong state đồ thị và payload `notify_guardian`; `channels/guardian.py::send_to_guardian` thấy
  `sim` ⇒ chỉ ghi bộ mock, không gọi client thật, không trừ hạn mức. Test: `HOICON_ZALO_MODE=live` + sự cố sim ⇒ 0 lời gọi
  `LiveZaloClient` (client giả đếm lời gọi); sự cố thường của gia đình demo giữ hành vi cũ.
  · Verify: `$PYTEST tests/integration/test_api_sim.py -k zalo tests/integration/test_notify_guardian.py tests/integration/test_guardian_alert.py`
- [ ] T005 [B-api] [FR-005] `GET /v1/sim/scenarios` đọc `data/scenarios/*.yaml` (qua `eval.cases.load_case`), trả `sim_scenarios.v1`
  (không `elder_note`, không `source_ref`), sắp theo id. Test: hợp lệ lược đồ, đủ số tệp YAML, không chứa khóa ngoài lược đồ.
  · Verify: `$PYTEST tests/integration/test_api_sim.py -k scenarios`
- [ ] T006 [B-api] [FR-005, FR-006] `POST /v1/sim/runs`: `build_event(case)` ⇒ **cùng đường** với `post_events` (tách phần ghi
  `risk_events` + `IncidentService` + `_start_graph` của `routers/events.py` thành hàm service nếu chưa tách; `post_events` gọi lại
  hàm đó, hành vi không đổi) với thiết bị demo; `services/sim_service.py` giữ runtime replay theo plan D2. Kịch bản không kích
  hoạt luật ⇒ 200, `incident_id: null`, `note`. Ảnh container không có cassette (`.dockerignore` loại `backend/eval`) ⇒ trong
  container `replay` không khả dụng: trả `llm_mode: "fallback"` và ghi điều này vào `docs/setup/SIM.md` (sim là công cụ máy dev; gian
  trưng bày công khai là spec 050). Test: replay `fake_police_safe_account_002` ⇒ dãy `agent_steps.node` và mức cuối
  **bằng** lượt eval cùng ca (gọi `eval.runner` cho ca đó làm đối chứng); `live` không khóa ⇒ `llm_mode: "fallback"`; toàn bộ
  `tests/integration/test_api_events.py` vẫn xanh.
  · Verify: `$PYTEST tests/integration/test_api_sim.py -k runs tests/integration/test_api_events.py`
- [ ] T007 [B-api] [FR-007] `GET /v1/sim/runs/{incident_id}` (sự cố phải là sự cố sim của gia đình phiên, không ⇒ 404) và `POST
  /v1/sim/runs/{incident_id}/answer` đi qua **cùng hàm** với `routers/elder.py::submit_elder_answer` (tách thành service nếu cần;
  không nhận `note`). Tin người giám hộ lấy từ bản ghi mock theo thứ tự, đã che. Test: E8 đang chờ hiện đúng `elder_question.v1`;
  trả lời ⇒ đồ thị đi tiếp; quyết định qua `POST /v1/incidents/{id}/decision` bằng phiên đó ⇒ trạng thái cuối; phản hồi không chứa
  số điện thoại/h1/tên gói (quét bằng `case_secrets`).
  · Verify: `$PYTEST tests/integration/test_api_sim.py -k "view or answer" tests/integration/test_api_elder.py`
- [ ] T008 [B-api] [FR-008] Hạn mức: 10 lượt `POST /v1/sim/runs`/giờ/phiên, 3 lượt đang chạy/gia đình (429 + `Retry-After`);
  registry D2 tối đa 20 runtime, quá 60 phút thì bỏ. Test: lượt 11 ⇒ 429; lượt đang chạy thứ 4 ⇒ 429; runtime hết hạn ⇒
  `llm_mode: "fallback"` ở lần `answer` sau.
  · Verify: `$PYTEST tests/integration/test_api_sim.py -k limit`
- [ ] T009 [B-api] [FR-009] `GET /v1/graphs/incident` (không cổng, không đăng nhập) sinh `graph_topology.v1` từ `build_graph` đã
  biên dịch + bảng nhãn tiếng Việt và `step_nodes` (ví dụ `verification` ⇒ `verify`) đặt cạnh `incident_graph.py`. Test
  `tests/integration/test_api_graphs.py`: hợp lệ lược đồ; tập nút = nút của đồ thị biên dịch; nút không có nhãn ⇒ test đỏ (thêm
  nút giả bằng `monkeypatch`); `version` đổi khi cạnh đổi.
  · Verify: `$PYTEST tests/integration/test_api_graphs.py`
- [ ] T011 [B-api] [FR-001, FR-014] `bash scripts/gen-api-client.sh`; cập nhật `docs/API.md` (`/v1/sim/*`, `/v1/graphs/incident`,
  `/v1/eval/summary` nếu đã có), `docs/AGENTS.md` (topology, cờ `sim`).
  · Verify: `bash scripts/gen-api-client.sh && $WEB typecheck`

## Nhóm [B-web]

- [ ] T012 [B-web] [FR-011] `pnpm --dir apps/web add --save-exact @xyflow/react@12.12.0`; ghi lý do (plan D6, giấy phép MIT) vào
  thông điệp commit; component `src/components/trace-graph.tsx` nạp động (`next/dynamic`, `ssr: false`), bố cục tĩnh từ
  `graph_topology`, trạng thái nút (đã chạy / đang chờ người / lỗi / rơi về mẫu) bằng màu **và** biểu tượng + chữ, tôn trọng
  `prefers-reduced-motion`. Đo kích thước JS của `/incidents` trước/sau (không được tăng).
  · Verify: `$WEB typecheck && $WEB lint && $WEB build` (ghi kích thước route từ output build vào evidence)
- [ ] T013 [B-web] [FR-011] Trang `src/app/trace/[runId]/page.tsx`: sơ đồ + **bản chữ** (danh sách bước theo thứ tự, dùng lại
  `describeStep`) + chi tiết bước khi chọn nút; dữ liệu qua `GET /v1/runs/{id}/steps` + `useRunStream`; không phải của mình ⇒
  "Không tìm thấy". Link "Xem sơ đồ" từ `incidents/[id]`. Playwright `e2e/trace.spec.ts`: bản chữ đủ bước của run seed; chọn nút
  hiện chi tiết; bước mới qua SSE hiện ≤ 1 s; run của gia đình khác ⇒ "Không tìm thấy"; axe 0 lỗi; ảnh 360 px + 1280 px.
  · Verify: `$WEB e2e trace a11y`
- [ ] T014 [B-web] [FR-010] Trang `src/app/sim/page.tsx` theo FR-010 (3 cột / 3 thẻ có tab dưới 768 px, nhãn "MÔ PHỎNG", nhãn
  "kịch bản nháp", nút E8 ≥ 64 px, quyết định có xác nhận dùng lại câu chữ của trang chi tiết 027). API 404 ⇒ "Trang này chưa mở".
  Playwright `e2e/sim.spec.ts`: (a) `fake_police_safe_account_002` replay từ "Bắt đầu" tới quyết định "nghi lừa đảo" ≤ 5 thao
  tác, mọi bước hiện, có tin Zalo mô phỏng mở đầu công khai AI; (b) một ca hợp lệ không kích hoạt luật ⇒ thông báo `note`; (c) chạy
  (a) hai lần ⇒ cùng dãy bước và cùng chữ tin (SC-002); (d) quét DOM không có số điện thoại/h1/tên gói (SC-006); axe 0 lỗi; ảnh
  360 px + 1280 px.
  · Verify: `$WEB e2e sim a11y`
- [ ] T015 [B-web] [FR-010, FR-011] Thêm `/sim` và `/trace` vào `e2e/a11y.spec.ts` (tệp có sẵn của 027) và kiểm tương phản bằng
  token của 010 (không mã màu cứng).
  · Verify: `$WEB e2e a11y && python3 scripts/gen-design-tokens.py --check`

## P3 — `/eval` (cắt được)

- [ ] T010 [B-api] [FR-012] `GET /v1/eval/summary` (sau cổng FR-002): đọc `backend/eval/baseline*.json` đã commit, trả danh sách
  `{suite, baseline}` kèm `gate` nếu có (036). Test: cổng tắt ⇒ 404; không đọc `reports/`; JSON không có `run_id` của gia đình thật.
  **Lưu ý:** `.dockerignore` hiện loại cả `backend/eval` (dòng 23) và `backend/Dockerfile` chỉ chép các thư mục được liệt kê ⇒ ảnh
  backend của 012 không có baseline. Thêm ngoại lệ `!backend/eval/baseline*.json` (giữ loại `cassettes/`, `reports/`) + dòng `COPY`
  tương ứng, và test hạ tầng (`scripts/tests/test_deploy_vps.py`) kiểm cả hai.
  · Verify: `$PYTEST tests/integration/test_api_eval_summary.py`
- [ ] T016 [B-web] [FR-012] Trang `src/app/eval/page.tsx`: bảng chỉ số, theo nhóm/miền, dòng cảnh báo "Số rào tất định — CHƯA PHẢI
  SỐ M3" khi verdict ≠ `pass` hoặc không có `gate`. Playwright `e2e/eval.spec.ts` + axe + ảnh.
  · Verify: `$WEB e2e eval`

## Rà soát & nghiệm thu

- [ ] T017 [AB] [FR-013] `ux-elder-reviewer` trên ảnh + câu chữ cột "điện thoại của bác" và nhãn "MÔ PHỎNG";
  `security-privacy-reviewer` trên `routers/sim.py`, `sim_service.py`, cờ `sim` ở kênh Zalo, cổng. Sửa mọi Chặn/Critical/High.
  · Verify: báo cáo hai reviewer trong `evidence.md`, không còn mục chặn chưa xử lý
- [ ] T018 [AB] [FR-014] `docs/setup/SIM.md` (bật cổng trên máy dev, seed gia đình demo, sinh liên kết đăng nhập, chọn replay),
  `specs/033-web-sim-eval/quickstart.md` (kịch bản quay video 1280×720), `docs/DESIGN-SYSTEM.md` (3 trang web).
  · Verify: làm theo `docs/setup/SIM.md` từ DB trống tới `/sim` chạy được (ghi lệnh + kết quả vào evidence)
- [ ] T019 [AB] [FR-001..FR-014] Bộ kiểm cuối: `$PYTEST`; `ruff check` + `ruff format --check`; `$WEB typecheck lint build e2e`;
  `hoicon-eval --suite smoke --compare baseline` (đường events đã tách hàm); gitleaks **từng thư mục** `backend/src`,
  `backend/tests`, `apps/web/src`, `apps/web/e2e`, `docs/schemas`, `specs/033-web-sim-eval`; `python3 scripts/check-spec-trace.py`.
  Điền `evidence.md`; ROADMAP `P2-19` ◐ (☑ khi SC-007 có video hoặc `/eval` được ✂ có ghi chú).
  · Verify: mọi lệnh xanh; check-spec-trace 0 lỗi

## Làn H (ngoài code)

- [ ] T020 [AB] [SC-007] Quay một lượt `/sim` cho video Vòng 2 (P2-21) theo `quickstart.md`. Không phải task của Sonnet; đánh dấu
  khi đội quay xong.
  · Verify: tệp video + ghi chú trong `evidence.md`
