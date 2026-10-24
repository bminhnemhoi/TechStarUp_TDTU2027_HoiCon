# Bằng chứng nghiệm thu Spec 031: Hồ sơ vụ việc

- **Trạng thái (22/10/2026, Wave 3 làn B)**: T001–T013, T015 xong; T014 (Android, làn A), T016 (cổng cuối cần chạy sau khi gộp), T017/T018 BLOCKED. Số liệu dưới đây: máy dev Linux, Postgres Docker dùng chung, cassette `synthetic`, không gọi LLM thật.
- **Nguồn số dự kiến**: pytest + Playwright trên máy dev; không có người giám hộ thật (T017 BLOCKED).

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 có hồ sơ khi nghi lừa đảo | 100% `case_open` thật có 1 bản nháp + 1 tin; 0 cho diễn tập/eval/sim | pytest đồ thị | `test_case_file_graph.py` (9) + `test_case_file_scenarios.py` (6 ca): `scam` ⇒ 1 dòng `draft` + 1 tin, chờ ở `await_case_approval`; `safe`, diễn tập, thread eval, chưa đồng ý `guardian_alerts` ⇒ 0; lỗi dựng hồ sơ không treo thread; runtime dựng lại vẫn chờ đúng interrupt. Máy dev, DB dev, n = 1 lượt/ca | ĐẠT |
| SC-002 không PII | 0 `case_secrets` trong content, tin, `agent_steps` | pytest | 5 kịch bản (3 thường + 2 chèn lệnh) quét `case_secrets` trong `content`, tin Zalo, `agent_steps` = 0; `test_case_file_content.py` (9) quét số/HMAC/tên gói; phản hồi API cũng quét | ĐẠT |
| SC-003 ô tự điền không rời máy | 0 yêu cầu mạng chứa giá trị | Playwright | `e2e/case-file.spec.ts`: điền số điện thoại + tài khoản/số tiền rồi duyệt và in ⇒ 0 yêu cầu chứa giá trị (URL + thân), không `<form>`, không localStorage/sessionStorage. **Giới hạn:** mạng bị chặn bằng fixture hợp đồng, chưa chạy với API thật | ĐẠT (fixture) |
| SC-004 máy trạng thái hồ sơ | 200/409 đúng; đóng sự cố khi `mark_sent`/`discard` | pytest | `test_api_case_file.py`: 4 đường hợp lệ (đúng trạng thái hồ sơ + sự cố đóng với actor guardian, lý do `case_sent`/`case_discarded`), 8 cặp không hợp lệ ⇒ 409 không đổi gì, gia đình khác ⇒ 404, sai Origin ⇒ 403, trường lạ ⇒ 422, chưa đồng ý ⇒ 404 | ĐẠT |
| SC-005 hạn lưu chạy được | 30 ngày ⇒ `closed`; 12 tháng ⇒ xóa; purge ⇒ 0 hồ sơ | pytest đồng hồ giả | `test_case_autoclose.py`: 29 ngày giữ, 31 ngày đóng (actor system; nháp ⇒ `discarded` + resume `discard`; `approved` giữ nguyên), lũy đẳng; `test_case_file_retention.py`: job 12 tháng chọn trúng sự cố có hồ sơ (dry-run, DB dùng chung), xóa dữ liệu gia đình ⇒ 0 hồ sơ; CASCADE ở `test_schema_0011.py`. **Giới hạn:** không chạy xóa thật 12 tháng trên DB dev dùng chung (sẽ xóa dữ liệu của người khác) | ĐẠT (có giới hạn) |
| SC-006 LLM không bắt buộc | không khóa ⇒ `template`; LLM bẩn ⇒ `template` | pytest | `test_case_file_summary.py` (≈ 270 ca): câu sạch ⇒ dùng; số/link/kênh chat/số tiền bằng chữ/lời khuyên nguy hiểm/NFD ⇒ mẫu; không khóa, lỗi, quá hạn ⇒ mẫu; mẫu đọc ổn ở 3 alias × 5 app × 4 mức × 4 tổ hợp. Cassette smoke/full không có phản hồi `case_file` ⇒ `template` | ĐẠT |
| SC-007 người giám hộ thật | duyệt + in, nói lại được | phỏng vấn | — | BLOCKED (thí điểm) |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| jsonschema: fixture `case_file.v1` (2 valid, 7 invalid), `case_file_action.v1` (3 valid, 3 invalid) | valid hợp lệ, invalid bị từ chối |

## Wave 3 làn A (22/10/2026) — T014 BLOCKED (chờ làn B)

Điều kiện tiên quyết "Sau T011" chưa có trên nhánh: `031 T011` (văn bản đồng ý gộp 031 + 032, làn B) chưa tick và `docs/legal/consent/manifest.json` vẫn là `2026.10-v3` chưa có bản gộp `guardian_alerts`. Chưa đồng bộ chuỗi Android; không tick T014.

## Wave 3 — ghi chú thi công (làn B, 22/10/2026)

- **Lệch so với chữ của tasks/spec (cần Opus):**
  1. Router chỉ có hồ sơ `fast` ⇒ đoạn tóm tắt dùng `fast`, không phải `strong` (T005).
  2. `unsafe_advice` của 036 chưa có trong mã ⇒ bộ lọc cụm từ riêng `_UNSAFE_ADVICE` ở `case_file_service` (cộng chặn mọi chữ số và tiền viết bằng chữ).
  3. Hướng dẫn trình báo (`report_guidance.vi.yaml`, `approved: false`) có tệp + test + `COPY` trong Dockerfile nhưng **chưa đưa lên web**: `case_file.v1` không có trường hướng dẫn, nên trang chỉ hiện câu chung "Anh/chị liên hệ công an nơi cư trú và ngân hàng của người thân". Muốn hiện hướng dẫn đã duyệt cần thêm trường vào hợp đồng (T018, chờ Minh).
  4. Test nội dung đặt ở `tests/integration/test_case_file_content.py` (cần DB), không phải `tests/unit/`.
  5. T011: văn bản đồng ý gộp 031 + 032 **khác chữ Opus soạn** theo `ux-elder-reviewer` (mức Chặn: câu "HỏiCon không tự gửi cho cơ quan nào" chưa nằm trong văn bản người dùng thấy; "máy bác hết được bảo vệ" nghe như bị hack). Bản `2026.10-v4`, `draft`, 160 từ, `consent_texts check` đạt; làn A phải ghim lại sha (T014).
  6. Hồ sơ chỉ đọc/duyệt được khi người cao tuổi còn đồng ý `guardian_alerts` (hồ sơ demo `is_demo` được miễn) và đồ thị bỏ qua hồ sơ khi chưa đồng ý — thêm theo `security-privacy-reviewer`, spec chưa nói.
  7. Đồ thị: lỗi dựng hồ sơ không làm hỏng kết cục (ghi bước `case_file` `created: false`, đi tiếp `END`).
- **Reviewer (T015):** `security-privacy-reviewer` 0 Critical/0 High, 4 Medium đều SỬA (đồng ý `guardian_alerts` ở đồ thị + route; bộ lọc LLM yếu — NFC, mọi chữ số, tiền bằng chữ, cụm khẳng định; `run_autoclose` không còn dừng cả vòng vì một sự cố; lỗi nút `case_file` không treo thread), Low chưa sửa: `await_case_approval` mặc định `discard` khi giá trị lạ, duyệt đến trước interrupt thì resume bị bỏ, DB không ép máy trạng thái hồ sơ, `source` chưa qua `mask_text`, GET 500 nếu đổi enum `content`, chưa có giới hạn tần suất riêng cho POST. `ux-elder-reviewer` 2 Chặn + 4 Cao + Trung bình đều SỬA (bản in giữ câu "không tự gửi" + chân trang có ngày duyệt + mã hồ sơ, 3 bước ngay đầu, nút xác nhận mang tên hành động, "Bỏ hồ sơ" tách xa + nói không hoàn lại được, trạng thái đã nộp/đã bỏ có lối ra, nhãn AI gộp một khung, ô tự điền có cảnh báo mất khi đóng + `inputMode`, tiêu đề con "{alias} trả lời", câu mẫu tóm tắt sửa ngữ pháp, ngôi thứ ba trong dòng thời gian). Chưa sửa: nút nghe đọc to cho phần tóm tắt, `aria-busy` cho nút đang gửi.
- **Hạ tầng:** migration `0011` đã áp lên DB dev (head = 0011; 032 sẽ là 0012). Chưa chạy lại `infra/postgres/roles.sql` trên DB dev: `hoicon_app` cần quyền `case_files` (SELECT/INSERT/UPDATE/DELETE) khi áp ở prod — **việc cho Tiến**: `roles.sql` cấp theo vòng lặp mọi bảng hiện có (dòng 41) nên chỉ cần chạy lại sau migration, như ghi chú trong tệp.
- **Lượt chạy cuối:** pytest cuối: **2627 passed, 21 skipped**; trước đó 1 lần `test_guardian_incidents::test_list_matches_the_contract_and_carries_alias_and_run_flag` đỏ trong lượt toàn bộ nhưng xanh khi chạy riêng và ở các lượt sau (nghi chạy chung DB dev, chưa tái hiện); web e2e 95 passed + 1 skipped.

## Wave 4 làn A (23/10/2026) — T014: đồng bộ chuỗi `guardian_alerts` `2026.10-v4` trên Android

- `consent_texts.xml` mảng `consent_guardian_alerts` = đúng 8 dòng `BEGIN-TEXT` của `docs/legal/consent/guardian_alerts.vi.md`; `sha256` khớp `manifest.json` (`afd24915…`).
- **Phiên bản theo từng mục đích.** Manifest giờ lẫn `2026.10-v4` (chỉ `guardian_alerts`) và `2026.10-v3` (chín mục còn lại), nên một hằng `ConsentLedger.VERSION` không còn đúng cho mọi dòng.
  `ConsentLedger.versionOf(purpose)` trả v4 cho `guardian_alerts` và `VERSION` (v3) cho các mục khác; `DISCLOSURE_VERSION` (= v4) là phiên bản E3 lưu khi bấm "Đồng ý" và là cửa
  `mayShareWithFamily`. Hệ quả: người đã đồng ý E3 bản v3 sẽ thấy E3 lại và chưa gửi gì cho gia đình tới khi đồng ý bản v4 (luật 7); `lookups` và `drills` **không** hỏi lại (chữ không đổi).
  Dòng sổ gửi máy chủ mang `versionOf(purpose)`.
- `ConsentManifestPinTest`: so version theo `versionOf`, ghim sha mới của `guardian_alerts`; test mới `guardianAlertsCarriesItsOwnNewerVersionSoE3IsAskedAgain`. Đột biến (đổi một dấu `.` thành `!` trong XML) ⇒ đỏ, đã khôi phục.
  Trước sửa: `ConsentManifestPinTest` đỏ (version v3 ≠ manifest v4). Sau sửa: `:rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug` xanh.
- Chạy thật hc-api36 (backend 18001, DB `hoicon_android`): sổ máy chủ có dòng `guardian_alerts` `2026.10-v4` granted sau khi bấm "Đồng ý, tiếp tục" ở E3.
- Ảnh E3 (thẻ guardian nằm trên E3, không phải trang quyền E4): `~/hoicon-evidence/031-case-file/w4/e3-{100,200}-*.png`.
- **`ux-elder-reviewer`:** 0 Chặn, 0 Cao (đọc 7 trong 14 ảnh; không đọc hết các ảnh giữa 200%). Trung bình (chữ nằm trong `docs/legal`, **cần Opus/Minh**): thẻ dài (≈ 160 từ, ≈ 9 màn ở 200%) nên thêm dòng tóm tắt đầu thẻ;
  khoảng cách tiêu đề–thân thẻ; câu "Muốn ngừng báo, bác nhờ người cài HỏiCon" khiến phụ thuộc; câu "Họ được báo nếu HỏiCon bị tắt" ngắn gây lo. Thấp: "Nghe lại" nằm trước thẻ guardian (chưa kiểm bản đọc to có đọc cả thẻ),
  "Ở bước sau…" cứng, "Khi nghi bác bị lừa" nên dịu hơn.
- Chưa làm: sửa bản đọc to `disclosure_speech` (câu về báo con qua Zalo vẫn đúng, không thêm ý mới). Tick T014.

## Wave 6 — T019 (làn B, 24/10/2026)

- **T019 ĐẠT**: `case_file_service.load_guidance()` (`@cache`, đọc `data/case_file/report_guidance.vi.yaml` một lần; kiểm: `approved` bool, `fallback_vi` 10–240, ≤ 8 bước, id đúng mẫu và không trùng, `text_vi` 10–240, không dãy ≥ 4 chữ số; sai ⇒ `ValueError`; chưa duyệt ⇒ `steps` rỗng dù tệp có bước) gọi lúc khởi động API (`lifespan`). `GET` và `POST /v1/guardian/incidents/{id}/case-file` luôn gửi `guidance` (`CaseGuidance` trong `CaseFileOut`, khớp `case_file.v1`). `spec.md` FR-005 đã ghi `fast` từ trước — không sửa.
  Đỏ trước (12 đỏ) → xanh: `tests/unit/test_case_guidance.py` (tệp thật chưa duyệt ⇒ 0 bước; tệp thử đã duyệt ⇒ đủ bước đúng thứ tự; 7 kiểu tệp hỏng bị từ chối), `test_api_case_file.py` (chưa duyệt ⇒ `steps == []` + `fallback_vi`, không dãy ≥ 4 chữ số; tệp thử `approved: true` qua monkeypatch ⇒ đủ bước, hợp lệ `case_file.v1`, POST cũng có `guidance`), `tests/contract`: **325 passed**. Client TS sinh lại, typecheck sạch, ruff sạch.
