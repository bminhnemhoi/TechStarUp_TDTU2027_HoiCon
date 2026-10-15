# Design system HỏiCon

> Trạng thái: **khung** (P0-05) — hoàn thiện ở P1-05 bằng `ui-ux-pro-max --design-system --persist -p "HoiCon"`
> (truy vấn "elderly-friendly fintech safety family protection"), kết quả ở `design-system/hoicon/`.
> **File này thắng mọi gợi ý của plugin thiết kế.**

## Màu thương hiệu (đã chốt)
| Token | Giá trị | Dùng |
|---|---|---|
| `brand.navy` | `#1F3A5F` | chữ chính, header |
| `brand.orange` | `#C4561D` | nền nút, chữ lớn (≥ 24sp) |
| `brand.orange.text` | `#B04A17` | chữ cam cỡ nhỏ (bản gốc chỉ ≈ 4,47:1 trên nền trắng) |
| `brand.green` | `#1E7B53` | trạng thái an toàn |
| `risk.low/medium/high/critical` | P1-05 | **luôn kèm biểu tượng + chữ** |
| `drill.*` | P1-05 | màu riêng cho diễn tập |

Font: **Be Vietnam Pro** (OFL). Một `tokens.json` dùng chung cho Tailwind `@theme` và Compose `Color.kt`/`Type.kt`.

## Chuẩn cho người cao tuổi (bắt buộc)
Chữ ≥ 20sp · nút chính ≥ 24sp đậm · vùng chạm ≥ 64dp · ≤ 2 hành động chính/màn · tương phản ≥ 7:1 · dùng được ở cỡ chữ
200% · màn quan trọng tự đọc to · nhãn TalkBack tiếng Việt · không đếm ngược gây hoảng.

**Nút bấm là chính, giọng nói chỉ bổ trợ.** Mọi hành động trả lời (có / không / không biết, gọi cho con, tiếp tục) phải làm
được bằng nút bấm; giọng nói (đọc to, và nếu sau này có: trả lời bằng giọng) chỉ là lớp thêm, không bao giờ là cách duy nhất —
bảo vệ người nói giọng địa phương, khó phát âm, nơi ồn, máy không có bộ nhận dạng vi-VN. Số đo và quy tắc quyết định:
`docs/spikes/P1-S5-giong-noi.md` (spec 004; trên ảnh máy ảo `google_apis_playstore`: nhận dạng vi-VN trên máy có ở API 36, không có ở API 34 — chưa đo máy thật).

## Màn hình app (E1–E12)
E1 Chào mừng (công khai AI) · E2 Ghép đôi · E3 Xin quyền (mỗi quyền một màn) · E4 Liên hệ tin cậy · E5 Thử giọng ·
E6 "Đang bảo vệ" · **E7 Dừng an toàn** · E8 Câu hỏi nhanh · E9 Chờ con · E10 Kết quả tra cứu · E11 Diễn tập ·
E12 Cài đặt & quyền riêng tư. Chi tiết luồng: kế hoạch đã duyệt §5; mỗi màn làm bằng skill `ui-screen`.

## Zalo (Z1–Z8) & Web
Xem kế hoạch §5; mẫu tin Zalo đặt ở `backend/src/hoicon/integrations/zalo/templates/` (mở đầu "Đây là trợ lý AI HỏiCon").
