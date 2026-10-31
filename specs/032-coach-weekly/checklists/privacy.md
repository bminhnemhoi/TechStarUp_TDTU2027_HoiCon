# Checklist riêng tư — Spec 032 (Coach hằng tuần + mất bảo vệ)

Người tick: `security-privacy-reviewer` hoặc Tiến/Minh (T012).

- [ ] Tin chỉ có bí danh, giờ, số đếm, phần trăm; 0 số điện thoại/h1/tên thật/Zalo ID trong tin, job, `agent_steps`
- [ ] Mỗi tin kiểm đồng ý `guardian_alerts` của người cao tuổi ngay trước khi xếp; đã rút ⇒ 0 tin
- [ ] Gia đình demo, thiết bị đã thu hồi ⇒ 0 tin
- [ ] Mọi tin qua `deliver` → `messages_out`; bản tin dừng ở 80%, tin mất bảo vệ tới 95%, tin sự cố không bị ảnh hưởng
- [ ] Lệnh "tắt/bật tin tuần": chữ thô không lưu (giữ quy tắc 002), chỉ đổi cờ của đúng người giám hộ
- [ ] Văn bản `guardian_alerts` thêm lại câu báo mất bảo vệ + bản tin (cùng PR với mã), sha mới, Android ghim lại; ★ Minh (MASTER-PLAN §8 mục 4–5)
- [ ] DPIA ghi việc dùng heartbeat để báo người giám hộ
