# Bằng chứng nghiệm thu Spec 031: Hồ sơ vụ việc

- **Trạng thái (18/10/2026)**: chỉ có spec/plan/tasks và hợp đồng (T001). **Chưa code.**
- **Nguồn số dự kiến**: pytest + Playwright trên máy dev; không có người giám hộ thật (T017 BLOCKED).

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 có hồ sơ khi nghi lừa đảo | 100% `case_open` thật có 1 bản nháp + 1 tin; 0 cho diễn tập/eval/sim | pytest đồ thị | chưa chạy | CHƯA ĐO |
| SC-002 không PII | 0 `case_secrets` trong content, tin, `agent_steps` | pytest | chưa chạy | CHƯA ĐO |
| SC-003 ô tự điền không rời máy | 0 yêu cầu mạng chứa giá trị | Playwright | chưa chạy | CHƯA ĐO |
| SC-004 máy trạng thái hồ sơ | 200/409 đúng; đóng sự cố khi `mark_sent`/`discard` | pytest | chưa chạy | CHƯA ĐO |
| SC-005 hạn lưu chạy được | 30 ngày ⇒ `closed`; 12 tháng ⇒ xóa; purge ⇒ 0 hồ sơ | pytest đồng hồ giả | chưa chạy | CHƯA ĐO |
| SC-006 LLM không bắt buộc | không khóa ⇒ `template`; LLM bẩn ⇒ `template` | pytest | chưa chạy | CHƯA ĐO |
| SC-007 người giám hộ thật | duyệt + in, nói lại được | phỏng vấn | — | BLOCKED (thí điểm) |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| jsonschema: fixture `case_file.v1` (2 valid, 7 invalid), `case_file_action.v1` (3 valid, 3 invalid) | valid hợp lệ, invalid bị từ chối |

## Wave 3 làn A (22/10/2026) — T014 BLOCKED (chờ làn B)

Điều kiện tiên quyết "Sau T011" chưa có trên nhánh: `031 T011` (văn bản đồng ý gộp 031 + 032, làn B) chưa tick và `docs/legal/consent/manifest.json` vẫn là `2026.10-v3` chưa có bản gộp `guardian_alerts`. Chưa đồng bộ chuỗi Android; không tick T014.
