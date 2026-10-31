# Kế hoạch Spec 011: Văn bản đồng ý, DPIA rút gọn, quy trình thí điểm

## 0. Kiểm theo hiến chương (bổ sung 18/10/2026 khi rà `/speckit-analyze`)

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Văn bản nói rõ dữ liệu nào đi đâu, giữ bao lâu; không số điều luật chưa kiểm |
| IV. Đồng ý + công khai AI | Mỗi mục đích enum có đúng một văn bản có phiên bản + sha256; 6 văn bản nhóm AI mở đầu câu công khai |
| V. Hợp đồng | `manifest.json` là hợp đồng giữa văn bản, sổ `consents` và chuỗi Android (T018 ghim sha của manifest) |
| VII. Bằng chứng | Văn bản hứa điều mã chưa làm ⇒ chặn phát hành có máy kiểm (T019), không chỉ ghi chú |
| IX. Chặn phát hành | P1-08 (phát hành) cần văn bản `approved` (T010) **và** T019 xanh |

## 1. Thiết kế

```
docs/legal/consent/
  README.md            cách soạn, cách băm, cách tăng phiên bản, trạng thái nháp
  manifest.json        {version_scheme, released: [], purposes: [{purpose, file, version, sha256, status}]}
  <purpose>.vi.md ×10  tiêu đề + banner nháp + <!-- BEGIN-TEXT --> chữ hiển thị <!-- END-TEXT --> + ghi chú duyệt
backend/src/hoicon/ops/consent_texts.py   extract_text · sha256_of · load_manifest · problems() · check/write (CLI)
backend/tests/contract/test_consent_texts.py   enum ↔ tệp ↔ manifest ↔ schema ↔ CHECK; sha256; chất lượng chữ; DPIA; PILOT
docs/PRIVACY-DPIA.md   hoàn thiện mục "Cần điền" 1–7, giữ nguyên phần quy trình đã cài đặt (034)
docs/PILOT-PROTOCOL.md hoàn thiện
```

## 2. Quyết định

| # | Quyết định | Lý do |
|---|---|---|
| D1 | Mô-đun nằm ở `hoicon/ops/` (CLI `check|write`) | Cùng mẫu các lệnh vận hành khác; không chạy trong API |
| D2 | Băm chữ hiển thị chuẩn hóa, không băm cả tệp | Ghi chú soạn thảo đổi không làm đổi bằng chứng (Q1) |
| D3 | `released` rỗng; test bất biến kiểm trên dữ liệu giả | Chưa có bản nào đưa cho người thật; vẫn bảo vệ được từ ngày đầu |
| D4 | Danh sách mục đích lấy từ `typing.get_args(Purpose)` | Thêm giá trị enum mà quên văn bản ⇒ test đỏ ngay |
| D5 | Đối chiếu thêm lược đồ `docs/schemas/consent_record.v1.json` và CHECK trong `db/models.py` | Ba nơi khai báo enum phải khớp; chỉ đọc lược đồ, không sửa |
| D6 | Luật chất lượng chữ ở mức thô (độ dài câu, từ cấm, công khai AI) | Máy không đánh giá được "ấm áp"; việc đó thuộc `ux-elder-reviewer` |
| D7 | Không trích điều luật | Chưa có nguồn đã kiểm; chỉ nêu tên + số hiệu từ ghi chú nghiên cứu, ghi rõ chưa đối chiếu |
| D8 | (18/10) Ba lời hứa chưa có mã (`llm_processing`, `pilot_research`, `voice_input`) được **thực thi bằng mã** khi tính năng có thật, không bỏ chữ | Lời hứa đúng về mặt riêng tư; bỏ chữ rồi thêm lại sau tốn một lần hỏi lại đồng ý. Trong lúc chờ: chưa có khóa LLM ⇒ không gửi gì cho dịch vụ AI; chưa có người thí điểm ⇒ chưa có báo cáo; chưa có giọng nói ⇒ chưa ghi âm. T019 chặn "phát hành" sớm |
| D9 | (18/10) Route đọc web của người giám hộ kiểm `guardian_alerts` qua một hằng số tên mục đích | Văn bản nháp nói việc xem lại trên web thuộc `guardian_alerts`; **★ Minh** quyết (MASTER-PLAN §8). Nếu Minh tách mục đích mới thì chỉ đổi hằng số + thêm enum (luật 7) |
| D10 | (18/10) Android đồng bộ theo bản nháp `v3` ngay (T018), không chờ Minh | Sổ `consents` trên máy dev/AVD hiện ghi sha của chữ `v2` (chỉ có trong `strings.xml`, không có trong `manifest.json`) ⇒ US-11.2 chưa đạt với bản ghi thật; bản nháp chưa đưa người thật nên đổi chữ lần nữa sau khi Minh duyệt chỉ tốn một lần nâng phiên bản |

## 3. Tái sử dụng (hiến chương VIII)

| Có sẵn | Dùng để |
|---|---|
| `typing.get_args(Purpose)` ở `api/routers/consents.py` | Nguồn danh sách mục đích (không chép tay) |
| `docs/schemas/consent_record.v1.json` + CHECK của `consents` trong `db/models.py` | Đối chiếu chéo enum (chỉ đọc) |
| Mẫu `tests/contract/test_*_schemas.py` (đọc tệp trong `docs/`, không cần DB) | Dáng test mới |
| Mẫu `ops/*.py` (`argparse`, chỉ in kết quả, mã thoát) | Dáng `ops/consent_texts.py` |
| `ConsentLedger.sha256Hex` + `consentTexts()` của Android (băm UTF-8 chuỗi nối `\n`) | Quy tắc chuẩn hóa chữ hiển thị |
| `DATA-MODEL.md` §6, spec 028 (≤ 2 lần/tháng), 034 (hạn lưu, xóa) | Nguồn của mọi con số trong văn bản |
Không thêm thư viện (chỉ `json`, `hashlib`, `re`, `pathlib`).

## 4. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Chữ nháp lệch chức năng thật (nói quá/thiếu) | Mỗi con số có nguồn trong ghi chú duyệt; `privacy-audit` đối chiếu mã |
| Android và manifest lệch (sha256 khác) | Liệt kê chỗ hard-code cần đồng bộ cho làn A; sha256 là hợp đồng |
| Minh duyệt bản nháp rồi sửa chữ | `released` + test bắt buộc tăng phiên bản |
| Văn bản dài, người cao tuổi không đọc | Giới hạn 160 từ/văn bản (kiểm bằng máy), `ux-elder-reviewer` |

## 5. Rà soát `/speckit-analyze` (18/10/2026, Opus — spec viết nhanh trong Wave 1)

Đối chiếu `spec.md` ↔ `plan.md` ↔ `tasks.md` ↔ mã (`ConsentLedger.kt`, `ConsentTextsPinTest.kt`, `routers/guardian.py`, `llm_router.py`).
Phủ FR: 11/11 FR có task. **0 CRITICAL, 2 HIGH (đã sửa), 4 MEDIUM, 3 LOW.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| A1 | HIGH | T013/T014 là task "Cần Tiến quyết" giữa `tasks.md` — trái MASTER-PLAN §2.6 (quyết định chốt ở plan, không có task chờ người); T013 tự gọi là "CRITICAL-for-release" nhưng không có gì chặn phát hành thật | Quyết định ghi ở D8; T013/T014 viết lại thành task thực thi BLOCKED có điều kiện gỡ chặn; thêm T019 (chốt chặn bằng test, chạy được ngay) |
| A2 | HIGH | T012 (đồng bộ Android) BLOCKED sau T010 (Minh duyệt) ⇒ Android vẫn ghi sổ đồng ý bằng chữ `v2` không có trong `manifest.json`, đúng điều US-11.2 muốn tránh | D10; T018 làm ngay theo `v3`; T012 chỉ còn là đồng bộ lại sau khi Minh sửa |
| A3 | MEDIUM | `plan.md` thiếu bảng kiểm hiến chương và thẻ làn (mẫu override yêu cầu) | Thêm mục 0; thẻ làn cho task chưa xong |
| A4 | MEDIUM | Đồng ý `drills` không có đường vào trên app (evidence, bảng privacy-audit) ⇒ 028 không mời được ai | Task 028 T023 [A] (dùng chuỗi của T018) |
| A5 | MEDIUM | `guardian_alerts` nói "xem lại trên web" nhưng route đọc web không kiểm đồng ý (027 ghi chú i) | T021 [B] + D9; quyết định ★ Minh ở MASTER-PLAN §8 |
| A6 | MEDIUM | `ConsentTextsPinTest` ghim sha chép tay ⇒ văn bản `docs/` đổi mà Android không đổi vẫn xanh | T018 ghim sha của `manifest.json` |
| A7 | LOW | Spec Q7 không tạo skill `consent-copy` trong khi CLAUDE.md nhắc skill này (MASTER-PLAN B1) | Giữ nguyên, B1 chờ Minh |
| A8 | LOW | `guardian_alerts` 159/160 từ: 031 và 032 đều cần thêm câu | Ghi rủi ro ở plan 031/032 (gộp một câu, rút gọn câu khác) |
| A9 | LOW | Tên giai đoạn trộn "Phase 4: Convergence" với "Giai đoạn" | Không sửa (không ảnh hưởng truy vết) |
