# Văn bản đồng ý theo từng mục đích (spec 011)

> **BẢN NHÁP — chờ Minh duyệt.** Mọi văn bản ở đây chưa được duyệt và **chưa được đưa cho người dùng thật**. Tên và số hiệu
> luật lấy từ `docs/research/notes/09_agentic_ai_tech_feasibility.md`, chưa đối chiếu văn bản gốc; các văn bản không trích số điều.

Mỗi giá trị của enum `consents.purpose` (10 giá trị, `backend/src/hoicon/api/routers/consents.py`) có **đúng một** tệp
`<purpose>.vi.md`. Bảng `consents` chỉ ghi thêm: mỗi dòng ghi `purpose`, `consent_version` và `text_sha256` — tệp trong thư mục
này là bản gốc để truy ra "người này đã đồng ý với chữ gì".

## Cấu trúc một tệp
1. Tiêu đề, dòng `BẢN NHÁP — chờ Minh duyệt` (khi `status = draft`).
2. **Chữ hiển thị** giữa `<!-- BEGIN-TEXT -->` và `<!-- END-TEXT -->`: mỗi đoạn một dòng, không ngắt dòng tay. Đây là phần duy nhất được băm.
3. "Nguồn của từng con số" (mỗi con số trong chữ phải truy được về mã hoặc tài liệu) và "Điểm chờ quyết" cho người duyệt. Hai mục này không hiển thị cho người dùng và không vào sha256.

## Băm và phiên bản
- `text_sha256` = SHA-256 của UTF-8 chữ hiển thị chuẩn hóa: các dòng khác rỗng, bỏ khoảng trắng cuối dòng, **nối bằng `\n`**. Cùng cách
  Android băm (`ConsentLedger.sha256Hex` trên các chuỗi nối `\n`): làn A chỉ cần để mỗi dòng ở đây là một chuỗi tài nguyên, đúng thứ tự.
- `manifest.json`: `purposes[]` (`purpose`, `file`, `version` dạng `YYYY.MM-vN` ≤ 16 ký tự, `sha256`, `status`) và `released[]`.
- `released[]` = các cặp (mục đích, phiên bản, sha256) **đã đưa cho người thật**. Đổi chữ của một cặp đã phát hành mà không tăng
  phiên bản thì kiểm tra thất bại (CLAUDE.md luật 7). Hiện `released` rỗng.

## Làm việc với văn bản
```bash
uv run --directory backend python -m hoicon.ops.consent_texts write   # sau khi sửa chữ: tính lại sha256 trong manifest.json
uv run --directory backend python -m hoicon.ops.consent_texts check   # kiểm đủ mục đích, sha256, phiên bản, chất lượng chữ
uv run --directory backend pytest tests/contract/test_consent_texts.py
```
Sửa chữ **chưa phát hành**: sửa tệp, chạy `write`. Sửa chữ **đã phát hành**: tăng `version` của mục đó trong `manifest.json` rồi chạy
`write`; giữ nguyên dòng cũ trong `released[]`. Thêm mục đích mới: thêm giá trị enum + tệp văn bản + migration CHECK (làn B), test sẽ đỏ nếu thiếu.

## Luật chất lượng (máy kiểm, ngưỡng ở `ops/consent_texts.py`)
Xưng "bác"/"con bác"; ≤ 160 từ mỗi văn bản, câu trung bình ≤ 25 từ; không số điều luật, không dãy số ≥ 4 chữ số; không cụm gây hoảng sợ hay hứa hoàn
tiền (dùng chung danh sách của eval); văn bản về AI/tác tử mở đầu bằng "Đây là trợ lý AI HỏiCon". "Ấm áp" thật sự do `ux-elder-reviewer` đánh giá.

## Còn chặn trước khi duyệt
`llm_processing`, `voice_input`, `pilot_research` hứa điều máy chủ/app **chưa thực thi** (xem mục "Điểm chờ quyết" trong từng tệp). Không đưa
cho người thật khi chưa thực thi hoặc chưa sửa chữ cho đúng sự thật.
