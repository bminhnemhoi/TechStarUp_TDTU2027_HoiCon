---
name: privacy-audit
description: Rà soát quyền riêng tư HỏiCon — tìm số điện thoại/tài khoản/OTP thô trong mã nguồn, log, DB và trace; kiểm tra che PII trước khi gọi LLM, độ phủ bản ghi đồng ý theo từng mục đích, job xóa dữ liệu theo thời hạn, manifest Android, công khai AI. Dùng trước mỗi gate từ M1, sau thay đổi lớn về dữ liệu, và trước khi cho gia đình thí điểm cài app.
---

# privacy-audit

## 1. Mã nguồn
```bash
# số điện thoại VN dạng thô ngoài tests/fixtures/data/docs
rg -n --pcre2 "(?<![\w.])(?:\+?84|0)[\s.-]?(?:3|5|7|8|9)(?:[\s.-]?\d){8}(?!\w)" apps backend -g '!**/test*/**' -g '!**/fixtures/**'
# log/print biến nhạy cảm không qua mask
rg -n -i "(log(ger)?\.|Log\.[dviwe]|print\(|console\.)[^\n]*(phone|caller|account|otp|cccd|zalo_?id)" apps backend -g '!**/test*/**'
# quyền cấm
rg -n "READ_SMS|RECEIVE_SMS|READ_CALL_LOG|READ_CONTACTS|QUERY_ALL_PACKAGES|BIND_ACCESSIBILITY|NOTIFICATION_LISTENER" apps/android
```

## 2. Dữ liệu đang chạy (Postgres 15432)
- Truy vấn mẫu các cột text/jsonb của `risk_events`, `agent_steps`, `messages_out`, `case_files` tìm chuỗi khớp regex số điện thoại → phải 0 dòng.
- Đếm `consents` theo `purpose` cho từng thiết bị đang hoạt động: mọi quyền đã cấp (`devices.permission_state`) phải có bản ghi `granted` chưa bị rút.
- Kiểm job xóa: bản ghi quá hạn (sự kiện > 90 ngày, nội dung bước tác tử > 30 ngày, demo > 24 giờ) = 0.

## 3. LLM & trace
- Lấy 20 `agent_steps` gần nhất: `input_redacted` không chứa số/tên thật; có `<untrusted>` quanh nội dung kẻ gian.
- Test công khai AI: mọi mẫu tin Zalo/màn đầu cho người cao tuổi bắt đầu bằng "Đây là trợ lý AI HỏiCon".
- Kiểm cấu hình: không dùng free tier của nhà cung cấp LLM cho dữ liệu thí điểm thật.

## 4. Báo cáo
`docs/phase-reports/privacy-<ngày>.md`: bảng `| Hạng mục | Kết quả | Bằng chứng | Việc cần sửa |`. Lỗi Critical/High ⇒ chặn gate và chặn cài cho gia đình thí điểm.
