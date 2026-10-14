# Tác tử AI HỏiCon (LangGraph + MCP)

> Trạng thái: **lõi đồ thị sự cố đã chạy** (spike P1-S4, ADR-009: `backend/src/hoicon/agents/`) — các nút `verification`,
> `rescore`, `case_file`, đồ thị `coach` hoàn thiện ở P2-08…P2-17. (Hướng dẫn cho tác tử lập trình
> nằm ở `CLAUDE.md`; file này mô tả **tác tử sản phẩm**.) Trước khi viết mã gọi Claude: đọc skill `claude-api`.

## 5 tác tử (theo thuyết minh)
| Tác tử | Vai trò | Node chính |
|---|---|---|
| Chấm rủi ro | Kết hợp `rule_floor` + câu trả lời E8 + ngữ cảnh ⇒ mức rủi ro (chỉ nâng) | `risk_scorer` |
| Can thiệp | Chọn lời nhắc/câu hỏi đã duyệt cho người cao tuổi, báo người giám hộ | `fast_alert`, `intervention` |
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

## Prompt
`backend/src/hoicon/agents/prompts/*.md`, có phiên bản trong front-matter; đổi prompt ⇒ `run-eval smoke`.
