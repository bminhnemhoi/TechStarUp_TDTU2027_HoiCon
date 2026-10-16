# Bằng chứng nghiệm thu Spec 026: Tác tử xác minh, tra cứu E10 & danh sách đe dọa trên máy

- **Trạng thái**: chưa triển khai. Đã có spec, plan và tasks từ 16/10/2026; chưa có số đo nào.
- **ADR-011** (bucket k-ẩn danh): Đề xuất, chờ Tiến chấp nhận.
- **Môi trường dự kiến**:
  - Linux CachyOS, Postgres dev trên Docker (cổng 15432), uvicorn trên localhost.
  - AVD `hc-api36` và `hc-api34` (`sdk_gphone64`).
  - Android build bằng JBR của Android Studio.
- **Nguồn số**: máy dev và máy ảo; máy ảo ≠ máy thật. Chưa có số đo trên máy thật vì Play Console/Firebase (P0-08) còn
  chặn.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 độ trễ tra cứu | API p95 ≤ 300 ms (n ≥ 50); E10 bấm → kết quả p95 ≤ 2 s (AVD 36) | `test_api_lookups.py` (đo thời gian) + log mốc thời gian trên AVD (T026) | chưa chạy | CHƯA ĐO |
| SC-002 riêng tư | 0 SĐT thô / h1 / URL trong DB, jobs, `agent_steps`, log; `threat-list` chỉ có bucket; chỉ lưu `bucket_enc`; ≥ 80 số/bucket ở b = 22 | quét DB + `caplog` (T013, T015, T018) + phép tính ở plan D1 + `security-privacy-reviewer` (T030) | chưa chạy | CHƯA ĐO |
| SC-003 kết luận & nâng mức | bảng plan §4 đúng 100%; phone không `safe`; mức không giảm, ≥ `rule_floor`; eval smoke ≥ baseline, 0 vi phạm, công khai AI 100% | `test_verification_rules.py`, `test_graph_verification.py`, `test_incident_service.py`, `hoicon-eval smoke --compare baseline` | chưa chạy | CHƯA ĐO |
| SC-004 ngoại tuyến | tra bucket p99 ≤ 5 ms / 100.000 bucket; đồng bộ lần 2 ⇒ 304; khớp nhầm trong ±30% của `N/2^b` | `:rules:test` (T020), `test_threat_list.py` (T015), E2E `fake_police` API 36 + 34 (T028) | chưa chạy | CHƯA ĐO |
| SC-005 E10 | 10 ảnh (5 trạng thái × 100%/200%); ≥ 20sp, ≥ 64dp, ≥ 7:1, công khai AI được đọc to; reviewer không còn mục chặn | ảnh ở `~/hoicon-evidence/026-verification-threat/` + `ux-elder-reviewer` (T026) | chưa chạy | CHƯA ĐO |
| SC-006 chống lạm dụng | 429 đúng ngưỡng (kể cả 25 request đồng thời ⇒ 20 lọt); 403 khi chưa đồng ý; 404 nhà khác; ≤ 1 tin bằng chứng/sự cố; `threat-list` ≤ 24/ngày | `test_api_lookups.py`, `test_threat_list.py`, `test_graph_verification.py` | chưa chạy | CHƯA ĐO |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` (sau khi tạo bộ spec) | xem báo cáo phiên 16/10/2026 |

## Review độc lập

Chưa chạy. Theo T026 và T030 sẽ gồm `ux-elder-reviewer` cho E10 và `security-privacy-reviewer` cho PII, manifest, đồng
ý, `bucket_enc` và hạn mức.

## Còn mở (không đánh ☑)

- Số đo trên máy thật cho E10 và cho `onScreenCall` với bucket.
- Sổ đăng ký tên miền/tổng đài chính thức: nguồn để kết luận `safe`. Cần dữ liệu đã kiểm và Minh duyệt.
- Tra cứu số tài khoản (`kind=account`): chưa có nguồn dữ liệu.
- Trạng thái `verifying`/`rescore` chưa được dùng; phải sửa `decided_state` trước.
