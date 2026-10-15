# Hợp đồng — spec 030

Hợp đồng nằm ở `docs/schemas/` (nguồn sự thật, viết **trước** code — Hiến chương V):

| Schema | Fixture | Dùng bởi |
|---|---|---|
| `docs/schemas/eval_cassette.v1.json` | `docs/schemas/fixtures/eval_cassette.v1.{valid,invalid}.json` | `backend/eval/cassettes/**`, `hoicon.eval.replay` |
| `docs/schemas/eval_report.v1.json` | `docs/schemas/fixtures/eval_report.v1.{valid,invalid}.json` | `hoicon.eval.report`, dashboard `/eval` (spec 033) |

Kịch bản vẫn theo `docs/schemas/scenario.v1.json` (không đổi). Test: `backend/tests/contract/test_eval_schemas.py`.
