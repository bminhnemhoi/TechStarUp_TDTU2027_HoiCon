# Bằng chứng nghiệm thu Spec 032: Coach hằng tuần + báo "mất bảo vệ"

- **Trạng thái (22/10/2026, Wave 3 làn B)**: T001–T009 xong (mã server + test + tài liệu); T010/T011 (Android, làn A), T012 (reviewer), T013 (cổng cuối) chưa; T014/T015 BLOCKED. Không có hợp đồng mới trong `docs/schemas/` (xem tasks.md).
- **Nguồn số dự kiến**: pytest (đồng hồ giả) + AVD `hc-api36` cho khoảng trống heartbeat (máy ảo ≠ máy thật); máy thật BLOCKED.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 phát hiện đúng | `silent` 24 giờ ± 1; `permission_off` 2 khung; 0 tin khi không đủ điều kiện | pytest | `test_protection_watch.py` (11, đồng hồ giả): 23 giờ ⇒ 0, 25 giờ ⇒ 1; 1 khung `false` ⇒ 0, 2 khung ⇒ 1 (mốc = khung `false` đầu tiên của đợt); thu hồi/demo/chưa đồng ý/chưa từng heartbeat/cờ tắt ⇒ 0; 22:30 hoãn tới 07:05; hạng 2 khi hạng 1 không có chat. Máy dev, DB dev, n = 1 lượt/ca | ĐẠT |
| SC-002 một tin mỗi đợt | 48 lần chạy ⇒ 1 tin | pytest | 48 lượt cùng đợt ⇒ 1 tin; máy báo về rồi mất lại (> 24 giờ sau) ⇒ tin thứ hai; đợt mới trong 24 giờ ⇒ không tin thêm; `coach_weekly` chạy hai lần cùng tuần ⇒ 1 tin/người giám hộ | ĐẠT |
| SC-003 bản tin đúng số | khớp seed; 0 câu "an toàn" khẳng định | pytest | `test_coach_weekly.py` (10): số lần nhắc (loại diễn tập/demo/ngoài 7 ngày) = 2, đã xử lý = 1, bài luyện tập = 1, độ phủ làm tròn 5%; opt-out theo người; `test_coach_texts.py` (36): không chuỗi "an toàn" ở mọi biến thể | ĐẠT |
| SC-004 hạn mức | 80% / 95% đúng hành vi; tin sự cố không ảnh hưởng | pytest | `test_coach_quota.py` (3): 75% ⇒ cả hai đi; ≥ 80% ⇒ bản tin `held_quota` (không thử lại), tin mất bảo vệ vẫn đi; ≥ 95% ⇒ cả hai giữ, tin sự cố khẩn vẫn `sent`. Hạn mức test = 20 tin | ĐẠT |
| SC-005 công khai AI + PII | 100% công khai; 0 PII | pytest | mọi mẫu mở đầu "Đây là trợ lý AI HỏiCon"; không dãy ≥ 4 chữ số, `mask_text` không đổi gì; quét `jobs`/`agent_steps` không có số/tên gói/h1; trace không chứa chữ tin | ĐẠT |
| SC-006 ngưỡng 24 giờ | khoảng trống dài nhất trên AVD < 24 giờ | AVD | chưa chạy (task T011 làn A) | CHƯA ĐO (làn A) |
| SC-007 máy thật | tỷ lệ báo nhầm 7 ngày thí điểm | thí điểm | — | BLOCKED (029 giai đoạn 2) |


## Wave 3 — ghi chú thi công (làn B, 22/10/2026)

- **Migration `0012`** (`members.weekly_digest_enabled`) áp lên DB dev sau `0011` của 031 (head = 0012). Hạ tầng: `data/coach` thêm vào `backend/Dockerfile` + test; `roles.sql` cần chạy lại sau migration (cấp theo vòng lặp mọi bảng).
- **Lệch so với chữ của tasks (cần Opus):**
  1. `send_to_guardian` mở rộng cho tin Coach: `job_key`, `urgent`, `member_id`, `quota_class` trong payload (tin sự cố giữ hành vi cũ); `quota_class = digest` ⇒ ngưỡng giữ = `warn_pct`.
  2. Chống trùng 24 giờ dựa vào `payload.queued_at` (đồng hồ của lượt chạy), không `jobs.created_at` (đồng hồ DB) để test đồng hồ giả đúng.
  3. Giờ trong tin mất bảo vệ viết "07:30 ngày 20 tháng 10" (dạng "20/10" bị `mask_text` che thành `[MÃ]`).
  4. Test hạn mức đặt chung ở `test_coach_quota.py`, không tách vào hai tệp `-k quota` như Verify; các hàm `find_protection_lapses`/`run_*` nhận `family_id` tùy chọn **chỉ để test** (DB dev dùng chung).
  5. T008: văn bản đồng ý đã vào ở 031 T011 và được sửa theo `ux-elder-reviewer` (khác chữ Opus soạn; xem evidence 031); ý I4 chưa quyết ⇒ giữ câu "Họ được báo nếu HỏiCon bị tắt"; `docs/PILOT-PROTOCOL.md` §4 đã thêm lại dòng.
  6. Hướng dẫn mẹo `tips.vi.yaml` có tệp (`approved: false`) và test hai chế độ; T015 (Minh duyệt) BLOCKED.
- **Chưa làm / ngoài quyền:** `ux-elder-reviewer` cho 5 mẫu tin và `security-privacy-reviewer` cho 032 (T012 không nằm trong phạm vi lượt này); dòng ROADMAP "Ghi chú" về trace của lượt `coach` (cấm sửa ROADMAP) — **việc cho Tiến/Opus**; chưa có route web cho người giám hộ xem trace lượt `coach`.
- **Rủi ro đã biết:** tin mất bảo vệ phụ thuộc heartbeat 15 phút; cho tới khi T011 (đo Doze/Standby trên AVD) có số, ngưỡng 24 giờ chưa được kiểm chứng.
