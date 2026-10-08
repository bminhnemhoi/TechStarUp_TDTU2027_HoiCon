# ADR-005: Phát hành app qua kênh thử nghiệm của Google Play, không phát APK

- Trạng thái: **Chấp nhận** · 08/10/2026

## Bối cảnh
Người cao tuổi là mục tiêu của chính các vụ lừa "cài app lạ". Hướng dẫn họ cài APK ngoài Play đi ngược thông điệp an
toàn của HỏiCon và bị Play Protect cảnh báo. App dùng vai trò sàng lọc cuộc gọi, UsageStats, hiển thị trên app khác —
cần khai báo Play Console (Data safety, foreground service `specialUse`, quyền nhạy cảm).

## Quyết định
- Đăng ký Play Console **ngay** (xác minh danh tính mất nhiều ngày). Phát hành qua **internal testing** (≤ 100 tester)
  rồi **closed testing** với Google Group cho gia đình thí điểm.
- Không bao giờ gửi APK cho người cao tuổi. Máy ảo/dev dùng `installDebug`.
- `docs/PLAY-POLICY.md` theo dõi khai báo cho từng quyền và video minh họa sử dụng quyền nếu Play yêu cầu.

## Hệ quả
- (+) Cài đặt quen thuộc, cập nhật tự động, uy tín với BGK.
- (−) Phụ thuộc thời gian duyệt của Play ⇒ nộp bản internal sớm (P1-08), dự trù 1–2 tuần cho closed testing.
- (−) Tài khoản **cá nhân** mới (kiểm chứng 08/10/2026, `docs/setup/ACCOUNTS.md` §1, §7):
  - phải **xác minh có điện thoại Android thật** (không root, Android 10+, app Play Console) trước khi đưa app lên
    Play — **máy ảo không được chấp nhận**; mượn máy người thân được phép ⇒ làm trước P1-08;
  - **12 tester × 14 ngày closed testing** chỉ bắt buộc để xin quyền **production** — thí điểm dùng internal/closed
    testing nên không bị chặn.
