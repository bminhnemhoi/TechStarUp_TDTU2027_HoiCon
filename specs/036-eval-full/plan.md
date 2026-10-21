# Implementation Plan: Eval full (`hoicon-eval --suite full|injection`)

**Branch**: `feat/w2-server` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: `specs/036-eval-full/spec.md`

## Summary

Mở rộng gói `hoicon.eval` (spec 030) từ 20 lên ≥ 100 ca mà không đổi runner, đồ thị, router, prompt hay hợp đồng. Thêm 50 kịch bản
hư cấu vào `data/scenarios/`, suite `full.v1.json` (110 id, ⊇ smoke) kèm bảng hành vi LLM ghi sẵn, bộ sinh cassette tất định
(`hoicon.eval.cassettes`), suite `injection` (lọc từ full), ngưỡng tuyệt đối của Gate M3 và baseline riêng `baseline-full.json`,
báo cáo tách ca provisional, test đột biến trên full, bước CI nếu < 2 phút.

**Quyết định kỹ thuật** (Tiến giao Wave 2; chạy một mạch, §2.6):
- F1: "ca" = một tệp kịch bản (hợp đồng ép `…_NNN`); +50 kịch bản mới thay vì biến thể trong cùng tệp.
- F2: cassette ngoài smoke được SINH từ `Case` + loại hành vi (không viết tay 90 tệp); tệp sinh được commit và có test "đĩa = bộ sinh".
- F3: cassette smoke viết tay giữ nguyên; full dùng lại qua danh sách thư mục cassette `full → smoke`.
- F4: `injection` = ca `injection: true` của full, không có baseline riêng, chỉ ngưỡng tuyệt đối.
- F5: không đổi `docs/schemas/`; provisional suy từ `draft` từng ca, báo ở Markdown/CLI/baseline.

## Technical Context

**Language/Version**: Python 3.12 (`uv`) · **Dependencies**: không thêm (PyYAML, jsonschema đã có) · **Storage**: Postgres DB eval, không migration
**Testing**: `uv run --directory backend pytest` · `ruff` · `hoicon-eval --suite smoke|full`
**Performance Goals**: full < 120 s (kỳ vọng ≈ 40 s: smoke 20 ca ≈ 6 s) · **Constraints**: không mạng, không khóa API, tất định, không tự ghi baseline
**Scale/Scope**: 110 ca (73 lừa đảo/37 hợp lệ…, xem evidence), 20 cassette tay + 90 sinh

## Constitution Check

| # | Nguyên tắc | Đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn | Không | Không đụng Android |
| II | Riêng tư | **Có** (đo) | Kịch bản/cassette hư cấu (dải `0900000xxx`); `leak_pii` quét tin, nội dung gửi LLM, `agent_steps`, checkpoint cho cả 110 ca |
| III | LLM chỉ nâng | **Có** (đo) | ≥ 25% ca đối kháng (hạ mức, nhét số/link, làm theo lệnh, refusal/timeout/malformed/missing) |
| IV | Công khai AI | **Có** (đo) | 100% tin + câu hỏi; DB riêng + `is_demo` |
| V | Hợp đồng trước | **Có** | `scenario.v1`/`eval_cassette.v1` giữ nguyên; test hợp đồng cho suite full viết trước code |
| VI | UX | Gián tiếp | `panic_wording`/`promise_refund` trên mọi mẫu tin |
| VII | Bằng chứng trung thực | **Có** | `synthetic` + provisional ghi ở mọi báo cáo; phần LLM thật BLOCKED, không giả số |
| VIII | Ít code | **Có** | Dùng lại runner/checks/report/CLI; chỉ thêm bộ sinh cassette + chọn suite + ngưỡng |
| IX | Chặn phát hành | Không | Công cụ dev/CI |

Kết quả: **ĐẠT**.

## Tái sử dụng *(mandatory)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới |
|---|---|---|
| Chạy đồ thị thật, thu kết quả | `eval/runner.py::run_suite` | **dùng lại**; mở rộng nhận danh sách thư mục cassette theo suite |
| Bộ kiểm tất định | `eval/checks.py` | **dùng lại** nguyên |
| Chỉ số, so baseline, báo cáo | `eval/report.py` | **mở rộng**: ngưỡng tuyệt đối theo suite, provisional |
| CLI + mã thoát | `eval/cli.py` | **mở rộng**: `full`/`injection`, `--compare baseline-full`, số ca tối thiểu theo suite |
| Đọc suite + kịch bản | `eval/cases.py::load_suite` | **mở rộng**: `full`, `injection`, tra cassette theo suite |
| Hình dạng cassette | `docs/schemas/eval_cassette.v1.json`, 20 cassette smoke làm mẫu | **dùng lại**; bộ sinh chỉ xuất đúng hình dạng đó |
| Mẫu test đột biến | `tests/integration/test_eval_mutations.py`, `eval_support.py` | **dùng lại** mẫu, thêm bản chạy trên tập con full |
| Mẫu kiểm kịch bản | `tests/contract/test_scenarios.py` | **dùng lại** nguyên (110 kịch bản vẫn qua) |
| Danh sách cụm hoảng sợ/hoàn tiền | `eval/checks.py::PANIC_PHRASES`, `REFUND_PHRASES` | **dùng lại** để bộ sinh tránh tự phạm |

## Project Structure

```text
specs/036-eval-full/{spec,plan,tasks,evidence}.md · contracts/README.md
data/scenarios/<50 kịch bản mới>.yaml
backend/eval/suites/full.v1.json                # cases[110] + behaviors{}
backend/eval/cassettes/full/<id>.json           # 90 tệp sinh (smoke dùng lại cassette smoke)
backend/eval/baseline-full.json                 # --write-baseline, chạy tay
backend/src/hoicon/eval/cassettes.py            # bộ sinh tất định + CLI `python -m hoicon.eval.cassettes write|check`
backend/src/hoicon/eval/{cases,runner,report,cli}.py   # mở rộng nhỏ
backend/tests/contract/test_eval_full_suite.py  # thành phần suite, cassette = bộ sinh
backend/tests/unit/test_eval_cassettes.py · test_eval_report.py (bổ sung) · test_eval_cases.py (bổ sung) · test_eval_cli.py (bổ sung)
backend/tests/integration/test_eval_full.py · test_eval_full_mutations.py
.github/workflows/backend.yml                   # bước full (nếu < 2 phút)
backend/README.md · docs/ROADMAP.md (dòng P2-15, P2-18)
```

## Thiết kế & trade-off

- **Bảng hành vi** (khóa `behaviors[id]` trong `full.v1.json`; thiếu khóa ⇒ `honest`):

  | Loại | Cassette sinh | Rào được đo |
  |---|---|---|
  | `honest` | scorer ≥ sàn (lừa đảo leo thang `critical` nếu người cao tuổi xác nhận bị đòi chuyển tiền), tóm tắt sạch | đường vui, recall/báo nhầm |
  | `lower` | scorer trả `none` cả hai lần | `raise_only` giữ mức sàn |
  | `leak_phone` | tóm tắt chứa số điện thoại hư cấu | `_UNSAFE_SUMMARY` + `leak_pii` |
  | `leak_link` | tóm tắt chứa `https://vi-du.example` | như trên (link/tên miền) |
  | `obey_injection` | scorer hạ mức + tóm tắt lặp lại câu chèn lệnh kèm link | không làm theo lệnh chèn, giữ sàn |
  | `refusal` / `timeout` / `malformed` / `missing` | scorer và/hoặc tóm tắt lỗi | rơi về mẫu soạn sẵn |

  Ca không kích hoạt luật (R0 / không mở app tài chính): cassette rỗng (không dùng).
- **Câu hỏi người cao tuổi**: phần tử đầu của `elder_answers` ⇒ `ask_question` đầu (`claims_authority`→`q_caller_authority`,
  `knows_caller`→`q_know_caller`, `asks_transfer`→`q_asked_transfer`), lần chấm thứ hai `none` (như cassette smoke).
- **Tra cassette**: `full`/`injection` ⇒ `[cassettes/full, cassettes/smoke]`, lấy tệp đầu tiên có; thiếu ⇒ lỗi cấu hình (exit 2).
- **Ngưỡng tuyệt đối**: `absolute_failures(metrics, suite)`; smoke giữ 2 điều kiện cũ, full/injection thêm recall ≥ 0,90 và nhầm ≤ 0,10.
- **Số ca tối thiểu theo suite**: smoke 20, full 100, injection 10 (thay hằng `SMOKE_CASES`).
- **Provisional**: `provisional = sum(o.case.draft)`; Markdown thêm mục; baseline-full lưu `provisional_cases`.
- **Tốc độ**: ≈ 0,3 s/ca ⇒ ≈ 35–40 s cho 110 ca; vượt 120 s thì tách job CI riêng.

## Complexity Tracking

Không vi phạm Hiến chương cần biện minh.
