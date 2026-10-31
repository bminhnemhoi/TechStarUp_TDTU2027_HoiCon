# Kế hoạch Spec 033: Web `/sim`, `/trace`, `/eval`

**Mã**: `033-web-sim-eval` · **ROADMAP**: `P2-19` · **Làn**: B (nhóm **[B-api]** rồi **[B-web]**) · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Chỉ gia đình `is_demo`, kịch bản hư cấu; phản hồi theo lược đồ đóng (`additionalProperties: false`), không có h1/tên gói/lời kể |
| III. LLM chỉ nâng | Sim chạy **đồ thị thật**, không có đường tắt; `replay` dùng cùng `LlmRouter` như eval |
| IV. Công khai AI | Lược đồ `sim_run.v1` bắt mọi tin mở đầu bằng "Đây là trợ lý AI HỏiCon" |
| V. Hợp đồng trước | 4 lược đồ + fixture đã viết ở giai đoạn 0 |
| VI. UX | Cột "điện thoại của bác" giữ chuẩn app (nút ≥ 64 px, chữ lớn); phần còn lại chuẩn web người giám hộ của 027; axe 0 lỗi |
| VII. Bằng chứng | Nhãn "MÔ PHỎNG"; `/eval` in verdict của 036, không tự tính lại |
| VIII. Ít code | Tái dùng `build_event`, `ReplayClient`, đường `/v1/events`, hàm trả lời E8, route quyết định, `useRunStream`, `describeStep`, `guardian-ui` |

## 2. Quyết định

| # | Quyết định | Lý do | Phương án bỏ |
|---|---|---|---|
| D1 | Đăng nhập = phiên `hc_guardian` của người giám hộ gia đình demo (027) | Không thêm cơ chế xác thực; quyết định dùng lại route có sẵn | Mật khẩu sim riêng; mở công khai |
| D2 | `replay`: mỗi lượt sim giữ **một** `IncidentRuntime` (deps có `ReplayClient(case)`) trong bộ nhớ, khóa theo `incident_id`, sống 60 phút, tối đa 20; mọi `answer`/`resume` của lượt đó đi qua runtime này. Mất (khởi động lại) ⇒ chạy tiếp bằng runtime mặc định và báo `llm_mode: "fallback"` | Con trỏ cassette nằm trong `ReplayClient`; một tiến trình (ADR-002) nên bộ nhớ là đủ; không đụng lõi `LlmRouter` | Chọn client theo state trong `LlmRouter` (sửa lõi tác tử); dựng lại client mỗi lần (con trỏ về 0 ⇒ sai câu trả lời) |
| D3 | Hẹn giờ T1/T2/T3 của sự cố sim vẫn chạy bằng worker thường | Sau `await_guardian` không còn lời gọi LLM (chỉ mẫu tin), nên vẫn tất định | Tắt hẹn giờ cho sim (đồ thị khác bản thật) |
| D4 | Tin sự cố sim ép đi bộ ghi mock bằng cờ `sim` trong state/payload, không theo `families.is_demo` | Không làm hỏng phép đo bot dev thật dùng gia đình demo (002 T024) | Ép mọi gia đình demo |
| D5 | Sơ đồ sinh từ `build_graph(...).get_graph()` qua `GET /v1/graphs/incident`; nhãn tiếng Việt ở bảng cố định cạnh đồ thị | 031 sẽ thêm `case_file`; chép tay sẽ lệch | Tệp JSON chép tay trong web |
| D6 | `@xyflow/react` **12.12.0** (MIT, phát hành 24/09/2026, ghim đúng phiên bản) chỉ dùng ở `/trace` và `/sim`, nạp động (`next/dynamic`, `ssr: false`) | MASTER-PLAN chọn xyflow; nạp động để trang danh sách 027 không nặng thêm | Vẽ SVG tay (tốn công, kém tương tác); `reactflow` 11 (tên gói cũ) |
| D7 | Bản chữ của trace là nội dung chính cho trình đọc màn hình; canvas `aria-hidden` kèm mô tả tóm tắt | Canvas kéo-thả không đọc được bằng TalkBack/NVDA | Chỉ có canvas |
| D8 | `/eval` đọc baseline đã commit qua API sau cổng | `reports/` bị git bỏ qua; baseline không có dữ liệu người dùng | Đọc tệp từ web lúc build (vượt ra ngoài gói `apps/web`) |

## 3. Luồng `/sim`

```
BGK (phiên người giám hộ demo) ─ POST /v1/sim/runs {scenario_id, llm} ─▶ sim.py
   build_event(case) ─▶ cùng hàm ingest của /v1/events ─▶ IncidentService + đồ thị (family demo, cờ sim)
   ◀─ sim_run.v1 (incident_id, run_id) ── web mở EventSource /v1/runs/{run_id}/stream (025, cookie)
BGK trả lời thay bác ─ POST /v1/sim/runs/{id}/answer ─▶ cùng hàm của routers/elder.py ─▶ runtime replay (D2)
BGK quyết định thay con ─ POST /v1/incidents/{id}/decision (route 027/023 có sẵn)
web thăm dò GET /v1/sim/runs/{id} mỗi 2 s khi trang hiện (tin Zalo mô phỏng, câu hỏi E8 đang chờ)
```

## 4. Bản đồ file

| Nhóm | File | Thay đổi |
|---|---|---|
| chung | `docs/schemas/{sim_run_request,sim_run,sim_scenarios,graph_topology}.v1.json` + fixtures | mới (giai đoạn 0, đã làm) |
| B-api | `backend/tests/contract/test_sim_schemas.py` | mới |
| B-api | `config.py` (`sim_enabled`), `api/routers/sim.py`, `api/routers/graphs.py`, `api/main.py` | mới / sửa |
| B-api | `services/sim_service.py` (registry runtime replay D2, hạn mức), tách hàm ingest khỏi `routers/events.py` và hàm trả lời khỏi `routers/elder.py` nếu chưa là service | mới / sửa nhỏ |
| B-api | `channels/guardian.py` (cờ `sim` ⇒ mock), `agents/incident_graph.py` (bảng nhãn nút) | sửa nhỏ |
| B-api | `tests/integration/test_api_sim.py`, `test_api_graphs.py`, `test_api_eval_summary.py` | mới |
| B-web | `apps/web/package.json` (`@xyflow/react` 12.12.0), `src/lib/client.ts` (sinh lại), `src/components/trace-graph.tsx`, `src/app/trace/[runId]/page.tsx`, `src/app/sim/page.tsx`, `src/app/eval/page.tsx`, link từ `incidents/[id]` | mới / sửa |
| B-web | `apps/web/e2e/{sim,trace,eval}.spec.ts` + `a11y.spec.ts` | mới / sửa |
| docs | `docs/API.md`, `docs/AGENTS.md`, `docs/DESIGN-SYSTEM.md`, `docs/setup/SIM.md`, `specs/033-web-sim-eval/quickstart.md` | sửa / mới |

## 5. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Sim bị bật ở prod và bị lạm dụng (chi phí LLM, rác DB) | TB | Cổng mặc định tắt; chỉ gia đình demo; hạn mức; `llm` mặc định `replay` |
| Sim đi đường khác thật ⇒ demo "đẹp hơn" sản phẩm | **Cao** (uy tín với BGK) | Bắt buộc tái dùng ingest + đồ thị + route quyết định; test so dãy bước sim với eval cùng kịch bản |
| xyflow nặng, chậm trên điện thoại | Thấp | Nạp động; chỉ ở 2 trang; đo kích thước JS trước/sau trong evidence |
| Video Vòng 1 (13/11) cần `/sim` sớm hơn Đợt 5 | TB | Nhóm [B-api] + `/sim` + `/trace` làm trước, `/eval` sau cùng; báo Tiến nếu muốn kéo sớm |

## 6. Rà soát `/speckit-analyze` (18/10/2026, vòng 1)

Phủ FR: 14/14 có task. **0 CRITICAL, 1 HIGH (đã sửa), 2 MEDIUM, 1 LOW.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| S1 | HIGH | Bản đầu FR-004 ép mọi gia đình **demo** đi Zalo mock ⇒ làm hỏng phép đo bot dev thật của 002 T024 (có thể dùng gia đình demo) | Thu hẹp: chỉ sự cố tạo qua `/v1/sim/runs` (cờ `sim`), plan D4 |
| S2 | MEDIUM | Ảnh backend của 012 không có `backend/eval` (`.dockerignore` dòng 23, `Dockerfile` chỉ COPY thư mục liệt kê) ⇒ `/v1/eval/summary` và `replay` không chạy trong container | T010 thêm ngoại lệ baseline + COPY; T006: trong container `replay` ⇒ `fallback`, ghi ở `docs/setup/SIM.md` |
| S3 | MEDIUM | `POST /v1/sim/runs` gọi đường `/v1/events` thay thiết bị demo mà không có JWT thiết bị ⇒ phải chắc chỉ cho gia đình demo | FR-003 + T003 (gia đình thật ⇒ 404) + T006 (cùng hàm, không có đường tắt) |
| S4 | LOW | Thêm phụ thuộc `@xyflow/react` | Lý do + phiên bản ghim ở D6; đo kích thước JS (T012) |

## Wave 4 (23/10/2026) — nhận các lệch thi công của làn B (evidence 033) vào plan

| # | Quyết định | Lý do | Hệ quả |
|---|---|---|---|
| D9 | Mỗi `POST /v1/sim/runs` tạo **một thiết bị demo riêng** nhãn `sim:<kịch bản>`; nhãn này là dấu bền "sự cố mô phỏng" (không migration). `ops guardian_link --seed` không tạo thiết bị | Dùng chung một thiết bị thì `correlate_event` gom hai lượt chạy cùng lúc vào một sự cố | Số thiết bị demo tăng theo lượt chạy ⇒ T023 dọn thiết bị `sim:` cũ > 24 giờ; `is_sim` (FR-015) suy từ nhãn này |
| D10 | "Bộ ghi mock" tin người giám hộ = `jobs.payload` (đã che PII, `sim: true`); `send_to_guardian` trả `simulated` trước `messages_out`/Zalo | Không thêm bảng; không chạm hạn mức thật | Đã có test 0 lời gọi Zalo với `ZALO_MODE=live` |
| D11 | Đồ thị lượt sim khởi động tại chỗ (`ingest_events(defer_graph=True)` → `start_prepared(sim=True)`), sự kiện nhận id mới mỗi lượt | `build_event` cho id tất định ⇒ chạy lại sẽ trùng | Tính tất định đo trên dãy bước/chữ tin, không trên id |
| D12 | `pending_question.expires_at` lấy từ hẹn giờ `ask_elder`, thiếu ⇒ +60 s | Khớp hẹn giờ thật của đồ thị | Không đổi hợp đồng |
