---
name: add-scam-scenario
description: Thêm kịch bản lừa đảo (hoặc cuộc gọi hợp lệ đối chứng) vào thư viện data/scenarios và bộ eval/cases của HỏiCon theo schema chuẩn — có nhóm thủ đoạn, vùng miền, cặp "song sinh hợp lệ", dấu hiệu đỏ, kết quả mong đợi, nguồn trích dẫn. Dùng khi soạn ca eval, bài diễn tập, hoặc khi có cảnh báo thủ đoạn mới từ cơ quan chức năng.
---

# add-scam-scenario

## Schema (YAML, một file một ca)
```yaml
id: fake_police_vneid_001          # <category>_<chủ đề>_<số>
category: fake_police              # fake_police|fake_tax|fake_evn|deepfake_relative|task_scam|recovery_scam|fake_vneid|fake_bank|investment|benign_bank|benign_relative_new_number|benign_shipper
is_benign: false
region: south                      # north|central|south
channel: phone_call                # phone_call|zalo|sms_reported
script_vi: |                       # lời người gọi, tên cơ quan & số HƯ CẤU
  ...
device_signals: {caller_flag: unknown, in_call: true, duration_bucket: 5_15m, app_category: bank}
elder_answers: {claims_authority: yes, asks_secrecy: yes, asks_transfer: yes}
expected:
  min_risk_level: high             # low|medium|high|critical
  notify_guardian: true
  must_call_tools: [threat.check_number]
  must_not: [lower_than_floor, missing_ai_disclosure]
red_flags: [xưng công an, đòi giữ bí mật, thúc ép thời gian, đòi chuyển tiền]
teach_points: [Công an không làm việc qua điện thoại để yêu cầu chuyển tiền]
source_ref: "Thanh Niên 02/01/2026 – Công an TP.HCM cảnh báo thủ đoạn giả danh công an gọi học sinh"
draft: true                        # Minh duyệt xong mới bỏ
```

## Quy tắc
1. Mỗi ca lừa đảo nên có một **ca hợp lệ song sinh** gần giống (ví dụ ngân hàng thật gọi xác minh, không đòi chuyển tiền) — giữ tỷ lệ hợp lệ ≥ 30% toàn bộ.
2. Chỉ dùng tên, số điện thoại (dải `0900000xxx`), số tài khoản **hư cấu**; nội dung đủ để kiểm thử, không viết thành "kịch bản mẫu" chi tiết dễ lạm dụng.
3. Bắt buộc `source_ref` từ cảnh báo chính thức/báo chí (xem `docs/research/notes/08_social_impact.md`).
4. Sau khi thêm: chạy `uv run --directory backend hoicon-eval --validate` (kiểm schema, tỷ lệ hợp lệ, trùng id).
