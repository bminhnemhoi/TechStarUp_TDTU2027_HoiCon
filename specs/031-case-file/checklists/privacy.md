# Checklist riêng tư — Spec 031 (hồ sơ vụ việc)

Người tick: `security-privacy-reviewer` hoặc Tiến/Minh (T015). Không tự tick để qua cổng (MASTER-PLAN §2.5).

- [ ] `case_files.content` chỉ chứa trường của `case_file.v1#/$defs/content`; 0 số điện thoại đầy đủ, h1, HMAC, tên gói, lời kể, tên thật
- [ ] Ô tự điền: không thuộc form gửi đi, không `localStorage`/`sessionStorage`/cookie, không có trong URL; Playwright chặn yêu cầu xác nhận
- [ ] Đoạn tóm tắt LLM đi qua `llm_router` (che PII, timeout ≤ 4 s, output có cấu trúc, lọc số/link, rơi về mẫu)
- [ ] HỏiCon không gửi hồ sơ cho bên thứ ba nào; câu này có trên trang, tin Zalo và bản in
- [ ] Hạn lưu: xóa cùng sự cố 12 tháng sau `closed_at`; tự đóng `case_open` sau 30 ngày; xóa gia đình ⇒ 0 hồ sơ
- [ ] Văn bản `guardian_alerts` nhắc hồ sơ (cùng PR với mã), sha mới, Android ghim lại; ★ Minh xác nhận phạm vi (MASTER-PLAN §8 mục 4)
- [ ] Diễn tập, eval, sim không bao giờ có dòng `case_files`
- [ ] `agent_steps` của nút `case_file` không chứa nội dung hồ sơ thô
