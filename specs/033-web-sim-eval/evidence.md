# Bằng chứng nghiệm thu Spec 033: Web `/sim`, `/trace`, `/eval`

- **Trạng thái (18/10/2026)**: chỉ có spec/plan/tasks và hợp đồng (T001). **Chưa code.**
- **Nguồn số dự kiến**: máy dev (API 18000 + web 3100, Playwright Chromium), chế độ `replay`. Không có số máy thật hay VPS.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 toàn luồng trên web | ≤ 5 thao tác, bước hiện ≤ 1 s | Playwright | chưa chạy | CHƯA ĐO |
| SC-002 tất định | hai lượt replay giống nhau | Playwright | chưa chạy | CHƯA ĐO |
| SC-003 cô lập | cổng, chỉ demo, Zalo mock ép, hạn mức | pytest | chưa chạy | CHƯA ĐO |
| SC-004 tiếp cận | axe 0 lỗi; bản chữ trace đủ bước | Playwright + axe | chưa chạy | CHƯA ĐO |
| SC-005 đúng đồ thị | topology = đồ thị biên dịch | pytest | chưa chạy | CHƯA ĐO |
| SC-006 không PII | 0 số/h1/tên gói trong API + DOM | pytest + Playwright | chưa chạy | CHƯA ĐO |
| SC-007 video | một lượt quay dùng được | đội quay | — | BLOCKED (P2-21) |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| jsonschema + `referencing`: fixture 4 lược đồ (8 valid, 15 invalid) | valid hợp lệ, invalid bị từ chối |
| `uv run --directory backend pytest -q tests/contract` | 257 passed (lược đồ mới chưa có test riêng — T002) |
