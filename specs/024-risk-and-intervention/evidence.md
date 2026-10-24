# Bằng chứng nghiệm thu Spec 024: Đánh giá rủi ro, câu hỏi nhanh E8 & tác tử can thiệp

- **Ngày đo**: 16/10/2026 (rà soát độc lập, viết lại toàn bộ bản bằng chứng trước đó)
- **Môi trường**: Linux CachyOS · Postgres dev (Docker, cổng 15432) · JBR Android Studio · AVD API 36 (`sdk_gphone64_x86_64`)
- **Nguồn số**: máy dev + máy ảo. Không có số đo máy thật, không có FCM thật, không có LLM thật (eval dùng phản hồi ghi sẵn).

## Bản bằng chứng trước bị sai ở đâu

| Ghi trước đây | Thực tế khi rà soát |
|---|---|
| T006 "scam ⇒ `case_open` tại `resolve`" | Chưa làm: `resolve` vẫn ra `resolved_prevented` và không ghi gì vào sự cố |
| SC-005 "10/10 test đồ thị T1/T2/T3" | Không có test nào của spec 024 cho hẹn giờ; test đồ thị cũ không đổi |
| SC-001 "p50/p95 227/327 ms" | Là độ trễ eval smoke (LLM ghi sẵn), không phải độ trễ giao tóm tắt tới người giám hộ |
| SC-004 "WCAG AAA" qua unit test | Không test UI; màn E8 có chữ 16–18sp, nút 52dp, chữ xám ~3,5:1, chữ trắng trên cam ~4,5:1 |
| T010 "retry an toàn" | Gửi một lần trong `lifecycleScope` rồi `finish()` ⇒ có thể mất câu trả lời, không thử lại |

## Kết quả sau rà soát

| Tiêu chí | Kết quả | Trạng thái |
|---|---|---|
| SC-001 tóm tắt p95 ≤ 15 s | Chưa đo với LLM thật (chưa có khóa). Trần LLM 4 s/lần gọi + mẫu dự phòng giữ nguyên | **CHƯA ĐO** |
| SC-002 `level ≥ rule_floor`, E8 "có" ⇒ nâng | `test_elder_answer_raises_level_above_floor`: sàn `medium`, LLM giả cố hạ `low`, "Không quen" ⇒ `high`; eval smoke 0 vi phạm | ĐẠT |
| SC-003 công khai AI, chỉ enum | `test_every_elder_question_discloses_ai` (mọi câu, thật + diễn tập); schema + API chỉ nhận enum + cờ bool | ĐẠT |
| SC-004 màn E8 | Ảnh máy ảo API 36 ở cỡ chữ 100% và 200% (bên dưới); chữ ≥ 20sp, vùng chạm ≥ 64dp, "CÓ" trắng trên `BrandOrangeText` ≈ 8,5:1, "KHÔNG" trắng trên `BrandNavy` ≈ 11,5:1; 200% vẫn thấy đủ 3 nút | ĐẠT (máy ảo) |
| SC-005 T1/T2/T3 qua jobs | `test_guardian_decision_outside_graph_stops_reminders`, `test_t3_without_answer_closes_incident_as_no_response`, `test_zalo_scam_reply_keeps_case_open`; kill -9: `test_graph_durable` (đã có) | ĐẠT |
| SC-006 eval smoke so baseline | 20 ca · recall 100% · báo nhầm 0% · vi phạm 0 · công khai AI 100% · so baseline +0,0 / +0,0 | ĐẠT |

## Lệnh đã chạy (16/10/2026, sau khi sửa)

| Lệnh | Kết quả |
|---|---|
| `uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache` | 1025 passed, thứ tự ngẫu nhiên (trước rà soát: 1016) |
| `ruff check` / `ruff format --check` (`src/ tests/`) | sạch / 137 file đã định dạng |
| `./apps/android/gradlew -p apps/android :app:testDebugUnitTest :app:lintDebug :app:assembleDebug` | BUILD SUCCESSFUL; 104 test JVM, 0 lỗi (`ElderApiClientTest` 6) |
| `gitleaks dir --config .gitleaks.toml` từng thư mục: `backend/src`, `apps/android/app/src`, `backend/tests`, `docs/schemas`, `specs/024-…` | 0 phát hiện mỗi thư mục |
| `hoicon-eval --suite smoke --compare baseline --shared-db-ok` | ĐẠT (bảng trên) |
| `python3 scripts/check-spec-trace.py` | 11 spec, 0 lỗi |

Lưu ý: `gitleaks dir … backend/src apps/android/app/src` (hai đường dẫn trong một lệnh) KHÔNG quét hai thư mục đó mà quét
cả cây làm việc, nên báo `backend/.env` và `apps/web/.next/` (cả hai bị git bỏ qua, không vào repo). Phải quét từng thư mục.

Ảnh E8 (máy ảo API 36, ngoài repo): `~/hoicon-evidence/024-risk-and-intervention/024-e8-{real,drill}-{100,200}.png`.
Activity `exported=false` nên ảnh được chụp từ một bản build tạm đặt `exported=true`. Manifest đã khôi phục và bản
chuẩn đã cài lại; `am start` từ shell giờ bị từ chối như mong đợi.

## Lượt review đầy đủ (JEV FULL_REVIEW)

- Tra danh sách đe dọa ở `POST /v1/events` từng mượn kết nối thứ hai của pool khi đang giữ khóa thiết bị ⇒ nay tra trong
  SAVEPOINT của chính giao dịch (`prepare_event(session, …)`); test `test_flagged_caller_is_looked_up_inside_the_batch`.
- Uvicorn thật: có DB ⇒ `/healthz` 200, `/readyz` 200, runtime mở/đóng sạch. DB không với tới ⇒ `/healthz` 200,
  `/readyz` 503, worker thử lại; tắt API có trần (`SHUTDOWN_WAIT_S` = 10 s, đo 12 s).
- DB dev còn 87 job `start_graph` cũ mang `h1` (từ lượt chạy code trước khi sửa, dữ liệu test hư cấu) ⇒ đã xóa; sau
  lượt pytest đầy đủ: 0 job mang `h1`.

## T013: đường tự kéo `pending-question` (Android, 18/10/2026)

- **Cách làm:** `POST /v1/events` trả `incident_id`/`incident_opened` (`events_result.v1.json`); `PairingApiClient` đọc ra
  `EventsResult.AcceptedWithIncident`; `OutboxSender` gọi `onIncident(id)` sau khi đánh dấu lô đã gửi;
  `SentinelServices.flushOutbox` xếp `ElderQuestionWorker` (cần mạng, KEEP theo sự cố); worker hỏi
  `GET /v1/incidents/{id}/pending-question` (thử lại tới 6 lần cách 2 giây vì đồ thị tới `ask_elder` chậm hơn lô một chút), rồi mở
  `ElderQuestionActivity` bằng đúng cách SafePause mở từ nền (quyền "hiển thị trên ứng dụng khác"). Mỗi câu hỏi chỉ mở một lần
  (`ElderQuestionStore`, chỉ lưu id). Chỗ cắm FCM: một push chỉ cần gọi cùng đường `claim` + `createIntent`.
- **Test JVM (đỏ nếu hỏng):** `EventsApiClientTest` (có/không/hỏng `incident_id`), `OutboxSenderTest` (chuyển tiếp incident; không chuyển
  khi lỗi/từ chối/rút đồng ý; vẫn chuyển khi tách lô hỏng), `ElderQuestionPollerTest` (tìm thấy sau vài lần 404; không chờ sau lần cuối; lỗi
  mạng ⇒ thử lại; token bị từ chối ⇒ dừng; một câu hỏi không mở hai lần). Cổng: `:app:testDebugUnitTest` 248 test, 0 lỗi.
- **Chạy thật trên hc-api36** (backend dev cổng 18001, Zalo mock): giả lập cuộc gọi lạ (số hư cấu) → mở app ngân hàng mẫu → sự kiện lên
  máy chủ (`POST /v1/events` 200) → `GET …/pending-question` 404, 404, 404 rồi **200** → `ElderQuestionActivity` tự mở (04:49 UTC) →
  bấm KHÔNG → `POST …/answers` 200, log máy chủ `elder_answer … answer=no`. Ảnh: `~/hoicon-evidence/024-risk-and-intervention/e8-pull-{100,200}.png`.
- **Chưa kiểm:** FCM thật; E8 mở khi chưa cấp quyền "hiển thị trên ứng dụng khác" (Android chặn mở từ nền, chưa có thông báo dự phòng);
  hc-api34/29; máy thật; E8 hiện 3 nút ngang hàng (CÓ/KHÔNG/KHÔNG RÕ) trong khi luật 15 nói ≤ 2 hành động chính (có sẵn từ T009, chưa xử lý ở đây).

## Còn mở (không đánh ☑)

- **E8 mở trên máy bằng đường tự kéo, chưa có FCM thật** (T013, 18/10/2026): xem mục "T013" bên dưới. FCM thật chờ P0-08 (Firebase);
  máy chủ chỉ có FCM mock.
- SC-001 với LLM thật; mức rủi ro đồ thị nâng (sau E8) chưa ghi ngược vào `incidents.level` (trang `/a/` vẫn hiện mức do luật đặt).
- FR-006 "nâng mức ⇒ đánh thức đồ thị": đồ thị khởi động khi sự cố đạt `high`/`critical` (mở mới hoặc được nâng), chưa
  đánh thức lượt đang chạy khi mức tăng thêm.
- Client TS (`apps/web/src/lib/api/schema.d.ts`) chưa sinh lại từ spec 020 tới nay (`scripts/gen-api-client.sh`).

## Wave 3 — F-2 (ADR-012), làn B, 22/10/2026

- **T014 ĐẠT** (đỏ trước): `test_guardian_brief_schema.py`, `test_brief_points.py` lỗi import; `-k prose_injection` đỏ ở dạng v1 trước khi sửa mã.
- **T015 ĐẠT:** `GuardianBrief` v2 (`extra=forbid`, 1–3 mã không trùng), `brief_points`, `texts.BRIEF_POINT_VI`/`brief_summary`, `prompts/intervention.md` v2, 20 cassette smoke sửa sang `points` + `intervention@2`, `docs/AGENTS.md`. `agent_steps.output` chỉ ghi mã `points_kept/points_dropped`.
- **T018 ĐẠT** (2 reviewer, môi trường: subagent đọc diff; lần đầu chết vì lỗi mạng, chạy lại):
  - bảo mật: 0 Critical/0 High; Medium #1 (`may_be_routine` đứng cạnh dữ kiện nguy hiểm) → SỬA: bỏ khi `flagged`/xưng cơ quan/đòi tiền/giữ kín/cài app; Medium #2 (kiểm eval hở alias và đuôi sau `\n\n`) → SỬA: alias chỉ chữ cái/cách/`/` ≤ 20, đuôi phải đúng `REPLY_GUIDE_NO_DETAIL`.
  - UX: Chặn B1 (trấn an cạnh cảnh báo) → SỬA bằng luật loại trừ trên + câu mới; B2 (nói như đã nghe cuộc gọi) → SỬA: 4 câu dùng "{alias} cho biết …"; Cao H1 (chữ hoa đầu câu với alias "bác Hùng") → SỬA trong `brief_summary`; H2 (`common_scam_pattern` "Đây là…") → SỬA câu; M1/M3/L1/L2 → SỬA câu.
  - **CHƯA sửa, cần Opus** (đổi `spec.md` §5 bảng câu chữ, tôi không sửa spec): thứ tự ghép cố định (sự kiện → nghi ngờ → nhận định) và loại trừ `common_scam_pattern`/`may_be_routine`; H3 câu `call_still_ongoing` kèm "máy báo bận" (sửa `ACTION_VI`); M2 (`sideloaded_app` lặp ý với ứng dụng tài chính); câu sửa B2 thêm "cho biết" nghĩa là spec §5 đã lệch mã. Bảng spec §5 nay khác `BRIEF_POINT_VI`.
  - Security Low chưa sửa: #3 số `19001234` trong cassette `fake_tax_debt_link_001` (có từ trước), #4 `unknown_call_then_finance_app` không xét danh bạ, #5 `common_scam_pattern` luôn đúng kể cả mức thấp, #6 `reasons` LLM nằm trong checkpoint; `_UNSAFE_SUMMARY` nay là mã chết (giữ cho test).
- **T019 ĐẠT:** pytest 2273 passed/21 skipped; ruff sạch; smoke 20 ca, full 110 ca, injection **17/17**, đều recall 100%, báo nhầm 0%, 0 vi phạm, công khai AI 100%, không lệch baseline; `check-spec-trace` 0 lỗi; gitleaks 8 thư mục sạch; `alembic heads` = 1. **SC-007 ĐẠT** trên cassette `synthetic` (n=1 lượt/suite, máy dev; chưa chứng minh bằng model thật, P0-08). SC-008/F-1: BLOCKED chờ Minh (§8 mục 8); T016/T017 không làm.

## Wave 5 — FR-013 (T020/T021), làn B, 23/10/2026

- **T020 ĐẠT** (đỏ trước): `pytest tests/unit/test_brief_points.py` 22 failed / 42 passed — đỏ đúng ở (c) hoán vị, (d) hai mã nhận định, (e) chỉ nhận định, (f) tóm tắt rỗng, (g) câu "máy bận"; (a) bảng = mã và (b) thứ tự khóa = enum hợp đồng = cột "#" xanh sẵn. 5 test cũ mâu thuẫn FR-013 đã đảo chiều (thứ tự theo bảng; `common_scam_pattern` cần ≥ 1 điểm trước nó; không ứng dụng ⇒ rỗng).
- **T021 ĐẠT:** `brief_points` 4 bước (lọc/cắt 3 → một mã nhận định → chỉ nhận định thì rơi về bộ mặc định → sắp theo bảng); `texts.ACTION_BUSY_VI`; `guardian_detail(..., call_ongoing=)` bỏ hẳn phần tóm tắt khi rỗng, thêm câu "máy bận" chỉ với `call_now`/`call_and_stay_on_line`; `fallback` của `intervention` dùng `["common_scam_pattern"]` làm chỗ giữ (hợp đồng đòi ≥ 1 mã), `brief_points` lọc lại. Bộ kiểm eval 036: tóm tắt rỗng hợp lệ, đuôi hành động nhận thêm câu bận. Test cũ "tóm tắt rỗng là vi phạm" đảo chiều (rỗng không chứa chữ lạ).
- Số đo: `cassettes check` khớp (không cần sinh lại); smoke 20 ca, full 110 ca, injection 17/17 — recall 100%, báo nhầm 0%, 0 vi phạm, công khai AI 100%, không lệch baseline (cassette `synthetic`, chưa phải số M3).
- `ux-elder-reviewer` đọc 3 tin mẫu: 0 High, 5 Medium. **CHƯA sửa, cần Opus** (đều đổi chữ bảng spec §5/`ACTION_VI`, ngoài quyền): (1) tin rất cao mở bằng "Mức nguy cơ: rất cao." trước việc cần làm — đề xuất "Cần anh/chị gọi ngay cho {alias} (mức nguy cơ: rất cao)."; (2) hai câu "{alias} cho biết…" liên tiếp — đề xuất gộp, thêm "(OTP)"; (3) tin có `call_still_ongoing` đã có câu bận nhưng tin không có nó thì thiếu hướng dẫn khi bác không nghe máy; (4) câu `common_scam_pattern` đứng cạnh `call_still_ongoing` — đề xuất "giống các cuộc gọi giả danh… nhưng trợ lý chưa chắc chắn"; (5) tóm tắt rỗng chỉ còn mức + lệnh gọi, người nhận không biết vì sao — đề xuất một câu trung tính thay phần bị bỏ.
- Cổng cuối: pytest 2726 passed/21 skipped; ruff sạch; `alembic heads` = 1 (0012); `check-spec-trace` 0 lỗi; gitleaks quét từng thư mục (`backend/src|tests|eval`, `data`, `specs`, `infra`, `apps/web/src`) sạch. `docs` có 1 dương tính giả: `docs/schemas/fixtures/device_me.v1.invalid.json:28` là SHA-256 của chuỗi rỗng (fixture "invalid" của Opus, không phải bí mật). Lưu ý: `gitleaks dir` chỉ nhận một đường dẫn; lệnh nhiều đường dẫn trong chỉ dẫn lần này quét cả `apps/web/.next` và `backend/.env` (bị ignore).
