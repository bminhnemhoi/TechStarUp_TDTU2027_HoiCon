# Bằng chứng nghiệm thu: Spec 003 — danh sách đe dọa HMAC, MCP `threat` có token + hạn mức, bench so model, trần chi tiêu bền

**Trạng thái: hiện thực xong, chờ Tiến duyệt.** Code, test, tài liệu, review bảo mật (0 Critical/High) đã xong (15/10/2026, máy dev Linux x86_64 16 lõi, Postgres 17 Docker 15432). Còn: các mục Medium/Low "chưa làm" (xem Review), reviewer chưa đọc lại phần đã sửa, và các mục BLOCKED bên ngoài. Không commit/push.

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Môi trường (n) | Đạt? | Bằng chứng |
|---|---|---|---|---|---|
| SC-001 | 0 h1 trong mọi bảng sau khi nạp + chạy đồ thị | 0: quét `threat_indicators`, checkpoint, `agent_steps`; truy vấn DB dev thật: 0 dòng khớp số điện thoại hoặc h1 demo ở `agent_steps`, `jobs.payload`, `messages_out.error`, `threat_indicators` | Postgres dev, test + truy vấn tay | Đạt (máy dev). CI: BLOCKED (chưa có PR) | `test_threat_indicators.py`, `test_incident_graph.py`, `privacy-audit` mục 2 |
| SC-002 | 100% không/sai token ⇒ 401, không chạy tool; vượt hạn mức ⇒ 429 | 401 (không header, sai token, scheme lạ, token rỗng, chưa cấu hình client), 429 + `Retry-After`; phiên `curl` thật: 401, 401, 200 ×3 (`verdict=flagged`), 429 (`retry-after` 14) | ASGI test + uvicorn cổng 18010 | Đạt | `test_mcp_auth.py` (12), `test_mcp_http.py` (7), phiên curl |
| SC-003 | smoke ĐẠT, so baseline +0,0 điểm % | 20 ca · recall 100% · báo nhầm 0% · vi phạm 0 · công khai AI 100% · +0,0/+0,0 điểm %; ≈ 5,2 s tổng | máy dev, DB `hoicon_eval`, khóa băm GIẢ | Đạt (máy dev). CI: BLOCKED | `hoicon-eval --suite smoke --compare baseline` |
| SC-004 | pytest ≥ 507 + test mới, ruff sạch | **607 passed, 0 skipped** (507 + 100); `ruff check` + `format --check` sạch (105 file) | máy dev | Đạt | lệnh bên dưới |
| SC-005 | tra cứu p95 ≤ 20 ms | 10,3 / 11,1 / 12,1 ms (n = 200, 3 lần) | Linux x86_64 16 lõi, Postgres Docker local | Đạt (máy dev; VPS: BLOCKED P1-09) | `test_lookup_p95` |
| SC-006 | bảng Haiku 4.5 vs 5.5 (n = 20) | **BLOCKED: chờ khóa API (P0-08).** Chỉ có số điều phối không khóa: `llm_mode: "fallback"`, fallback 100%, p50 ≈ 0,04 s/lượt — KHÔNG phải số của model | — | BLOCKED | lệnh chạy sẵn bên dưới |

Lệnh chạy khi có khóa: `uv run --directory backend python -m hoicon.agents.spike bench --n 20 --model claude-haiku-4-5 --json h45.json` và `--model claude-haiku-5-5 --json h55.json`.

## Yêu cầu chức năng (FR) ↔ test

| FR | Test | Kết quả |
|---|---|---|
| FR-001 | `test_schema_0004.py`; alembic up → down → up | Đạt |
| FR-002 | `test_threat_indicators.py` (idempotent, lô hỏng không ghi gì, prod từ chối, chỉ in số lượng) + `test_threat_schemas.py` | Đạt |
| FR-003/004 | `test_threat_indicators.py`, `test_threat_lookup.py`, `test_pii_kids.py`, `test_incident_graph.py` (lỗi tra cứu ⇒ `unknown`+`OperationalError`, sự cố vẫn tới `ask_elder`) | Đạt |
| FR-005/006/007/009 | `test_mcp_auth.py`, `test_mcp_http.py` (streamable HTTP thật, log không lộ h1/token/hash/IP) | Đạt |
| FR-008 | `test_mcp_token.py` | Đạt |
| FR-010 | `test_bench_json.py` (hợp đồng, chỉ run của bench, model lạ ⇒ exit 2, khóa rỗng = không khóa) | Đạt |
| FR-011 | `test_llm_budget.py` (bền qua restart, ranh giới 00:00 VN, giữ chỗ đang bay, lỗi DB ⇒ `budget_unknown`) | Đạt |
| FR-012 | `test_eval_smoke.py` (runner nạp seed, thiếu khóa ⇒ `IsolationError`) + `backend.yml` (khóa giả công khai) | Đạt; CI BLOCKED |
| FR-013 | các test trên | Đạt |
| FR-014 | ADR-009 §9/§10, DATA-MODEL, AGENTS, spike §3–4, `backend/README.md`, `.env.example`, ROADMAP; MASTER-PLAN §3 đã có sẵn | Đạt |
| FR-015 | bảng SC-006 + mục BLOCKED | Đạt (ghi BLOCKED) |

Độ nhạy của test: 3 đột biến (bỏ xác thực; bỏ lọc `expires_at`; trần không đọc DB) ⇒ 8 / 1 / 5 test đỏ; hoàn nguyên thì xanh.

## Cổng các tầng

| Tầng | Kết quả |
|---|---|
| Backend | ruff sạch · **607 passed** · alembic `0004` up/down/up · gitleaks 0 phát hiện trên mọi đường đã sửa |
| Eval | ĐẠT, +0,0 điểm % (khóa băm giả đặt trên dòng lệnh) |
| Truy vết | `check-spec-trace.py`: 5 spec, 0 lỗi |
| Android / Web / máy ảo | SKIPPED: không đụng `apps/**` |
| Windows | chưa chạy |

## Phát hiện trong lúc làm (đã sửa, có test)

1. Bench báo "có khóa API" sai khi `.env` có dòng khóa rỗng (`is not None` vs `bool`) — `test_an_empty_key_counts_as_no_key`.
2. Fixture `seeded_threat` ban đầu xóa theo `list_version` nên xóa luôn dòng demo nạp bằng khóa thật của máy dev — nay chỉ xóa đúng HMAC khóa giả.
3. Test trần chi tiêu treo vô hạn vì DB dev đã có chi tiêu của test khác — trần tính theo chi tiêu hiện có + biên, có `asyncio.timeout`.
4. SC-001 đòi quét `agent_steps` mà test chưa quét — đã thêm (converge, MEDIUM).
Ghi chú trung thực: `test_mcp_token.py` và `test_pii_kids` viết xong code ngay sau test nên chưa chứng kiến đỏ riêng cho mcp_token (các test còn lại đã thấy đỏ trước).

## Review

| Reviewer | Kết quả | Đã xử lý |
|---|---|---|
| `privacy-audit` | Sạch: 0 số điện thoại thô, 0 h1 trong DB dev; các khớp ở mục 1b/1c là chú thích/thông báo, không phải dữ liệu | — |
| `security-privacy-reviewer` | **0 Critical · 0 High · 4 Medium · 10 Low** (reviewer chỉ đọc + thăm dò ASGI, không chạy pytest/DB) | Xem bảng dưới. Reviewer ĐÃ đọc lại phần sửa: các mục #1,#5,#6,#8,#12 đạt; #2,#3,#7,#14 đạt một phần (phần còn lại ở ROADMAP); lỗi mới L1 (lỗi không tính tiền bị tính ⇒ đã sửa: chỉ tính khi quá hạn), L3 (`SeedError` ở eval ⇒ đã sửa thành `IsolationError`), #14 engine eval (đã sửa `hide_parameters`); L2 (`env` mặc định `dev` nằm trong danh sách trắng ⇒ phụ thuộc ROADMAP (c)) và L4 (body chunked chưa chặn, Caddy 012) chưa làm. 607 test xanh sau các sửa này |
| `/ponytail-review` | Chưa chạy (không phải reviewer độc lập nếu tự chạy) | — |

### Xử lý phát hiện của `security-privacy-reviewer`

| # | Mức | Xử lý |
|---|---|---|
| 1 | TB | **Sửa**: lời gọi lỗi/quá hạn ghi chi phí = phần giữ chỗ vào `agent_steps` (trước đó ghi 0 ⇒ trần bị vượt âm thầm). Test `test_a_failed_call_is_still_charged_its_reservation` |
| 2 | TB | **Sửa một phần**: đọc chi tiêu có `asyncio.timeout(1 s)` ⇒ `budget_unknown` (test). **Chưa làm**: chỉ mục `agent_steps(at)` (cần migration mới) — ghi ROADMAP "Ghi chú" |
| 3 | TB | **Sửa**: nạp seed `is_demo` theo danh sách trắng `dev/test/ci` (quên đặt `HOICON_ENV=prod` vẫn bị từ chối). **Chưa làm**: lọc `is_demo` ở tra cứu prod / đưa `is_demo` vào `ThreatVerdict` — ghi ROADMAP |
| 4 | TB | **Chưa làm**: kiểm pepper/số dòng ở `/readyz` (lỗi tra cứu hiện chỉ có dòng log `warning`) — ghi ROADMAP |
| 5 | Thấp | **Sửa**: websocket bị đóng (1008), chỉ `lifespan` đi thẳng. Test |
| 6 | Thấp | **Sửa một phần**: dòng log nay nằm trong `finally` (test). Còn: hạn mức tính cả `initialize`/`tools/list`, cửa sổ cố định, chỉ đúng một worker (đã ghi ở tài liệu) |
| 7 | Thấp | **Sửa**: `GET` ⇒ 405 sau xác thực; `Content-Length` > 64 KB ⇒ 413. Test. Body chunked chưa chặn (Caddy, 012) |
| 8 | Thấp | **Sửa**: `fullmatch` cho h1/`last3` (`$` cho lọt `\n`). Test |
| 9, 10, 11, 13 | Thấp | **Chưa làm**, ghi ROADMAP: lệnh gỡ số bị gắn cờ nhầm + DPIA; `list_version` so chuỗi; kid cố định (1, 2); eval `--shared-db-ok` để lại dòng demo |
| 12 | Thấp | **Sửa**: chú thích sai số trần chi tiêu nêu đúng (≤ số lời gọi đồng thời) |
| 14 | Thấp | **Sửa**: engine `hide_parameters=True` (thông điệp lỗi SQLAlchemy không kèm HMAC). Chưa xác minh bằng lỗi tool thật |

## Còn hở

- Mục "Chưa làm" ở bảng trên (đã ghi ROADMAP); reviewer chưa đọc lại phần đã sửa.
- SC-006 (khóa API, P0-08); p95 trên VPS (P1-09); CI trên PR (chưa commit/push); Windows.
- Hạn mức MCP đếm trong bộ nhớ ⇒ chỉ đúng với một tiến trình (ADR-002); `/mcp/threat` chưa mở ra Internet (spec 012).
