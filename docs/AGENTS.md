# Tác tử AI HỏiCon (LangGraph + MCP)

> Trạng thái: **khung** (P0-05) — chi tiết hoàn thiện ở spike P1-S4 và P2-08…P2-17. (Hướng dẫn cho tác tử lập trình
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

## `llm_router`
| Hồ sơ | Mô hình | Dùng cho |
|---|---|---|
| `fast` | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) / Gemini Flash-Lite | bước thường xuyên |
| `strong` | Claude Sonnet 5.5 (`claude-sonnet-5-5`) / Gemini Pro | xác minh, hồ sơ |
| `judge` | nhà cung cấp khác bên sinh | chấm eval |

Mọi lời gọi: che PII → `<untrusted>` cho nội dung kẻ gian → timeout ≤ 4 s → output có cấu trúc → ghi `agent_steps`
→ rơi về mẫu. Công cụ có tác dụng phụ chỉ gọi từ node trong danh sách cho phép.

## MCP servers (`/mcp/*`)
`threat` (tra cứu/gắn cờ) · `zalo` (gửi qua bộ kiểm hạn mức) · `scenario` (kịch bản diễn tập) · `docs` (tài liệu hướng
dẫn) · `voice` (âm thanh thu sẵn). `docs`/`voice`/`scenario` nằm trong danh sách cắt (có thể thành tool nội bộ).

## Prompt
`backend/src/hoicon/agents/prompts/*.md`, có phiên bản trong front-matter; đổi prompt ⇒ `run-eval smoke`.
