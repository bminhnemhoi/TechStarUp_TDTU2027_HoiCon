# Evidence Spec 037: Gia cố phần còn lại (làn B, 23/10/2026)

> **BẢN NHÁP — Opus /speckit-analyze lại khi có quota.** Số đo ở máy dev (Postgres dev, cassette `synthetic`).

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 ép văn bản đồng ý | cặp ngoài manifest bị từ chối ở chế độ nghiêm; trong manifest nhận; dev không đổi | `test_consent_manifest_enforcement.py` (8) | 422 không ghi dòng, không nêu sha; draft bị từ chối khi nghiêm; manifest hỏng ⇒ 503 đóng; mặc định bật ngoài dev | ĐẠT |
| SC-002 kiểm đồng ý lúc gửi | rút `guardian_alerts` ⇒ 0 tin mới | `test_send_checks_consent.py` (5) | tin đã xếp lúc còn đồng ý nhưng rút trước khi gửi ⇒ `skipped_consent`, client Zalo giả 0 lời gọi; tin demo và tin Coach được miễn; chặn trộn demo/thật (luật 8) vẫn đi trước | ĐẠT |
| SC-003 ma trận IDOR | cùng mã + cùng thân cho "nhà khác" và "không có" | `test_idor_matrix.py` (35 ô: 11 route × 3 kiểu + 2 kiểm bao phủ OpenAPI) | 35/35 đạt; đột biến (bỏ `family_id` ở `load_incident`) ⇒ 3 ô đỏ | ĐẠT |
| SC-004 báo cáo quyền riêng tư | thoát 0, đủ bảng; bảng giả ⇒ thoát khác 0 | `test_privacy_report.py` (10) + chạy thật `ops.privacy_report` | 20/20 bảng có dòng; 0 số thô trong mã/fixture; văn bản đồng ý khớp; 0 dòng nghi PII trong kho dev | ĐẠT |
| SC-005 rà soát bảo mật cuối | 0 Critical/High chưa xử lý | `security-privacy-reviewer` + `pnpm audit` | xem mục dưới | MỘT PHẦN |
| SC-006 crash-free | ≥ 99% đo bằng Crashlytics | — | chưa đo | BLOCKED (Firebase, W0-3/P0-08) |

## Việc đã làm

- **T001:** `HOICON_CONSENT_STRICT` (mặc định bật ngoài dev, `config.consent_strict_on`); `POST /v1/consents` nhận (mục đích, phiên bản, sha) ở trạng thái `approved` hoặc `released` của `docs/legal/consent/manifest.json`; `Dockerfile` copy manifest; `infra/env.prod.example` ghi cờ.
- **T002:** `send_to_guardian` đọc `consent_gate` lúc gửi (payload mang `protected_member_id` cho diễn tập và Coach; sự cố tra qua `incident_id`).
- **T003:** `GET /v1/action/{token}` trả cùng 404 với liên kết không tồn tại khi người cao tuổi đã rút/chưa đồng ý `guardian_alerts` (demo miễn); `POST …/decision` vẫn ghi để đóng sự cố (đường an toàn). `test_withdrawn_links.py` (4). **Giả định cần Minh xác nhận (★ MASTER-PLAN §8):** chọn "ghi quyết định nhưng không đọc dữ liệu"; `POST /incidents/{id}/decision` (JWT) vẫn như cũ (thân tối thiểu đã đủ: `success/state/outcome`, không đổi hợp đồng).
- **T004:** ma trận IDOR đọc OpenAPI nên route mới có id mà chưa vào bảng làm test đỏ; 6 route miễn có lý do.
- **T005:** giới hạn 20 lần/phút/thiết bị cho `/v1/consents` (429 + `Retry-After`, bộ nhớ có trần 4096).
- **T006:** `queue.py` ghi tên lớp lỗi + dòng mã, KHÔNG `exc_info` (thông điệp SQLAlchemy nhúng tham số SQL); fixture `0912345678` đổi sang số hư cấu `0900000001`.
- **T007:** sao lưu v2: khóa con HKDF theo từng tệp, salt 16 byte; **đọc được bản v1 cũ** (fixture sinh bằng mã trước khi đổi); `test_backup_restore.py` (sao lưu + khôi phục thật) 33 passed, `test_backup_subkeys.py` 7 passed.
- **T008:** `ops/privacy_report.py` (bảng dữ liệu sinh từ `Base.metadata`, hạn lưu lấy từ `RETENTION`, quét số thô ở mã + fixture trừ fixture "invalid" cố ý, đếm dòng nghi PII).

## Rà soát bảo mật cuối (T009)

- **`pnpm audit --prod` TÌM RA THẬT:** `next@16.3.8` có 2 Critical (RCE không xác thực: Image Optimization với SVG; `use cache` trả typed array) + 1 High (DoS Server Actions), bản vá `>= 16.4.1`. **ĐÃ SỬA:** nâng `next` và `eslint-config-next` lên 16.4.1 (không thêm thư viện), `pnpm audit` ⇒ "No known vulnerabilities found"; typecheck, lint, build, e2e web 107 passed lặp nhiều lần.
- **Lỗi e2e chập chờn tìm ra khi lặp:** xyflow ẩn nút tới khi đo xong ⇒ `.first()` rơi vào nút `__end__` chưa hiện; sửa ở mã (`initialWidth/initialHeight` cho nút) và test (`:visible`, hạn chờ 20 s cho nạp động). Lặp 25 lần liên tiếp: không đỏ.
- `osv-scanner` có trên máy nhưng lệnh `scan source -L …` lỗi cú pháp ở phiên bản này; **UNAVAILABLE cho backend (`uv.lock`)** — chưa quét phụ thuộc Python.
- `security-privacy-reviewer` đọc diff 037: xem báo cáo ở cuối tệp (mục "Kết quả reviewer").

## Chưa làm / BLOCKED

- **T009 một phần** (xem trên), **T010** (gate đầy đủ ghi ở commit), **T011** (Crashlytics, Firebase), **T012** (sửa `docs/`: ngoài quyền làn B; nội dung cần thêm đã ghi ở `tasks.md`).
- Đồng ý đổi từ kênh khác không gọi `invalidate` ⇒ đệm tối đa 60 giây (đã nêu ở 011); DPIA chưa ghi — việc cho Opus.

## Sửa theo reviewer bảo mật (23/10)

- **High** — `POST /v1/consents`: chế độ nghiêm chỉ áp cho mục `granted=true`; lệnh RÚT luôn được nhận, kể cả manifest bản nháp/không đọc được (test `test_a_withdrawal_is_always_recorded_…`).
- **Medium** — bản tin tuần mang `protected_member_id` (cổng đồng ý lúc gửi áp được); cổng gửi đóng mặc định: tin thật không xác định được người cao tuổi ⇒ `skipped_consent` (test `…_names_no_protected_member_fails_closed`).
- **Medium** — `privacy_report`: thiếu thư mục nguồn ⇒ báo (không "sạch giả"); quét thêm `apps/android/*/src/main`; bắt số viết cách bằng dấu cách/chấm. Fixture `test_api_events.py` (ca từ chối PII cố ý) vào danh sách fixture âm.
- Test cũ `test_real_incident_never_reaches_a_demo_family_either` nay cấp `guardian_alerts` cho ca "thật ↔ thật" (hệ quả đúng của FR-002, không nới điều kiện).
- Ghi nhận, chưa sửa (Low): #5 `POST /decision` sau khi rút vẫn trả `state/outcome` (chủ ý, đường an toàn — cần Minh/Opus quyết); #6 hạn mức theo tiến trình (ADR-002 một worker); #7 giải mã sao lưu phải coi `BackupError` là bỏ cả lượt khi khôi phục thật; #8 đọc v1 còn nguy cơ trùng nonce thấp — tái mã hóa v1→v2 khi hết hạn lưu.
