# Bằng chứng nghiệm thu Spec 036: Eval đầy đủ

- **Trạng thái (18/10/2026)**: chỉ có spec/plan/tasks và hợp đồng (T001). **Chưa code.**
- **Nguồn số dự kiến**: máy dev + runner CI, cassette `synthetic` ⇒ verdict tối đa `provisional`. Số M3 thật cần cassette
  `recorded` (T016, BLOCKED P0-08).

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 cấu trúc bộ | ≥ 100 ca, ≥ 30% hợp lệ song sinh khép kín, ≥ 10 chèn lệnh | `test_eval_suites.py` | chưa chạy | CHƯA ĐO |
| SC-002 thời gian | `full` ≤ 180 s, `injection` ≤ 60 s | `time`, log CI | chưa chạy | CHƯA ĐO |
| SC-003 rào tất định | 0 vi phạm, công khai AI 100%, recall ≥ 0,90, leo thang nhầm ≤ 0,10 (cassette synthetic) | báo cáo `full` | chưa chạy | CHƯA ĐO |
| SC-004 đột biến | 6/6 ⇒ thoát 1 đúng loại | `test_eval_mutations.py` | chưa chạy | CHƯA ĐO |
| SC-005 tất định | hai lượt giống hệt (trừ độ trễ, id) | so JSON | chưa chạy | CHƯA ĐO |
| SC-006 số M3 thật | verdict `pass` trên `recorded` | `--record` | — | BLOCKED (P0-08) |
| SC-007 kịch bản chính thức | ≥ 100 ca `draft: false` | `gate.official_cases` | — | BLOCKED (Minh, 005) |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `uv run --directory backend pytest -q tests/contract` (sau T001) | 257 passed |
| jsonschema: fixture `eval_suite.v1` (2 valid, 6 invalid), `eval_report.v1` (3 valid, 9 invalid), `smoke.v1.json` theo `eval_suite.v1` | valid hợp lệ, invalid bị từ chối, smoke hợp lệ |
