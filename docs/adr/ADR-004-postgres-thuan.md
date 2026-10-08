# ADR-004: Postgres là kho duy nhất (dữ liệu, hàng đợi job, checkpoint, vector)

- Trạng thái: **Chấp nhận** · 08/10/2026

## Bối cảnh
Cần: dữ liệu quan hệ có ràng buộc (sự cố, đồng ý), hàng đợi hẹn giờ bền vững (T1/T2/T3 phải chạy kể cả khi tiến trình
khởi động lại), checkpoint LangGraph, tìm kiếm tương tự cho kịch bản/tài liệu (nhỏ). Máy dev đã có nhiều stack khác
chiếm cổng 5432/6379.

## Quyết định
- Postgres 17 + pgvector (`pgvector/pgvector:pg17`), dev ở cổng **15432** qua `infra/compose.dev.yml`.
- SQLAlchemy 2 + Alembic + psycopg 3 (dùng chung driver với `AsyncPostgresSaver`).
- Hàng đợi job: bảng `jobs` + `SELECT … FOR UPDATE SKIP LOCKED`; khóa `pg_advisory_xact_lock` cho chuyển trạng thái sự cố.
- Không Redis, không message broker.

## Hệ quả
- (+) Một dịch vụ để sao lưu/khôi phục; giao dịch bao trùm cả "đổi trạng thái + đặt hẹn giờ + ghi tin chờ gửi".
- (−) Độ trễ hàng đợi phụ thuộc chu kỳ poll (≤ 500 ms) + `LISTEN/NOTIFY` để đánh thức — đủ cho mục tiêu ≤ 10 s.
