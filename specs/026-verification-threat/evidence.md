# Bằng chứng nghiệm thu Spec 026: Tác tử xác minh, tra cứu E10 & danh sách đe dọa trên máy

- **Trạng thái (16/10/2026)**: Làn B (server, T001–T019) đã triển khai, chưa commit. Làn A (Android T020–T027) và giai
  đoạn Z (T028–T031) CHƯA làm; các dòng SC-001/004/005 phần máy ảo vẫn CHƯA ĐO.
- **Số đo Làn B (máy dev, Postgres 15432, không phải máy thật)**:
  - `pytest` toàn bộ 1501 passed; `ruff check` và `ruff format --check` sạch; `check-spec-trace` 17 spec, 0 lỗi.
  - `hoicon-eval --suite smoke --compare baseline --shared-db-ok`: 20 ca, recall 100%, báo nhầm 0%, vi phạm 0, công khai
    AI 100%, lệch baseline +0,0 điểm %.
  - `POST /v1/lookups` p95 ≈ 14 ms (n = 50, trong tiến trình, `test_lookup_latency_p95`); 25 request đồng thời ⇒ đúng 20
    lọt; `GET /v1/threat-list` 24 lượt/ngày/thiết bị rồi 429.
  - Migration `0007` lên/xuống/lên ổn trên DB dev (kể cả khi sổ đồng ý đã có dòng `lookups`).
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

`security-privacy-reviewer` (server, 16/10/2026): 0 Critical, 0 High, 6 Medium, 8 Low. Đã sửa (test đỏ trước):
- #1 parser URL lệch trình duyệt (`\`, userinfo, `.apk` trong truy vấn); #2 khóa job `evidence` giờ theo `verification_id`;
- #4 dựng ảnh chụp: single-flight + giải mã ngoài event loop; #8 thiết bị chỉ gắn tra cứu vào sự cố CỦA mình;
- #10 lỗi 5xx của `threat-list` không tốn lượt ngày; #11 node `verification` không gọi `raise_level` với mức `none`.

Để lại, cần Tiến quyết (đã ghi ở ADR-011 / DATA-MODEL / API):
- #3 job xóa theo hạn + xóa khi rút đồng ý `lookups` (nợ P2-20); #5/#6 k-ẩn danh chỉ là ước tính, khóa `bucket_enc` dùng
  chung `HOICON_DATA_KEY` với `chat_id` (cân nhắc khóa riêng/HKDF); #7 người giám hộ chưa có đường ghi đồng ý `lookups`
  (403, spec 023/027); #9 `HOICON_ENV` mặc định `dev`; #12–#14 (last3 do client khai, thiếu `is_drill`/vết kiểm toán
  `raise_level`, vài CHECK/chỉ mục `(family_id, at)`).
- Lỗ hổng còn lại của #2: lần tra `dangerous` ĐẦU TIÊN rơi vào lúc đồ thị chưa tới `await_guardian` vẫn có thể không
  sinh tin `evidence` nếu không có lần tra nguy hiểm sau đó.

Chưa chạy: `ux-elder-reviewer` cho E10 (thuộc Làn A, T026) và lượt đọc lại của reviewer sau các sửa trên.

## Còn mở (không đánh ☑)

- Số đo trên máy thật cho E10 và cho `onScreenCall` với bucket.
- Sổ đăng ký tên miền/tổng đài chính thức: nguồn để kết luận `safe`. Cần dữ liệu đã kiểm và Minh duyệt.
- Tra cứu số tài khoản (`kind=account`): chưa có nguồn dữ liệu.
- Trạng thái `verifying`/`rescore` chưa được dùng; phải sửa `decided_state` trước.
