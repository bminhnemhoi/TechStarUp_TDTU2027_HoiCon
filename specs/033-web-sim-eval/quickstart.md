# Quickstart 033 — quay một lượt `/sim` (video, 1280×720)

Dùng cho 033 T020 và video Vòng 2 (P2-21, skill `demo-video-director`). Mọi dữ liệu hư cấu (gia đình `is_demo`), chế độ `replay`.

## Chuẩn bị (một lần)
1. Dựng theo `docs/setup/SIM.md` mục "Từ DB trống tới `/sim`" (API 18000, web 3100, `HOICON_SIM_ENABLED=true`).
2. `uv run --directory backend python -m hoicon.ops.guardian_link --seed` ⇒ mở `login_url` trong cửa sổ trình duyệt **1280×720**,
   thu phóng 100%, tắt thanh dấu trang. Vào `/sim`.
3. Kiểm: băng "MÔ PHỎNG — dữ liệu hư cấu, không có cuộc gọi hay tin Zalo thật" ở đầu trang; ô chọn kịch bản hiện tên tiếng Việt.

## Kịch bản quay (≈ 60 giây)
| Giây | Thao tác | Trên màn hình |
|---|---|---|
| 0–5 | Chọn "Giả danh công an · ca 2" (`fake_police_safe_account_002`), chế độ "Bản ghi", bấm Bắt đầu | Ba cột: điện thoại của bác · trợ lý AI · Zalo của con |
| 5–20 | Chờ | Cột giữa: các bước sáng dần; cột phải: tin đầu mở bằng "Đây là trợ lý AI HỏiCon" |
| 20–35 | Cột trái: bấm câu trả lời của bác cho câu hỏi E8 | Mức rủi ro đổi, có biểu tượng + chữ |
| 35–50 | Cột phải: "Nghi lừa đảo" → "Đúng, gửi xác nhận" | Sự cố đóng |
| 50–60 | Bấm "Xem trợ lý AI đã làm gì" ⇒ `/trace/<runId>` | Sơ đồ tô nút đã chạy, bản chữ bên dưới |

Lặp lại với một ca hợp lệ (ví dụ `benign_bank_card_delivery_001`) để thấy HỏiCon **không** báo con.

## Sau khi quay
- Không quay thanh địa chỉ có token (`/login/<token>` đã tự bỏ token khỏi URL; vẫn kiểm lại khung đầu).
- Ghi nguồn số trên video: "máy dev, chế độ phát lại, không phải máy thật" (CLAUDE.md: không tuyên bố số chưa đo).
