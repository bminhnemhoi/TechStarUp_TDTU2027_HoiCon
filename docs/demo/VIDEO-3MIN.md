# Video demo 3 phút — Vòng 1 (P1-03): kịch bản, shot list, số liệu có nguồn

> **Trạng thái (21/10/2026):** đây là **tư liệu và kịch bản đề xuất**, chưa dựng phim, chưa có giọng đọc. Người dựng phim (Minh/Tiến) quyết cuối cùng.
> Mọi cảnh dưới đây quay trên **máy ảo** (không phải điện thoại thật); số điện thoại, tên gia đình, tên cơ quan, ngân hàng đều **hư cấu**.
> Chưa duyệt bởi Minh. Không có tệp video nào nằm trong repo (xem "Tệp tư liệu").

## 1. Luồng và nguyên tắc

Cuộc gọi lạ → mở app ngân hàng (`:demobank`, ngân hàng mẫu) → **dừng an toàn** → HỏiCon hỏi bác một câu → bác bấm **"Hỏi con"** → cảnh báo tới người giám hộ
(tin Zalo **MÔ PHỎNG** + trang `/a/[token]`) → người con xác nhận.

- Cảnh Zalo luôn có dải **"MÔ PHỎNG — Zalo MOCK, không gửi tin thật"** trên khung hình (đã có sẵn trong tệp `s6`). Chữ tin là **chữ thật** do máy chủ soạn, lấy từ
  nhật ký của bộ Zalo giả (số cuối "002" là số hư cấu).
- Không nói số đo của máy ảo như số đo của máy thật. Trên màn hình/phụ đề ghi "đo trên máy ảo".
- Câu "Đây là trợ lý AI HỏiCon" xuất hiện trên mọi màn nói với người cao tuổi và ở đầu tin Zalo (luật công khai AI) — giữ nguyên trong khung hình.
- Skill `demo-video-director` gợi ý vài thứ **không dùng ở đây** vì chưa có bằng chứng đo hoặc lệnh không tồn tại: "100% WCAG AAA", "0 số điện thoại thô" (chưa đo bằng
  số liệu có nguồn), lệnh `emu-scenario.py reset` / `call-incoming` (không có); thay bằng `scripts/emu-demo-record.py` và số liệu ở mục 4.

## 2. Shot list (tổng ≤ 3:00)

| # | Mốc | Cảnh | Nguồn hình | Thời lượng tư liệu | Lời thoại đề xuất (giọng ấm, ~125 từ/phút) |
|---|---|---|---|---|---|
| 0 | 0:00–0:20 | Mở đầu: thẻ chữ, ảnh/đồ họa người cao tuổi và điện thoại (người đóng hoặc ảnh dựng — **chưa có tư liệu**) | cần dựng | — | "Bác nhận được một cuộc gọi từ số lạ. Người bên kia nói là công an, và giục bác chuyển tiền ngay. Con cháu không thể ở bên cha mẹ cả ngày." *(không nêu con số thống kê: chưa có nguồn)* |
| 1 | 0:20–0:35 | Cuộc gọi đến từ số lạ, bác nhấc máy | `s1_cuoc_goi_la.mp4` | 13,8 s | "HỏiCon là trợ lý AI trên điện thoại của bác. Khi có số lạ gọi, HỏiCon chỉ để ý 10 phút sau cuộc gọi đó. HỏiCon không nghe, không ghi âm cuộc gọi." |
| 2 | 0:35–0:50 | Bác mở ứng dụng ngân hàng → **dừng an toàn** hiện ra ngay | `s2_mo_ung_dung_ngan_hang.mp4` (cắt 0–4 s) | 12,1 s | "Bác vừa mở ứng dụng ngân hàng. HỏiCon hiện ngay màn dừng lại, không cần chờ mạng." |
| 3 | 0:50–1:10 | HỏiCon hỏi bác một câu (CÓ / KHÔNG / KHÔNG RÕ) | `s3_cau_hoi_cua_hoicon.mp4` | 10,1 s (hình E8 nằm cả cuối `s2`) | "HỏiCon hỏi một câu thật ngắn: người gọi có bảo bác chuyển tiền không? Bác trả lời bằng một cú chạm." |
| 4 | 1:10–1:30 | Bác bấm **"Hỏi con"** → mở bàn phím gọi trống (không tự gọi) | `s4_hoi_con.mp4`, `s5_ban_phim_goi.mp4` | 11,4 s + 8 s | "Bác bấm Hỏi con. HỏiCon chỉ mở sẵn bàn phím, bác tự gọi cho con. HỏiCon không bao giờ tự bấm hay chặn thay bác." |
| 5 | 1:30–1:55 | Tin Zalo tới người giám hộ (**MÔ PHỎNG**) | `s6_zalo_mo_phong.webm` + `.png` | ~17 s | "Cùng lúc đó, người con nhận một tin Zalo. Đây là trợ lý AI HỏiCon, kèm mức nguy cơ và cách trả lời 1, 2 hoặc 3." |
| 6 | 1:55–2:30 | Trang `/a/[token]`: nội dung cảnh báo, "Gọi điện cho Bố/Mẹ", xác nhận "Đã gọi được, Bố/Mẹ an toàn" | `s7_trang_hanh_dong.webm`, `s7_*-1/2/xacnhan.png` | ~25 s | "Con mở trang cảnh báo, gọi cho bác, rồi xác nhận bác an toàn. HỏiCon ghi nhận và đóng cảnh báo." |
| 7 | 2:30–2:50 | Thẻ chữ: số đo có nguồn (mục 4), ghi "đo trên máy ảo" | đồ họa | — | "Màn dừng an toàn không dùng mạng hay AI trên máy chủ. Trên máy ảo, nó hiện ra sau khoảng 0,9 giây (trung vị) và 1,4 giây (p95) trong 10 lần thử." |
| 8 | 2:50–3:00 | Logo + câu kêu gọi | đồ họa | — | "HỏiCon — hỏi con trước khi chuyển tiền." |

Tổng lời thoại ≈ 270 từ (còn dư thời gian cho nhạc và khoảng lặng; giữ ≤ 360 từ).

## 3. Cách đã quay (tái lập được)

| Cảnh | Lệnh / công cụ |
|---|---|
| s1–s5 (máy ảo hc-api36, 1080×2400, chữ 100%) | `python3 scripts/emu-demo-record.py` (dùng `adb shell screenrecord`; một cú quay liền, mỗi cảnh một tệp) |
| s6 Zalo mô phỏng | `docs/demo/zalo-mo-phong.html` (khung mô phỏng, mã một lần thay bằng `<mã-một-lần>`) — bản quay dùng đúng chữ tin thật từ nhật ký bộ Zalo giả; Playwright (390×844, ×2) |
| s7 trang người giám hộ | web dev (`HOICON_API_URL=http://127.0.0.1:18001 pnpm --dir apps/web dev --port 3100`), liên kết `/a/<mã một lần>` sinh bởi chính đường gửi tin Zalo; Playwright quay video + ảnh |
| Điều kiện | backend dev cổng 18001, DB riêng `hoicon_android` (đã migrate), Zalo MOCK (`HOICON_ZALO_MODE=mock`), `HOICON_WEB_BASE_URL=http://localhost:3100`; gia đình thử `w2-gia-dinh-*` (hư cấu) |

**Giới hạn cần biết trước khi dựng:**
- **Không có tiếng.** Máy ảo chạy `-no-window -no-audio`, nên giọng đọc tiếng Việt của HỏiCon (TTS) **không nằm trong video**. Cần quay trên máy thật có âm thanh hoặc thu riêng
  (nội dung đọc: mảng `pause_speech` trong `res/values/strings.xml`). Bản đo "câu nói đầu" (mốc `first_speech`) có trong báo cáo `emu-scenario` nhưng chỉ chứng minh app gọi TTS, không chứng minh nghe được.
- Trong `s2` màn dừng an toàn hiện ở giây 2–3, rồi câu hỏi E8 (`s3`) tự kéo từ máy chủ sau vài giây và nằm trên màn dừng; sau khi trả lời, màn dừng hiện lại (`s4`).
  Nếu muốn giữ màn dừng suốt, quay lại và bấm "Hỏi con" trong khoảng 4 giây đầu (E8 chưa tới).
- Cảnh `s6`/`s7` quay sau cảnh điện thoại (cùng sự cố, mã một lần chỉ dùng được 1 lần và hết hạn sau ít phút); `s7` có "Quay lại"/"Đúng, gửi xác nhận" là bước **xác nhận 2 lần** của trang.
- Web chạy chế độ dev (đã ẩn biểu tượng Next.js trong bản quay); bản cuối nên quay từ bản build.
- Trang người giám hộ hiện "sdk_gphone64_x[MÃ]" là tên máy ảo (dữ liệu thử); khi dựng phim che hoặc quay với máy ảo đặt tên khác.
- Thời gian trên trang (`09:3x`) là giờ máy ảo; trên video điện thoại cũng là giờ đó, nhưng các cảnh `s6`/`s7` là hai lần quay riêng nên mốc giờ không liền nhau — đừng hiện đồng hồ khi ghép.

## 4. Bảng số liệu và nguồn (chỉ nói những số này)

| Số liệu | Giá trị | Nguồn / cách đo | Ghi chú |
|---|---|---|---|
| Dừng an toàn hiện sau khi mở app ngân hàng, hc-api36 | **trung vị 875 ms, p95 1440 ms, 10/10 lần hiện** (ngưỡng ≤ 3000 ms) | `python3 scripts/emu-scenario.py --scenario fake_police --runs 10 --avd hc-api36`, 21/10/2026 (lần chạy thứ hai; lần đầu có 1 lần cây UI không thấy màn E7 nên script báo TRƯỢT dù 10/10 có mốc hiện) | số **máy ảo**, mỗi bản ghi từ mốc `risk_detected` → khung hình đầu |
| Dừng an toàn, hc-api34 | **trung vị 670 ms, p95 1957 ms, 10/10 lần hiện** (ngưỡng ≤ 3000 ms) | cùng lệnh, `--avd hc-api34`, 21/10/2026, sau khởi động nguội (bản trước khi đổi thứ tự phần đầu E7 ở chữ lớn; bản cuối chưa đo được vì máy ảo, xem `specs/010-design-system/evidence.md`) | số **máy ảo**; p95 dao động giữa các lượt |
| Đường dừng không dùng mạng hay LLM | thiết kế | CLAUDE.md luật 4; `docs/ARCHITECTURE.md` | **không** có số đo "ngoại tuyến" riêng cho video; không nói "đã đo ngoại tuyến" |
| App chỉ để ý 10 phút sau cuộc gọi số lạ | 10 phút | văn bản đồng ý `docs/legal/consent/core_protection.vi.md` (bản nháp chờ Minh duyệt) | |
| App không nghe/ghi âm cuộc gọi, không đọc tin nhắn, danh bạ | — | luật CLAUDE.md số 3; manifest đã có cổng `scripts/release-gate.sh` | |
| Tin tới người giám hộ có "Đây là trợ lý AI HỏiCon" | có | tin thật ở cảnh `s6` (test công khai AI ở backend) | |
| Số điện thoại chỉ hiện 3 số cuối | có | tin `s6` ("đuôi 002"); `docs/PRIVACY-DPIA.md` | |
| **Không dùng** | "100% WCAG AAA", "0 số điện thoại thô", mọi số thống kê vụ lừa đảo | chưa đo / chưa có nguồn đã kiểm | thêm khi có nguồn |

## 5. Tệp tư liệu (ngoài repo): `~/hoicon-evidence/video/`

`s1_cuoc_goi_la.mp4` · `s2_mo_ung_dung_ngan_hang.mp4` · `s3_cau_hoi_cua_hoicon.mp4` · `s4_hoi_con.mp4` · `s5_ban_phim_goi.mp4` (1080×2400, h264, 100% chữ) ·
`s6_zalo_mo_phong.webm` (+ `-1.png`, `-2.png`) · `s7_trang_hanh_dong.webm` (+ `-1.png`, `-2.png`, `-xacnhan.png`).
Ảnh chụp nhật ký/dump giao diện **không** được lưu (chứa số gọi đến). Việc còn lại: giọng đọc, nhạc, dựng, phụ đề, quay mở đầu, quay lại trên máy thật.
