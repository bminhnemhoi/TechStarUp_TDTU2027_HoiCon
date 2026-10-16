# Công việc Spec 034: Gia cố lõi trước người dùng thật

Chạy một mạch trong worktree làn B. Mỗi task phải có `Verify` xanh rồi mới sang task kế. Biến dùng trong lệnh:
`PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`.

Số migration là số kế tiếp sau head lúc thi công (`alembic heads`); không giẫm số mà 026/028 đã ghi trong plan nếu các
spec đó chưa merge.

## Giai đoạn 1: Lược đồ
- [ ] T001 [FR-001] Viết migration: bảng `data_requests` (các CHECK, không cột văn bản tự do), `families.deleted_at`,
  `members.deleted_at`, chỉ mục `agent_steps(at)`, `jobs(done_at)`, `risk_events(received_at)` (nếu chưa có). Cập nhật
  `db/models.py`.
  · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head`
- [ ] T002 [FR-001] Viết `backend/tests/integration/test_schema_<số>.py` kiểm các CHECK, chỉ mục và cột mới.
  · Verify: `$PYTEST tests/integration/test_schema_<số>.py`

## Giai đoạn 2: Mặc định an toàn
- [ ] T003 [FR-006] Đổi `Settings.env` mặc định thành `prod`, rồi đặt `HOICON_ENV` tường minh ở:
  - `backend/.env.example` (`dev`);
  - `tests/conftest.py` (`test`, đặt trước khi nạp cấu hình);
  - `.github/workflows/*.yml`;
  - `ops/init_env.py`.

  Không đọc `.env` thật.
  · Verify: `$PYTEST` (toàn bộ, phải xanh như trước)
- [ ] T004 [FR-006] Thêm vào `/readyz` kiểm pepper hiện hành, khóa dữ liệu hiện hành và khóa JWT; thiếu thì trả 503
  `{"missing": [...]}` (chỉ tên). Thêm middleware giới hạn thân 256 KB, áp cho cả `Content-Length` và thân chunked.
  · Verify: `$PYTEST tests/integration/test_ops_safety.py`
- [ ] T005 [FR-006] Viết `backend/tests/integration/test_ops_safety.py`. Các ca:
  - không đặt env ⇒ chặn prod bật (seed demo bị từ chối);
  - thiếu từng khóa ⇒ 503 nêu đúng tên, không lộ giá trị;
  - thân 300 KB (có `Content-Length` và dạng chunked) ⇒ 413;
  - thân 200 KB ⇒ qua.

  · Verify: như T004

## Giai đoạn 3: Thực thi đồng ý
- [ ] T006 [FR-005] Thêm kiểm `core_protection` vào `POST /v1/events` (và `/v1/heartbeat` nếu đã có route); thiếu
  `guardian_alerts` thì vẫn nhận sự kiện nhưng không xếp tin Zalo. Đệm 60 giây; `/v1/consents` xóa mục đệm khi ghi.
  · Verify: `$PYTEST tests/integration/test_consent_enforcement.py tests/integration/test_api_events.py`
- [ ] T007 [FR-005] Viết `backend/tests/integration/test_consent_enforcement.py`. Các ca:
  - rút đồng ý ⇒ 403 `consent_withdrawn`, không có dòng `risk_events`;
  - đồng ý lại ⇒ 200;
  - thiếu `guardian_alerts` ⇒ sự cố được mở nhưng 0 job `notify_guardian`;
  - mục đệm bị xóa khi ghi đồng ý mới.

  Sửa các test cũ chưa ghi đồng ý trước khi gửi sự kiện (ghi rõ số test đã sửa vào evidence).
  · Verify: như T006

## Giai đoạn 4: Hạn lưu
- [ ] T008 [FR-002] Viết `services/retention_service.py`:
  - `RETENTION` theo `DATA-MODEL.md` §6;
  - một hàm cho mỗi loại, nhận `now`;
  - xóa theo lô 1.000;
  - checkpoint qua `adelete_thread`;
  - `messages_out.text` làm rỗng sau 30 ngày;
  - `verifications`/`drills` chỉ xử lý nếu bảng tồn tại;
  - cờ `--dry-run`.

  Đăng ký job `retention` chạy hằng ngày (khóa `retention:<ngày>`), cộng lệnh `ops data retention [--dry-run]`.
  · Verify: `$PYTEST tests/integration/test_retention.py`
- [ ] T009 [FR-002] Viết `backend/tests/integration/test_retention.py`. Các ca:
  - với mỗi loại: dòng quá hạn 1 giây ⇒ xử lý, dòng còn hạn 1 giây ⇒ giữ;
  - `consents` không đổi;
  - chạy lần hai không đổi gì;
  - `--dry-run` không ghi;
  - checkpoint của sự cố đóng 8 ngày bị xóa, 6 ngày thì giữ;
  - `RETENTION` khớp bảng trong `DATA-MODEL.md` (đọc tệp markdown).

  · Verify: như T008

## Giai đoạn 5: Xóa theo yêu cầu
- [ ] T010 [FR-003] Viết `services/purge_service.py` theo thứ tự ở plan D1, job `purge_family` (lũy đẳng), và lệnh
  `ops data request-delete|status`.
  · Verify: `$PYTEST tests/integration/test_purge_family.py`
- [ ] T011 [FR-003] Viết `backend/tests/integration/test_purge_family.py`. Các ca:
  - dựng một gia đình đủ dữ liệu (ghép đôi, đồng ý, sự kiện, sự cố, đồ thị đã chạy với checkpoint, tin Zalo mock,
    token, xác minh/diễn tập nếu bảng có), cộng một gia đình đối chứng;
  - sau purge: duyệt `information_schema` lấy mọi bảng có `family_id`/`incident_id`, mỗi bảng 0 dòng của gia đình
    (trừ `consents`, `data_requests`, tombstone đã ẩn danh); checkpoint của các thread đã mất;
  - gia đình đối chứng nguyên vẹn;
  - JWT thiết bị và JWT người giám hộ cũ ⇒ 401;
  - chạy lại lần hai không lỗi.

  · Verify: như T010

## Giai đoạn 6: Sao lưu & khôi phục
- [ ] T012 [FR-004] Viết `ops/backup.py` (`backup`, `restore-check`, `rotate`) theo plan D3, `scripts/backup.sh` và
  biến `HOICON_BACKUP_KEY_<kid>` (sinh bằng `init_env`). Tên container và DB lấy từ cấu hình.
  · Verify: `$PYTEST tests/integration/test_backup_restore.py`
- [ ] T013 [FR-004] Viết `backend/tests/integration/test_backup_restore.py` (bỏ qua nếu không có Docker). Các ca:
  - backup ⇒ tệp không chứa chuỗi rõ đã biết (bí danh demo);
  - sửa 1 byte ⇒ giải mã báo lỗi;
  - cắt khối cuối ⇒ báo lỗi;
  - khóa sai ⇒ báo lỗi;
  - `restore-check` ⇒ `alembic_version` = head, số dòng khớp manifest, trigger ở chế độ `ALWAYS`; thời gian được in ra;
  - DB tạm bị xóa sau khi kiểm.

  · Verify: như T012

## Giai đoạn 7 (P2)
- [ ] T014 [FR-007] Thêm `ops devices revoke`, `ops threat_list unflag --h1-file` (không in h1) và lọc `is_demo` ở tra
  cứu khi prod. Viết test cho từng lệnh. Bổ sung thủ tục gỡ cờ vào `PRIVACY-DPIA.md`.
  · Verify: `$PYTEST tests/integration/test_threat_indicators.py tests/integration/test_api_devices.py`
- [ ] T015 [FR-008] Viết `infra/postgres/roles.sql` (role `hoicon_app`, chỉ INSERT/SELECT trên `consents` và
  `incident_transitions`). Viết `backend/tests/integration/test_db_roles.py`: tạo role trên DB dev, rồi kiểm `UPDATE`,
  `DELETE` và `ALTER TABLE … DISABLE TRIGGER` đều bị từ chối bởi quyền; dọn role sau test.
  · Verify: `$PYTEST tests/integration/test_db_roles.py`

## Giai đoạn 8: Rà soát & nghiệm thu
- [ ] T016 [FR-009] Chạy skill `privacy-audit` trên toàn repo và gửi `security-privacy-reviewer` toàn bộ codebase (không
  chỉ diff), gồm:
  - ma trận IDOR mọi route có `{id}`;
  - quét log của bộ test đầy đủ (`$PYTEST -o log_cli=true`) tìm số điện thoại, h1, token;
  - manifest Android.

  Sửa mọi Critical/High (thêm test cho từng bản sửa); ghi quyết định cho Medium.
  · Verify: báo cáo trong evidence: 0 Critical, 0 High chưa xử lý
- [ ] T017 [FR-010] Chạy đủ bộ lệnh kiểm:
  - `$PYTEST`; `ruff check` và `ruff format --check`;
  - `hoicon-eval --suite smoke --compare baseline`;
  - gitleaks **từng thư mục**: `backend/src`, `backend/tests`, `infra`, `scripts`, `specs/034-hardening-core`;
  - `python3 scripts/check-spec-trace.py`.

  Cập nhật `DATA-MODEL.md` §6, `PRIVACY-DPIA.md`, `docs/setup/BACKUP.md` (mới), `API.md`. Điền `evidence.md`. Đặt ROADMAP
  `P2-20` ◐, ghi phần BLOCKED bởi 012.
  · Verify: mọi lệnh xanh; `python3 scripts/check-spec-trace.py` ⇒ 0 lỗi
