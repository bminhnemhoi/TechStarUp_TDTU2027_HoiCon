# Contracts: spec 002

- **Mới:** `docs/schemas/zalo_update.v1.json` — tập con của cập nhật webhook Zalo mà HỏiCon dùng (mã cập nhật, loại sự kiện,
  người gửi, văn bản/callback). Viết **sau** research R1 (theo tài liệu chính thức), kèm fixture
  `docs/schemas/fixtures/zalo_update.v1.valid.json` / `.invalid.json` với định danh **hư cấu**. Mock và test dùng chung fixture.
- **Nội bộ (không phải hợp đồng giữa làn):** payload job `notify_guardian` thêm `family_id` (tùy chọn, tương thích ngược).
- **API:** `POST /webhooks/zalo/{bot_id}` — ghi vào `docs/API.md` (header `X-Bot-Api-Secret-Token`, 200/401/503).
  Không có endpoint `/v1` mới ⇒ không cần sinh lại client TS.
