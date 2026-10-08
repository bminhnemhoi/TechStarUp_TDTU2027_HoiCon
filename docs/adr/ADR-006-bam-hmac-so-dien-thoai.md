# ADR-006: Số điện thoại / số tài khoản chỉ rời máy dưới dạng băm; máy chủ lưu HMAC có pepper xoay vòng

- Trạng thái: **Chấp nhận** · 08/10/2026
- Liên quan: DATA-MODEL §3, CLAUDE.md luật 1–2, Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15

## Bối cảnh
Cần so khớp số gọi đến với danh sách đe dọa và liên hệ tin cậy, đếm số lần một số xuất hiện, hiển thị "số đuôi …123"
cho người giám hộ — mà không giữ số thô (rò rỉ DB không làm lộ danh bạ/cuộc gọi của người cao tuổi). Không gian số di
động VN nhỏ (~10⁹) nên SHA-256 trơn có thể bị dò ngược.

## Quyết định
- Máy chuẩn hóa E.164 rồi tính `h1 = SHA-256("hoicon:v1:" + e164)`; chỉ gửi `h1` + 3 số cuối.
- Máy chủ lưu `HMAC-SHA256(pepper[kid], h1)` + `kid` + `last3`. Pepper nằm ngoài DB (biến môi trường / `D:\secrets`),
  xoay vòng bằng `kid` mới (tính lại khi số xuất hiện lần sau).
- Danh sách đe dọa gửi xuống máy dạng tập `h1` để so khớp cục bộ.
- Số tài khoản ngân hàng: cùng cơ chế với tiền tố `"hoicon:acct:v1:"`.
- Log, trace, prompt LLM chỉ được thấy `…123`. Hook `guard-privacy` + skill `privacy-audit` kiểm tra.

## Hệ quả
- (+) DB bị lộ không đủ để dò số (cần pepper); tuân thủ tối thiểu hóa dữ liệu.
- (−) `h1` vẫn dò được nếu kẻ tấn công có `h1` — `h1` chỉ đi trên kênh TLS và không lưu ở máy chủ.
- (−) Không tra cứu ngược được số thô để hỗ trợ người dùng ⇒ người giám hộ nhìn số trên máy người cao tuổi.
