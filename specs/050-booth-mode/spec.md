# Spec 050: Chế độ gian trưng bày (`/booth`, `/join/[code]`, `/demo/console`, phát lại khi mất mạng, reset < 1 phút)

> **BẢN NHÁP — Opus /speckit-analyze lại khi có quota.** Soạn 23/10/2026 bởi làn B (Sonnet) khi Opus nghỉ: đã chạy
> specify → clarify → plan → tasks → analyze (0 CRITICAL, 2 HIGH đã xử lý bằng cách tách giai đoạn, xem `plan.md` mục 5).
> **Chưa có hợp đồng mới** (Opus viết `docs/schemas` ở giai đoạn 0): phần cần hợp đồng nằm trong nhóm BLOCKED.

**Mã ROADMAP**: `P4-02` · **Làn**: A+B (`[B-web]` = `apps/web/**`; `[B-api]` = `backend/**`; `[A]` = `apps/android/**`)
· **Cột mốc**: chung kết 27/02/2027, xong trước 07/02/2027; **Gate G4 (26/02)**: chạy gian 3 lần liên tiếp thành công, cảnh báo < 5 s,
phát lại khi mất mạng hoạt động, có video dự phòng, reset demo < 1 phút · **Phụ thuộc**: 033 (`/v1/sim/*`, `/sim`, `/trace`, cổng
`HOICON_SIM_ENABLED`), 027 (phiên `hc_guardian`), 012 (hồ sơ `demo`, khởi động nguội), 036 (cassette tất định) · **US**: US-10
· **ADR**: ADR-002, ADR-009 (không đổi).

> **Chỉ nói phần chênh lệch.** 033 đã có điện thoại mô phỏng `/sim` cho một người dùng tương tác. Gian trưng bày khác ở chỗ:
> (1) **tự chạy** không cần người thao tác, trên màn hình lớn, chữ to; (2) **nhiều khách** cùng xem trên điện thoại riêng;
> (3) người điều khiển có **bảng điều khiển**; (4) **mất mạng vẫn trình diễn được**; (5) **dọn sạch trong một phút** giữa hai lượt khách.

---

## 1. Bối cảnh

Chung kết là gian trưng bày với Wi-Fi hội trường không đáng tin và khách đi qua trong vài chục giây. Cần: màn hình tự kể câu chuyện
"cuộc gọi lạ → bác được nhắc dừng → con nhận tin → hồ sơ", đo được thời gian cảnh báo (< 5 s), không phụ thuộc mạng, không làm lộ
dữ liệu thật, và đặt lại nhanh cho khách sau.

| Trang | Ai dùng | Dữ liệu | Mức |
|---|---|---|---|
| `/booth` | khách đứng trước màn hình lớn | gia đình **demo** (`is_demo`), kịch bản hư cấu, đồ thị thật qua `/v1/sim/*` (cờ `sim`) | P1 |
| `/demo/console` | người điều khiển gian (đội) | như trên + chỉ số lần chạy | P1 |
| `/join/[code]` | khách quét QR bằng điện thoại | vai người giám hộ của gia đình demo, chỉ xem + quyết định | P2 |

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-50.1 | **P1** | Là khách đi qua gian, tôi thấy màn hình tự chạy một kịch bản lừa đảo từ đầu tới cuối trong dưới 90 giây, chữ đủ to để đọc từ xa, và hiểu HỏiCon làm gì mà không cần ai giải thích |
| US-50.2 | **P1** | Là người điều khiển, tôi bấm một nút để chạy kịch bản, chuyển chế độ, đặt lại, và thấy thời gian từ "bắt đầu" tới "tin cho con xuất hiện" của mỗi lượt |
| US-50.3 | **P1** | Là người điều khiển khi Wi-Fi sập, màn hình tự chuyển sang phát lại bản ghi đã lưu, **ghi rõ đó là bản ghi**, và quay lại chạy trực tiếp khi có mạng |
| US-50.4 | **P1** | Là người điều khiển giữa hai khách, tôi đặt lại gian trong dưới 1 phút (xóa lượt mô phỏng, dừng vòng lặp, đóng liên kết tham gia) |
| US-50.5 | **P2** | Là khách có điện thoại, tôi quét QR và vào `/join/<mã>` để xem cùng câu chuyện dưới vai con của bác, bấm "Tôi đã gọi cho bác, an toàn" |

## 3. Yêu cầu chức năng

- **(FR-001)** *[Opus, giai đoạn 0]* Hợp đồng cho phần cần máy chủ mới: `docs/schemas/sim_reset.v1.json` (kết quả đặt lại: số lượt đã xóa, thời gian)
  và `booth_join.v1.json` (đổi mã tham gia lấy phiên người giám hộ demo) + fixture valid/invalid. Chưa có ⇒ FR-005 phần máy chủ và FR-007 **BLOCKED**; mọi phần còn lại dùng hợp đồng `sim_*` có sẵn.
- **(FR-002)** *[B-web]* `/booth`: trang toàn màn hình, tự chạy **danh sách phát** (mặc định 3 kịch bản: giả danh công an, thẻ ngân hàng bị khóa, và một cuộc gọi
  hợp lệ để thấy HỏiCon không báo nhầm) qua `/v1/sim/*` (`llm: "replay"`); trả lời của bác và quyết định của con do kịch bản tự thực hiện, mỗi bước có nhịp
  dừng đủ đọc. Bố cục 3 cột (điện thoại của bác · trợ lý AI · Zalo của con) trên màn hình ≥ 1280 px, một cột trên điện thoại. Chữ ≥ 28 px ở khối nội dung chính, tương phản ≥ 7:1,
  mọi trạng thái có biểu tượng + chữ (luật 15). Nhãn "MÔ PHỎNG — dữ liệu hư cấu" luôn hiện.
- **(FR-003)** *[B-web]* Đo cảnh báo: mỗi lượt đo `t_alert_ms` = từ lúc bấm bắt đầu tới lúc tin `fast_alert` của con có trong `GET /v1/sim/runs/{id}` (đo bằng đồng hồ trình duyệt,
  ghi rõ "đo ở trình duyệt, gồm độ trễ mạng nội bộ"). Hiển thị ở console; lượt đạt khi `t_alert_ms < 5000`.
- **(FR-004)** *[B-web]* `/demo/console`: danh sách kịch bản + nút Bắt đầu, chọn chế độ (Trực tiếp · Bản ghi), nút Đặt lại, trạng thái kết nối (API, luồng), bảng các lượt gần đây
  (kịch bản, `t_alert_ms`, đạt/không, chế độ) và **bộ đếm "đạt liên tiếp"** cho Gate G4 (3 lượt liên tiếp đạt). Cần phiên `hc_guardian` của gia đình demo (như `/sim`).
- **(FR-005)** *Đặt lại < 1 phút.* (a) *[B-web]* phía màn hình: dừng danh sách phát, xóa trạng thái lượt, đóng luồng — tức thì. (b) *[B-api]* phía dữ liệu:
  `python -m hoicon.ops.booth reset` xóa lượt mô phỏng của gia đình demo (sự cố + `agent_runs` + job + checkpoint + token tham gia), in thời gian; **mục tiêu < 30 giây ở máy dev**
  (đo, ghi nguồn). (c) *[B-api, BLOCKED bởi FR-001]* `POST /v1/sim/reset` cho nút Đặt lại của console.
- **(FR-006)** *[B-web]* Phát lại khi mất mạng: gói **bản ghi** (khung `sim_run` đã ghi, có thời điểm tương đối) nằm trong bản dựng web (`public/booth/replay/*.json`), kiểm theo
  `sim_run.v1`; trang chuyển sang phát lại khi (i) `navigator.onLine === false`, (ii) 2 lần liên tiếp gọi API hỏng/quá 3 giây, hoặc (iii) người điều khiển chọn "Bản ghi".
  Trong phát lại: băng rôn **cố định** "ĐANG PHÁT LẠI BẢN GHI — không phải trực tiếp" (không giấu), không gọi API, vẫn đo nhịp. Có mạng trở lại ⇒ thông báo và chuyển về trực tiếp ở lượt kế.
- **(FR-007)** *[B-api + B-web, BLOCKED bởi FR-001]* `/join/[code]`: mã tham gia ngắn hạn (≤ 10 phút, dùng nhiều lần trong hạn, tối đa 50 khách/mã) do console tạo; đổi mã lấy phiên
  `hc_guardian` của gia đình demo với quyền như `/sim` (xem + quyết định, không đặt lịch, không đổi cấu hình); hết hạn/đặt lại ⇒ mã vô hiệu. Trang chào bằng chữ lớn: "Bạn đang xem bản trình diễn — mọi dữ liệu là hư cấu".
- **(FR-008)** *[Ràng buộc chung]* Mọi dữ liệu gian mang `is_demo`; mọi sự cố mang cờ `sim` (không Zalo thật, kể cả `HOICON_ZALO_MODE=live`); không có số điện thoại/tên/tài khoản thật
  (kịch bản và bản ghi chỉ dùng số hư cấu đã đăng ký); các trang trả "Trang này chưa mở" khi `HOICON_SIM_ENABLED=false` (404 từ API); `compose.prod.yml` không bật cổng.
- **(FR-009)** *[A]* Ứng dụng Ngân hàng Mẫu (`:demobank`) và kịch bản máy ảo để diễn cảnh "mở app ngân hàng" tại gian: tài liệu bấm máy và một lệnh `emu-scenario` gọi tên danh sách phát. **Làn A**, không làm ở đây.
- **(FR-010)** *[B-web]* Kiểm chứng: Playwright cho `/booth`, `/demo/console` (ảnh 390/768/1440 px, axe 0 lỗi), kịch bản **mất mạng** (chặn mạng giữa chừng ⇒ băng rôn + tiếp tục), và 3 lượt liên tiếp có `t_alert_ms` ghi lại.

## 4. Tiêu chí thành công

- **(SC-001)** Một lượt `/booth` (kịch bản giả danh công an) chạy từ đầu tới hết trong ≤ 90 giây ở chế độ trực tiếp-replay. Đo: Playwright ghi thời gian.
- **(SC-002)** `t_alert_ms` < 5000 ở 3 lượt liên tiếp (Gate G4) trên máy dev với API + web chạy cục bộ. Đo: bảng 3 lượt trong `evidence.md`, ghi rõ nguồn ("máy dev, replay, mạng cục bộ"; **không** phải số ở hội trường).
- **(SC-003)** Mất mạng giữa lượt ⇒ trong ≤ 6 giây băng rôn "BẢN GHI" hiện và lượt kết thúc đủ 3 cột; có mạng ⇒ lượt kế chạy trực tiếp. Đo: Playwright chặn mạng.
- **(SC-004)** Đặt lại: `ops.booth reset` ≤ 30 giây và sau đó 0 lượt mô phỏng còn lại của gia đình demo; tổng thao tác người điều khiển (dừng phát + reset + bắt đầu lại) ≤ 60 giây. Đo: thời gian lệnh + đếm DB.
- **(SC-005)** 0 chữ nào từ bản ghi/kịch bản chứa số điện thoại thô hoặc tên thật; mọi khung bản ghi hợp lệ `sim_run.v1`. Đo: quét `gitleaks`/mẫu số điện thoại + kiểm lược đồ trong test.
- **(SC-006)** axe 0 lỗi và chữ chính ≥ 28 px ở `/booth` 1440 px; một cột đọc được ở 390 px. Đo: Playwright (`getComputedStyle`).

## 5. Ngoài phạm vi

Gian vật lý (bàn, poster, QR in), mạng 4G dự phòng, cấp phát tài khoản Zalo thật cho khách, đăng nhập khách bằng danh tính thật, ghi hình khách, thu thập số liệu khách (không có phân tích/cookie theo dõi).
