# Ma trận thiết bị — kết quả đo chuỗi cảm biến

> Mỗi dòng ghi rõ **máy ảo** hay **máy thật** (model + Android). Không suy kết quả máy ảo cho máy thật. Chi tiết và
> điều kiện đo: `docs/spikes/P1-S1-cam-bien.md`. Ngưỡng: bắt 10/10 cuộc gọi lạ; `app_foreground → pause_shown` p95 ≤ 3 s.

| Ngày | Thiết bị | Loại | Kịch bản | n | Bắt được | p50 (ms) | p95 (ms) | Đạt ≤ 3 s? | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|
| 08/10/2026 | AVD hc-api36 (Android 16) | máy ảo | ấm, 2 lô | 20 | 20/20 | 1 462 / 1 378 | 7 380 / 7 110 | ✗ (18/20 ≤ 3 s) | máy chủ 0,6–1,8 GB RAM trống |
| 08/10/2026 | AVD hc-api36 | máy ảo | nguội, Compose | 10 | 10/10 | 4 187 | 6 375 | ✗ | đối chứng: mở app tầm thường 4–6 s |
| 08/10/2026 | AVD hc-api36 | máy ảo | nguội, tắt mạng | 10 | 10/10 | 4 043 | 5 288 | ✗ | đường găng offline đúng |
| 08/10/2026 | AVD hc-api36 | máy ảo | Doze ép, ấm | 3 | 3/3 | 1 035 | 1 637 | ✓ | đã miễn tối ưu pin |
| 08/10/2026 | AVD hc-api34 (Android 14) | máy ảo | nguội, View | 23 | 23/23 | 2 620 | 5 926 | ✗ (15/23) | loại 7 lần lỗi modem giả lập |
| 08/10/2026 | AVD hc-api34 | máy ảo | ấm, View | 10 | 10/10 | 1 135 | 9 768 | ✗ (8/10) | lần đầu lô 9,8 s |
| 08/10/2026 | AVD hc-api29 (Android 10) | máy ảo | nguội, View | 5 | 5/5 | 1 665 | 2 132 | ✓ | |
| 08/10/2026 | AVD hc-api29 | máy ảo | ấm, View | 5 | 5/5 | 2 177 | 3 486 | ✗ (4/5) | |
| 15/10/2026 | AVD hc-api36 (Android 16) | máy ảo | `:latency`, E7 View, nguội | 10 | 10/10 | 1 244 | 1 487 | ✓ | Linux headless, `compile=speed`, bản debug; RAM máy dev chưa đo lại nên không so được với lô 08/10 |
| 15/10/2026 | AVD hc-api36 | máy ảo | `:latency`, E7 View, ấm | 10 | 10/10 | 1 215 | 1 370 | ✓ | như trên |
| 15/10/2026 | AVD hc-api36 | máy ảo | `:latency`, E7 Compose, nguội | 10 | 10/10 | 1 408 | 1 601 | ✓ | như trên |
| 15/10/2026 | AVD hc-api36 | máy ảo | `:latency`, E7 Compose, ấm | 10 | 10/10 | 1 271 | 1 404 | ✓ | như trên |
| 15/10/2026 | AVD hc-api34 (Android 14) | máy ảo | `:latency`, E7 View, nguội | 10 | 10/10 | 1 577 | 1 755 | ✓ | khởi động `--cold` (tránh lỗi modem giả lập) |
| 15/10/2026 | AVD hc-api34 | máy ảo | `:latency`, E7 View, ấm | 10 | 10/10 | 1 468 | 1 688 | ✓ | như trên |
| 15/10/2026 | AVD hc-api34 | máy ảo | `:latency`, E7 Compose, nguội | 10 | 10/10 | 1 592 | 1 758 | ✓ | như trên |
| 15/10/2026 | AVD hc-api34 | máy ảo | `:latency`, E7 Compose, ấm | 10 | 10/10 | 1 525 | 1 790 | ✓ | như trên |
| 15/10/2026 | AVD hc-api36 | máy ảo | `emu-scenario.py fake_police` (ấm, `--prep none`) | 10 | 10/10 | 537 | 1 387 | ✓ | cây UI thiếu chữ "gọi cho con" 1/10 ⇒ script báo TRƯỢT; mốc `pause_shown` có đủ 10/10 |
| 15/10/2026 | AVD hc-api34 | máy ảo | `emu-scenario.py fake_police` (ấm) | 10 | 10/10 | 670 | 1 800 | ✓ | lô đầu 0/10: script chẩn đoán "Telecom không thấy cuộc gọi đến (lỗi modem giả lập)" ⇒ boot `--cold` rồi chạy lại (lô báo ở dòng này) |
| _BLOCKED 15/10/2026_ | Firebase Test Lab / máy mượn | **máy thật** | nguội + ấm | ≥ 10 | | | | | **BLOCKED: chưa có tài khoản Firebase (P0-08), `gcloud` chưa cài** — cần trước G1 (08/11) — `bash scripts/ftl-latency.sh --variant view|compose model=…,version=…` (bộ đo `:latency`, cuộc gọi mô phỏng, ADR-008) |

## Giọng nói tiếng Việt (spec 004, spike P1-S5) — 15/10/2026

> Máy ảo `-no-audio`, mạng tắt trừ khi ghi khác. Chi tiết, giới hạn và quyết định: `docs/spikes/P1-S5-giong-noi.md`.

| Thiết bị | Loại | Phép đo | n | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| AVD hc-api36 (Android 16) | máy ảo | TTS vi-VN offline: giọng / `speak→onStart` nguội · ấm p95 | 20 + 20 | 6 giọng offline · 64 ms · 3 ms | nguội + `onInit` p95 370 ms (lượt sớm: 65 / 6 / 345 ms) |
| AVD hc-api34 (Android 14) | máy ảo | như trên | 20 + 20 | 6 giọng offline · 404 ms · 1 ms | nguội + `onInit` p95 411 ms |
| AVD hc-api36 / hc-api34 | máy ảo | phát clip thu sẵn (`MediaPlayer`) nguội · ấm p95 | 20 + 20 mỗi máy | 42 · 35 ms / 50 · 36 ms | clip tổng hợp, không phải giọng người |
| AVD hc-api36 | máy ảo | nhận dạng vi-VN **trên máy**, 20 câu tổng hợp | 20 | WER 7,2 % · ý định 12/12 | cận trên lạc quan |
| AVD hc-api34 | máy ảo | vi-VN trên máy | — | **không có** (không cài được) | bộ mặc định dùng mạng: WER 8,6 % · ý định 11/12 |
| _BLOCKED 15/10/2026_ | Firebase Test Lab / máy mượn | **máy thật**: TTS + STT | — | | **BLOCKED: chờ Firebase/máy thật (W0-3)** |
| _BLOCKED 15/10/2026_ | bản thu giọng của đội | bộ `team`, 20 câu | — | | **BLOCKED: chờ Tiến thu âm** |
