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
| _chờ_ | Firebase Test Lab / máy mượn | **máy thật** | nguội + ấm | ≥ 10 | | | | | cần trước G1 (08/11) |
