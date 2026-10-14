# ADR-008: Dừng an toàn khi mở app ngân hàng — không dùng full-screen intent, thử bằng `:demobank`, chỉ phát hành qua Play

- Trạng thái: **Chấp nhận** · 14/10/2026 · số đo máy thật **chờ FTL** (P0-08) và **chờ Play internal** (P1-08)
- Bằng chứng: spike P1-S2 `docs/spikes/P1-S2-dung-an-toan.md`
- Liên quan: ADR-001 (luật tất định), ADR-005 (phát hành qua Play testing), ADR-007 (cơ chế cảm biến)

## Bối cảnh
ADR-007 đã chốt cách mở SafePause: dùng activity riêng được miễn trừ BAL nhờ quyền SAW, kèm đường dự phòng heads-up
+ TTS. Còn ba câu hỏi:
1. Full-screen intent (FSI) trên Android 14+ có thay được SAW không?
2. Thử với app ngân hàng thật bằng cách nào?
3. Danh sách app tài chính quản lý ra sao?

Thông tư 77/2025/TT-NHNN (hiệu lực 01/3/2026) buộc app Mobile Banking tự dừng khi phát hiện máy ảo, trình gỡ lỗi,
chế độ ADB, hooking, root (theo nguồn thứ cấp, chưa đối chiếu Công báo; tra vbpl.vn trước khi đưa vào thuyết minh).

## Quyết định
1. **Không khai báo `USE_FULL_SCREEN_INTENT` ở bản phát hành.** R1 chỉ kích hoạt khi app ngân hàng đang ở tiền cảnh,
   tức máy đang mở khóa; khi đó FSI chỉ hiện heads-up, trùng với đường dự phòng của ADR-007. Từ Android 14, Play chỉ
   cấp quyền này cho app gọi điện/báo thức. Thí nghiệm FSI chỉ nằm trong manifest `src/debug`. CI chặn nếu manifest
   release có quyền này.
2. **`:demobank` là mục tiêu thử và demo duy nhất** trên máy ảo, FTL, video và gian trưng bày. App mô phỏng luồng
   chuyển tiền kèm các hành vi của app thật có ảnh hưởng tới HỏiCon (`FLAG_SECURE` bật được, trạng thái giữ nguyên qua
   SafePause). Không quay hay chụp app ngân hàng thật.
3. **Độ trễ trên máy thật đo bằng `:latency` trên Firebase Test Lab.** Cuộc gọi được mô phỏng bằng
   `ScenarioReceiver`, receiver này chỉ có ở bản debug và được bảo vệ bằng quyền `DUMP` (chỉ shell/adb, root hoặc app
   hệ thống gửi được). Phần còn lại là đường găng thật. Bộ đo chỉ chạy trên máy ảo hoặc FTL (tự bỏ qua máy khác) và
   hoàn tác cài đặt sau khi đo. Kết quả FTL thay cho số máy ảo khi xét ngưỡng p95 ≤ 3 s của ADR-007, luôn kèm nhãn
   "máy thật FTL · bản debug · cuộc gọi mô phỏng · demobank": đạt thì kết luận được; trượt thì chưa (bản debug chậm
   hơn bản phát hành), phải đo lại bằng bản `demo` có R8 (P1-08).
4. **HỏiCon chỉ đến tay người dùng qua Google Play** (củng cố ADR-005). Không bao giờ gửi APK; không hướng dẫn bật tùy
   chọn nhà phát triển hay gỡ lỗi USB, vì làm vậy khiến app ngân hàng của người già ngừng chạy (TT 77).
5. **Danh sách app tài chính có một nguồn sự thật** là `data/bank_apps.vn.json` (schema `bank_apps.v1.json`).
   `scripts/gen-bank-apps.py` sinh `BankAppCatalog` (`:rules`) và `<queries>`; `BankAppCatalogTest` chặn lệch. Chỉ
   khớp đúng tên gói. Rà soát mỗi quý; tải bản mới qua `GET /v1/config` từ P2.
6. **Phản ứng của app ngân hàng thật với các quyền của HỏiCon** được thử theo giao thức §5 của spike: trên máy của
   thành viên đội sau P1-08; trên máy mượn chỉ sau P1-08 **và** P2-02, P2-05 (mục "Chặn phát hành"). Nếu ≥ 1
   app trong top 10 chặn khi có SAW: SAW thành tùy chọn ở E3, người dùng app đó đi đường heads-up + TTS, đồng thời gửi
   thư cho ngân hàng (gắn với mục tiêu LOI).

## Hệ quả
- P1-03 (video) quay bằng `:demobank` với `secure=false`. Bộ thí điểm (P2-14) và tài liệu cài đặt viết cho kênh Play.
- Ngưỡng p95 ≤ 3 s của gate G1 dựa trên số FTL (≥ 2 máy thật). Nếu trượt: làm ấm UI SafePause khi mở cửa sổ rủi ro,
  chọn View thuần, quét 500 ms (đã liệt kê ở ADR-007).
- Có thêm module `:latency` (phụ thuộc `androidx.test:runner`, `junit`), chỉ dùng để đo, không vào APK sản phẩm.

## Phương án đã loại
- FSI làm đường chính hoặc thay SAW: vô hiệu khi máy mở khóa, và vướng chính sách Play.
- Thử app ngân hàng thật trên máy ảo/FTL, hoặc cài APK lên máy thật qua adb: app ngân hàng sẽ tự dừng (TT 77) ⇒ số
  liệu sai lệch, và có hại nếu làm trên máy của người già.
- `QUERY_ALL_PACKAGES` hoặc khớp theo tiền tố gói: bị cấm (CLAUDE.md luật 3) và báo nhầm (`com.vnpay.*`).
