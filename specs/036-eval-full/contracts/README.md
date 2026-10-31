# Hợp đồng — spec 036

Không đổi hợp đồng: `docs/schemas/` giữ nguyên (cấm sửa theo lệnh giao Wave 2).

| Schema | Dùng cho | Ghi chú |
|---|---|---|
| `docs/schemas/scenario.v1.json` | 50 kịch bản mới trong `data/scenarios/` | `id` dạng `…_NNN` ⇒ mỗi ca là một tệp kịch bản |
| `docs/schemas/eval_cassette.v1.json` | `backend/eval/cassettes/full/*.json` (sinh) | `case_id` trùng id kịch bản; `source: synthetic` |
| `docs/schemas/eval_report.v1.json` | `…-full.json` | `suite: "full"`; `draft` từng ca đã có sẵn, nên không cần trường mới cho "provisional" |

Tệp mới KHÔNG thuộc `docs/schemas/`: `backend/eval/suites/full.v1.json` (định dạng nội bộ như `smoke.v1.json`, có thêm `behaviors`)
và `backend/eval/baseline-full.json` (như `baseline.json`). Test: `backend/tests/contract/test_eval_full_suite.py`.
