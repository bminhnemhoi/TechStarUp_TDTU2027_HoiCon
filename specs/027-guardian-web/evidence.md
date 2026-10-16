# Bằng chứng nghiệm thu Spec 027: Web người giám hộ

- **Trạng thái**: chưa triển khai. Đã có spec, plan và tasks từ 16/10/2026; chưa có số đo nào.
- **Môi trường dự kiến**: Linux CachyOS, Postgres dev (cổng 15432), API uvicorn cổng 18000, web `next start` cổng 3100,
  Playwright Chromium, Zalo **mock** (chưa có token bot thật).
- **Nguồn số**: chỉ máy dev, localhost. Chưa có Caddy/VPS (thuộc 012).

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 đăng nhập qua Zalo | liên kết ≤ 5 s (mock); một lần dùng; hạn 15 phút; lỗi có hướng dẫn | `test_guardian_login.py`, `test_guardian_session.py`, `e2e/login.spec.ts` | chưa chạy | CHƯA ĐO |
| SC-002 cô lập gia đình | 0 truy cập chéo (404); thành viên bị xóa ⇒ 401 | `test_guardian_incidents.py` (ma trận route × 2 gia đình) | chưa chạy | CHƯA ĐO |
| SC-003 bảo mật phiên | cờ cookie đúng; POST bằng cookie thiếu Origin ⇒ 403; 0 token thô trong log, `jobs`, `messages_out` | `test_guardian_session.py`, quét DB và `caplog` | chưa chạy | CHƯA ĐO |
| SC-004 trace trực tiếp | bước mới hiện ≤ 1 s; nối lại không trùng; `done` ⇒ "Đã xong" | `e2e/live.spec.ts` (API thật, localhost) + `e2e/detail.spec.ts` (luồng giả) | chưa chạy | CHƯA ĐO |
| SC-005 UX & khả năng tiếp cận | ảnh 360/768/1280 px + 200%, không tràn; axe 0 lỗi serious/critical; nút chính ≥ 64 px | `e2e/a11y.spec.ts` + `ux-elder-reviewer` | chưa chạy | CHƯA ĐO |
| SC-006 hợp đồng & hồi quy | schema có test; client TS sinh lại; web lint/typecheck/build xanh; pytest không hỏng | CI + lệnh T021 | chưa chạy | CHƯA ĐO |

## Next 16 và SSE (T003–T004)

Chưa đo.

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` (sau khi tạo bộ spec) | xem báo cáo phiên 16/10/2026 |
