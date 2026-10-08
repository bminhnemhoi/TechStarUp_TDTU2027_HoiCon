# ADR-002: Một tiến trình FastAPI chứa API + LangGraph + MCP

- Trạng thái: **Chấp nhận** · 08/10/2026
- Liên quan: ARCHITECTURE §4, `docs/AGENTS.md`

## Bối cảnh
Một người code, 13 tuần tới MVP, VPS nhỏ. Cần: API cho app/web, đồ thị tác tử có trạng thái và chờ người (interrupt),
công cụ MCP (để trình bày "agentic" chuẩn), hàng đợi hẹn giờ, SSE cho trace.

## Quyết định
- Một dự án `uv` (Python 3.12) `backend/`, một tiến trình FastAPI: router `/v1`, LangGraph với `AsyncPostgresSaver`,
  FastMCP mount tại `/mcp/{threat,zalo,scenario,docs,voice}` và được đồ thị gọi qua `langchain-mcp-adapters`.
- Worker job (Postgres `FOR UPDATE SKIP LOCKED`) chạy như task nền trong cùng tiến trình ở dev; ở prod có thể chạy
  lệnh `hoicon worker` riêng từ cùng mã nguồn nếu cần.
- Không dùng LangGraph Platform/Server, Celery, Redis.

## Hệ quả
- (+) Một thứ để deploy/debug; dùng chung model, session DB, cấu hình; test tích hợp đơn giản.
- (+) MCP vẫn là ranh giới công cụ thật (có schema, có thể gọi từ client MCP ngoài khi demo).
- (−) Tải nặng của LLM chia event loop với API — chấp nhận ở quy mô thí điểm (≤ 50 gia đình); mọi I/O là async.
- (−) Nếu cần tách sau này: worker tách trước, MCP tách sau (đã có ranh giới HTTP).

## Phương án đã loại
- Microservice cho từng tác tử: quá nhiều vận hành cho một người.
- LangGraph Platform: thêm chi phí/phụ thuộc, khó chạy offline ở gian chung kết.
