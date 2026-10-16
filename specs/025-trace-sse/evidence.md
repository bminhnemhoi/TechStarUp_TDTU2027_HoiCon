# Bằng chứng nghiệm thu Spec 025: Luồng SSE truy vết tác tử

- **Trạng thái**: chưa triển khai. Spec, plan và tasks hoàn thành ngày 16/10/2026; chưa có số đo nào.
- **Môi trường dự kiến**: Linux CachyOS, Postgres dev trên Docker (cổng 15432), uvicorn chạy trên localhost.
- **Nguồn số**: chỉ máy dev. Chưa có Caddy/VPS (thuộc 012), nên phần "qua reverse proxy" vẫn ghi CHƯA ĐO.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 độ trễ bước → client | p95 ≤ 500 ms, n ≥ 30 | `test_trace_sse_live.py -s` (uvicorn thật, localhost) | chưa chạy | CHƯA ĐO |
| SC-002 che PII | 0 SĐT thô · 0 hex ≥ 32 · 0 khóa cấm · không có `input_redacted` | `test_api_runs.py` (bước "đầu độc") + `test_redact_json.py` | chưa chạy | CHƯA ĐO |
| SC-003 `: ping` mỗi 15 s | có ping sau `PING_S` im lặng; đi qua Caddy | `test_trace_stream.py` + `test_trace_sse_live.py` (PING_S thu nhỏ); Caddy: 012 | chưa chạy | CHƯA ĐO |
| SC-004 lịch sử `/steps` | khớp DB theo `(at, id)`, giống payload SSE; 401/404 | `test_api_runs.py` | chưa chạy | CHƯA ĐO |
| SC-005 `event: done` | đúng 1 lần, sau bước cuối, số đếm/chi phí khớp DB; `waiting` không đóng | `test_trace_stream.py` + `test_api_runs.py` | chưa chạy | CHƯA ĐO |
| SC-006 không rò tài nguyên | `checkedout()` + bộ đếm về mức cũ sau 50 lần ngắt; 503 khi vượt trần | `test_trace_sse_live.py` + `test_api_runs.py` | chưa chạy | CHƯA ĐO |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` (sau khi sửa regex cho dạng `**(FR-001)**`) | 12 spec, 0 lỗi |
| `python3 -m unittest discover -s scripts/tests` | 68 test, OK |
