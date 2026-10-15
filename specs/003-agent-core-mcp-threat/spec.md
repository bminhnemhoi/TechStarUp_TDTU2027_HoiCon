# Feature Specification: Hoàn tất lõi tác tử P1-S4 — danh sách đe dọa trong DB (HMAC), MCP `threat` có token + giới hạn tần suất, bench so model, trần chi tiêu bền

**Feature Branch**: `feat/003-agent-core-mcp-threat`

**Created**: 2026-10-15

**Status**: Ready — quyết định kỹ thuật T1–T7 (plan.md) do Opus soạn theo ủy quyền của Tiến (kỹ sư chủ trì, 15/10/2026);
áp dụng mặc định khi giao implement, chạy tự hành một mạch (MASTER-PLAN §2.6). Spec 003 trước đây là "lite" (chỉ bench);
Tiến nâng thành spec đầy đủ khi giao "P1-S4 Lõi tác tử & MCP threat" ngày 15/10.

**Input**: Tiến giao 15/10/2026: "soạn Spec + Plan cho Đợt 3 (… Làn B: P1-S4 Lõi tác tử & MCP threat) theo chế độ tự hành một mạch".

## Truy vết *(mandatory)*

- **Mã ROADMAP**: P1-S4 (phần còn mở: so model, MCP `threat` không xác thực, danh sách đe dọa demo) + **kéo sớm** phần hạ
  tầng của P2-11 (bảng `threat_indicators` + HMAC, token + giới hạn tần suất cho `/mcp/threat`). Phần còn lại của P2-11 (tác tử
  xác minh, `rescore`, `/v1/lookups`, E10) vẫn ở spec 026. Trần chi tiêu bền: mục "P2-04" trong `docs/spikes/P1-S4-loi-tac-tu.md` §4
- **User story PRD**: US-06 (nền: tra cứu có nguồn) · US-05 (tác tử chấm rủi ro, chi phí có trần)
- **ADR liên quan**: ADR-009 §9 (MCP chỉ dev tới khi có token + giới hạn tần suất) và §10 (model chờ đo) — **cập nhật** ADR-009,
  không đổi quyết định; ADR-006 (máy chủ chỉ lưu `HMAC(pepper[kid], h1)` + 3 số cuối); ADR-002 (một tiến trình); ADR-004
- **Gate nghiệm thu**: G1 (08/11) — báo cáo spike P1-S4 đóng được phần "MCP không xác thực" và có công cụ so model; số model
  thật chờ khóa (P0-08)
- **Phụ thuộc spec**: 002 (pepper/khóa trong cấu hình, migration 0003), 030 (eval smoke phải vẫn ĐẠT). Khóa Anthropic (P0-08)
  **không chặn** (§2.6): phần cần khóa ⇒ BLOCKED, phần còn lại làm hết
- **Làn**: B — `backend/**`, `data/threat_seed.demo.json`, `docs/{adr/ADR-009*,DATA-MODEL.md,AGENTS.md,spikes/P1-S4-loi-tac-tu.md,MASTER-PLAN.md}`,
  `docs/ROADMAP.md` (dòng P1-S4), `.github/workflows/backend.yml`. Không đụng `apps/**`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Danh sách đe dọa nằm trong Postgres dạng HMAC, không còn h1 trên đĩa máy chủ (Priority: P1)

Người vận hành nạp danh sách số lừa đảo (hiện là tệp demo số hư cấu) bằng một lệnh. Máy chủ chỉ lưu `HMAC(pepper[kid], h1)` +
3 số cuối (nếu có) + nguồn, độ tin cậy, thủ đoạn, hạn dùng. Đồ thị sự cố và MCP tra trong bảng này.

**Why this priority**: ADR-006 cấm lưu h1 (dò ngược được ra số điện thoại), nhưng `lookup_h1` hiện đọc h1 trong tệp JSON. Danh
sách thật (P3) không thể nạp theo cách đó.

**Independent Test**: nạp tệp demo vào DB test ⇒ `lookup` số gắn cờ trả `flagged`, số khác `unknown`; quét byte bảng
`threat_indicators` không có h1 nào.

**Acceptance Scenarios**:

1. **Given** DB trống, **When** chạy lệnh nạp với `data/threat_seed.demo.json`, **Then** có 1 dòng `is_demo = true`, cột giá
   trị là HMAC 64 hex, không cột nào chứa h1; chạy lại lần hai không thêm dòng.
2. **Given** dòng đã quá `expires_at`, **When** tra, **Then** `unknown`.
3. **Given** `HOICON_ENV=prod`, **When** nạp tệp có `is_demo: true`, **Then** từ chối (exit ≠ 0), không ghi gì.
4. **Given** tra danh sách lỗi (DB lỗi, thiếu pepper), **When** sự cố khởi động, **Then** sự cố vẫn chạy với `threat =
   unknown` + mã lỗi trong trace; mức rủi ro không thấp hơn `rule_floor` (luật 5); không bao giờ chặn đường cảnh báo.

---

### User Story 2 - `/mcp/threat` chỉ trả lời người có token, và không cho dò hàng loạt (Priority: P1)

Công cụ của đội (Claude qua MCP connector, script tra cứu) gọi `/mcp/threat` kèm `Authorization: Bearer <token>`. Không có
hoặc sai token ⇒ 401. Gọi quá nhanh ⇒ 429 kèm `Retry-After`. Điều này cho phép gắn MCP ở mọi môi trường (không còn "chỉ dev").

**Why this priority**: ADR-009 §9 và báo cáo spike ghi rõ: h1 không có muối ⇒ ai gọi được MCP thì thử hết số VN để dò danh
sách. Đây là lỗ hổng duy nhất còn mở của P1-S4.

**Independent Test**: pytest gọi MCP qua HTTP thật (ASGI): không token / token sai / token đúng / vượt hạn mức.

**Acceptance Scenarios**:

1. **Given** không có header `Authorization`, **When** gọi `tools/call lookup_phone`, **Then** 401 + `WWW-Authenticate: Bearer`,
   tool không chạy.
2. **Given** token đúng, **When** gọi với h1 gắn cờ, **Then** 200 và `flagged` kèm nguồn, độ tin cậy, thủ đoạn, phiên bản danh sách.
3. **Given** token đúng, **When** gọi vượt hạn mức phút, **Then** 429 + `Retry-After`; hạn mức của token khác không bị ảnh hưởng.
4. **Given** máy chủ chưa cấu hình token nào, **When** gọi bất kỳ, **Then** 401 (đóng mặc định).
5. **Given** bất kỳ yêu cầu nào, **When** ghi log, **Then** log chỉ có tên client, mã trạng thái, verdict — không có h1, không
   có token.

---

### User Story 3 - Một lệnh so được Haiku 4.5 với Haiku 5.5 khi có khóa (Priority: P2)

Tiến có khóa API thì chạy `spike bench --model <id> --n 20 --json <tệp>` cho từng model. Kết quả JSON ghi độ trễ p50/p95 theo
lượt, tỷ lệ rơi về mẫu, chi phí trung bình mỗi sự cố, có khóa hay không. Không có khóa ⇒ vẫn chạy (đo điều phối), JSON ghi
`llm_mode: "fallback"` để không ai nhầm là số model.

**Why this priority**: ROADMAP P1-S4 và ADR-009 §10 đòi số so model; công cụ phải sẵn để chạy ngay khi P0-08 xong.

**Independent Test**: bench với client giả (2 model) ⇒ JSON đúng hợp đồng, `llm_mode` đúng.

**Acceptance Scenarios**:

1. **Given** không khóa, **When** `bench --model claude-haiku-4-5 --n 3 --json out.json`, **Then** JSON có `llm_mode:
   "fallback"`, `fallback_rate: 1.0`, 3 lượt đo.
2. **Given** model không có trong bảng giá, **When** chạy, **Then** exit 2 và nói rõ model chưa có giá.

---

### User Story 4 - Trần chi tiêu LLM không bị reset khi tiến trình khởi động lại (Priority: P3)

Trần chi tiêu/ngày hiện đếm trong bộ nhớ: tiến trình sập và khởi động lại nhiều lần trong ngày thì trần mất tác dụng. Router
cộng chi tiêu đã ghi trong `agent_steps` của ngày (giờ Việt Nam) với phần đang giữ chỗ trong tiến trình.

**Why this priority**: an toàn tài chính khi có khóa thật; nhỏ, nhưng có thể cắt nếu trễ.

**Independent Test**: ghi sẵn `agent_steps.cost_usd` bằng trần ⇒ router mới khởi tạo trả fallback `budget_exhausted`.

**Acceptance Scenarios**:

1. **Given** `agent_steps` hôm nay đã cộng = trần, **When** router mới gọi LLM, **Then** rơi về mẫu với `budget_exhausted`,
   không gọi client.
2. **Given** chi tiêu hôm qua = trần, hôm nay = 0, **When** gọi, **Then** được gọi.

### Edge Cases

- **h1 sai định dạng / số thô**: `ValueError` như hiện tại; MCP trả lỗi tool, không log giá trị.
- **Xoay pepper (kid 2)**: tra theo mọi kid đã cấu hình; nạp dùng kid hiện hành; dòng kid cũ vẫn tra được.
- **Gửi trùng / chạy lại lệnh nạp**: upsert theo `(kind, value_kid, value_hmac)`; cập nhật `last_seen`, nguồn, độ tin cậy.
- **Nhiều tiến trình** (sau này): hạn mức MCP đếm trong bộ nhớ ⇒ chỉ đúng với một tiến trình (ADR-002); ghi rõ, đổi khi scale.
- **Diễn tập / demo**: dòng demo mang `is_demo`; prod từ chối nạp; eval nạp vào DB eval.
- **LLM quá hạn / hết ngân sách**: không đổi — fallback mẫu (ADR-009).
- **Eval smoke**: `flagged` trong kịch bản phải vẫn ra `flagged` (runner nạp danh sách demo vào DB eval).
- **Token lộ**: thu hồi bằng cách xóa hash khỏi cấu hình và khởi động lại; máy chủ không lưu token thô.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Migration `0004` MUST tạo bảng `threat_indicators` theo `docs/DATA-MODEL.md` (bổ sung cột `tactic`, `list_version`,
  `is_demo`): `id`, `kind` (`phone`), `value_hmac` (64 hex), `value_kid`, `last3` (tùy chọn), `source`, `confidence` (0–1),
  `tactic`, `list_version`, `is_demo`, `first_seen`, `last_seen`, `expires_at` (tùy chọn); khóa duy nhất
  `(kind, value_kid, value_hmac)`. Không có cột nào lưu h1. Có `downgrade`.
- **FR-002**: Lệnh `python -m hoicon.ops.threat_list load <tệp>` MUST nạp idempotent (upsert), tính HMAC lúc nạp bằng
  `domain.pii.hmac_h1`, từ chối h1 sai định dạng (cả lô, không ghi một phần), từ chối tệp `is_demo` khi `env=prod`, chỉ in số
  dòng thêm/cập nhật (không in h1, không in HMAC).
- **FR-003**: Tra cứu MUST đi qua một hàm async duy nhất (`lookup_h1(sessions, h1)` hoặc tên tương đương) tra theo HMAC với mọi
  kid đã cấu hình; dòng hết hạn ⇒ `unknown`; trả `ThreatVerdict` cùng hình dạng hiện tại (`verdict`, `source`, `confidence`,
  `tactic`, `list_version`).
- **FR-004**: `IncidentRuntime.start` MUST dùng tra cứu mới; lỗi tra cứu ⇒ `threat = {"verdict": "unknown", "error": <tên lớp lỗi>}`,
  sự cố vẫn chạy; h1 và tên gói vẫn không vào state/checkpoint (test quét byte hiện có vẫn xanh).
- **FR-005**: `/mcp/threat` MUST yêu cầu `Authorization: Bearer <token>` cho mọi yêu cầu; máy chủ chỉ giữ SHA-256 của token theo
  tên client (cấu hình); so sánh thời gian hằng; thiếu/sai/không cấu hình ⇒ 401 + `WWW-Authenticate: Bearer`. Kiểm Host của SDK
  giữ nguyên.
- **FR-006**: `/mcp/threat` MUST giới hạn tần suất theo client: mặc định 30 yêu cầu/phút và 1.000 yêu cầu/ngày (cấu hình
  được); vượt ⇒ 429 + `Retry-After` (giây), tool không chạy. Đếm trong bộ nhớ tiến trình (ADR-002).
- **FR-007**: MCP MUST được gắn ở mọi môi trường (bỏ điều kiện `env == "dev"`), vì đã có FR-005/FR-006. Lifespan chạy
  session manager như hiện tại.
- **FR-008**: Lệnh `python -m hoicon.ops.mcp_token new --client <tên>` MUST sinh token ngẫu nhiên (≥ 32 byte, `secrets`), in token
  **một lần** và dòng cấu hình chứa hash để người dùng tự dán vào `.env` (agent không đọc/ghi `.env`).
- **FR-009**: Mỗi yêu cầu MCP MUST ghi một dòng log: tên client, mã trạng thái, tool, verdict (nếu có), độ trễ — không có h1,
  token, hash token, IP đầy đủ.
- **FR-010**: `spike bench` MUST nhận `--model` (ghi đè `llm_fast_model`, phải có trong `MODELS`) và `--json <tệp>`; JSON gồm
  `model`, `llm_mode` (`live`/`fallback`), `n`, độ trễ p50/p95/max theo lượt, `fallback_rate`, `cost_usd_avg`, `measured_at`,
  `host` (mô tả máy, không định danh người). Thiếu khóa ⇒ `llm_mode: "fallback"`.
- **FR-011**: `LlmRouter` MUST tính trần ngày = `SUM(agent_steps.cost_usd)` của ngày hiện tại theo giờ `Asia/Ho_Chi_Minh` +
  giữ chỗ đang bay trong tiến trình; lỗi đọc DB ⇒ rơi về mẫu (`budget_unknown`), không gọi LLM (đóng mặc định). Router không
  có `sessions` (test đơn vị cũ) giữ hành vi hiện tại.
- **FR-012**: `hoicon-eval --suite smoke` MUST vẫn ĐẠT, so baseline +0 điểm %: runner nạp `data/threat_seed.demo.json` vào DB
  eval trước khi chạy (idempotent). CI bước eval có pepper giả dùng riêng cho test (không phải bí mật).
- **FR-013**: Test MUST phủ: nạp idempotent + từ chối prod/h1 sai + quét byte không có h1; tra `flagged`/`unknown`/hết hạn/kid
  cũ; lỗi tra cứu ⇒ `unknown` và sự cố vẫn tới `ask_elder`; MCP 401 (không token, sai token, không cấu hình), 200, 429 +
  `Retry-After`, tách hạn mức theo client; log không chứa h1/token (caplog); bench JSON; trần chi tiêu bền.
- **FR-014**: Tài liệu MUST cập nhật: ADR-009 §9 (token + giới hạn tần suất đã có; vẫn chưa mở ra Internet tới khi 012 quyết
  Caddy) và §10 (công cụ so model sẵn sàng, số chờ khóa); `docs/DATA-MODEL.md` (dòng `threat_indicators`); `docs/AGENTS.md`
  (mục MCP); `docs/spikes/P1-S4-loi-tac-tu.md` §4; `backend/README.md` (lệnh nạp, tạo token, bench); MASTER-PLAN §3 (003 thành
  spec đầy đủ, 026 bớt phần MCP token); ROADMAP dòng P1-S4.
- **FR-015**: Phần cần khóa API (bench thật Haiku 4.5 vs 5.5, chốt model ở ADR-009 §10) và đo p95 trên VPS (P1-09) MUST được ghi
  BLOCKED trong tasks/evidence kèm lệnh chạy sẵn, không giả số.

### Key Entities

- **ThreatIndicator** (`threat_indicators`, mới — `docs/DATA-MODEL.md` §bảng tra cứu): một số điện thoại bị gắn cờ, chỉ lưu
  HMAC + 3 số cuối + nguồn + độ tin cậy + thủ đoạn + phiên bản danh sách + cờ demo + hạn dùng.
- **McpClient** (cấu hình, không vào DB): tên client ↔ SHA-256(token) + hạn mức.
- **BenchReport** (tệp JSON ngoài repo, không vào DB): kết quả một lần bench.

## Bất biến an toàn *(mandatory)*

- **Dừng an toàn** (I): không đụng tới Android. Đường cảnh báo máy chủ (`fast_alert`) không phụ thuộc tra cứu (lỗi ⇒ `unknown`).
- **LLM chỉ nâng** (III): không đổi node, prompt hay `raise_only`. `flagged` vẫn đẩy mức lên `critical` như cũ. Trần chi tiêu đóng
  mặc định ⇒ fallback mẫu.
- **Công khai AI** (IV): không có tin mới. MCP chỉ trả dữ liệu tra cứu, không gửi tin.

## Quyền riêng tư & đồng ý *(mandatory)*

| Dữ liệu mới / thay đổi | Dạng lưu | Mục đích đồng ý | Hạn lưu | Gửi LLM? |
|---|---|---|---|---|
| Số bị gắn cờ trong danh sách đe dọa | `HMAC(pepper[kid], h1)` + 3 số cuối; không h1 | không cần (dữ liệu về kẻ gian từ nguồn công khai/demo, không phải người dùng) | tới `expires_at` (mặc định nguồn quyết; demo không hạn) | Không (LLM chỉ thấy `verdict`) |
| Token MCP | chỉ SHA-256 trong cấu hình | — | tới khi thu hồi | Không |
| Log MCP | tên client, mã, verdict, độ trễ | — | theo log ứng dụng | Không |
| Bench JSON | số đo, không PII | — | tệp tạm ngoài repo | Không |

Quyền Android mới: không có. `privacy-audit` + `security-privacy-reviewer` bắt buộc (đụng xác thực, PII băm, MCP).

## UX người cao tuổi

Không có màn hình hay câu chữ mới.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 h1 trong mọi bảng sau khi nạp + chạy đồ thị (quét byte `threat_indicators`, checkpoint, `agent_steps`) — đo trên:
  Postgres 17 dev (Docker 15432) + CI.
- **SC-002**: 100% yêu cầu MCP không token/sai token bị 401 và không chạy tool (n ≥ 3 ca); vượt hạn mức ⇒ 429 (n = hạn mức + 1).
- **SC-003**: `hoicon-eval --suite smoke` ĐẠT, so baseline +0,0 điểm % — đo trên: máy dev (DB eval) + CI.
- **SC-004**: `pytest` toàn bộ xanh (≥ 507 + test mới), `ruff` sạch — máy dev + CI.
- **SC-005**: tra cứu p95 ≤ 20 ms trên DB dev (n = 200, đo trong test/bench, ghi máy) — không làm chậm `start`.
- **SC-006** *(BLOCKED tới P0-08)*: bảng so Haiku 4.5 vs 5.5 (n = 20 mỗi model): p50/p95 mỗi lượt, tỷ lệ fallback, chi phí/sự cố.

## Kế hoạch bằng chứng *(mandatory)*

- Output `uv run --directory backend pytest` (số test), `ruff check`, `alembic upgrade head` + `downgrade -1` + `upgrade head`.
- Output lệnh nạp (2 lần: thêm 1 rồi cập nhật 1/thêm 0) + truy vấn quét byte không có h1.
- Phiên `curl` (hoặc client MCP) tới `/mcp/threat`: 401 / 200 / 429, kèm dòng log tương ứng (đã kiểm không có h1).
- `hoicon-eval --suite smoke --compare baseline` (máy dev nếu có `HOICON_EVAL_DATABASE_URL`, nếu không ghi SKIPPED + kết quả CI).
- `spike bench --model claude-haiku-5-5 --n 20 --json …` không khóa (llm_mode fallback) + BLOCKED cho chạy có khóa.
- Báo cáo `security-privacy-reviewer` (0 Critical/High còn mở) + `privacy-audit`.

## Ngoài phạm vi & mốc cắt

- Ngoài phạm vi: tác tử xác minh, `rescore`, `/v1/lookups`, E10 (spec 026); đồng bộ danh sách xuống máy `GET /v1/threat-list`
  (022/026); nguồn danh sách thật và quy trình gắn cờ (P3); provider Gemini (B6, chờ khóa); OAuth cho MCP; hạn mức nhiều tiến
  trình; mở `/mcp/threat` ra Internet qua Caddy (012 quyết); đo p95 trên VPS (012).
- Nếu trễ, cắt trước: US-4 (trần chi tiêu bền) → FR-010 phần `host`/`--json` (giữ `--model`). Không cắt: FR-001…FR-006.

## Assumptions

- Pepper và khóa dữ liệu có trong `.env` của worktree (Tiến tự chép, agent không đọc); test dùng khóa giả của
  `tests/integration/conftest.py`.
- Giờ "ngày" của trần chi tiêu theo `Asia/Ho_Chi_Minh` (người dùng và đội ở Việt Nam).
- Một tiến trình API (ADR-002) ⇒ hạn mức trong bộ nhớ đủ cho thí điểm.
