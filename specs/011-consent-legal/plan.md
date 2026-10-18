# Kế hoạch Spec 011: Văn bản đồng ý, DPIA rút gọn, quy trình thí điểm

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
