# Tác tử AI HỏiCon (LangGraph + MCP)

> Trạng thái: **lõi đồ thị sự cố đã chạy** (spike P1-S4, ADR-009: `backend/src/hoicon/agents/`) — các nút `verification`,
> `rescore`, `case_file`, đồ thị `coach` hoàn thiện ở P2-08…P2-17. (Hướng dẫn cho tác tử lập trình
> nằm ở `CLAUDE.md`; file này mô tả **tác tử sản phẩm**.) Trước khi viết mã gọi Claude: đọc skill `claude-api`.

## 5 tác tử (theo thuyết minh)
| Tác tử | Vai trò | Node chính |
|---|---|---|
| Chấm rủi ro | Kết hợp `rule_floor` + câu trả lời E8 + ngữ cảnh ⇒ mức rủi ro (chỉ nâng) | `risk_scorer` |
| Can thiệp | Chọn lời nhắc/câu hỏi đã duyệt cho người cao tuổi; báo người giám hộ bằng **mã điểm** (LLM chỉ chọn mã từ danh sách đóng, máy chủ ghép câu cố định — ADR-012) | `fast_alert`, `intervention` |
| Xác minh | Tra số/link/QR qua MCP `threat`, nguồn công khai | `verification`, `rescore` |
| Hồ sơ | Soạn hồ sơ vụ việc, chờ người giám hộ duyệt | `case_file` |
| Huấn luyện (Coach) | Bản tin tuần, diễn tập cá nhân hóa | đồ thị `coach` |

## Đồ thị sự cố
`ingest → load_memory → fast_alert (mẫu, không LLM) → risk_scorer ⇄ [INTERRUPT ask_elder] → intervention →
[INTERRUPT await_guardian] (T1/T2/T3) → verification → rescore → resolve` + nhánh `case_file → [INTERRUPT await_case_approval]`.

Đã có (P1-S4): `ingest` (tra `threat`) → `fast_alert` → `risk_scorer` ⇄ `ask_elder` → `intervention` → `await_guardian`
(T1 nhắc, T2 chuyển người giám hộ 2, T3 kết thúc "không phản hồi") → `resolve`. Chạy: `IncidentRuntime` (checkpoint
Postgres đồng bộ, khóa theo thread, `recover()` sau sập); hẹn giờ là job `graph_resume`; tin gửi đi là job
`notify_guardian` có khóa chống trùng. Thử: `uv run --directory backend python -m hoicon.agents.spike demo`.

**Xác minh (spec 026):** node `verification` chèn giữa `risk_scorer` (khi không còn câu hỏi) và `intervention`, **không dùng
LLM** (lệch bảng hồ sơ `strong` ở trên có chủ ý: "nguồn dẫn" phải là dữ kiện có thật — tên danh sách, phiên bản, mã quy tắc —
mà LLM chỉ có thể bịa thêm). Nó đọc các dòng `verifications` của sự cố (do `POST /v1/lookups` và `POST /v1/events` ghi), nâng
`level = max(state.level, sàn)` (`dangerous` ⇒ `critical`, `warning` ⇒ `high`), ghi xuyên `incidents.level` qua
`IncidentService.raise_level` (gồm cả mức `risk_scorer` đã nâng) và ghi `agent_steps.node = "verify"` với
`{checked, dangerous, warning, level_before, level_after}` (không HMAC). Lượt eval/demo không có sự cố thật bỏ qua DB. Trạng
thái `verifying`/`rescore` của máy trạng thái chưa dùng. `await_guardian` nhận thêm resume `{"evidence": <verification_id>}`
(người cao tuổi tự tra ra số/link nguy hiểm lúc sự cố còn chờ): nếu người giám hộ chưa quyết và dòng xác minh là `dangerous`
của đúng sự cố này thì gửi MỘT tin mẫu `evidence` (`texts.guardian_evidence`, mở đầu công khai AI, nhãn `[DIỄN TẬP]` khi diễn
tập, chỉ "số đuôi …" hoặc "một đường link"), khóa `{incident}:msg:evidence`, rồi quay lại chờ; hẹn giờ T1/T2/T3 không dời.

**Gửi thật tới người giám hộ (spec 002, ADR-010):** `IncidentRuntime.start(..., family_id=)` đưa `family_id` vào state và payload
`notify_guardian` (vắng ⇒ chỉ log như cũ). Handler `notify_guardian` → `channels/guardian.py::send_to_guardian` → cổng duy nhất
`deliver`: dòng `messages_out` (gửi đúng một lần), từ chối tin không mở đầu bằng câu công khai AI, chặn sự cố demo tới gia đình
thật, hạn mức tin/tháng (giữ tin không khẩn ≥ 95%, tin gắn sự cố luôn đi), lỗi vĩnh viễn/hết lần thử ⇒ `fallback_required`.
Job `zalo_update` (do webhook xếp) ghép người giám hộ `/start <mã>` và nhận phản hồi **1** (an toàn) / **2** (nghi lừa đảo) /
**3** (xem chi tiết) ⇒ `runtime.resume(incident, {"decision": …}, expect="await_guardian")`. Zalo không có nút bấm.
`ZaloClient` có hai bản: `LiveZaloClient` và `MockZaloClient` (mặc định, `HOICON_ZALO_MODE=mock`). Chưa có MCP `zalo`.

## `llm_router`
| Hồ sơ | Mô hình | Dùng cho |
|---|---|---|
| `fast` | Claude Haiku 5.5 (`claude-haiku-5-5`, mặc định tạm) / Claude Haiku 4.5 (`claude-haiku-4-5`) / Gemini Flash-Lite (chưa có provider) — chốt sau khi đo (ADR-009) | bước thường xuyên |
| `strong` | Claude Sonnet 5.5 (`claude-sonnet-5-5`) / Gemini Pro | xác minh, hồ sơ |
| `judge` | nhà cung cấp khác bên sinh | chấm eval |

Mọi lời gọi: che PII → `<untrusted>` cho nội dung kẻ gian → timeout ≤ 4 s → output có cấu trúc → ghi `agent_steps`
→ rơi về mẫu. Công cụ có tác dụng phụ chỉ gọi từ node trong danh sách cho phép.

## MCP servers (`/mcp/*`)
`threat` (tra cứu/gắn cờ) · `zalo` (gửi qua bộ kiểm hạn mức) · `scenario` (kịch bản diễn tập) · `docs` (tài liệu hướng
dẫn) · `voice` (âm thanh thu sẵn). `docs`/`voice`/`scenario` nằm trong danh sách cắt (có thể thành tool nội bộ).

`threat` (đã dựng, spec 003) tại `/mcp/threat/`: tool `lookup_phone(h1)` tra bảng `threat_indicators` (chỉ HMAC). **Đóng
mặc định**: mọi yêu cầu cần `Authorization: Bearer <token>` (cấu hình `HOICON_MCP_THREAT_CLIENTS` = tên client → SHA-256
token; sinh bằng `python -m hoicon.ops.mcp_token new --client <tên>`), giới hạn tần suất theo client (429 + `Retry-After`),
mỗi yêu cầu một dòng log (client, mã, tool, verdict — không h1/token/IP). Cùng middleware (`mcp_servers/auth.py`) dùng
cho các MCP server sau.

## Prompt
`backend/src/hoicon/agents/prompts/*.md`, có phiên bản trong front-matter; đổi prompt ⇒ `run-eval smoke`.

## Eval (`hoicon-eval`, spec 030 + 036)
`uv run --directory backend hoicon-eval --suite smoke [--compare baseline]` chạy 20 kịch bản `data/scenarios/` qua **đồ thị
sự cố thật** (`IncidentRuntime` + `AsyncPostgresSaver`) trên DB eval riêng; LLM thay bằng `ReplayClient` đọc cassette
`backend/eval/cassettes/smoke/<id>.json` (hợp đồng `docs/schemas/eval_cassette.v1.json`) cắm vào `LlmRouter` nên vẫn qua
che PII, ngân sách, fallback; **không khóa API, không mạng ngoài, không worker ⇒ không tin nào tới Zalo**.
- Bộ kiểm tất định (không LLM-judge): `lower_than_floor`, `missing_ai_disclosure`, `leak_pii`, `panic_wording`,
  `promise_refund`, `follow_injected_instruction`, `graph_loop` + lệch kỳ vọng của kịch bản (mức tối thiểu/tối đa, báo
  người giám hộ, công cụ, kết cục).
- Chỉ số: recall leo thang, tỷ lệ báo nhầm, vi phạm an toàn, công khai AI, tỷ lệ rơi về mẫu, p50/p95. Báo cáo
  `backend/eval/reports/<ngày>-smoke.{json,md}` (JSON theo `docs/schemas/eval_report.v1.json`); so `backend/eval/baseline.json`
  theo ngưỡng skill `run-eval`. Baseline chỉ ghi bằng `--write-baseline` chạy tay.
- Cô lập: từ chối khi `HOICON_ENV=prod` hoặc URL DB eval trùng DB ứng dụng (trừ `--shared-db-ok` ở CI); sự cố mang id
  `eval-<nonce>-<case>`, `is_demo=True`, job/hẹn giờ bị xóa cuối mỗi ca.
- `--suite full --compare baseline-full` (spec 036): 110 ca (20 smoke + 90 cassette sinh tất định bằng
  `python -m hoicon.eval.cassettes write|check` từ `backend/eval/suites/full.v1.json`), ngưỡng Gate M3 tuyệt đối (recall ≥ 0,90,
  báo nhầm ≤ 0,10, 0 vi phạm, công khai AI 100%), baseline `backend/eval/baseline-full.json`. `--suite injection`: 17 ca chèn lệnh,
  không baseline. Vẫn không khóa API: phần LLM thật (cassette `recorded`, lặp prompt) BLOCKED P0-08.
- Giới hạn đã biết: cassette `synthetic` + kịch bản `draft: true` chỉ đo **rào tất định**, không đo chất lượng model.
  **F-2** (đã đóng, ADR-012, spec 024 T015): `intervention` không còn tóm tắt tự do; LLM chỉ chọn 1–3 mã điểm
  (`GuardianBrief` v2, `docs/schemas/guardian_brief.v2.json`), máy chủ bỏ mã có dữ kiện sai và ghép câu cố định
  `texts.BRIEF_POINT_VI`; eval có kiểm `brief_outside_vocabulary`. **F-1**: `("q_asked_transfer","yes") ⇒ critical` báo nhầm chuyển tiền chính đáng ⇒
  phương án ở spec 024 §5 (chờ Minh, MASTER-PLAN §8).

## Sơ đồ đồ thị và cờ `sim` (spec 033)
- `GET /v1/graphs/incident` sinh `graph_topology.v1` từ `build_graph(...).compile().get_graph()`. Nhãn tiếng Việt nằm ở
  `incident_graph.NODE_LABELS_VI` (cùng `INTERRUPT_NODES`, `STEP_NODES`: nút `verification` ghi bước `verify`); thêm nút mà
  quên nhãn ⇒ `graph_topology()` ném `MissingLabelError` (test đỏ).
- State `sim: true` (chỉ có ở sự cố tạo qua `/v1/sim/runs`) ⇒ `notify` đặt `payload.sim` và `send_to_guardian` trả
  `"simulated"` mà không gọi Zalo, không tạo `messages_out`. `IncidentRuntime.start_prepared(..., sim=True)`.
