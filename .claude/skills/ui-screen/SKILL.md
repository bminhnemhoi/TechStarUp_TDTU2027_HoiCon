---
name: ui-screen
description: Thiết kế và dựng một màn hình HỏiCon đạt chuẩn — nhánh "elder" cho app Lính gác (Compose, người cao tuổi, giọng nói, cỡ chữ 200%) và nhánh "web" cho Next.js (trang hành động người giám hộ, dashboard, trace, booth) — rồi xác minh bằng ảnh chụp. Dùng cho mọi màn hình/component mới hoặc chỉnh sửa giao diện lớn.
---

# ui-screen

## 1. Chuẩn bị
- Đọc `docs/DESIGN-SYSTEM.md` (token, mã màn E1–E12/Z1–Z8, giọng văn) và user story trong `docs/PRD.md`.
- Tra cứu bằng plugin nếu có: **UI UX Pro Max** (`search.py "<loại màn hình>"`, file `design-system/hoicon/pages/<màn>.md`), **frontend-design** (web). Xung đột ⇒ **DESIGN-SYSTEM.md thắng**.

## 2a. Nhánh elder (Compose)
- Chỉ dùng token trong `ui/theme` (Color.kt/Type.kt sinh từ `design-system/hoicon/tokens.json`); không hardcode màu.
- Chữ ≥ 20sp, nút chính ≥ 24sp đậm, vùng chạm ≥ 64dp, ≤ 2 hành động chính; màu rủi ro luôn kèm biểu tượng + chữ.
- Mọi màn quan trọng tự đọc to (TTS/âm thanh thu sẵn) và có nút "Nghe lại"; `contentDescription` tiếng Việt.
- Màn diễn tập dùng màu riêng + nhãn "ĐÂY LÀ DIỄN TẬP". Màn dừng an toàn: không chặn vĩnh viễn (giữ 3 giây để tiếp tục).
- Xác minh trên máy ảo (skill `android-emulator-test`): ảnh chụp ở `font_scale` 1.0 và 2.0 bằng `android screen capture`, kiểm cây giao diện bằng `android layout`; gọi `ux-elder-reviewer` kèm ảnh.

## 2b. Nhánh web (Next.js)
- shadcn/ui + token Tailwind `@theme`; Server Component mặc định; đủ trạng thái loading/empty/error.
- Responsive từ 360 px; trang `/a/[token]` dùng được bằng một tay, nút lớn.
- Xác minh bằng Playwright: ảnh 390×844 và 1440×900, axe không lỗi serious/critical, điều hướng bàn phím.

## 3. Đầu ra
- Màn chạy được + ảnh chụp lưu trong `docs/spikes/shots/` hoặc thư mục snapshot test.
- Báo Minh: route/màn, ảnh, trạng thái đã kiểm, góp ý review còn mở.
