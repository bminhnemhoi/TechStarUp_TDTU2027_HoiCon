# Bằng chứng nghiệm thu Spec 034: Gia cố lõi trước người dùng thật

- **Trạng thái**: phần lõi (T001–T017) đã làm và kiểm trên máy dev ngày 16/10/2026; review bảo mật T016 xem mục cuối.
  Chưa commit.
- **BLOCKED một phần bởi 012** (chưa có spec): lịch chạy sao lưu trên VPS, nơi lưu ngoài máy, áp role DB ở prod, đo khôi phục
  trên VPS, cảnh báo khi sao lưu thất bại.
- **Môi trường**: Linux CachyOS, Postgres dev trong Docker (container `hoicon-db`, cổng 15432), `HOICON_ENV=test` cho bộ test.
- **Nguồn số**: máy dev; thời gian khôi phục đo trên dữ liệu dev (23 bảng, ≈184 nghìn dòng, bản mã ≈8 MB), không đại diện cho prod.
  Chưa chạy: CI trên PR, Windows, máy chủ thật.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 hạn lưu | 100% dòng quá hạn được xử lý; 0 dòng trong hạn bị đụng; `consents` nguyên; lũy đẳng; lô ≤ 1.000 | `test_retention.py` (20 test) | Mỗi loại ở biên ±1 giây (`risk_events` 90 ngày, nội dung `agent_steps` 30 ngày, sự cố đóng 12 tháng kèm nhật ký/xác minh/token/`agent_runs`, `jobs` 30 ngày sau `done_at`, `action_tokens` 30 ngày sau hết hạn, `verifications` 90 ngày, `drills` 12 tháng, checkpoint sự cố đóng 8 ngày bị xóa còn 6 ngày giữ); job chưa xong không bị xóa; chạy lần 2 = 0; `--dry-run` không ghi; lô chia đúng cỡ; `RETENTION` khớp bảng DATA-MODEL §6; log chỉ có số dòng | ĐẠT |
| SC-002 xóa theo yêu cầu | 0 dòng nhận diện trong mọi bảng có `family_id`/`incident_id` + checkpoint; `consents` nguyên; tombstone ẩn danh; JWT cũ ⇒ 401 | `test_purge_family.py` (14 test) | Duyệt `information_schema` (mọi bảng có `family_id`/`incident_id`/`member_id`/`thread_id`) ⇒ 0 dòng ngoài `consents`, `data_requests`, tombstone; đồ thị thật đã chạy (checkpoint + `agent_runs` + `agent_steps` + job) bị xóa sạch; sổ đồng ý giữ nguyên từng dòng; `members`/`families` đã ẩn danh; gia đình đối chứng nguyên vẹn; token thiết bị và người giám hộ cũ ⇒ 401, của gia đình đối chứng vẫn 200; lỗi giữa chừng ⇒ `failed` + thử lại ⇒ `done`; chạy 2 lần không lỗi; worker thi hành job | ĐẠT |
| SC-003 sao lưu & khôi phục | bản mã không đọc được khi thiếu khóa; sửa/cắt ⇒ lỗi; khôi phục khớp manifest + trigger `ALWAYS`; có thời gian | `test_backup_restore.py` (33 test) + chạy thật `ops.backup` | Bản mã không chứa chuỗi rõ nào; sửa 1 byte ở mọi vị trí, cắt khối cuối, đảo/nhân đôi khối, thêm đuôi, sai khóa ⇒ `BackupError`; `restore-check`: `alembic_version` = head `0009`, 23 bảng và 183.968 dòng khớp manifest, 4 trigger bất biến ở `ALWAYS`, DB tạm đã xóa (kể cả khi lỗi). **Đo trên máy dev: khôi phục ≈ 3 giây (3,05 s / 3,09 s tổng)** | ĐẠT (số đo máy dev; VPS BLOCKED bởi 012) |
| SC-004 đồng ý ở máy chủ | rút `core_protection` ⇒ 403, không ghi; thiếu `guardian_alerts` ⇒ không gửi Zalo | `test_consent_enforcement.py` (17 test) | Chưa đồng ý/đã rút ⇒ 403 `consent_withdrawn`, 0 dòng `risk_events`/`incidents`; đồng ý lại ⇒ 200; mục đích khác không thay thế được; thiếu `guardian_alerts` ⇒ mở sự cố nhưng 0 job `notify_guardian` (cả cảnh báo nhanh lẫn đồ thị); đệm 60 giây theo người, `/v1/consents` xóa đệm ngay | ĐẠT |
| SC-005 mặc định an toàn | không đặt env ⇒ prod; `/readyz` báo khóa thiếu; thân > 256 KB ⇒ 413 | `test_ops_safety.py` (24 test) | `Settings.env` mặc định `prod`; ở `prod`: seed demo bị từ chối, Zalo mock bị từ chối, kịch bản diễn tập chưa duyệt bị đóng; `/readyz` 503 nêu đúng tên từng khóa thiếu (kể cả theo `kid` hiện hành), không lộ giá trị; 300 KB (có `Content-Length`, chunked, và khai gian `Content-Length`) ⇒ 413, 200 KB và đúng 256 KiB lọt, 256 KiB + 1 ⇒ 413 | ĐẠT |
| SC-006 review bảo mật | 0 Critical, 0 High chưa xử lý trên toàn codebase | `privacy-audit` + `security-privacy-reviewer` (T016) | 0 Critical, 1 High (đã sửa + test), 7 Medium (3 đã sửa, 4 ghi quyết định), 9 Low (4 đã sửa) | ĐẠT (còn Medium ghi dưới) |

Kiểm phụ (FR-007/FR-008): `test_ops_hardening.py` (17 test: `ops devices revoke`, `threat_list unflag`, tra cứu đe dọa ở prod bỏ số
hư cấu), `test_db_roles.py` (21 test, DB dev thật: `hoicon_app` bị từ chối `UPDATE`/`DELETE`/`TRUNCATE` trên `consents` và
`incident_transitions` bằng **quyền** (42501), không tắt/xóa được trigger, không DDL, không sở hữu bảng; ứng dụng vẫn chạy trên
các bảng thường; xóa dây chuyền sự cố vẫn qua), `test_schema_0009.py` (21 test).

## Số test của các test cũ đã phải đổi (T007)
Đồng ý nay được thực thi nên mọi test gửi sự kiện cần thiết bị đã đồng ý. Sửa **tập trung** thay vì từng test: `pair_device`
(`consent_support.py`) mặc định ghi `core_protection` + `guardian_alerts` qua `POST /v1/consents` thật như app làm sau khi ghép đôi
(⇒ toàn bộ test `test_api_events/incidents/elder/drills/lookups/…` giữ nguyên nội dung). Phải thêm `consent=False` ở
`test_api_consents.py` (17 lời gọi) và `test_api_devices.py` (6 lời gọi) vì các test đó khẳng định "thiết bị mới chưa có đồng ý".
Đổi mặc định `prod` làm 7 test của hai lệnh dev-only đỏ (`ops/pairing_code.py`, `ops/zalo_simulate.py` so sánh cứng `== "dev"`):
nay dùng `is_dev_env` (dev/test/ci; `prod` vẫn bị từ chối); 2 test `/readyz` cũ (`test_db.py`, `test_review_hardening.py`) thêm
fixture `service_keys` vì `/readyz` nay đòi đủ khóa.

## Lệnh đã chạy (16/10/2026)

| Lệnh | Kết quả |
|---|---|
| `alembic upgrade head && downgrade -1 && upgrade head` | 0008 → 0009 → 0008 → 0009, `alembic current` = `0009 (head)` (`alembic check` chỉ báo bảng checkpoint của LangGraph, có từ trước) |
| `uv run --directory backend pytest` | **1950 passed** (toàn bộ; ngày 16/10 trước khi thêm 3 test `init_env` = 1953) |
| `uv run --directory backend ruff check .` / `ruff format --check` | sạch / 191 file đúng định dạng |
| `hoicon-eval --suite smoke --compare baseline --shared-db-ok` (`HOICON_ENV=test`) | 20/20 ca đạt, recall 100%, báo nhầm 0%, vi phạm 0, công khai AI 100%, lệch baseline +0,0 điểm |
| `gitleaks` (từng thư mục: `backend/src`, `backend/tests`, `infra`, `scripts`, `specs/034-hardening-core`; cấu hình `.gitleaks.toml`) | 0 rò rỉ ở cả 5 |
| `python3 scripts/check-spec-trace.py` | 17 spec, 0 lỗi |
| `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck` | client TS đồng bộ (đổi kiểu thân `/readyz`), typecheck sạch |
| Quét log của bộ test đầy đủ (`pytest -o log_cli=true --log-cli-level=DEBUG`, 475 KB) | 0 số điện thoại thô (khớp duy nhất là mảnh UUID và tên test dùng số hư cấu `0900000xxx`), 0 JWT/`Bearer`, 0 h1 thật (chỉ chuỗi `abab…`/`aaaa…` trong tham số test) |
| Đột biến: 24 đột biến vào purge/hạn lưu/đồng ý/giới hạn thân/`/readyz`/mặc định env | 21 bị test bắt ngay; 3 sống sót (bỏ xóa job `zalo_update`, bỏ xóa `agent_runs` theo `thread_id`, bỏ cổng `guardian_alerts` ở cảnh báo nhanh) → siết test (có người giám hộ thật, `AgentRun` để `incident_id` NULL như đồ thị thật, job `zalo_update` mồ côi) → 3/3 bị bắt |

## Quyết định cần Tiến/Minh biết
1. **Thân 403**: làm theo lệnh giao: `{"detail": "consent_withdrawn"}` (chuỗi). Plan §5 từng ghi dạng lồng `{"detail": {"code": "consent_withdrawn"}}`
   cho Android 029. Chốt một dạng trước khi sửa `PairingApiClient`/`ElderApiClient`; đổi ở một chỗ (`events.CONSENT_WITHDRAWN`).
2. **`HOICON_ENV` mặc định `prod`**: cấu hình cục bộ cũ không có dòng này sẽ chạy ở `prod` (Zalo mock bị từ chối khi khởi động worker,
   cookie `Secure`, seed demo bị chặn). `init_env` KHÔNG tự nối `dev` vào tệp có sẵn (lỡ chạy ở máy chủ thật sẽ tắt chặn) mà in
   cảnh báo; máy dev cần thêm `HOICON_ENV=dev`.
3. **`init_env` nay sinh thêm** `HOICON_DEVICE_JWT_SECRET` (vì `/readyz` đòi) và `HOICON_BACKUP_KEY_KID`/`HOICON_BACKUP_KEY_1`
   (khóa sao lưu riêng). Cấu hình cũ chạy lại `init_env` sẽ được nối các khóa này.
4. **Bản sao lưu cũ còn dữ liệu của gia đình đã yêu cầu xóa** tới khi xoay vòng đẩy đi (≈ 4 tuần). Ghi trong DPIA/BACKUP.md; cần nêu
   trong văn bản đồng ý khi thí điểm.
5. **`hoicon_app` ở prod**: `IncidentRuntime.open` gọi `AsyncPostgresSaver.setup()` (DDL) nên cần chạy `setup()` bằng role chủ trước
   khi chuyển ứng dụng sang `hoicon_app` (012).
6. `messages_out` **không có cột `text`** (lệnh giao nói "làm rỗng text sau 30 ngày"): toàn văn tin nằm ở `jobs.payload` và bị xóa cùng
   `jobs`; dòng `messages_out` giữ để đếm hạn mức. Đã ghi trong DATA-MODEL §6 và test.
7. `agent_runs.incident_id` của đồ thị thật là NULL (khóa là `thread_id` = id sự cố) nên purge và hạn lưu xóa theo `thread_id`.
8. Chưa có route `/v1/heartbeat`; `POST /v1/incidents/{id}/answers` (câu trả lời E8 của người cao tuổi) chưa qua cổng đồng ý.

## Review bảo mật (T016)
`security-privacy-reviewer` đọc toàn codebase (không chỉ diff) + ma trận IDOR mọi route có `{id}`: **0 Critical · 1 High · 7 Medium · 9 Low**.
Reviewer chỉ đọc mã (không chạy pytest/DB/AVD). Sau các sửa dưới đây chạy lại: pytest **1958 passed**, ruff check + format sạch, gitleaks
5 thư mục 0 rò rỉ, spec-trace 0 lỗi. **Chưa có reviewer nào đọc lại các bản sửa.**

**Đã sửa (có test):**
- **High #1** — prod quên `HOICON_ZALO_MODE=live`: worker chết im lặng (cảnh báo/xóa dữ liệu/hạn lưu đứng) mà `/readyz` vẫn 200.
  Nay `_worker_loop` log `error` khi không dựng được kênh gửi và `/readyz` trả 503 `{"misconfigured": ["zalo_mode"]}`
  (`mock_allowed` dùng chung với `build_zalo_client`). Test: `test_readyz_fails_when_prod_would_run_the_mock_zalo_channel`,
  `test_the_worker_loop_logs_loudly_instead_of_dying_silently`.
- **Medium #3** — race của `purge_family`: bước 1 nay đặt luôn `deleted_at` cho gia đình + thành viên (token người giám hộ hết hiệu lực
  ngay, trước khi xóa gì); checkpoint được quét lần hai sau khi job đã bị xóa. Test: `test_guardian_tokens_are_closed_before_anything_is_deleted`,
  `test_checkpoints_are_swept_again_once_the_jobs_are_gone`.
- **Low #10** — purge xóa `messages_out` làm hạn mức Zalo 3.000 tin/tháng đếm thiếu: nay giữ dòng, chỉ cắt `family_id/incident_id/member_id/job_key`.
  Test: `test_the_zalo_quota_counter_survives_but_every_link_to_the_family_is_cut`.
- **Low #11** — lỗi `pg_dump/pg_restore/psql` không còn in đuôi stderr (có thể kèm nội dung hàng); chỉ in mã thoát.
- **Low #13** — `backup_dir()` chỉ `chmod 700` thư mục do chính nó tạo; thư mục có sẵn thì chỉ cảnh báo.
- **Low #16** — `hoicon_app` không còn `DELETE/TRUNCATE` trên `data_requests` (vết pháp lý). `test_db_roles.py` vẫn xanh.

**Medium chưa sửa — quyết định / việc kế tiếp (ghi ở ROADMAP):**
- **#2** `init_env` giữ `HOICON_ENV=dev` từ `.env.example`: đúng theo yêu cầu spec (đặt tường minh) và `init_env` là công cụ dev; ops dựng VPS phải
  tự đặt `HOICON_ENV=prod` (012 sẽ cấp `.env` riêng). Không đổi.
- **#4** rút `guardian_alerts` giữa chừng không tác động sự cố đang mở (cờ đóng băng trong state đồ thị; `send_to_guardian` và tin tổng kết
  diễn tập không kiểm đồng ý lúc gửi). Cần đưa `consent_gate` vào `send_to_guardian` (payload cần `protected_member_id`) — làm ở spec sau.
- **#5** Android gộp `403 consent_withdrawn` thành "cần ghép đôi lại" và thử lại vô hạn — việc của spec 029 (Android), chốt dạng thân 403 trước.
- **#6** sao lưu cũ làm sống lại dữ liệu đã xóa: cần "sổ xóa" ngoài DB + chạy lại `purge_family` sau mỗi restore (012; đã nêu ở BACKUP.md/DPIA).
- **#7** server chưa ép `consent_version/text_sha256` thuộc danh sách văn bản đã duyệt — gắn với spec văn bản đồng ý (037).
- **#8** (nghi vấn, chưa đo) `hoicon_app` có thể không chạy được `AsyncPostgresSaver.setup()` (DDL), thiếu `ALTER DEFAULT PRIVILEGES` và URL admin riêng cho
  backup — kiểm khi chuyển ứng dụng sang `hoicon_app` ở 012.
- **Low còn lại** (#9 giới hạn tần suất `/v1/consents`, #12 nonce 32 bit của sao lưu — nên dẫn xuất khóa phụ theo tệp, #14 `exc_info` trong
  `queue.py` có thể kèm tham số SQL, #15 fixture dùng `0912345678`, #17 mục đích `llm_processing` chưa thu/kiểm): ghi ở ROADMAP.

**Route chưa có test IDOR đầy đủ** (reviewer): `POST /v1/lookups` với người giám hộ + `incident_id` nhà khác; token chéo audience trên các route
ngoài `runs`; mọi route với token cũ của gia đình đã purge (đã có `test_old_device_and_guardian_tokens_are_refused_afterwards` cho `devices/me` và `guardian/me`).
