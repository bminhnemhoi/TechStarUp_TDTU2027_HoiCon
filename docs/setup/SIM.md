# Mô phỏng cho BGK (`/sim`, spec 033)

Công cụ **máy dev / buổi demo có người điều khiển**. Gian trưng bày công khai (không cần đăng nhập) là spec 050, không phải đây.

## Từ DB trống tới `/sim` (đã chạy thử 24/10/2026 trên Postgres tạm, mọi bước dưới đây)

```bash
docker compose -f infra/compose.dev.yml up -d                       # Postgres cổng 15432
uv run --directory backend alembic upgrade head                      # DB trống ⇒ tới head (0013)
export HOICON_ENV=dev HOICON_SIM_ENABLED=true
uv run --directory backend uvicorn hoicon.api.main:app --port 18000 --reload --loop asyncio:SelectorEventLoop
pnpm --dir apps/web dev                                              # http://localhost:3100 (rewrite /v1 → API 18000)
uv run --directory backend python -m hoicon.ops.guardian_link --seed # in login_url (gia đình demo + người giám hộ)
```
Mở `login_url` trên trình duyệt ⇒ vào `/incidents`, rồi `/sim`. Cần các khóa dev trong cấu hình cục bộ (do Minh/Tiến tự đặt
theo `docs/setup/ACCOUNTS.md`; thiếu khóa ⇒ `/readyz` 503 nêu TÊN biến, không in giá trị).
Kết quả đã quan sát với DB trống: `/healthz` 200, `/readyz` 200, `guardian_link --seed` in một liên kết (token 43 ký tự), đổi token
lấy phiên 200, `GET /v1/sim/scenarios` trả 110 kịch bản (mỗi kịch bản có `title_vi`, ví dụ "Giả danh công an · ca 2"), `POST
/v1/sim/runs` với `llm: replay` trả `llm_mode: replay`, có câu hỏi cho người cao tuổi, `is_demo: true`. (Giao diện `/sim` được
kiểm bằng Playwright với fixture hợp đồng: `pnpm --dir apps/web build && pnpm --dir apps/web e2e sim trace`.)

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

## Trên màn hình
- Ô chọn kịch bản hiện **tên tiếng Việt** (`title_vi` = nhóm thủ đoạn + " · ca N"); mã kịch bản ở dòng "Mã kịch bản: …" bên dưới.
- Băng **MÔ PHỎNG** dính đầu trang `/sim` và `/trace/<run>` của lượt mô phỏng, màu riêng `sim.*` (xanh dương) — khác màu
  diễn tập (tím) và các mức rủi ro. Trang `/trace` của lượt thật không có băng.
- Màn hình hẹp có 3 tab (điện thoại của bác · trợ lý AI · Zalo của con), điều khiển bằng ←/→/Home/End.
- Sơ đồ `/trace` rộng ~500 px: màn hẹp cuộn ngang; bản chữ "Các bước đã làm" luôn đủ cho bàn phím/đọc màn hình.

## Quay video 1280×720 (P2-21; do đội quay, chưa quay)
1. Cửa sổ trình duyệt 1280×720, chữ mặc định; đăng nhập bằng `login_url`; vào `/sim`.
2. Chọn "Giả danh công an · ca 2", `Phát lại bản đã ghi`, bấm **Bắt đầu**; đọc câu hỏi cho bác, bấm **Có**.
3. Chuyển qua cột trợ lý AI (bước hiện dần) rồi cột Zalo của con (2 tin, mở đầu "Đây là trợ lý AI HỏiCon").
4. Bấm "Tôi nghi … đang bị lừa" → xác nhận; chỉ băng MÔ PHỎNG. Tổng ≤ 4 thao tác.
5. Mở `/trace/<run>` từ lượt vừa chạy để cho thấy sơ đồ + băng MÔ PHỎNG.
Số đo trên máy dev/replay không phải số ở hội trường; không nói là số thật trong video.

## Dọn

Gia đình demo xóa bằng `guardian_link --cleanup <family_id>` (thiết bị mô phỏng đi theo gia đình, CASCADE).
Thiết bị mô phỏng của lượt đã kết thúc quá 24 giờ bị job `retention` xóa (sự cố giữ nguyên theo hạn lưu; lượt cũ không còn nhãn
MÔ PHỎNG ở `/trace`).
