# Bằng chứng nghiệm thu Spec 011: Văn bản đồng ý, DPIA rút gọn, quy trình thí điểm

- **Trạng thái (18/10/2026)**: bản nháp đầy đủ và kiểm được bằng máy; **mọi văn bản là BẢN NHÁP — chờ Minh duyệt, chưa dùng với người thật**.
  Ba văn bản (`llm_processing`, `voice_input`, `pilot_research`) hứa điều mã chưa thực thi nên **bị chặn phát hành** cho tới khi thực thi hoặc sửa chữ.
- **Môi trường**: Linux CachyOS, nhánh `feat/w1-server`. Không gọi LLM thật, không đọc `.env`, không sửa `apps/android/**` hay `docs/schemas/**`.
- **Nguồn số**: máy dev. Luật: chỉ nêu tên và số hiệu từ `docs/research/notes/09_agentic_ai_tech_feasibility.md`, chưa đối chiếu văn bản gốc, không trích số điều.
  Chưa chạy: CI trên PR, Windows, máy thật, người cao tuổi thật đọc thử, nghe đọc to bằng TTS.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 phủ mục đích | 10/10 giá trị enum có đúng 1 văn bản; 0 tệp thừa | `tests/contract/test_consent_texts.py` (41 test) + `python -m hoicon.ops.consent_texts check` | `Đạt: 10 mục đích ↔ 10 văn bản, sha256 khớp`. Enum, lược đồ `consent_record.v1.json` và CHECK của `consents` cùng 10 giá trị | ĐẠT |
| SC-002 sha256 khớp | 10/10 khớp; đổi 1 ký tự ⇒ đỏ | test + đột biến | Đổi một dấu `!` trong `lookups` ⇒ đỏ; xóa 1 tệp ⇒ đỏ; thêm giá trị enum không có văn bản ⇒ đỏ. Băm khớp quy tắc Android (`"a\nb"` và `"Bác\nơi"` có giá trị tham chiếu trong test) | ĐẠT |
| SC-003 bất biến phiên bản | đổi chữ cặp đã phát hành, giữ phiên bản ⇒ đỏ; tăng phiên bản ⇒ xanh | test trên dữ liệu giả; kiểm dùng sha **tính lại**, không tin manifest | Cả 4 ca (đổi/giữ/tăng/ghi manifest gian) đúng; `write` từ chối ghi đè cặp đã phát hành. Hiện `released` rỗng | ĐẠT |
| SC-004 dễ đọc | ≤ 25 từ/câu trung bình, ≤ 40 từ/câu, ≤ 160 từ/văn bản; 0 số điều luật; 0 dãy ≥ 4 chữ số | `style_problems()` trong test và CLI | 10/10 đạt. Số từ: core 158 · guardian 159 · lookups 156 · drills 129 · llm 117 · call 112 · overlay 113 · usage 113 · pilot 110 · voice 87 | ĐẠT (ngưỡng thô) |
| SC-005 công khai AI | 6/6 văn bản nhóm AI mở đầu bằng "Đây là trợ lý AI HỏiCon" | test | 6/6 (`core_protection`, `guardian_alerts`, `llm_processing`, `voice_input`, `drills`, `lookups`) | ĐẠT |
| SC-006 duyệt độc lập | `privacy-audit` 0 High; `ux-elder-reviewer` 0 chặn | xem các mục dưới | `privacy-audit`: 0 số điện thoại thô trong mã/DB, nhưng **3 văn bản hứa điều mã chưa làm** (High cho việc phát hành). UX: 4 Chặn (đều là 3 văn bản đó), 6 Cao đã sửa chữ | MỘT PHẦN |
| SC-007 Minh duyệt | `draft` → `approved` | — | Chờ Minh | BLOCKED |
| SC-008 người thật đọc thử | người cao tuổi thật hiểu | — | Cần thí điểm (029 giai đoạn 2) | BLOCKED |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `pytest tests/contract/test_consent_texts.py` | 41 passed |
| Đột biến (13 sửa văn bản/manifest/enum/DPIA/PILOT + xóa tệp + 1 sau khi siết test DPIA) | 14/14 làm test đỏ; 1 đột biến sống sót lượt đầu (DPIA nhắc mục đích ở chỗ khác) ⇒ siết test: bảng mục 1 phải liệt kê đủ 10 mục đích |
| `python -m hoicon.ops.consent_texts check` | rc = 0 |
| `uv run --directory backend pytest` | 2059 passed, 21 skipped (role `hoicon_app` có sẵn trên DB dev nên `test_db_roles.py` tự bỏ qua) |
| `ruff check .` + `ruff format --check .` | sạch (202 tệp) |
| `hoicon-eval --suite smoke --compare baseline` (DB `hoicon_eval` riêng) | 20 ca · recall 100% · báo nhầm 0% · vi phạm 0 · công khai AI 100% · lệch baseline +0,0 điểm % |
| `python3 -m unittest discover -s scripts/tests` | 108 test, exit 0 |
| `python3 scripts/check-spec-trace.py` | 19 spec, 0 lỗi |
| `gitleaks dir` (cấu hình `.gitleaks.toml` của repo) | `infra`, `specs`, `docs`, `scripts`, `apps/web/src`, `backend/src`, `backend/tests`, `backend/migrations`, `backend/eval`: 0. Thư mục `backend` nguyên cả: **4 phát hiện, tất cả trong tệp cấu hình cục bộ của máy dev** (bị `.gitignore`, `git ls-files` rỗng; không đọc giá trị, chỉ thấy tên biến) |

## `privacy-audit` (skill, 18/10/2026) — mã ↔ chữ ↔ DPIA

- **Mã nguồn** (`rg`): 0 số điện thoại thô ngoài tests/fixtures (1 khớp là chú thích ví dụ trong `PiiMasker.kt`); các dòng `print`/log khớp từ khóa là thông báo cố định
  (không in giá trị); quyền cấm chỉ xuất hiện trong chú thích và manifest ghi "CẤM".
- **DB dev** (chỉ đếm, `hoicon-db`): 0 dòng khớp số điện thoại thô ở `risk_events.payload`, `agent_steps.input_redacted/output`, `jobs.payload`,
  `verifications.sources`; 0 dòng quá hạn (`risk_events` > 90 ngày, `jobs` > 30 ngày, `verifications` > 90 ngày). **Không đủ dữ liệu** để đối chiếu
  quyền-đồng ý theo thiết bị (DB dev chỉ còn 1 dòng đồng ý) hay mẫu `agent_steps` gần nhất (`input_redacted` rỗng: chưa có lượt LLM thật, chưa có khóa API).
  Mục "demo > 24 giờ" của skill: không có bảng/job nào thực thi (đã ghi từ review 034).
- **Văn bản ↔ mã** (phát hiện chính):

| Văn bản hứa | Mã hiện làm | Mức |
|---|---|---|
| `llm_processing`: "chưa đồng ý thì không gửi gì ra ngoài, chỉ dùng câu viết sẵn" | Không đâu kiểm đồng ý `llm_processing` | **High cho phát hành** |
| `pilot_research`: ghi số liệu khi đồng ý; "gộp chung nhiều người" | Heartbeat chỉ kiểm `core_protection`; `ops pilot report` in theo từng gia đình (đã ẩn danh) | **High cho phát hành** |
| `voice_input`: nói thay bấm nút | Chưa có tính năng, chưa có mã ghi/kiểm | **High cho phát hành** (chữ nói về tính năng chưa có) |
| `drills`: "khung giờ con bác đã đặt" | Khung giờ do người giám hộ/đội đặt; **không có màn Android nào ghi đồng ý `drills`**, mà 028 chỉ mời bài khi sổ có `drills` ⇒ không ai được mời | Medium |
| `guardian_alerts`: "họ xem lại được trên trang web" | Route đọc web không kiểm đồng ý (câu hỏi mở (i) của 027) | Medium (đã nêu ở "Điểm chờ quyết") |
| `core_protection`/`guardian_alerts`: "giữ 90 ngày; ghi chép nhắc dừng lại 12 tháng" | Khớp `DATA-MODEL.md` §6. **Chữ Android hiện tại nói "tối đa 90 ngày" cho mọi thứ** | Medium (đồng bộ Android) |
| `lookups`: rút đồng ý | Sau sửa 026 #3: rút ⇒ xóa phần nhận diện của lượt tra cứu | Đã khớp |

## `ux-elder-reviewer` (18/10/2026)

**4 Chặn, 6 Cao, 18 Trung bình, 5 Thấp.** 4 Chặn là `llm_processing` (2), `voice_input`, `pilot_research`: đúng ba văn bản bị chặn vì hứa điều chưa thực thi,
nên không thể "hết chặn" chỉ bằng sửa chữ.

**Đã sửa chữ:** 6 Cao (#5 "đang tham gia" áp đặt; #6 khung giờ; #7 một câu hạn lưu thống nhất 90 ngày/12 tháng; #8 đường rút lại cụ thể; #9 tách câu 30 từ; #10 bỏ "dãy ký tự đại diện"),
phần chữ của Chặn (#1 #2 #3 #4: bỏ câu tuyệt đối "đã xóa hết PII" và "không dạy máy", nói thẳng Google có thể nhận tiếng, nói rõ cách rút) và đa số Trung bình/Thấp
(#11 #12 #13 #14 #15 #17 #19 #20 #21 #22 #24 #27 #28 #29 #30 #31 #33); thêm câu "chưa đồng ý cũng không sao" cho 5 văn bản (core, guardian, drills, voice, pilot).

**Chưa làm / cần Minh hoặc làn A:** #16 "con bác" khi người giám hộ không phải con (app chèn tên); #25 câu tóm tắt đầu; #26 chia thẻ có nút "Nghe lại" (`core_protection` 158 từ ≈ 4–6 màn ở chữ 200%);
#32 hướng dẫn trang quyền của hệ điều hành; số hỗ trợ thật (reviewer đề xuất đặt vào #4 và #8, hiện chỉ có "người đã hướng dẫn bác"); ngoặc kép cong; thử TTS với "ĐÂY LÀ DIỄN TẬP".
Chưa có reviewer đọc lại các bản sửa chữ.

## Android đang hard-code chuỗi đồng ý — cần đồng bộ cho làn A (chỉ liệt kê, không sửa)

Đường dẫn dưới `apps/android/app/src/main/java/vn/hoicon/sentinel/` trừ khi ghi khác.

1. `data/consent/ConsentLedger.kt:21` — `VERSION = "2026.10-v2"`; manifest dùng `2026.10-v3`. Chữ đổi ⇒ phải nâng phiên bản (luật 7) và hiện lại E3.
2. `data/consent/ConsentTexts.kt` — ghép chuỗi tài nguyên cho **6** mục đích (`core_protection`, `guardian_alerts`, `lookups`, 3 trang quyền) rồi băm `join("\n")`.
   Muốn khớp manifest: mỗi dòng trong `docs/legal/consent/<purpose>.vi.md` là một chuỗi tài nguyên, đúng thứ tự, nối bằng `\n` ⇒ `sha256` trùng `manifest.json`.
   **Thiếu hẳn** chữ cho `llm_processing`, `voice_input`, `drills`, `pilot_research` (`texts.getValue(purpose)` sẽ ném lỗi nếu gọi).
3. `res/values/strings.xml` — các khóa cần viết lại theo văn bản: `disclosure_title`, `disclosure_1..4_title/body`, `disclosure_next` (core, guardian), `lookups_consent_ai/title/summary/1..3`
   (lookups), `perm_role_*`, `perm_usage_*`, `perm_overlay_*` (3 trang quyền). Chữ hiện tại nói "tối đa 90 ngày" cho mọi thứ (cần tách 90 ngày / 12 tháng).
4. `res/values/strings.xml` — mảng đọc to `disclosure_speech`, `lookups_consent_speech` phải đổi theo (TTS đọc cùng chữ).
5. `ui/ProminentDisclosureScreen.kt` (E3: 4 thẻ hay một khối), `ui/PermissionsScreen.kt`, `LookupModel.kt`/`LookupActivity.kt` (đồng ý đúng lúc `lookups`,
   `storage.acceptedLookupsVersion == ConsentLedger.VERSION`), `OnboardingModel.kt:103,126`, `MainActivity.kt:57` — dùng `ConsentLedger.VERSION` để quyết hiện lại.
6. `data/drill/DrillInvitation.kt` — ghi chú "không giữ bản sao đồng ý `drills`": **không có màn nào ghi đồng ý `drills`** ⇒ máy chủ không bao giờ mời diễn tập.
7. `data/remote/PairingApiClient.kt:128`, `data/consent/ConsentSync.kt`, `ConsentLedger.changes()` — logic gửi lô đồng ý (không cần đổi nếu giữ nguyên `purpose/version/sha256`).
8. Test Android nên ghim `sha256` của `manifest.json` (hiện chỉ có `AiDisclosureCopyTest` cho câu công khai AI).

## `ux-elder-reviewer` lượt 2 (18/10/2026)

Đọc lại sau các bản sửa: **0 Chặn, 4 Cao, 13 Trung bình, 9 Thấp** (không tính 3 văn bản bị chặn phát hành vì mã). Mục Cao đã xử lý:

| Mục Cao | Xử lý |
|---|---|
| Câu "con bác có thể biết" ở 3 văn bản quyền nghe như đe dọa và **chưa có mã thực thi** (`heartbeat_service.py` chỉ lưu `permission_state` để đo độ phủ) | ĐÃ bỏ khỏi 3 văn bản; bỏ cả câu "thỉnh thoảng báo họ biết quyền còn bật" ở `guardian_alerts`; sửa dòng tương ứng ở `PILOT-PROTOCOL.md` §4; ghi điểm chờ trong `guardian_alerts.vi.md` |
| `guardian_alerts` và `llm_processing` hứa "tắt/đổi ý" mà không nói cách | ĐÃ thêm "nhờ người đã hướng dẫn bác cài HỏiCon" |
| `llm_processing`: "không gửi gì ra ngoài" quá rộng | ĐÃ đổi thành "không gửi bản tóm tắt cho dịch vụ AI" |
| `core_protection`: câu đầu 39 từ | ĐÃ tách; kèm bỏ "Lúc khác không theo dõi gì" (mâu thuẫn với màn quét cuộc gọi), "mã OTP" → "mã xác thực (OTP)", tên nút "Vẫn tiếp tục" ở `overlay_pause` |

Chữ hiển thị đổi nên `sha256` trong `manifest.json` đổi theo (các văn bản chưa phát hành, chưa có dòng đồng ý nào dùng chúng nên không tăng version). **Android phải ghim lại sha mới khi làn A đồng bộ (T012).** Còn mở, chờ Minh hoặc làn A: 13 Trung bình và 9 Thấp (hạn lưu "rồi xóa" rõ hơn, "đường link", thêm cách rút cho `voice_input`, `lookups`, `drills`, số hỗ trợ thật…). Reviewer không kiểm được: nghe TTS, chữ 200%, điều khoản nhà cung cấp LLM.

## Còn mở (không đánh ☑)

T010 (Minh duyệt), T011 (người thật đọc thử), T012 (làn A đồng bộ). Thực thi `llm_processing`, `voice_input`, `pilot_research` ở mã. Nhờ người có chuyên môn pháp lý rà soát và đối chiếu luật gốc.

## Android đã đồng bộ (Làn A Wave 2, 21/10/2026) — T012 MỘT PHẦN, không tick

- `res/values/consent_texts.xml`: 10 mảng chuỗi, mỗi mục đích đúng một mảng, mỗi dòng = một dòng khối `BEGIN-TEXT` của `docs/legal/consent/<purpose>.vi.md`. `ConsentTexts.kt` đọc đúng các mảng này (nối `\n`), và E3, E4 (3 trang quyền), E10 vẽ chính các dòng đó, nên chữ băm vào sổ là chữ người dùng đọc.
- `ConsentLedger.VERSION` = `2026.10-v3` (khớp manifest). Người đã đồng ý bản v2 sẽ thấy E3 lại (luật 7).
- `ConsentManifestPinTest` (thay `ConsentTextsPinTest`): chữ app = chữ `.md` từng dòng; sha256 = manifest; version = `VERSION`; thêm ghim sha cứng. Đột biến (đổi một dấu `.` thành `!` trong XML) ⇒ đỏ, đã khôi phục. Test thứ hai cấm các câu hứa "quyền nào đang tắt".
- Đã bỏ câu "cho con biết quyền nào đang bật hay tắt" ở E3 và ở bản đọc to; bản đọc to E3/E10 viết lại cho khớp chữ mới (3 số cuối + mã thay cho số, hạn 90 ngày).
- App chỉ xin 7 trong 10 mục đích; `llm_processing`, `voice_input`, `pilot_research` có chữ trong app nhưng KHÔNG có màn nào xin và không bao giờ ghi vào sổ (mã chưa thực thi, xem trên).
- Chưa làm: #16 tên người giám hộ thay "con bác", chia thẻ có "Nghe lại" cho `core_protection`; chưa chụp E3/E4 chữ 200% sau đổi; văn bản vẫn là BẢN NHÁP chờ Minh duyệt (T010) nên T012 không tick.

## Wave 3 (22/10/2026) — T018: kiểm lại Verify của đồng bộ chuỗi Android

- `gradlew :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`: xanh (gồm `ConsentManifestPinTest`, thay `ConsentTextsPinTest` như đã ghi ở Wave 2).
  `scripts/release-gate.sh` còn gọi tên test cũ ⇒ đã đổi (xem `specs/012-release-and-hosting/evidence.md`), cổng chạy thoát 0 trên AAB release và demo.
- `emu-scenario.py --scenario fake_police` (n = 10, số máy ảo): hc-api36 10/10 ĐẠT (SafePause p95 1091 ms điều khiển từ xa, 1270 ms ngân hàng); hc-api34 10/10 ĐẠT. Đường dừng an toàn không đổi.
- **Ảnh** `~/hoicon-evidence/011-consent-legal/w3/` (hc-api36, 1080×2400, backend dev cổng 18001, DB `hoicon_android`): E3 `e3-{100,200}-*` (đầu → cuối cuộn), trang quyền E4 đầu tiên
  `e4page-{100,200}-*`, màn "Xong rồi" `e4-{100,200}-*`, E10 `e10-{100,200}-*`. Chỉ chụp trang quyền đầu tiên (2 trang còn lại cùng khung, khác chữ): chưa chụp.
- **`ux-elder-reviewer` (22/10, đọc 15 ảnh):** 0 Chặn, **1 Cao**: "Đã kết nối với w3-gia-dinh." hiện mã kỹ thuật. Đây là **tên gia đình thử** do tôi đặt trong DB dev
  (dữ liệu hư cấu), không phải chuỗi của sản phẩm; app hiện tên backend trả về. Còn mở để cân nhắc: dòng đó nên đổi thành "Đã kết nối với gia đình của bác" nếu tên
  gia đình thật không phải lúc nào cũng đọc được. Trung bình: khối chữ E3 dày ở 100% (đề xuất tách 3 ý có tiêu đề), câu đường lui "bác muốn đổi ý lúc nào cũng được" nên rõ hơn,
  trang quyền có 4 đoạn trước nút "Mở cài đặt" (đề xuất đưa nút lên), màn "Xong rồi" thiếu "Kéo xuống đọc tiếp ↓", nhãn "✗ Chưa bật" nhỏ. Thấp: nháy thẳng ở E10, câu
  "để không bị kẻ xấu lợi dụng". Phần chữ của các đề xuất nằm trong `docs/legal/consent/` (làn B/Minh duyệt, T010) và phần bố cục ngoài task ⇒ **cần Opus/Minh**; không sửa.
- Văn bản vẫn là bản nháp `2026.10-v3` chờ Minh duyệt (T010); T012 vẫn BLOCKED. Tick T018.
## Wave 3 (làn B)

- **T019 ĐẠT:** `backend/tests/contract/test_consent_release_block.py` (5 test; chưa có mã Wave 2 như ghi chú ban đầu nên viết mới). Đột biến: thêm `llm_processing` vào `released` ⇒ báo thiếu `test_consent_enforcement_llm_processing.py`.

## Wave 5 — T013, T014, T021, làn B, 23/10/2026

- **T013 ĐẠT:** `LlmRouter.structured(..., consented: bool)` bắt buộc (không mặc định, quên truyền ⇒ `TypeError`); `consented=False` ⇒ trả `fallback` trước mọi truy cập client, `error="consent"`, chi phí 0. Đồ thị gọi `llm_consented()` (đọc `consent_gate.state_for(...).llm_processing` lúc gọi) ở 3 chỗ: `risk_scorer`, `intervention`, `case_file`. Miễn khi eval/demo/mô phỏng (`incident_id` không phải UUID, `is_demo`, `sim`); không có dòng sự cố / `member_id` NULL / lỗi đọc ⇒ **đóng**. Test: `tests/unit/test_llm_router.py` (2), `tests/integration/test_consent_enforcement_llm_processing.py` (7: chưa có dòng, đã rút, đã đồng ý, mục đích khác không thay thế, demo miễn, không có dòng sự cố, đệm không sống sau `invalidate`). Đột biến (cổng luôn mở) ⇒ 3 test đỏ.
- **T014 ĐẠT:** `ops/pilot.py::build_report` bỏ thiết bị/sự cố của người chưa (hoặc không còn) đồng ý `pilot_research`; nhà không có ai đồng ý không có mặt; `evaluate_gate` ẩn độ phủ gộp khi < 3 gia đình (`MIN_GROUP`). Heartbeat vẫn được nhận (không đổi `heartbeat_service`). Test: `tests/integration/test_consent_enforcement_pilot_research.py` (5) + `test_ops_pilot.py` (fixture mặc định cấp `pilot_research`). `consent_texts check` đạt.
- **T021 ĐẠT:** `consent_gate.web_readable()` + `WEB_READ_PURPOSE = "guardian_alerts"` (hằng số, plan D9); danh sách `/v1/guardian/incidents` lọc theo thành viên còn đồng ý (mặc định: rỗng), chi tiết, `/v1/incidents/{id}/run`, `/v1/runs/{id}/steps|stream` ⇒ cùng 404; luồng SSE đang mở kiểm lại mỗi nhịp (`still_allowed`) và dừng khi rút. Dữ liệu demo được miễn. Test: `tests/integration/test_guardian_consent_gate.py` (4) + `test_trace_stream.py` (2).
- **T020 MỘT PHẦN (chưa tick):** hai trong ba lời hứa đã có mã + test (tên tệp khớp T019); `voice_input` chờ spec 004; Minh chưa duyệt văn bản (T010) nên không đổi trạng thái `approved`.
- **security-privacy-reviewer (đọc diff chưa commit):** 0 Critical, 2 High, 4 Medium, 3 Low. ĐÃ SỬA: #2 High (luồng SSE vẫn chạy sau khi rút) · #3 Medium (cổng LLM mở khi không có dòng sự cố/`member_id` NULL) · #4 Medium (race `state_for` ↔ `invalidate`: bộ đếm thế hệ, truy vấn bắt đầu trước `invalidate` không ghi đệm) · #9 Low (`getattr` mặc định False).
  **CHƯA sửa — cần Minh/Opus quyết:** #1 High: `GET /action/{token}` (link Zalo đã gửi) và `POST /incidents/{id}/decision` không qua `web_readable` — người giám hộ vẫn mở được link cũ/ghi quyết định sau khi người cao tuổi rút `guardian_alerts` (đây là đường an toàn: ghi quyết định dừng nhắc/leo thang; chặn nó là quyết định chính sách, ngoài phạm vi T021 "route đọc web"). #5 (ngưỡng < 3 gia đình chỉ ẩn độ phủ gộp, báo cáo từng nhà vẫn liệt kê cho người vận hành), #6 (N+1 và đồng ý đọc lúc chạy báo cáo, loại hồi tố), #7 (hồ sơ dùng `row.is_demo`, nơi khác `incident.is_demo` — test 031 yêu cầu), #8 (N+1 danh sách web). Đệm đồng ý trễ tối đa 60 giây khi đồng ý đổi từ kênh khác không gọi `invalidate` (đã ghi từ spec 034); DPIA chưa nêu — việc cho Opus.

## Wave 6 (làn A, 24/10/2026) — T022 bố cục (không đổi chữ đồng ý)

**Nguồn: máy ảo hc-api36 (API 36), bản debug; máy ảo ≠ máy thật.** Lưu ý lịch sử commit: mã T022 nằm chung commit `6c318d7` (050 T014) và `3781648` (010 T029 evidence) — sai chỗ so với quy tắc "mỗi task một commit", nội dung đúng.

- **Đã làm:** (a) màn "Xong rồi" truyền `scrollHint = true` cho `OnboardingScaffold` (dùng lại dải "Kéo xuống đọc tiếp ↓" có sẵn, không chép mã); (b) `PermissionsScreen` cắt chữ giải thích sau đoạn đầu (`splitLead`, test `PermissionLeadSplitTest`): đoạn đầu → nhãn trạng thái → nút "Mở cài đặt" → các đoạn còn lại; vẫn một nút chính mỗi mục; (c) nhãn "✓ Đã bật"/"✗ Chưa bật" đậm (`bodyLarge` + `FontWeight.Bold`, cả ở thẻ "Xong rồi" qua `InfoCard(bodyBold = true)`), vẫn biểu tượng + chữ; (d) không đụng dòng "Đã kết nối với …". Nút "Mở cài đặt" đổi viền xanh đậm 2 dp như nút phụ khác (reviewer vòng 1: viền nhạt trông như bị vô hiệu). Chữ đồng ý không đổi: `ConsentManifestPinTest` xanh; `:rules:test :app:testDebugUnitTest :app:lintDebug` xanh.
- **Ảnh** `~/hoicon-evidence/011-consent-legal/w6b/` (1080×2400, 100% và 200%, có cuộn thật): `e3-*` (tham chiếu), `e4page-*` (trang quyền từng bước, không đổi), `e4list-{100,200}-N` (danh sách quyền, có mục ✗ Chưa bật), `done-{100,200}-N` ("Xong rồi"), `e10-{100,200}-N`. Thư mục `w6/` là lượt đầu (một số ảnh sai màn), bỏ. Chỉ chụp hc-api36 như task yêu cầu.
- **`ux-elder-reviewer`:** vòng 1 (w6/): 0 Chặn, 2 Cao — cả hai là ảnh tôi chụp sai màn (danh sách quyền 200% rơi về màn chính; E10 là màn "Xong rồi"), 1 Trung bình thật (viền nút nhạt ⇒ đã sửa). **Vòng 2 (w6b/, 18/40 ảnh đã xem): lỗi bản dựng 0 Chặn / 0 Cao / 1 Trung bình / 3 Thấp ⇒ ĐẠT.** (a) (b) (c) xác nhận bằng ảnh. Còn mở (không chặn): chưa có ảnh "Xong rồi" với mục ✗ (Trung bình; mọi quyền đã bật trong lượt chụp); vùng chạm nút phụ ước lượng 62–63 dp từ ảnh (code đặt `heightIn(min = 64.dp)`, chưa đo `uiautomator`); `e4list-200` không bắt đầu từ đầu danh sách; vùng mờ cuối cuộn ở 200% làm mờ nửa dòng.
- **Cần Minh/Opus (chữ đồng ý, không làm):** thêm nút "Mở cài đặt để tắt" cho mục đã bật (quyền rút đồng ý); đoạn "Nhờ vậy…" đứng sau nút nên các câu an toàn bị đẩy xuống dưới nút — cân nhắc viết lại; thống nhất dấu nháy “ ” trong chữ đồng ý; "✗" có thể gây cảm giác lỗi — cân nhắc "○ Chưa bật" + `stateDescription`; ô tích "từ 18 tuổi" ở E10 cần đo vùng chạm cả hàng.

## Lượt 9 (làn A, 24/10/2026) — T023 bố cục/nhãn (không đổi văn bản đồng ý)

**Nguồn: hc-api36 (API 36), bản debug; máy ảo ≠ máy thật.**
- **Đã làm:** (1) mục đã bật có nút phụ "Mở cài đặt để tắt" (`PermissionsScreen`, viền navy 2 dp, `heightIn(min = 64.dp)`; `PermissionOpener.openToDisable` mở trang tắt đúng loại: Mặc định ứng dụng cho vai trò sàng lọc, trang overlay/usage access/thông báo/pin của chính mục đó); (2) "✗ Chưa bật" ⇒ "○ Chưa bật" + `stateDescription` "Chưa bật"/"Đã bật" (TalkBack đọc trạng thái bằng chữ, không đọc ký tự); (3) hàng ô tích "từ 18 tuổi" ở E10 **đã** là `toggleable` cả hàng `heightIn(min = 64.dp)` từ trước (`DrillConsentScreen.kt`) — không cần sửa mã, chỉ đo: **uiautomator = 64,0 dp cao × 363,4 dp rộng ở 100%; 95,2 dp cao ở 200%**. Nút "Mở cài đặt để tắt" đo **64,0 dp** ở cả 5 mục. Chữ đồng ý không đổi (`ConsentManifestPinTest` xanh); `PermissionSwitchOffTest` (3 kiểm: trang tắt của từng quyền, chuỗi) đỏ (không biên dịch) → xanh; `:app:testDebugUnitTest :app:lintDebug` xanh.
- Ảnh `~/hoicon-evidence/011-consent-legal/w9/`: `e4list-{100,200}-N` (mọi mục bật: có nút tắt), `off-100-p2` + `off-200-N` (mục chưa bật: "○ Chưa bật" + "Mở cài đặt"), `chk1` ("Xong rồi" với "Còn nữa ở dưới ↓"), `e10-{100,200}-N`. `trung-gian/` = ảnh trạng thái trung gian (không dùng làm bằng chứng).
- **`ux-elder-reviewer`:** lỗi bản dựng vòng 1 = 0 Chặn, **1 Cao** (A1: dòng trạng thái dùng `contentDescription` thay `stateDescription`) ⇒ đã sửa `stateDescription` và chạy lại test/lint xanh (không đổi ảnh). Còn: A2 Trung bình (nhãn nút tắt ghi đè chữ hiển thị nhưng chứa trọn chữ — chấp nhận), A3 TB (ảnh `off-100-a/b/c` là trạng thái trung gian ⇒ đã chuyển vào `trung-gian/`), A4/A5 Thấp (khoảng trống E10; hộp tích nhỏ ~24 dp — cả hàng nhận chạm). **Sau sửa: A = 0 Chặn / 0 Cao.** Chưa chạy TalkBack thật (chỉ đọc mã/ảnh).
- **Trả lời B1 của reviewer (rút đồng ý):** tắt quyền ở Cài đặt rồi quay lại ⇒ `MainActivity.refresh()` đồng bộ sổ đồng ý (`ConsentSync`): quyền tắt thành dòng `granted=false` mới (đã có từ Wave 4, chưa chụp ảnh "sau khi tắt").
- **Cần Opus/Minh (không làm):** câu mở đầu "Mục nào chưa bật, bác bấm để bật." chưa nhắc đường tắt (chữ); hai nút "Mở cài đặt" / "Mở cài đặt để tắt" cùng kiểu dễ bấm nhầm — cân nhắc vị trí/biểu tượng; ở 200% mỗi mục dài vài màn hình (cần đầu trang tóm tắt "Đã bật 4/5"); câu "Bác chưa đồng ý cũng không sao" ở E10 đến muộn; ô tích nên có viền/nền để thấy vùng chạm.

## Lượt 10 — T024 Medium/Low còn lại của rà soát T021 (làn B, 25/10/2026)
- **#7** hồ sơ vụ việc dùng `incident.is_demo` (như mọi route khác) thay `row.is_demo`: test đỏ trước (`test_case_file_visibility_follows_the_incident_is_demo_flag_not_the_row_copy`): sự cố THẬT mà hồ sơ gắn nhãn demo nhầm, chưa đồng ý ⇒ trước đây đọc được, nay 404; sự cố demo + hồ sơ nhãn thật ⇒ đọc được. Test 031 cũ (`…404_until_it_consents`) dựng "nhà thật" bằng cách chỉ đặt `row.is_demo=False` trên một sự cố demo (cách dựng sai nguồn sự thật) ⇒ đổi sang đặt `incident.is_demo=False`; ý nghĩa test giữ nguyên.
- **#6/#8** N+1: thêm `consent_gate.states_for(session, member_ids)` (mục còn đệm lấy từ đệm, phần còn lại MỘT truy vấn `DISTINCT ON (member_id, purpose)`; người chưa có dòng nào ⇒ đóng) dùng ở `web_readable_members` (danh sách web) và báo cáo thí điểm (`ops.pilot`, đồng ý `pilot_research` theo từng gia đình). Test đỏ trước `tests/integration/test_consent_gate_batch.py` (đếm câu SQL tới `consents` ≤ 1, kết quả bằng `state_for`, lần hai toàn bộ từ đệm, người lạ đóng). Báo cáo thí điểm vẫn mỗi gia đình một lô (không N+1 theo thiết bị).
- Verify: `pytest tests/integration -k "case_file or guardian_web or pilot or consent or incidents"` 250 passed, 10 skipped; ruff sạch.
