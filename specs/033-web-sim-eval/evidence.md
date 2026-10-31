# Bằng chứng nghiệm thu Spec 033: Web `/sim`, `/trace`, `/eval`

- **Trạng thái (18/10/2026)**: chỉ có spec/plan/tasks và hợp đồng (T001). **Chưa code.**
- **Nguồn số dự kiến**: máy dev (API 18000 + web 3100, Playwright Chromium), chế độ `replay`. Không có số máy thật hay VPS.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 toàn luồng trên web | ≤ 5 thao tác, bước hiện ≤ 1 s | Playwright | Playwright `sim.spec.ts` (fixture hợp đồng): Bắt đầu → trả lời → quyết định = 4 thao tác; bước hiện từ SSE ≤ 1 s (`trace.spec.ts`) | ĐẠT (e2e dùng fixture, chưa đo với API thật) |
| SC-002 tất định | hai lượt replay giống nhau | Playwright | `sim.spec.ts` "chạy hai lần": hai lượt cùng dãy bước và cùng chữ tin (bỏ giờ) | ĐẠT |
| SC-003 cô lập | cổng, chỉ demo, Zalo mock ép, hạn mức | pytest | `test_api_sim.py` (cổng 404 khi tắt, gia đình thật 404, Zalo mock ép, hạn mức) + rà soát bảo mật T009 (cổng không bao giờ bật ở prod) | ĐẠT |
| SC-004 tiếp cận | axe 0 lỗi; bản chữ trace đủ bước | Playwright + axe | axe 0 lỗi nghiêm trọng ở 390/768/1440 (`sim`, `trace`), `a11y.spec.ts` 360/768/1280 + chữ 200%; bản chữ đủ bước | ĐẠT |
| SC-005 đúng đồ thị | topology = đồ thị biên dịch | pytest | `test_api_graphs`/topology khớp đồ thị biên dịch (pytest toàn bộ xanh 2881) | ĐẠT |
| SC-006 không PII | 0 số/h1/tên gói trong API + DOM | pytest + Playwright | `sim.spec.ts` "DOM không có số điện thoại…" + `test_api_sim.py` không PII | ĐẠT |
| SC-007 video | một lượt quay dùng được | đội quay | — | BLOCKED (P2-21) |
| SC-008 nhận ra được | 100% kịch bản có `title_vi` đúng bảng; `/trace` sim có băng, thật không; `sim.*` ≥ 7:1 | pytest + Playwright + `gen-design-tokens.py --check` | `test_sim_titles.py` (18 nhóm), `trace.spec.ts` (băng có/không), `sim.fg` 9,28:1 trên trắng, 8,49:1 trên nền sim | ĐẠT |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| jsonschema + `referencing`: fixture 4 lược đồ (8 valid, 15 invalid) | valid hợp lệ, invalid bị từ chối |
| `uv run --directory backend pytest -q tests/contract` | 257 passed (lược đồ mới chưa có test riêng — T002) |

## Wave 3 — [B-api] T002–T009, T011 (làn B, 22/10/2026)

- **T002–T009 ĐẠT:** `tests/contract/test_sim_schemas.py` (9), `tests/integration/test_api_sim.py` (22), `test_api_graphs.py` (5). Cổng tắt ⇒ 404 cả khi chưa đăng nhập; gia đình thật ⇒ 404; thiếu phiên ⇒ 401; sai `Origin` ⇒ 403; `compose.prod.yml` không đặt cổng; 0 lời gọi tới client Zalo với `ZALO_MODE=live`; một lượt `replay` của `fake_police_safe_account_002` có dãy `agent_steps.node` và mức **bằng lượt eval cùng ca**; hạn mức 10/giờ và 3 đồng thời ⇒ 429 + `Retry-After`; runtime hết hạn ⇒ `fallback`.
- **T011 ĐẠT:** `scripts/gen-api-client.sh` sinh lại `schema.d.ts`; `pnpm --dir apps/web typecheck` xanh; `docs/API.md`, `docs/AGENTS.md`, `docs/setup/SIM.md` cập nhật.
- **Lệch so với chữ của task (quyết định kỹ thuật, cần Opus cân nhắc sửa plan):**
  1. Mỗi lượt `POST /runs` tạo MỘT thiết bị demo riêng (nhãn `sim:<kịch bản>`, cũng là dấu "sự cố mô phỏng" bền, không cần migration) thay vì một thiết bị dùng chung, vì dùng chung thì `correlate_event` gom hai kịch bản chạy cùng lúc vào một sự cố. Vì vậy `ops guardian_link --seed` KHÔNG tạo thêm thiết bị (T003).
  2. "Bộ ghi mock" của tin người giám hộ là chính `jobs.payload` (đã che PII, `sim: true`); `send_to_guardian` trả `"simulated"` trước khi chạm `messages_out` hay client Zalo.
  3. Đồ thị lượt mô phỏng khởi động tại chỗ bằng runtime phát lại (`ingest_events(defer_graph=True)` rồi `start_prepared(sim=True)`), không qua job `start_graph`; sự kiện nhận id mới mỗi lượt (`build_event` cho id tất định theo kịch bản nên chạy lại sẽ trùng).
  4. `pending_question.expires_at` lấy từ hẹn giờ `ask_elder`, thiếu ⇒ +60 giây.
- **Ngoài quyền:** dòng ROADMAP của 033 (cấm sửa ROADMAP).

## Wave 3 — [B-web] T012–T015 (làn B, 22/10/2026)

- **T012 ĐẠT:** `@xyflow/react@12.12.0` (MIT, ghim đúng phiên bản; lý do ở plan D6) chỉ nạp động (`next/dynamic`, `ssr: false`) ở `/sim` và `/trace`. Kích thước JS gzip trước/sau: tổng chunk 202.572 B → 283.994 B (xyflow nằm trong chunk riêng của hai trang mới); trang `/incidents` **không đổi** 11.899 B (đo bằng client-reference-manifest sau `pnpm build`).
- **T013 ĐẠT:** `/trace/[runId]` = sơ đồ (bố cục tĩnh dọc từ `graph_topology`) + bản chữ + chi tiết khối; trạng thái nút bằng màu token + biểu tượng + chữ; lượt nhà khác/404 ⇒ "Không tìm thấy"; link "Xem sơ đồ các bước" ở trang chi tiết sự cố. `e2e/trace.spec.ts` (8 test): đủ bước, chọn khối, bước SSE mới < 1 s, 404, sơ đồ lỗi vẫn có bản chữ, axe + ảnh 390/768/1440.
- **T014 ĐẠT:** `/sim` đủ 3 cột (≥ 1024 px) / 3 thẻ có tab (< 1024 px), nhãn "MÔ PHỎNG", nhãn "kịch bản nháp", nút E8 ≥ 64 px, quyết định có xác nhận (dùng lại câu chữ 027 qua `lib/decision-copy.ts`), API 404 ⇒ "Trang này chưa mở". `e2e/sim.spec.ts` (10 test): (a) lừa đảo từ Bắt đầu tới "nghi lừa đảo" trong 4 thao tác, tin mở đầu công khai AI; (b) ca hợp lệ ⇒ `note`; (c) chạy hai lần cho cùng bước + chữ tin; (d) DOM không có số điện thoại/h1/tên gói; 404/429; axe + ảnh 390/768/1440. **Giới hạn trung thực:** e2e dùng fixture hợp đồng chặn mạng (như 027), nên (c) chứng minh giao diện, còn tính tất định của bước nằm ở `test_api_sim.py` (lượt replay = lượt eval); chưa chạy e2e với API thật.
- **T015 ĐẠT:** `/sim` và `/trace` thêm vào `e2e/a11y.spec.ts` (360/768/1280 + chữ 200%); `gen-design-tokens.py --check` exit 0; không mã màu cứng ngoài nét cạnh sơ đồ (`#1f3a5f` = token brand-navy, vì React Flow nhận giá trị chứ không nhận lớp Tailwind).
- Toàn bộ e2e web: **86 passed, 1 skipped (live)**; `pnpm typecheck`, `lint`, `build` xanh. Ảnh: `~/hoicon-evidence/033-sim-trace/{sim,trace}-{390,768,1440}.png`.
- **`ux-elder-reviewer` (T013/T014):** 0 Chặn, 4 Cao đều SỬA (chữ sơ đồ quá nhỏ ⇒ khoảng cách hàng + chiều cao theo số hàng + không thu nhỏ; "gặp lỗi" mâu thuẫn bản chữ khi có `fallback_used`; lưới 3 cột bắt đầu từ 1024 px thay vì 768 px; canvas bắt thao tác chạm ⇒ tắt kéo/thu phóng). Trung bình đã sửa: chú thích ký hiệu `aria-hidden` + bỏ tiếng Anh khỏi dòng chính, tiêu đề + vùng đọc bước mới cho danh sách, bước không có khối không còn là nút, khối "Kết thúc" theo trạng thái lượt, nút trả lời `text-title`, "Nghe lại câu hỏi" (đọc to), trạng thái rỗng sau khi bác trả lời, nhãn chế độ chạy dễ hiểu, thông báo 404 bớt kỹ thuật, báo mất kết nối khi thăm dò, banner dính + biểu tượng, "(mô phỏng)" ở cột AI. **Chưa sửa, cần Opus/hợp đồng:** tên kịch bản tiếng Việt trong ô chọn (cần `title_vi` trong `sim_scenarios.v1`), banner dùng màu diễn tập (cần token màu riêng cho mô phỏng), `/trace` mở từ lượt mô phỏng chưa có nhãn (cần cờ `is_sim` trong hợp đồng), đồng bộ giờ tin Zalo mock với giờ bước, chữ hoa đầu `describeStep`, mẫu tab đủ phím mũi tên.

## Wave 3 — T010 (P3, `GET /v1/eval/summary`), 23/10/2026

- **T010 ĐẠT:** `routers/eval_summary.py` sau cổng FR-002 và phiên demo (như `/v1/sim/*`); chỉ đọc `backend/eval/baseline*.json` (không `reports/`, không `cassettes/`); `gate.verdict = provisional` + lý do khi cassette `synthetic` hoặc còn kịch bản `draft` (đúng với baseline hiện tại: số rào tất định, **chưa phải số M3**). `tests/integration/test_api_eval_summary.py` (4): cổng tắt ⇒ 404, gia đình thật ⇒ 404, chỉ số đúng baseline, tệp `reports/` chứa `RUN-CANARY` không bao giờ xuất hiện. Hạ tầng: `.dockerignore` thêm ngoại lệ `!backend/eval/baseline*.json` (cassettes/reports vẫn loại), `backend/Dockerfile` `COPY backend/eval/baseline*.json`, test `test_deploy_vps.py`. Client TS sinh lại; `docs/API.md` cập nhật.
- **Không làm:** T016 (trang web `/eval`, nằm trong danh sách cắt).

## Wave 6 — T021 (làn B, 24/10/2026)

- **T021 ĐẠT**: `SCENARIO_TITLE_VI` (18 nhóm, đúng chữ FR-015) + `title_vi(case_id, category)` ở `sim_service`; `GET /v1/sim/scenarios` luôn gửi `title_vi`; `GET /v1/runs/{id}/steps` luôn gửi `is_sim` (join thiết bị của sự cố, nhãn `sim:`).
  Test đỏ trước (8 đỏ: thiếu `SCENARIO_TITLE_VI`, thiếu `title_vi`, thiếu `is_sim`) → xanh: `test_sim_titles.py` (mọi enum `category` của `scenario.v1.json` có nhãn; `fake_police_safe_account_002` ⇒ "Giả danh công an · ca 2"; nhóm lạ ⇒ KeyError), `test_api_sim.py`, `test_api_runs.py` (`is_sim` false/true), `tests/contract`: 340 passed. Client TS sinh lại, `pnpm typecheck` sạch, ruff sạch.

## Wave 6 — T022 (làn B, 24/10/2026)

- **T022 ĐẠT**: ô chọn kịch bản hiện `title_vi` (mã chỉ ở `title` của `<option>` và dòng "Mã kịch bản: …"); `SimBanner` dùng chung cho `/sim` và `/trace` (`/trace` hiện băng khi `is_sim`, `useRunStream` trả `isSim`); token `sim.*` (`#0A4A78`/`#EEF6FC`/`#1F76B5`, xanh dương, chữ trên trắng 9,28:1, trên nền sim 8,49:1, viền 4,86:1; cách màu hue của diễn tập và mọi mức rủi ro ≥ 30°, có test `SimHueTest`).
  3 mục Thấp: chữ hoa đầu chi tiết `describeStep`, tab `/sim` đủ ←/→/Home/End (vòng tròn, `tabIndex` chỉ ở tab chọn), giờ tin Zalo mô phỏng lấy theo giờ bước tạo tin (`fast_alert`→`fast_alert`, `detail`→`intervention`; không khớp thì giữ `at` của tin).
  Đỏ trước: 5 e2e đỏ trên bản build cũ (ô chọn, giờ tin, phím tab, chữ hoa, băng /trace) → sau `pnpm build`: `e2e sim trace a11y` **52 passed**; `gen-design-tokens.py --check` OK; `unittest discover scripts/tests` 114 OK (7 skipped); typecheck + lint sạch. Ảnh 390/768/1440 ở `~/hoicon-evidence/033-sim-trace/`.
- **Lưu ý cho người tích hợp**: `gen-design-tokens.py` sinh lại `Tokens.kt` (thêm `Sim*`) của Android — kiểm Gradle khi gộp. Màu "Kịch bản nháp" đổi từ màu diễn tập sang `sim.*` (màu diễn tập chỉ cho diễn tập).

## Wave 6 — T023 (làn B, 24/10/2026)

- **T023 ĐẠT**: `retention_service.purge_sim_devices` (và khóa `sim_devices` trong báo cáo `run_retention`): xóa thiết bị nhãn `sim:` tạo > 24 giờ mà mọi sự cố của nó đã đóng > 24 giờ (không có sự cố ⇒ theo tuổi thiết bị; sự cố còn mở ⇒ giữ). Sự cố không bị xóa (`device_id` SET NULL). Hằng `SIM_DEVICE_TTL` đứng ngoài `RETENTION` vì bảng §6 của DATA-MODEL là dữ liệu thật (test `RETENTION` so khớp tập khóa).
  Đỏ trước (5 đỏ, thiếu hàm) → `test_sim_cleanup.py` 6 passed (23 giờ giữ, 25 giờ xóa, không nhãn/`xsim:`/nhãn khác không đụng, sự cố còn mở giữ, dry-run, tiền tố khớp `sim_service`) + `test_retention.py` vẫn xanh (26 passed cùng lượt).
- **Hệ quả cần biết**: sau khi dọn, `/trace` của lượt sim cũ > 24 giờ không còn băng MÔ PHỎNG (`is_sim` suy từ nhãn thiết bị — plan D9) và `/v1/sim/runs/{id}` trả 404. Gia đình vẫn `is_demo`. Muốn giữ cờ bền ⇒ cần cột/migration (quyết định phạm vi, không làm ở đây).
- Chưa cập nhật `docs/DATA-MODEL.md` §6 / `PRIVACY-DPIA.md` (cấm `docs/**` ở Wave 6): thiết bị demo `sim:` 24 giờ — việc của người có quyền sửa docs.

## Wave 6 — T017, T019, T024 (làn B, 24/10/2026)

- **T017 ĐẠT (phần UX + bảo mật; phần [A] không có)**: `ux-elder-reviewer` trên ảnh `~/hoicon-evidence/033-sim-trace/` + mã: 0 Chặn, 3 Cao, 6 Trung bình, 4 Thấp. **Cao đã xử lý**: (1) sơ đồ `/trace` 390 px bị cắt mép trái ⇒ sơ đồ nay trong khung cuộn ngang `min-w-[500px]` (test `390 px: sơ đồ không bị cắt mép trái`); (2) thiếu ảnh `/trace` có băng ⇒ thêm `trace-sim-banner-1440.png` (e2e); (3) "giờ tin Zalo khớp giờ bước" lệch trong ảnh vì fixture hợp đồng `run_steps.v1.valid.json` KHÔNG có bước `fast_alert` ⇒ mã rơi về giờ `at` của tin (đồng hồ DB); với dữ liệu thật đồ thị luôn ghi bước này — để nguyên, ghi nhận.
  Đã sửa thêm: nút radio `shrink-0`, tab `min-h-16`, bỏ hậu tố "(kịch bản nháp)" trong `<option>` (chip bên dưới đã báo). **Chưa sửa** (chủ Tiến): băng `sticky` chiếm nhiều chỗ ở 390 px/chữ 200%; câu hỏi E8 dài ~30 từ và chưa tự đọc to (luật 15; câu nằm ở mẫu 024); chưa có ảnh 390/768 tab "Điện thoại của bác"; `opacity-60` nút khi đang gửi; xưng hô "bác"/"Mẹ" (đã biết, cần Opus); tiêu đề bước "người thân chưa trả lời" viết thường khi alias trống.
  Bảo mật `routers/sim.py`, `sim_service.py`, cờ `sim` Zalo, cổng: nằm trong rà soát T009 của 037 (0 Critical/High; cổng 404 trước xác thực, `HOICON_SIM_ENABLED` không có ở prod, nhãn `sim:` do client bị đổi thành `sim-`, tin sim không tới Zalo) — xem evidence 037.
- **T019 ĐẠT (trừ ROADMAP)**: pytest toàn bộ **2881 passed, 22 skipped, 1 xfailed** (xfail = lệch hợp đồng error.v1, 037 T013); ruff check + format sạch; web `typecheck lint build e2e` **118 passed, 3 skipped** (3 test live cần `HOICON_E2E_LIVE=1`); `hoicon-eval` smoke 20 / full 110 / injection 17: recall 100%, báo nhầm 0%, vi phạm 0, công khai AI 100%, không lệch baseline (chạy trên Postgres tạm `hoicon-db-eval-w6` cổng 15434 vì không được đọc mật khẩu DB dev; số vẫn là số rào tất định trên cassette synthetic, chưa phải số M3); gitleaks từng thư mục sạch (riêng `docs`/`docs/schemas` luôn 1 dương tính giả đã biết: sha256 chuỗi rỗng trong fixture "invalid"); `check-spec-trace` 25 spec 0 lỗi; `alembic heads` = 0012 (1 head). **Không làm**: ROADMAP `P2-19` (cấm sửa ROADMAP ở Wave 6) — người có quyền cập nhật.
- **T024 ĐẠT**: bảng SC ở đầu tệp đã điền (SC-001…SC-006 từ pytest/Playwright; e2e dùng fixture hợp đồng, ghi rõ) + SC-008.

## Lượt 7 — T016 `/eval` (P3) và T018 một phần (làn B, 24/10/2026)

- **T016 ĐẠT (có hạn chế)**: trang `/eval` (`src/app/eval/page.tsx`) đọc `GET /v1/eval/summary`: mỗi bộ kiểm một bảng chỉ số tiếng Việt (số ca, recall, báo nhầm, vi phạm an toàn, công khai AI, dùng câu soạn sẵn, thời gian, chi phí), dòng "Số rào tất định — CHƯA PHẢI SỐ M3" (+ lý do) khi `gate.verdict ≠ recorded`, băng MÔ PHỎNG (`SimBanner`), trạng thái 404 ("Trang này chưa mở"), rỗng và lỗi. Đỏ trước (6 e2e đỏ khi chưa có trang) → `e2e eval` 6 passed (axe 0 lỗi nghiêm trọng, không tràn ngang, ảnh 390/768/1440 `~/hoicon-evidence/033-sim-trace/eval-*.png`, đã xem ảnh 390). **Hạn chế**: "theo nhóm/miền" chưa làm — API hiện chỉ trả số cấp bộ kiểm (không có số theo nhóm thủ đoạn); thêm cần mở rộng `/v1/eval/summary` (chọn: tính từ `cases` của baseline) — quyết định phạm vi, ghi lại.
- **T018 vẫn CHƯA TICK**: xem evidence 037 (Lượt 7 — T021): `SIM.md` xong + đã chạy từ DB trống; còn `quickstart.md` và DESIGN-SYSTEM (ngoài quyền).

## T018 xong (nhà điều phối, 24/10/2026)

- `docs/setup/SIM.md` (làn B, đã chạy từ DB trống — mục Lượt 7) + `quickstart.md` (kịch bản quay 1280×720) + `docs/DESIGN-SYSTEM.md` mục "Web mô phỏng và đánh giá (spec 033)". Verify của task (chạy theo SIM.md từ DB trống) do làn B đã ghi ở trên.
- **T016 hạn chế "theo nhóm/miền"**: chấp nhận ở mức hiện tại (FR-012 là P3, nằm trong danh sách cắt; số eval hiện là số rào tất định, chia nhỏ theo nhóm chưa có ý nghĩa). Làm khi có cassette `recorded` (P0-08) — ghi ở ROADMAP "Ghi chú".
