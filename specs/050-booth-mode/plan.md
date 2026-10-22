# Plan: 050 — Chế độ gian trưng bày

## 0. Kiểm theo hiến chương
| Nguyên tắc | Cách giữ |
|---|---|
| I. Dừng an toàn | Máy `demo` dùng nguyên đường E7 offline; gian không đổi `:rules` |
| II. Riêng tư | Khách không đăng nhập/không số điện thoại; `booth_event` đã che PII |
| IV. Công khai AI | Mọi tin khách thấy mở đầu câu công khai (dùng lại `texts._message`) |
| V. Hợp đồng trước | T001 hai lược đồ trước mã |
| VIII. Ít code | Dựng trên `/v1/sim/runs` + `/trace` của 033; SSE dùng lại hạ tầng 025 |

## 1. Quyết định
| # | Quyết định | Lý do |
|---|---|---|
| D1 | Lượt gian = lượt sim của 033 + mã tham gia | Tái dùng cô lập, cờ `sim`, thiết bị riêng mỗi lượt (033 D9) |
| D2 | SSE cho khách phát từ bộ đệm sự kiện của lượt (fan-out trong tiến trình) | ADR-002 một tiến trình; ≤ 200 khách đủ |
| D3 | Phát lại cục bộ = tệp JSON tĩnh trong `public/` | Không phụ thuộc API/mạng; sinh từ lượt replay thật nên không bịa |
| D4 | Mã 6 ký tự bảng chữ không nhầm (bỏ 0/O/1/I/L), hạn 15 phút | Đọc to được, đoán ngẫu nhiên khó trong hạn |

## 2. Tệp
B: `api/routers/booth.py`, `services/booth_service.py`, migration `booth_sessions`, `tests/**`. Web: `apps/web/src/app/{booth,join/[code],demo/console}`,
`public/booth/replay/`. A: chế độ gian cho bản `demo` (chỉ nếu FR-005), `scripts/booth-record.py`. Chung: `docs/schemas/booth_*.v1.json`.

## 3. Rủi ro
| Rủi ro | Mức | Giảm |
|---|---|---|
| Mạng gian kém | Cao | FR-007 + video dự phòng (G4) |
| Máy Android thật chưa có (W0-3) | Cao | Cắt FR-005, chạy mô phỏng; SC-003 BLOCKED |
| Lộ dữ liệu thật qua gian | TB | Cổng + chỉ gia đình demo + test 404 như 033 |
