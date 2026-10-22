# Mô phỏng cho BGK (`/sim`, spec 033)

Công cụ **máy dev / buổi demo có người điều khiển**. Gian trưng bày công khai (không cần đăng nhập) là spec 050, không phải đây.

## Bật

```bash
export HOICON_SIM_ENABLED=true          # mặc định false; compose.prod.yml KHÔNG đặt (có test)
uv run --directory backend python -m hoicon.ops.guardian_link --seed   # in login_url của người giám hộ gia đình demo
```

Mở `login_url` trên trình duyệt (cổng web 3100), rồi vào `/sim`. Tắt cổng ⇒ mọi `/v1/sim/*` trả 404 và trang web hiện
"Trang này chưa mở".

## Hai chế độ

| `llm` | Hành vi |
|---|---|
| `replay` (mặc định) | `ReplayClient` với cassette của kịch bản (`backend/eval/cassettes/{full,smoke}`): tất định, cùng bước và câu chữ ở mọi lần chạy |
| `live` | `LlmRouter` thật; không có `HOICON_ANTHROPIC_API_KEY` ⇒ rơi về mẫu soạn sẵn và khung nhìn ghi `llm_mode: "fallback"` |

**Trong container, `replay` không khả dụng:** `.dockerignore` loại `backend/eval`, nên ảnh không có cassette ⇒ API trả
`llm_mode: "fallback"` (mẫu soạn sẵn), không báo lỗi. Muốn phát lại tất định, chạy API trực tiếp bằng `uv run`.

## Không có gì thật

- Tin "Zalo của con" chỉ là bản ghi (`jobs.payload`, đã che PII): sự cố mô phỏng mang cờ `sim` nên **không bao giờ** gọi Zalo,
  kể cả `HOICON_ZALO_MODE=live`, không trừ hạn mức.
- Chỉ gia đình `is_demo`; kịch bản đều hư cấu (số `0900000xxx`, miền `*.example`); kịch bản `draft: true` có nhãn "kịch bản nháp".
- Mỗi lượt có một thiết bị demo riêng (nhãn `sim:<kịch bản>`) để hai lượt song song không bị gom vào một sự cố.
- Hạn mức: 10 lượt/giờ/người giám hộ, 3 lượt đang chạy/gia đình (429 + `Retry-After`); runtime phát lại sống 60 phút, tối đa
  20; mất (khởi động lại) ⇒ lượt tiếp tục bằng runtime chung và báo `fallback`.

## Dọn

Gia đình demo xóa bằng `guardian_link --cleanup <family_id>` (thiết bị mô phỏng đi theo gia đình, CASCADE).
