# Pipeline dựng thuyết minh HỏiCon (Word + PDF)

Sinh `HoiCon_Ban_mo_ta_y_tuong_TSC2027.docx/.pdf` từ mã nguồn: số liệu tài chính (`model.py`), hình (`figs.py`,
`journey.dot`), nội dung + định dạng (`build.js`, thư viện `docx`), cập nhật mục lục và xuất PDF bằng Word (`convert.ps1`).

> ⚠️ **Bản `.docx` trong `docs/proposal/` đã được Minh sửa tay trong Word.** Chạy lại pipeline sẽ tạo bản mới từ
> `build.js` và **mất các sửa tay đó**. Trước khi dựng lại: so sánh hai bản, chép các sửa tay vào `build.js`, rồi mới
> ghi đè. Ghi ra thư mục `out/` trước, không ghi thẳng vào `docs/proposal/`.

## Yêu cầu
Node ≥ 20 (`npm install` trong thư mục này — chỉ cần gói `docx`), Python 3.12 + matplotlib + numpy, Graphviz `dot`,
Microsoft Word (cho `convert.ps1`, dùng COM).

## Các bước (chạy trong `docs/proposal/src/`)
```bash
npm install
python model.py                     # → model.json + fig_finance.png (in bảng tóm tắt)
python figs.py                      # → fig_arch.png, fig_position.png
dot -Tpng journey.dot -o fig_journey.png
mkdir -p out && node build.js out/HoiCon_raw.docx
powershell -ExecutionPolicy Bypass -File convert.ps1 `
  -InDocx  "$PWD\out\HoiCon_raw.docx" `
  -OutDocx "$PWD\out\HoiCon_Ban_mo_ta_y_tuong_TSC2027.docx" `
  -OutPdf  "$PWD\out\HoiCon_Ban_mo_ta_y_tuong_TSC2027.pdf"     # in PAGES=<số trang>
```
Kiểm tra PDF (mục lục, không có trang trắng, bảng không vỡ, BMC vừa trang ngang) rồi mới chép sang `docs/proposal/`;
chép hình cuối cùng sang `docs/proposal/figures/` với tên `Hinh1…4`.

## Ghi chú
- `fig_*.png` và `out/` là sản phẩm sinh ra — đã gitignore.
- Định dạng theo thể lệ: tiếng Việt, Times New Roman 14, A4. Graphviz cần tên font có dấu phẩy cuối (`"Arial,"`) để
  Pango không hiểu nhầm.
- Mọi thay đổi cam kết (đội ngũ, quy mô thí điểm, số liệu) đi qua skill `pitch-sync`.
