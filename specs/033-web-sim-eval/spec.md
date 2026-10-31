# Spec 033: Web `/sim`, `/trace`, `/eval` cho BGK và video demo

**Mã ROADMAP**: `P2-19` · **Làn**: B, tách hai nhóm task: **[B-api]** (`backend/**`, `docs/schemas/**`) và **[B-web]**
(`apps/web/**`) · **Cột mốc**: video Vòng 2 (P2-21, 09/01/2027); `/sim` + `/trace` dùng được sớm cho video Vòng 1 nếu kịp
· **Phụ thuộc**: 025 (`/v1/runs/{id}/steps` + SSE), 027 (phiên `hc_guardian`, `require_same_origin`, giao diện người giám
hộ), 030 (`eval.cases.build_event`, `ReplayClient`), 036 (báo cáo `full` cho `/eval`) · **US**: US-10 ("Là BGK, tôi xem tác tử
suy luận từng bước và thử toàn luồng trên web") · **ADR**: ADR-002, ADR-009 (không đổi).

> **Ưu tiên**: `/sim` (P1) và `/trace` (P1) phục vụ video. `/eval` là P3 và nằm trong **danh sách cắt** của ROADMAP
> ("giao diện `/eval`" — mục thứ 3): làm sau cùng, cắt đầu tiên nếu trễ.

---

## 1. Bối cảnh

BGK cần thấy hai thứ mà app Android không cho thấy: (1) toàn luồng người cao tuổi ↔ tác tử ↔ người giám hộ trên **một màn
hình**, (2) tác tử đi qua những bước nào và vì sao. Hiện có: trang chi tiết sự cố của 027 hiện danh sách bước theo thời gian
thực (dạng chữ), đồ thị sự cố chạy thật, Zalo mock, bộ chuyển kịch bản → `RiskEvent` của eval. Chưa có: cách chạy một sự cố
**mà không cần máy Android**, sơ đồ đồ thị, trang chỉ số eval.

| Trang | Ai dùng | Dữ liệu | Mức |
|---|---|---|---|
| `/sim` | BGK, đội quay video | gia đình **demo** (`is_demo`), kịch bản hư cấu trong `data/scenarios/` | P1 |
| `/trace/[runId]` | BGK, người giám hộ (gia đình mình) | `agent_steps` đã che PII | P1 |
| `/eval` | BGK | baseline eval đã commit (không có dữ liệu người dùng) | P3, cắt được |

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-33.1 | **P1** | Là BGK, tôi chọn một kịch bản lừa đảo, bấm "Bắt đầu", rồi thấy trên một màn: điện thoại mô phỏng của bác (câu hỏi E8), tin Zalo mô phỏng của con, và các bước của trợ lý AI; tôi trả lời thay bác và quyết định thay con |
| US-33.2 | **P1** | Là đội quay video, tôi chạy lại đúng một kịch bản và được đúng cùng các bước, cùng câu chữ (chế độ phát lại tất định) |
| US-33.3 | **P1** | Là BGK hoặc người giám hộ, tôi mở `/trace/<run>` và thấy sơ đồ đồ thị tác tử, bước nào đã chạy, bước nào đang chờ người, mức rủi ro đổi ở đâu, có bản chữ cho trình đọc màn hình |
| US-33.4 | **P3** | Là BGK, tôi xem chỉ số eval mới nhất (recall, báo nhầm, vi phạm an toàn, công khai AI) kèm nhãn rõ "số rào tất định" hay "số LLM thật" |

## 3. Yêu cầu chức năng

- **(FR-001)** Hợp đồng trước: `docs/schemas/sim_run.v1.json` (khung nhìn một lượt mô phỏng), `sim_run_request.v1.json`,
  `sim_scenarios.v1.json` (danh sách kịch bản chọn được), `graph_topology.v1.json` (nút + cạnh của đồ thị sự cố) + fixture
  valid/invalid; test hợp đồng; sinh lại client TS.
- **(FR-002)** Cổng bật: mọi route `/v1/sim/*` và `/v1/eval/*` trả **404** trừ khi `HOICON_SIM_ENABLED=true` (mặc định `false`;
  `compose.prod.yml` không đặt). Trang web `/sim`, `/eval` hiện "Trang này chưa mở" khi API trả 404.
- **(FR-003)** Chỉ gia đình demo: mọi lệnh `/v1/sim/*` cần phiên `hc_guardian` của người giám hộ thuộc gia đình `is_demo=true`
  (gia đình thật ⇒ 404, không lộ sự tồn tại); lệnh ghi qua `require_same_origin`. Sự cố mô phỏng mang `is_demo=true`, không bao
  giờ `is_drill` (diễn tập là việc khác, luật 8).
- **(FR-004)** Không Zalo thật: tin của sự cố **mô phỏng** (tạo qua `/v1/sim/runs`, mang cờ `sim` trong state và payload
  `notify_guardian`) **luôn** đi vào bộ ghi mock, cả khi `HOICON_ZALO_MODE=live`; không trừ hạn mức thật. Chỉ áp cho sự cố mô
  phỏng, không cho mọi gia đình demo (bot dev thật của 002 T024 có thể dùng gia đình demo). Test: chế độ `live` + sự cố mô phỏng
  ⇒ 0 lời gọi tới `LiveZaloClient`.
- **(FR-005)** `GET /v1/sim/scenarios` trả danh sách theo `sim_scenarios.v1` từ `data/scenarios/` (id, nhóm, hợp lệ/lừa đảo, chèn
  lệnh, `draft`); `POST /v1/sim/runs {scenario_id, llm: "replay"|"live"}` dựng `RiskEvent` bằng **`eval.cases.build_event`**
  (tái dùng, không viết bộ chuyển thứ hai), đưa qua **cùng đường** với `POST /v1/events` (ghi `risk_events`, mở sự cố qua
  `IncidentService`, khởi động đồ thị với `family_id` demo), trả `sim_run.v1`. Kịch bản không kích hoạt luật ⇒ 200 với
  `incident_id: null` và lời giải thích "Máy không bật nhắc dừng lại với tình huống này".
- **(FR-006)** `llm: "replay"` dùng `ReplayClient` với cassette của kịch bản (thứ tự tìm như 036 D2) ⇒ tất định; `llm: "live"` dùng
  `LlmRouter` thật (không khóa ⇒ rơi về mẫu, ghi rõ `llm_mode: "fallback"` trong khung nhìn). Mặc định `replay`.
- **(FR-007)** `GET /v1/sim/runs/{incident_id}` trả trạng thái, mức rủi ro, câu hỏi E8 đang chờ (theo `elder_question.v1`), tin
  người giám hộ đã xếp (văn bản mẫu đã che, theo thứ tự), `run_id`; `POST /v1/sim/runs/{incident_id}/answer` trả lời E8 thay
  người cao tuổi, đi qua **cùng hàm** với `routers/elder.py` (không nhận `note` tự do: chỉ `answer` + cờ đã biết). Quyết định
  người giám hộ dùng **route có sẵn** `POST /v1/incidents/{id}/decision` bằng chính phiên đó.
- **(FR-008)** Hạn mức mô phỏng: ≤ 10 lượt `POST /v1/sim/runs` mỗi giờ mỗi phiên, ≤ 3 lượt đang chạy mỗi gia đình demo (429 kèm
  `Retry-After`); `llm: "live"` tính vào trần chi tiêu của `llm_router`.
- **(FR-009)** `GET /v1/graphs/incident` trả `graph_topology.v1` sinh **từ đồ thị đã biên dịch** (`build_graph(...).get_graph()`),
  kèm nhãn tiếng Việt từ một bảng cố định; nút interrupt (`ask_elder`, `await_guardian`) đánh dấu `kind: "interrupt"`. Test: mọi
  nút của đồ thị có nhãn; thêm nút mới mà quên nhãn ⇒ đỏ. Route này **không** nằm sau cổng FR-002 (`/trace` của người giám hộ
  thật cũng dùng) và không cần đăng nhập: nó chỉ mô tả cấu trúc mã, không có dữ liệu người dùng.
- **(FR-010)** Web `/sim` (Client Component): cột trái "Điện thoại của bác (mô phỏng)" — câu hỏi E8 với nút trả lời ≥ 64 px; giữa
  "Trợ lý AI" — sơ đồ + danh sách bước trực tiếp (dùng lại `useRunStream`, `describeStep`); phải "Zalo của con (mô phỏng)" — tin
  theo thứ tự + 3 nút quyết định có xác nhận như trang chi tiết 027. Trên điện thoại (< 768 px) ba cột thành ba thẻ xếp dọc có
  tab. Nhãn cố định đầu trang: "MÔ PHỎNG — dữ liệu hư cấu, không có cuộc gọi hay tin Zalo thật". Kịch bản `draft` có nhãn "kịch
  bản nháp".
- **(FR-011)** Web `/trace/[runId]`: sơ đồ bằng `@xyflow/react` (thêm phụ thuộc có lý do: MASTER-PLAN chọn xyflow cho `/trace`;
  bố cục tĩnh từ `graph_topology`), tô nút đã chạy/đang chờ/lỗi/rơi về mẫu (màu **kèm** biểu tượng + chữ), chọn một nút ⇒ chi tiết
  bước đã che. **Bản chữ bắt buộc** bên dưới sơ đồ (danh sách bước có thứ tự) cho trình đọc màn hình; `prefers-reduced-motion`
  tắt hiệu ứng. Trang mở được cho người giám hộ (sự cố gia đình mình) và phiên demo; không phải của mình ⇒ "Không tìm thấy".
- **(FR-012)** (P3) `GET /v1/eval/summary` (sau cổng FR-002) trả các baseline đã commit (`baseline.json`, `baseline-full.json`,
  `baseline-injection.json` nếu có) kèm `gate` của 036; web `/eval` hiện bảng chỉ số, theo nhóm thủ đoạn/miền, và dòng cảnh báo
  "Số rào tất định — CHƯA PHẢI SỐ M3" khi verdict ≠ `pass`. Không đọc thư mục `reports/` (bị git bỏ qua, có thể chứa `run_id`).
- **(FR-013)** Kiểm chứng: pytest (cổng, chỉ demo, Zalo mock ép, hạn mức, tái dùng đường events/elder, topology), Playwright
  (`/sim` đi hết một kịch bản lừa đảo + một kịch bản hợp lệ ở chế độ replay; `/trace` có bản chữ; `/eval`), axe 0 lỗi, ảnh chụp
  360 px và 1280 px; `ux-elder-reviewer` cho câu chữ phần "điện thoại của bác"; `security-privacy-reviewer`.
- **(FR-014)** Tài liệu: `docs/API.md`, `docs/AGENTS.md` (topology), `docs/DESIGN-SYSTEM.md` (trang web mới), `docs/setup/` (cách bật
  sim trên máy dev và tạo gia đình demo bằng `ops guardian_link --seed`), quickstart quay video.
- **(FR-015)** *(Wave 4, 23/10/2026 — theo `ux-elder-reviewer` T013/T014)*: (a) `GET /v1/sim/scenarios` gửi `title_vi` (hợp đồng
  `sim_scenarios.v1`) dựng **tất định** = nhãn nhóm thủ đoạn + " · ca " + số thứ tự trong id bỏ số 0 đầu (ví dụ
  `fake_police_safe_account_002` ⇒ "Giả danh công an · ca 2"); không đọc chữ tự do của kịch bản, không cần sửa `data/scenarios/`.
  Nhãn: `fake_police` Giả danh công an · `fake_tax` Giả danh cơ quan thuế · `fake_evn` Giả danh điện lực · `deepfake_relative` Giả
  giọng/mặt người thân · `task_scam` Việc làm online · `recovery_scam` Hứa lấy lại tiền · `fake_vneid` Giả danh VNeID · `fake_bank` Giả
  danh ngân hàng · `investment` Mời đầu tư · `fake_delivery` Giả danh giao hàng · `prize_gift` Trúng thưởng, quà tặng · `fake_health`
  Giả danh y tế · `benign_bank` Cuộc gọi thật: ngân hàng · `benign_relative_new_number` Cuộc gọi thật: người thân đổi số · `benign_shipper`
  Cuộc gọi thật: người giao hàng · `benign_official` Cuộc gọi thật: cơ quan · `benign_utility` Cuộc gọi thật: điện, nước · `benign_family`
  Cuộc gọi thật: người nhà. Nhóm mới mà thiếu nhãn ⇒ test đỏ. (b) `GET /v1/runs/{id}/steps` gửi `is_sim` (hợp đồng `run_steps.v1`) =
  sự cố của lượt chạy là sự cố mô phỏng (thiết bị nhãn `sim:` — plan D9); `/trace` hiện băng "MÔ PHỎNG" như `/sim`. (c) Băng mô phỏng
  dùng token màu riêng `sim.*` (không dùng màu diễn tập — luật 15 "diễn tập dùng màu riêng" phải giữ phân biệt được).

## 4. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Toàn luồng trên web | Kịch bản `fake_police_safe_account_002` ở replay: từ "Bắt đầu" tới quyết định của con ≤ 5 thao tác, mọi bước hiện ≤ 1 s sau khi ghi | Playwright + mốc thời gian |
| **(SC-002)** | Tất định | Hai lượt replay cùng kịch bản ⇒ cùng dãy nút, cùng mức, cùng câu chữ tin | Playwright so ảnh chụp chữ |
| **(SC-003)** | Cô lập | Cổng tắt ⇒ 404; gia đình thật ⇒ 404; Zalo `live` + sự cố mô phỏng ⇒ 0 lời gọi thật; 11 lượt/giờ ⇒ 429 | pytest |
| **(SC-004)** | Tiếp cận | axe 0 lỗi ở `/sim`, `/trace`, `/eval`; bản chữ của trace đủ bước; chữ ≥ 16 px web, nút ≥ 44 px (≥ 64 px ở cột "điện thoại của bác") | Playwright + axe |
| **(SC-005)** | Đúng đồ thị | `graph_topology` = nút/cạnh của đồ thị biên dịch; mọi nút có nhãn | pytest |
| **(SC-006)** | Không PII | 0 số điện thoại/h1/tên gói trong phản hồi `/v1/sim/*` và DOM | pytest + Playwright quét DOM |
| **(SC-007)** | Video | Một lượt quay `/sim` (1280×720) dùng được cho P2-21 | đội quay, **BLOCKED** tới P2-21 |
| **(SC-008)** | Nhận ra được | 100% kịch bản trong ô chọn có `title_vi` đúng bảng FR-015; `/trace` của lượt mô phỏng có băng "MÔ PHỎNG", lượt thật không có; token `sim.*` tương phản ≥ 7:1 với chữ | pytest + Playwright + `gen-design-tokens.py --check` |

## 5. Làm rõ (clarify, 18/10/2026 — tự quyết)

| # | Điểm mơ hồ | Quyết định | Lý do |
|---|---|---|---|
| Q1 | `/sim` có mô phỏng app Android? | Không vẽ lại E7; cột trái chỉ có câu hỏi E8 và dòng "Màn nhắc dừng lại đã hiện trên máy" | E7 chạy trên máy, không qua máy chủ; vẽ lại dễ lệch so với app thật |
| Q2 | Ai đăng nhập `/sim`? | Người giám hộ của gia đình demo, bằng liên kết `/login/<token>` (027) do `ops guardian_link` sinh | Tái dùng phiên 027; không thêm cơ chế đăng nhập |
| Q3 | Mở `/sim` cho công chúng? | Không ở spec này; gian trưng bày `/booth`, `/join/[code]` là spec 050 | Hạn mức, chi phí LLM, chống lạm dụng |
| Q4 | Sơ đồ lấy từ đâu? | Sinh từ đồ thị LangGraph đã biên dịch qua API | Không chép tay danh sách nút ⇒ không lệch khi 031 thêm `case_file` |
| Q5 | Có thêm shadcn? | Không (quyết định của 027) | Giữ một bộ thành phần `guardian-ui` |
| Q6 | `/eval` đọc báo cáo nào? | Chỉ baseline đã commit | `reports/` bị git bỏ qua, không có trên máy chủ |

## 6. Ngoài phạm vi

`/booth`, `/join/[code]`, `/demo/console` (050); vẽ lại E7/E11 trên web; chạy sim với gia đình thật; đổi cách chấm eval.
