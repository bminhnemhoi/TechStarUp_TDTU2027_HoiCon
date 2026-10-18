# Văn bản đồng ý · `call_screening` · Nhận biết cuộc gọi số lạ

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Nhận biết cuộc gọi số lạ
HỏiCon xin phép được biết khi có số chưa lưu trong danh bạ gọi tới, hoặc khi bác gọi cho số chưa lưu.
HỏiCon biết có cuộc gọi, lúc nào và bao lâu. HỏiCon không nghe cuộc gọi, không chặn cuộc gọi và không đọc danh bạ của bác.
HỏiCon không giữ số đầy đủ của bác, chỉ giữ 3 số cuối và một mã thay cho số đó, để nhận ra số đã gặp.
Bác tắt quyền này trong Cài đặt của điện thoại bất cứ lúc nào. Khi đó HỏiCon thôi làm việc này, và con bác có thể biết để hỏi thăm bác.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- Cả cuộc gọi đến và đi: `docs/PRIVACY-DPIA.md` mục 3 (review bảo mật 09/10); chữ app `perm_role_*`, `disclosure_1_body`.
- "Dãy ký tự đại diện + 3 số cuối": ADR-006 (`h1` rồi HMAC có pepper ở máy chủ).

## Điểm chờ quyết
- Không có. Trang quyền của Android do hệ điều hành hiện, văn bản này là lời giải thích trước đó.
