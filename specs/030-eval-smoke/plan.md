# Implementation Plan: Eval smoke tất định (`hoicon-eval --suite smoke`)

**Branch**: `feat/030-eval-smoke` (nối tiếp `feat/002-zalo-guardian-channel`) | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/030-eval-smoke/spec.md`

## Summary

Gói mới `backend/src/hoicon/eval/` chạy 20 kịch bản `data/scenarios/` qua **đồ thị sự cố thật** (`IncidentRuntime` +
`AsyncPostgresSaver`, DB eval riêng), LLM thay bằng `ReplayClient` (cassette JSON) cắm vào `LlmRouter` hiện có. Bộ kiểm tất
định chấm từng ca theo `expected` của kịch bản + bất biến toàn cục, tính chỉ số, so baseline theo ngưỡng skill `run-eval`, ghi báo
cáo JSON (hợp đồng) + Markdown. CI chạy ngay sau `pytest`. Không đổi prompt, đồ thị, router, DB schema.

**Quyết định kỹ thuật — Tiến ĐÃ duyệt trước E1–E5 (15/10/2026); chạy một mạch, §2.6:**
- E1: chạy đồ thị thật trên Postgres (không giả lập state) — chậm hơn mock nhưng đo đúng thứ chạy production.
- E2: DB eval riêng `hoicon_eval` ở máy dev; CI dùng DB service + `--shared-db-ok`.
- E3: cassette tổng hợp viết tay (`source: synthetic`) cho tới khi có khóa; ≥ 6 ca đối kháng (FR-016).
- E4: dữ liệu eval ở `backend/eval/` (khớp đường dẫn `eval/baseline.json` của skill `run-eval` khi chạy `--directory backend`).
- E5: baseline đầu tiên do spec này ghi; cập nhật sau đó theo skill `run-eval` (người duyệt PR đồng ý).

## Technical Context

**Language/Version**: Python 3.12 (`uv`)

**Primary Dependencies**: LangGraph + `AsyncPostgresSaver`, SQLAlchemy 2, Pydantic v2, `pyyaml` (đã có, nhóm dev), `jsonschema`
(đã có, nhóm dev, chỉ dùng trong test hợp đồng) — **không thêm thư viện**

**Storage**: Postgres 17 — DB eval (`hoicon_eval` ở dev; DB service ở CI); không migration mới

**Testing**: `uv run --directory backend pytest` (unit + integration + contract) · `ruff` · CLI smoke trong CI

**Target Platform**: máy dev Linux/Windows (vòng lặp `SelectorEventLoop` như `tests/conftest.py`) + GitHub Actions ubuntu-latest

**Project Type**: monorepo — chỉ làn B

**Performance Goals**: 20 ca < 60 s (mục tiêu thực tế < 20 s)

**Constraints**: không mạng ra ngoài; không khóa API; không gửi Zalo; tất định; không ghi đè baseline tự động

**Scale/Scope**: 20 ca smoke; khung dùng lại cho 036 (≥ 100 ca)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Nguồn: `.specify/memory/constitution.md`.

| # | Nguyên tắc | Đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn | Không | Không đụng Android |
| II | Riêng tư | **Có** (kiểm PII) | `leak_pii` quét tin, nội dung gửi LLM, `agent_steps`, checkpoint; dữ liệu hư cấu; báo cáo chỉ in tin của 5 ca tệ nhất sau `mask_text` |
| III | LLM chỉ nâng, mọi lời gọi qua router | **Có** (đo) | `ReplayClient` cắm vào `LlmRouter`, không đường vòng; cassette đối kháng kiểm `raise_only` + `_UNSAFE_SUMMARY` |
| IV | Công khai AI | **Có** (đo) | Kiểm 100% tin + câu hỏi; DB riêng + `is_demo` + dọn job ⇒ không tin thật |
| V | Hợp đồng trước | **Có** | `eval_cassette.v1.json`, `eval_report.v1.json` + fixture + test trước code |
| VI | UX | Gián tiếp | Kiểm `panic_wording` |
| VII | Bằng chứng trung thực | **Có** | Cassette ghi `synthetic`; báo cáo ghi "kịch bản nháp"; số đo kèm môi trường |
| VIII | Ít code | **Có** | Dùng lại runtime, router, `mask_text`, `texts.AI_DISCLOSURE`, mẫu `ScriptedClient`; không thư viện mới |
| IX | Chặn phát hành | Không | Công cụ dev/CI |

Kết quả: **ĐẠT**.

## Tái sử dụng *(mandatory)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới |
|---|---|---|
| Chạy đồ thị bền vững, interrupt, resume | `backend/src/hoicon/agents/runtime.py::IncidentRuntime` (`open`, `start`, `resume(expect=…)`, `clean_resume`) | **dùng lại** nguyên |
| Cổng LLM, fallback, che PII, `<untrusted>` | `agents/llm_router.py::LlmRouter` (nhận `MessagesClient`) | **dùng lại**; `ReplayClient` theo mẫu `ScriptedClient` (`tests/integration/test_incident_graph.py`) |
| Deps + cấu hình timer | `agents/spike.py::deps`, `incident_graph.Deps` | **mẫu**; eval tạo `Deps` với `Settings.model_copy(update={database_url: <eval>})` |
| Sự kiện rủi ro | `domain/events.py::RiskEvent`, `spike.demo_event` (mẫu dựng event) | **dùng lại** |
| Che/phát hiện PII | `domain/pii.py::mask_text`, `note_flags` | **dùng lại**: `mask_text(x) != x` ⇒ có PII |
| Câu công khai, nhãn diễn tập | `agents/texts.py::AI_DISCLOSURE`, `DRILL_LABEL` | **dùng lại** |
| Đọc checkpoint của thread | `test_incident_graph.py::checkpoint_bytes` (truy vấn SQL) | **chuyển** thành hàm dùng chung trong `eval/checks.py`, test cũ gọi lại |
| Kịch bản + schema | `data/scenarios/*.yaml`, `docs/schemas/scenario.v1.json`, `tests/contract/test_scenarios.py` | **dùng lại** (đọc YAML + kiểm schema) |
| Số hư cấu, h1 gắn cờ | `data/fixtures/phones.json`, `data/threat_seed.demo.json`, `spike.DEMO_H1` | **dùng lại** |
| Dọn job theo tiền tố | `jobs/queue.py::cancel_prefix` | **dùng lại** (+ xóa job `notify_guardian` eval bằng tiền tố khóa) |
| Percentile | `agents/spike.py::percentile` | **dùng lại** |

## Project Structure

### Documentation (this feature)

```text
specs/030-eval-smoke/
├── spec.md · plan.md · quickstart.md · tasks.md
├── contracts/README.md    # trỏ docs/schemas/eval_{cassette,report}.v1.json + fixture
└── evidence.md            # phase cuối
```

### Source Code (repository root)

```text
docs/schemas/eval_cassette.v1.json · docs/schemas/eval_report.v1.json
docs/schemas/fixtures/eval_cassette.v1.{valid,invalid}.json · docs/schemas/fixtures/eval_report.v1.{valid,invalid}.json
backend/src/hoicon/eval/__init__.py
backend/src/hoicon/eval/cases.py      # đọc suite + YAML, Scenario → RiskEvent + kịch bản trả lời (FR-002, FR-003)
backend/src/hoicon/eval/replay.py     # ReplayClient (FR-004)
backend/src/hoicon/eval/runner.py     # lái IncidentRuntime, thu kết quả, cô lập + dọn (FR-005, FR-010, FR-011)
backend/src/hoicon/eval/checks.py     # bộ kiểm tất định (FR-006)
backend/src/hoicon/eval/report.py     # chỉ số, so baseline, JSON + Markdown (FR-007…FR-009)
backend/src/hoicon/eval/cli.py        # argparse, exit code, SelectorEventLoop (FR-001)
backend/pyproject.toml                # [project.scripts] hoicon-eval = "hoicon.eval.cli:main"
backend/eval/suites/smoke.v1.json · backend/eval/cassettes/smoke/<id>.json (20) · backend/eval/baseline.json
backend/eval/.gitignore               # reports/
backend/tests/contract/test_eval_schemas.py
backend/tests/unit/test_eval_{cases,checks,report,replay}.py
backend/tests/integration/test_eval_smoke.py · backend/tests/integration/test_eval_mutations.py
.github/workflows/backend.yml         # bước smoke sau pytest
.claude/skills/run-eval/SKILL.md · docs/AGENTS.md · backend/README.md · docs/ROADMAP.md (dòng P2-15)
```

**Structure Decision**: gói `hoicon.eval` trong backend (dùng thẳng runtime/router, không lớp API); dữ liệu eval cạnh backend.

## Thiết kế & trade-off

- **Ánh xạ kịch bản → sự kiện** (bảng có test, trích ADR-001/`RiskEngine.kt` v`0.1.0-s1`):

  | `caller_flag` | `app_category` | `in_call`/`duration_bucket` | Kết quả |
  |---|---|---|---|
  | `trusted` | bất kỳ | bất kỳ | không sự cố (R0) |
  | `unknown`/`flagged` | `bank`/`wallet`/`securities` | đang gọi hoặc vừa gọi (≤ 10 phút) | R1: `critical` nếu `flagged` hoặc `5_15m`/`gt_15m`; ngược lại `high` |
  | `unknown`/`flagged` | `sideloaded` | đang/vừa gọi | R2 `critical` (ADR-001; **máy chưa cài R2** — ghi chú báo cáo) |
  | bất kỳ | `none` | — | không sự cố |

  Lưu ý F3: `tests/contract/test_scenarios.py::device_floor` dùng `high` cho sideloaded (cận dưới an toàn cho `expected`); eval
  theo ADR-001 ⇒ sàn `critical`. Cả hai thỏa `min_risk_level: high`; khác biệt ghi vào evidence, không sửa test cũ.
  `in_call=false` ⇒ cuộc gọi vừa kết thúc: `call.active=false`, `since_end_s=60` (trong cửa sổ R1). Id: xem FR-011 (nonce theo lượt).
  `duration_bucket` ⇒ `duration_s` đại diện: `lt_1m` 30, `1_5m` 180, `5_15m` 600, `gt_15m` 1200. `flagged` ⇒ h1 = `DEMO_H1`;
  `unknown` ⇒ h1 = SHA-256(`"hoicon:v1:"` + E164 của `unknown_caller`) tính lúc chạy, `last3` từ số hư cấu.
  Rủi ro lệch với Kotlin: ghi vào "Ghi chú" ROADMAP đề xuất vector luật dùng chung (làn A + B) — không làm ở spec này.
- **Trả lời người cao tuổi**: `q_caller_authority` ⇐ `claims_authority`; `q_asked_transfer` ⇐ `asks_transfer`;
  `q_know_caller` ⇐ `knows_caller`; thiếu ⇒ `unsure`. Lần trả lời đầu kèm `note = elder_note` (runtime chỉ giữ `note_flags`).
  Giới hạn 3 lượt `ask_elder` (chống vòng lặp) ⇒ vượt là vi phạm `graph_loop`.
- **Người giám hộ**: `{"timer": "t1"}` (sinh tin nhắc) rồi `{"decision": "scam"|"safe"}`; kỳ vọng outcome
  `resolved_prevented`/`resolved_safe`.
- **Thu tin**: đọc `jobs` loại `notify_guardian` theo khóa `<incident_id>:msg:` (payload `text`) + `interrupt.text` của
  `ask_elder`. Không chạy worker ⇒ không có gửi Zalo.
- **`ReplayClient`**: `parse(output_format=…)` lấy phản hồi kế tiếp theo node (`RiskAssessment` ⇒ `risk_scorer`,
  `GuardianBrief` ⇒ `intervention`); `{"error":"refusal"}` ⇒ trả `stop_reason="refusal"`; `"timeout"` ⇒ ném `TimeoutError`;
  hết danh sách ⇒ ném lỗi (router ⇒ fallback). Ghi `system` + `messages` đã nhận để quét PII. `usage` cố định ⇒ chi phí tính
  được nhưng ghi `cost_usd` thật = 0 trong báo cáo (phát lại).
- **Tất định**: `RiskEvent.id` = UUID5(case_id); id sự cố/thread `eval-<nonce8>-<case_id>` (nonce mới mỗi lượt vì
  `agent_runs.thread_id` + `jobs.idempotency_key` UNIQUE; nonce không vào chỉ số); thứ tự ca theo suite; `occurred_at` cố
  định; chỉ số không dùng độ trễ hay id.
- **DB riêng cho runner**: runner tự dựng engine/sessionmaker từ URL eval (không dùng `get_sessionmaker()` cache theo DB
  ứng dụng); `checkpoint_bytes` nhận `sessions`. Test tích hợp eval dùng `HOICON_EVAL_DATABASE_URL`, không có thì rơi về
  DB ứng dụng với `shared_db_ok=True` (CI), DB tắt ⇒ skip như các test khác.
- **`leak_pii`**: văn bản tự do (tin, nội dung gửi LLM đã ghi lại) ⇒ `mask_text(x) == x`; `agent_steps` và checkpoint chứa số
  hợp lệ (`duration_s`, timestamp) nên KHÔNG dùng `mask_text` — chỉ tìm chuỗi bí mật đã biết của ca (số điện thoại, h1,
  tên gói, `elder_note`, mã OTP trong kịch bản) trong bytes.
- **`must_call_tools`**: `threat.lookup_phone` ⇔ bước `ingest` có `threat` (và `flagged` với số gắn cờ).
- **Cô lập + dọn**: `try/finally` xóa `jobs` có khóa bắt đầu `eval-` và hủy timer; `agent_runs`/checkpoint giữ lại để xem
  `run_id` (DB eval xóa được bất kỳ lúc nào). Kiểm `HOICON_ENV != prod` và so URL DB trước khi mở pool.
- **Đột biến (FR-014)**: test dùng `monkeypatch` thay `incident_graph.raise_only` bằng hàm trả mức LLM, thay
  `texts.AI_DISCLOSURE`/mẫu, thay `_UNSAFE_SUMMARY` bằng regex không khớp gì ⇒ chạy 2–3 ca liên quan qua runner ⇒ khẳng định vi phạm.
- **Baseline**: JSON chỉ số tổng + theo ca (đạt/trượt); so sánh theo điểm %; `--write-baseline` chỉ chạy tay.
- **Hiệu năng**: một `IncidentRuntime.open` cho cả lượt; các ca chạy tuần tự (tất định); timer thật không chờ (resume trực tiếp).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
