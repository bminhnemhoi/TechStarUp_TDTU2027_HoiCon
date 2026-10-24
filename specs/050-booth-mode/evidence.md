# Evidence Spec 050: Chế độ gian trưng bày (giai đoạn 1, làn B, 23/10/2026)

> Đã đối soát 24/10/2026 (kiến trúc sư). Mọi số dưới đây đo ở **máy dev**, API + web cục bộ, `llm: "replay"`
> (cassette `synthetic`), mạng cục bộ. **Không phải** số ở hội trường, không phải số model thật.

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 một lượt ≤ 90 giây | ≤ 90 s | `booth-live.spec.ts` (HOICON_E2E_LIVE=1, nhịp thật) | 3 lượt + 2 khoảng nghỉ 6 s trong 47 s ⇒ mỗi lượt ≈ 12 s | ĐẠT (máy dev) |
| SC-002 cảnh báo < 5 giây × 3 lượt liên tiếp | 3/3 lượt < 5000 ms | cùng spec; bảng ở console | 116 / 116 / 132 ms, "Đạt liên tiếp: 3/3" (đo ở trình duyệt, gồm POST `/v1/sim/runs` trả tin `fast_alert`) | ĐẠT (máy dev; chưa đo ở hội trường) |
| SC-003 mất mạng ⇒ bản ghi ≤ 6 s | băng rôn ≤ 6 s, đủ 3 cột, có mạng ⇒ lượt kế trực tiếp | `booth.spec.ts` (Playwright `setOffline`, fixture hợp đồng, `?fast=1`) | băng rôn hiện trong giới hạn, 3 cột + 2 tin, băng rôn biến mất ở lượt kế khi có mạng | ĐẠT (kịch bản chặn mạng; chưa thử Wi-Fi thật) |
| SC-004 đặt lại ≤ 30 s / tổng thao tác ≤ 60 s | ≤ 30 s lệnh, 0 lượt sim còn lại | `test_ops_booth.py` (20 lượt) + chạy lệnh thật | 20 lượt xóa trong 0,03 s; lệnh thật 2,5 s (gồm khởi động `uv`); 5 test: không đụng gia đình thật, sự cố demo thường, sự cố không phải mô phỏng trên thiết bị nhãn `sim:`, lũy đẳng | ĐẠT (máy dev) |
| SC-005 không PII | 0 số thô; mọi khung hợp `sim_run.v1` | `test_booth_recordings.py` (10) + `booth-record.spec.ts` (3) | 3 bản ghi hợp lệ; 0 chuỗi giống số điện thoại thô trong tin/câu hỏi/ghi chú/bước; mọi tin mở đầu bằng câu công khai AI | ĐẠT |
| SC-006 tiếp cận và chữ | axe 0 lỗi, chữ chính ≥ 28 px, không cuộn ngang | `booth.spec.ts` (390/768/1440 px + console) | axe 0 lỗi ở cả 4 ca; `question` ≥ 28 px (36 px sau khi sửa theo UX); không cuộn ngang | ĐẠT |

## Việc đã làm

- **T002–T006 ĐẠT:** `lib/booth.ts`, `lib/use-booth-runner.ts`, `components/booth-columns.tsx`, `/booth`, `/demo/console`; không lưu gì ở trình duyệt; điều khiển qua `BroadcastChannel` (cùng nguồn), `mode`/bản ghi nhận từ kênh được kiểm.
- **T003 ĐẠT:** 3 bản ghi (`fake_police_safe_account_002`, `fake_bank_card_locked_002`, `benign_family_son_rent_002`) ghi từ đồ thị thật qua `/v1/sim/*` bằng `BOOTH_RECORD=1 e2e booth-record` (≈ 12 s mỗi bản, 3 khung, 7 bước).
- **T007 ĐẠT:** `booth.spec.ts` 9 test (mock hợp đồng) + `booth-live.spec.ts` (API thật) + `booth-record.spec.ts`. Ảnh: `~/hoicon-evidence/050-booth-mode/{booth-390,booth-768,booth-1440,console-768}.png`.
- **T009, T010 ĐẠT:** `ops/booth.py reset --confirm-demo`; `test_deploy_vps` 31 OK (`compose.prod.yml` không bật cổng).
- **Lỗi thật tìm thấy khi ghi bản ghi:** trạng thái sự cố vẫn là `detected` trong lúc chờ con quyết định (không phải `awaiting_guardian`) ⇒ bộ chạy chờ vô hạn tới trần 90 s; đã sửa điều kiện quyết định thành "tin `detail` đã tới con và không còn câu hỏi".
- **`ux-elder-reviewer`** (ảnh + mã): 1 Chặn, 5 Cao, 6 Trung bình — ĐÃ SỬA: console khóa nút Chạy khi chưa có màn hình gian kèm hướng dẫn (Chặn); nút Dừng đỏ ở đầu; "Đặt lại cho khách mới" không xóa bảng G4 (xóa riêng, có xác nhận); dải trạng thái; nút chế độ ≥ 64 px; băng rôn MÔ PHỎNG/BẢN GHI dùng màu diễn tập riêng, đặt "KHÔNG PHẢI TRỰC TIẾP" lên đầu; cột đánh số 1-2-3; câu hiện tại 36 px; mức nguy cơ có nền màu + hành động; câu quyết định mềm hơn, không "giữ bác"; ca hợp lệ không nhắc "tạm dừng"; lệnh kỹ thuật thu vào mục gập; lỗi trên màn gian nói thật, không chữ kỹ thuật. **Chưa sửa:** xưng hô "Mẹ" trong tin Zalo của kịch bản vs "bác" ở cột 1 (chữ nằm trong mẫu tin 024, cần Opus); thu mỗi cột chỉ còn một câu ở 48 px (đổi thiết kế, để Tiến xem ảnh thật tại gian).
- **`security-privacy-reviewer`:** 0 Critical, 1 High, 4 Medium, 3 Low — ĐÃ SỬA: #1 High (xóa theo nhãn tự do `sim:`: nay chỉ sự cố `is_demo`, chỉ xóa thiết bị khi không còn sự cố gắn; `pairing.py` biến nhãn `sim:` của client thành `sim-`; +1 test) · #2/#3 (chọn+xóa cùng giao dịch có khóa dòng; checkpoint xóa sau) · #4 (từ chối ngoài dev/`HOICON_SIM_ENABLED`) · #5/#8 (kiểm `mode` và bản ghi nhận từ kênh) · quét cả `steps[].output`. **Không sửa (ghi nhận):** #6/#7 (trang gian và console không cần phiên; chỉ dữ liệu hư cấu, UUID DB demo trong bản ghi).

## Chưa làm / BLOCKED

- **T001 [Opus]**, **T011–T013**: chờ hợp đồng `sim_reset.v1` + `booth_join.v1` (FR-001, FR-005c, FR-007); **T014 [A]**: làn A.
- **SC ngoài phạm vi máy dev:** số ở hội trường (Wi-Fi thật), tổng duyệt 3 lần liên tiếp (Gate G4) cần người điều khiển chạy ở gian.
- `?fast=1` rút nhịp ở mọi môi trường (không riêng test): chấp nhận (không lộ dữ liệu), ghi để Opus cân nhắc.

## Bẫy khi chạy kiểm (ghi cho người sau)

- **Đừng chạy API dev (cổng 18010) trong lúc chạy `pytest` toàn bộ:** worker của API nhặt job `notify_guardian`/`graph_resume` của test trên DB dùng chung ⇒ 3 test đỏ (`test_guardian_reply` ×2, `test_incident_graph::test_guardian_silence…`); tắt API thì xanh (2763 passed). Đã gặp và xác nhận ngày 23/10.
- **Test e2e từng chập chờn ~1/6** (khung 390/768/1440 px): nguyên nhân gốc là câu hỏi của bác bị gỡ khỏi màn ngay khi bác trả lời, test đo cỡ chữ đúng lúc phần tử biến mất (`NaN`). Đã sửa ở mã (câu hỏi giữ trên màn cùng đáp án), không nới test; sau đó toàn bộ e2e web 107 passed × 6 lần liên tiếp (3 test live bị bỏ qua có chủ đích).
