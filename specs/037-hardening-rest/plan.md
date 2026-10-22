# Plan: 037 — Gia cố phần còn lại

## 0. Kiểm theo hiến chương
| Nguyên tắc | Cách giữ |
|---|---|
| I. Dừng an toàn | Không đụng `:rules`, E7, `SafePauseActivity` |
| II. Riêng tư | Kiểm đồng ý lúc gửi; sổ xóa chỉ id + mã hóa; không SDK mới khi chưa có đồng ý |
| IV. Đồng ý chỉ ghi thêm | FR-004 chỉ kiểm, không sửa dòng `consents` |
| V. Hợp đồng trước | `error.v1.json` thêm `consent_withdrawn`/`unknown_consent_text` trước mã (T001) |
| VIII. Ít code | Android vitals thay Crashlytics; HKDF và rate limit dùng thư viện/khung có sẵn |

## 1. Quyết định
| # | Quyết định | Lý do |
|---|---|---|
| D1 | Kiểm đồng ý trong `send_to_guardian` (một chỗ), không ở từng node | Mọi mẫu tin đều đi qua hàm này; node quên kiểm thì vẫn chặn được |
| D2 | `protected_member_id` vào payload job; job cũ tra theo `incident_id` | Không migration; tương thích job đang xếp |
| D3 | Manifest đồng ý nạp lúc khởi động, so (`version`, `sha256`) | Một nguồn sự thật với 011 (`consent_texts check`) |
| D4 | Rate limit dùng bộ đếm của `/v1/lookups` (026) | Tái dùng, không thêm thư viện |
| D5 | Sổ xóa là tệp cạnh sao lưu, không là bảng | Bảng nằm trong chính bản sao lưu nên không giải được #6 |
| D6 | Android vitals trước, Crashlytics chỉ khi Minh duyệt | Luồng dữ liệu mới cho bên thứ ba ⇒ luật 7 + DPIA; vitals có sẵn, 0 dòng mã |

## 2. Tệp
B: `channels/guardian.py`, `agents/incident_graph.py` (payload), `api/routers/consents.py`, `api/errors.py`, `ops/backup.py`,
`ops/restore.py`, `jobs/queue.py`, `tests/**`. A: `data/net/*`, `data/consent/*`, `ui/ProtectionStatusScreen.kt`, `strings.xml`.
Chung: `docs/schemas/error.v1.json` (checkout chính), `docs/setup/STABILITY.md`, `docs/PRIVACY-DPIA.md` (nếu Crashlytics).

## 3. Rủi ro
| Rủi ro | Mức | Giảm |
|---|---|---|
| Kiểm đồng ý chặn nhầm tin của sự cố demo/sim | TB | Giữ miễn trừ `is_demo`/`sim` như 033/034; test riêng |
| Manifest prod chưa có `released` ⇒ prod từ chối mọi đồng ý | Cao | FR-004 chỉ ép `released` khi `HOICON_ENV=prod`; release-gate 011 đã chặn phát hành bản nháp |
| Đổi `exc_info` làm mất dấu vết lỗi | Thấp | Log tên lớp + mã job; traceback chỉ ở `HOICON_ENV=dev` |
