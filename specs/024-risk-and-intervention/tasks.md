# Danh sách Công việc Spec 024: Đánh giá rủi ro, Ngân hàng câu hỏi E8 & Tác tử can thiệp

- [x] T001 [FR-001] Định nghĩa JSON Schema hợp đồng `docs/schemas/elder_question.v1.json` và `docs/schemas/elder_answer.v1.json`.
- [x] T002 [FR-001] Tạo fixtures kiểm thử valid và invalid trong `docs/schemas/fixtures/` cho `elder_question` và `elder_answer`.
- [x] T003 [FR-002] Hiện thực kênh FCM client `hoicon.channels.fcm` với hỗ trợ dry-run/mock khi chưa có credentials production.
- [x] T004 [FR-003] Xây dựng router `hoicon.api.routers.elder` với endpoint `POST /v1/incidents/{id}/answers` xác thực token thiết bị.
- [x] T005 [FR-004] Xây dựng endpoint `GET /v1/incidents/{id}/pending-question` phục vụ cơ chế polling/fallback của thiết bị.
- [x] T006 [FR-005] Nâng cấp `incident_graph.py`: cập nhật `risk_scorer` theo câu trả lời E8, trần thời gian trong `intervention`, sửa invariant scam chuyển `case_open` tại `resolve`.
- [x] T007 [FR-006] Tích hợp tự động kích hoạt đồ thị LangGraph từ `POST /v1/events` khi sự cố mới được tạo hoặc nâng mức.
- [x] T008 [FR-007] Hoàn thiện xử lý job `graph_resume` cho timer T1 (120s nhắc), T2 (300s chuyển người giám hộ 2), T3 (900s dừng chờ) và timeout E8 trong worker.
- [x] T009 [FR-008] Thiết kế và triển khai màn hình Compose E8 `ElderQuestionScreen.kt` & `ElderQuestionActivity.kt` trên Android với 3 nút lớn, TTS offline, nhãn AI và diễn tập.
- [x] T010 [FR-009] Hiện thực `ElderApiClient` trên Android gửi câu trả lời `POST /v1/incidents/{id}/answers`; gửi qua `ElderAnswerWorker` (WorkManager, cần mạng, backoff, KEEP theo sự cố).
- [x] T011 [FR-010] Viết test hợp đồng schemas, test tích hợp API elder questions/answers và test đồ thị LangGraph với chuỗi hẹn giờ T1/T2/T3.
- [x] T012 [FR-010] Chạy toàn bộ testsuite pytest, ruff check, gitleaks, `hoicon-eval smoke` và cập nhật bằng chứng `evidence.md`.
- [x] T013 [FR-002] Nối đường mở E8 trên máy: nhận FCM thật (chờ Firebase P0-08) hoặc tự kéo `pending-question` sau khi gửi sự kiện mở sự cố. — đã làm đường tự kéo; FCM thật chờ P0-08.

---

## Wave 3 (22/10/2026) — F-2 an toàn (làm ngay) và F-1 (chờ Minh)

**Chế độ chạy**: tự hành một mạch, làn B (`[B-api]`, chỉ `backend/**`). Test viết trước và PHẢI đỏ trước khi sửa mã (dán
dòng đỏ vào evidence). `$PYTEST` = `uv run --directory backend pytest`. Không đọc tệp bí mật, không gọi LLM thật. **Dừng** khi:
một ca smoke/full đổi recall/báo nhầm/vi phạm so baseline mà không giải thích được bằng ADR-012; hoặc `ux-elder-reviewer`
còn High ở câu chữ sau 2 vòng.

- [x] T014 [B-api] [FR-011] Test đỏ trước, không sửa mã sản phẩm:
  (a) `backend/tests/contract/test_guardian_brief_schema.py`: fixture `docs/schemas/fixtures/guardian_brief.v2.{valid,invalid}.json`
  chạy với `Draft202012Validator`; enum `points` của hợp đồng == `typing.get_args(BriefPoint)`; `GuardianBrief.model_json_schema()`
  có `additionalProperties: false`;
  (b) `backend/tests/unit/test_brief_points.py`: mỗi mã bị bỏ khi điều kiện sai, giữ khi đúng (bảng spec §5); `may_be_routine` bị
  bỏ ở `high`/`critical`, giữ ở `medium`; rỗng ⇒ bộ mặc định; thứ tự giữ theo LLM; mọi câu `BRIEF_POINT_VI` không khớp
  `_UNSAFE_SUMMARY`, không chứa cụm hoảng sợ/hoàn tiền của `hoicon.eval.checks`, không chứa marker nào của
  `backend/eval/suites/full.v1.json`, `mask_text(câu) == câu`;
  (c) đảo chiều test ghim F-2 trong `backend/tests/integration/test_eval_full.py`
  (`test_known_gap_prose_injection_passes_the_graph_filter_on_every_injection_case` ⇒ đổi tên
  `test_prose_injection_never_reaches_the_guardian_on_any_injection_case`, kỳ vọng `violations == []` cho cả 13 ca; cassette của
  test dùng dạng v1 `summary` chữ thuần **và** dạng v2 mã lạ `["skip_guardian"]`).
  · Verify (đỏ): `$PYTEST tests/contract/test_guardian_brief_schema.py tests/unit/test_brief_points.py -q` lỗi import/assert;
  `$PYTEST tests/integration/test_eval_full.py -q -k prose_injection` đỏ 13 ca.
- [x] T015 [B-api] [FR-011] Hiện thực ADR-012 theo plan "Wave 3": `incident_graph.py` (`BriefPoint`, `GuardianBrief` v2,
  `brief_points`, `intervention` ghép câu cố định, `agent_steps.output` ghi `points_kept`/`points_dropped`), `texts.py`
  (`BRIEF_POINT_VI`, `brief_summary`), `prompts/intervention.md` `version: 2`; sửa tay 20 cassette `backend/eval/cassettes/smoke/`
  sang `points` + `prompt_versions.intervention = "intervention@2"`; cập nhật `docs/AGENTS.md` mục `intervention` (tóm tắt =
  mã điểm, ADR-012). Gọi `ux-elder-reviewer` đọc 11 câu `BRIEF_POINT_VI` trong khung tin `guardian_detail` (người đọc: con cháu).
  Phụ thuộc: T014; **036 T025 làm ngay sau trong cùng nhánh** (cassette full sinh lại, nếu không `cassettes check` đỏ).
  · Verify: `$PYTEST tests/contract tests/unit/test_brief_points.py tests/integration/test_eval_full.py -q` xanh;
  `uv run --directory backend ruff check . && uv run --directory backend ruff format --check .`;
  `uv run --directory backend hoicon-eval --suite smoke --compare baseline --shared-db-ok` exit 0 (recall/báo nhầm +0,0, 0 vi phạm);
  báo cáo reviewer 0 High ghi vào `specs/024-risk-and-intervention/evidence.md`.
- [ ] T016 [B-api] [FR-012] **★ CHỜ MINH (MASTER-PLAN §8 mục 8). Không bắt đầu khi §8 chưa ghi "A".** Test đỏ trước:
  đảo chiều `test_known_finding_f1_asking_about_a_transfer_escalates_every_legitimate_transfer_to_critical` thành
  `test_a_confirmed_transfer_is_followed_by_one_who_is_calling_question` (10 ca ép hỏi chuyển tiền ⇒ đúng 2 câu hỏi, câu thứ hai
  `q_know_caller`; ≤ 3 ca `above_max_level`); `backend/tests/unit/test_answer_floor.py` (`transfer=yes` ⇒ `high`;
  + `know=no|unsure|timeout` ⇒ `critical`; + `know=yes` ⇒ `high`; không câu thứ ba); test đồ thị: ca lừa đảo smoke có
  `asks_transfer=yes` vẫn ≥ `min_risk_level`.
  · Verify (đỏ): `$PYTEST tests/unit/test_answer_floor.py tests/integration/test_eval_full.py -q -k "answer_floor or who_is_calling"`
- [ ] T017 [B-api] [FR-012] **★ CHỜ MINH.** Hiện thực phương án A (plan "Wave 3": `answer_floor`, câu nối tiếp tất định,
  `asked` trong state; `MAX_ASK_ELDER = 3` của eval giữ nguyên), cập nhật `docs/AGENTS.md` (đồ thị: tối đa 2 câu hỏi) và
  `.claude/skills/run-eval/SKILL.md` (bỏ F-1 khỏi "phát hiện mở") — phụ thuộc T016, T015.
  · Verify: `$PYTEST -q` xanh; `hoicon-eval --suite full --compare baseline-full --shared-db-ok` exit 0 (recall 1,000, báo nhầm
  ≤ 0,10, 0 vi phạm); `hoicon-eval --suite smoke --compare baseline --shared-db-ok` exit 0.
- [x] T018 [B-api] [FR-011, FR-012] `security-privacy-reviewer` (prompt v2, điều kiện điểm đọc state nào, `agent_steps` không
  có chữ LLM) + `/ponytail-review` trên diff T014–T017 ⇒ sửa mọi High/Medium.
  · Verify: báo cáo 0 High/Medium dán vào evidence.md.
- [x] T019 [B-api] [FR-011, FR-012] Cổng: `$PYTEST -q`; `ruff check` + `ruff format --check`; smoke + full + injection như trên;
  `python3 scripts/check-spec-trace.py`; `gitleaks dir backend/src backend/tests backend/eval specs docs`. Ghi SC-007 (và SC-008
  nếu A) vào `specs/024-risk-and-intervention/evidence.md` (số + môi trường + n); cập nhật dòng P2-09 `docs/ROADMAP.md`.
  F-1 vẫn chờ Minh ⇒ SC-008 ghi `BLOCKED: chờ Minh (§8 mục 8)`, không tick T016/T017.
  · Verify: `python3 scripts/check-spec-trace.py` 0 lỗi.

Thứ tự: T014 → T015 → (036 T025 → T026 → T027) → T018 → T019. T016 → T017 chỉ khi Minh chọn A, chen trước T018.

---

## Wave 4 (23/10/2026) — thứ tự ghép cố định (FR-013, SC-009)

**Chế độ chạy**: làn B (`[B-api]`, chỉ `backend/**`), một mạch, test đỏ trước. Không đổi hợp đồng (`guardian_brief.v2.json` giữ
nguyên enum; thứ tự enum chính là thứ tự ghép). **Dừng** khi một ca smoke/full đổi recall/báo nhầm/vi phạm so baseline.

- [x] T020 [B-api] [FR-013] Test đỏ trước trong `backend/tests/unit/test_brief_points.py`:
  (a) `BRIEF_POINT_VI` == bảng spec §5 (11 câu, đúng chữ — chép bảng vào test làm hằng số kỳ vọng);
  (b) thứ tự khóa `BRIEF_POINT_VI` == enum `points` của `docs/schemas/guardian_brief.v2.json` == cột "#";
  (c) đặc tính: mọi tập con ≤ 3 mã hợp lệ, mọi hoán vị ⇒ cùng `brief_summary` (dùng `itertools.permutations`, state dựng sao cho
  mọi điều kiện đúng); (d) có cả `common_scam_pattern` và `may_be_routine` ⇒ chỉ còn `common_scam_pattern`; (e) chỉ có mã nhận
  định ⇒ rơi về bộ mặc định; (f) sự cố không ứng dụng (không #1/#2) và LLM trả mã sai ⇒ `summary == ""` và `guardian_detail` không
  có hai dấu cách liền, không có ". ." ; (g) `call_still_ongoing` + `call_now` ⇒ tin có `ACTION_BUSY_VI`, không có `call_still_ongoing`
  ⇒ không có.
  · Verify (đỏ): `uv run --directory backend pytest tests/unit/test_brief_points.py -q` đỏ ở (c)(d)(f)(g).
- [x] T021 [B-api] [FR-013] Sửa `incident_graph.py::brief_points` theo 5 bước của FR-013 và `texts.py` (`ACTION_BUSY_VI`,
  `guardian_detail` bỏ phần tóm tắt khi rỗng); cassette smoke/full không cần sinh lại (mã không đổi) — chạy `cassettes check` để
  chắc. `ux-elder-reviewer` đọc 3 tin mẫu (lừa đảo đủ 3 nhóm; ca có `call_still_ongoing`; ca tóm tắt rỗng).
  Phụ thuộc: T020.
  · Verify: `uv run --directory backend pytest tests/unit/test_brief_points.py tests/integration/test_eval_full.py -q`;
  `uv run --directory backend ruff check . && uv run --directory backend ruff format --check .`;
  `uv run --directory backend python -m hoicon.eval.cassettes check`;
  `hoicon-eval --suite smoke --compare baseline --shared-db-ok`, `--suite full --compare baseline-full --shared-db-ok`,
  `--suite injection --shared-db-ok` đều exit 0; reviewer 0 Chặn/Cao ghi vào `evidence.md` (SC-009).

## Lượt 10 (nhà điều phối 25/10/2026) — lỗi từ GAP-REPORT làn A (có chứng cứ trong evidence 024)
- [ ] T022 [A] [FR-005] E8 đúng luật 15 (≤ 2 hành động chính): hai câu trả lời chính là nút đặc ≥ 64dp; lựa chọn thứ ba ("Không rõ"/tương đương theo
  `elder_question.v1`) là nút chữ phụ; không đổi mã trả lời gửi máy chủ. Khi thiếu quyền "hiển thị trên ứng dụng khác" ⇒ thông báo ưu tiên cao (kênh có sẵn,
  không xin quyền mới — luật 3) mở E8 khi chạm. Test Compose + đơn vị đỏ trước; ảnh 100/200%; `ux-elder-reviewer` 0 Chặn/Cao.
  · Verify: `apps/android/gradlew -p apps/android :app:testDebugUnitTest :app:lintDebug`
- [x] T023 [B] [FR-005] Mức rủi ro nâng sau câu trả lời E8 ghi ngược `incidents.level` (chỉ nâng, không hạ — luật 5; không phải chuyển trạng thái nên
  không qua `transition()`, nhưng ghi `agent_steps`). Test đỏ: trả lời làm nâng ⇒ `incidents.level` = mức mới; trả lời không nâng ⇒ giữ nguyên.
  · Verify: `uv run --directory backend pytest -q tests/integration -k "elder_answer"`
- [x] T024 [B] [SC-001] Đo đúng SC-001 "tóm tắt tới người giám hộ ≤ 15 s": từ `received_at` của sự kiện tới lúc job `notify_guardian` gọi client Zalo
  (mock, có dấu thời gian) qua đồ thị thật ở chế độ replay, 20 lượt; ghi p50/p95 + nguồn ("máy dev, Zalo mock") vào evidence 024; sửa câu cũ dùng nhầm
  số eval 227/327 ms. · Verify: `uv run --directory backend pytest -q tests/integration -k "summary_latency"` + bảng số trong evidence
