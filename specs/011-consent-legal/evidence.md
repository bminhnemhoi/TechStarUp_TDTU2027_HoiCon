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
