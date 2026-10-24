# Evidence Spec 037: Gia cố phần còn lại (làn B, 23/10/2026)

> Đã đối soát 24/10/2026 (kiến trúc sư). Số đo ở máy dev (Postgres dev, cassette `synthetic`).

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

## Wave 6 — T013, T014 (làn B, 24/10/2026)

- **T014 ĐẠT**: trước đây chỉ có `restore-check` (vào DB tạm, luôn xóa) — chưa có lệnh khôi phục thật nên chữ "DB đích" của task chưa có nghĩa. Thêm `ops.backup restore --to <CSDL rỗng> [--file]` (`run_restore`): CSDL đích phải có sẵn, rỗng, không phải CSDL đang chạy / hệ thống / DB kiểm tra; `pg_restore --single-transaction --exit-on-error`; `BackupError` giữa dòng giải mã ⇒ giết tiến trình (giao dịch chưa commit bị hủy) ⇒ đích không đổi; xong thì kiểm `alembic_version` + số dòng theo manifest. Phần đẩy `pg_restore` dùng chung với `restore-check` (`_pg_restore`).
  Test (`-k atomic`, 3): bản tốt ⇒ đích khớp manifest; sửa 1 byte ở khối giữa (đã chỉnh sha manifest để lỗi nằm ở AES-GCM) ⇒ `BackupError`, số dòng mọi bảng đích trước = sau (không bảng nào); từ chối CSDL đang chạy và đích không rỗng. **Đột biến**: bỏ `--single-transaction` ⇒ test khối giữa ĐỎ (đích còn bảng dở) ⇒ test thật sự đo tính nguyên tử. `test_backup_restore.py` + `test_backup_subkeys.py` **36 + 6 passed** (dùng Docker `hoicon-db`, DB đích tạm `hoicon_restore_atomic_test` luôn xóa). Chưa cập nhật `docs/setup/BACKUP.md` (cấm `docs/**`): thêm mục "Khôi phục thật" cho người có quyền docs.
- **T013 CHƯA TICK — BLOCKED bởi lệch hợp đồng** (cần quyết định, không tự sửa `docs/schemas`): `tests/contract/test_error_schema.py` (10 passed): fixture valid/invalid, enum `purpose` == mục đích trong `docs/legal/consent/manifest.json` (task ghi nhầm đường dẫn `backend/src/hoicon/consent_texts/manifest.json`), mã `consent_withdrawn` của `routers/events.py`/`devices.py` ∈ enum `error`. **Thân phản hồi thật KHÔNG khớp `error.v1.json`**: 403 thật = `{"detail": "consent_withdrawn"}` (Android `OutboxSender`/`PairingApiClient` và 3 test ghim dạng này; thêm `test_heartbeat`), 422 `/v1/consents` = `{"detail": "<câu tiếng Việt>"}`; lược đồ yêu cầu `{"error": ..., "purpose": ...}` với `additionalProperties:false`, chưa nơi nào gửi `error`/`purpose`. Test thân thật là `xfail(strict)` ở `tests/integration/test_error_body_contract.py` (flip khi sửa).
  Hai lựa chọn cho Opus/Tiến: (a) sửa `error.v1.json` mô tả đúng thân thật (`detail` là mã hoặc câu), hoặc (b) server gửi cả `{"detail": "consent_withdrawn", "error": "consent_withdrawn", "purpose": "core_protection"}` (không gãy Android) + đổi lược đồ cho phép `detail`. Khuyến nghị (b) tối thiểu hoặc (a) nếu không muốn đụng server.

## Wave 6 — T009 rà soát bảo mật cuối (làn B, 24/10/2026)

- **Quét phụ thuộc**: `osv-scanner` (1.9.2; không đọc được `uv.lock` trực tiếp ⇒ `uv export --no-hashes` ra `requirements.txt` tạm rồi quét, 84 gói) tìm **certifi 2026.7.22 — PYSEC-2026-4320 / GHSA-6q48-6c7w-9gw2, CVSS 9.1** (gốc emSign bị lộ khóa trung gian; sửa từ 2026.10.19) ⇒ **ĐÃ SỬA**: `uv lock --upgrade-package certifi` ⇒ 2026.10.23 (commit 5503698, chỉ đổi 3 dòng `uv.lock`). `pnpm-lock.yaml` (15 gói): osv-scanner "No issues found"; `pnpm audit --prod`: không có lỗ hổng đã biết. Lưu ý: osv-scanner gọi API osv.dev (gửi danh sách tên gói + phiên bản công khai).
- **`security-privacy-reviewer`** (đọc `git diff main...HEAD`, chưa chạy lại test): **0 Critical, 0 High, 4 Medium, 6 Low**.
  Medium **#1 ĐÃ SỬA**: trả lời "3" trên Zalo gửi lại chi tiết sự cố không qua điều kiện đồng ý lúc gửi (FR-002) ⇒ `channels/updates.py` nay kiểm `guardian_alerts` của người cao tuổi (sự cố demo miễn); đã rút ⇒ chỉ báo chung `incident_closed`. Test đỏ trước (`test_3_on_a_real_incident_needs_guardian_alerts_consent_at_reply_time[False]`) → xanh; `test_guardian_reply` + `test_review_hardening` + `test_consent_enforcement` 49 passed.
  Medium còn lại (chủ + ngày, theo yêu cầu T009):
  - **#2** prod chạy role chủ bảng, chưa áp `roles.sql` (`infra/compose.prod.yml`) — chủ **Tiến**, làm cùng 012 T013 khi có VPS (012 T010); đã thử được ở 012 T017/T020. Hạn đề xuất: trước khi cho gia đình thí điểm cài app (≤ 08/11/2026 nếu VPS kịp).
  - **#3** `HOICON_CONSENT_STRICT` không được `compose.prod.yml` chuyển vào container, trong khi cả 10 mục đích trong manifest đang `draft` ⇒ ở prod mọi lần CẤP đồng ý bị 422 (đóng mặc định, đúng) — chủ **Minh** (duyệt văn bản, 011 T010); nếu cần tắt tạm: thêm biến vào compose (**Tiến**). Hạn đề xuất: trước thí điểm. KHÔNG sửa `env.prod.example` cho sai sự thật.
  - **#4** (nghi vấn pháp lý) người giám hộ ghép qua Zalo lưu `zalo_user_hmac`/`zalo_chat_enc` nhưng không có bản ghi `consents` cho người giám hộ (enum `Purpose` và kênh chỉ dành cho thiết bị người cao tuổi) — chủ **Minh/Opus** (quyết định phạm vi + `consent-copy`, luật 7). Hạn đề xuất: trước thí điểm (G2).
  Low: **#10 ĐÃ SỬA** (`next.config.ts` thêm `privateHeaders` cho `/a/:path*`). Chưa sửa: #5 (thân `POST .../decision` sau rút — chờ Minh, §8 mục 14), #6 (`/v1/lookups` guardian chưa kiểm `web_readable`), #7 (`elder.py` chưa khóa theo `member_id`), #8 (`get_action_view_data` chưa kiểm scope), #9 (JWT người giám hộ 7 ngày, `DELETE /session` không thu hồi phía máy chủ) — chủ **Tiến**, hạn đề xuất 08/11/2026 (G1), ghi vào ROADMAP "Ghi chú".
  Ghi nhận thêm của reviewer: (a) `ops restore` chưa kiểm `REQUIRED_TRIGGERS` ở chế độ ALWAYS như `restore-check` (sửa nhỏ, chủ Tiến); (b) bản sao lưu cũ làm sống lại dữ liệu đã xóa nếu không phát lại `purge_family` sau khôi phục (nghi vấn quy trình; cần ghi vào `docs/setup/BACKUP.md`, chủ Opus/Tiến). Android (`apps/android`) ngoài phạm vi lượt này.
- **Không còn Critical/High chưa xử lý.**

## Wave 6 — T010/T016 bộ kiểm đầy đủ (làn B, 24/10/2026)

- **ĐẠT**: pytest **2881 passed, 22 skipped, 1 xfailed** (API 18010 tắt); `ruff check` + `format --check` sạch; `hoicon-eval` smoke `--compare baseline` / full `--compare baseline-full` / injection: recall 100%, báo nhầm 0%, vi phạm 0, không lệch (Postgres tạm cổng 15434); `check-spec-trace` 25 spec 0 lỗi; `alembic heads` = `0012` (1 head); gitleaks từng thư mục sạch (`docs`, `docs/schemas`: 1 dương tính giả đã biết).
- SC-001: `test_consent_manifest_enforcement.py` xanh · SC-002: test đếm lời gọi Zalo giả xanh, thêm đường "3" (T009 #1) · SC-003: ma trận IDOR xanh · SC-004: `test_privacy_report.py` xanh (có đột biến) · SC-005: 0 Critical/0 High, Medium có chủ+ngày (T009) · SC-006: BLOCKED (Firebase) — chưa đo.

## T013 gỡ chặn (nhà điều phối, 24/10/2026)

- Chọn phương án (a): **hợp đồng theo thân thật**. `error.v1.json` nay là `{"detail": <mã máy `consent_withdrawn` | câu tiếng Việt>}`,
  bỏ `error`/`purpose` (lược đồ 23/10 do kiến trúc sư viết theo giả định, chưa đối chiếu mã; máy chủ và Android đã dùng `detail` từ spec 034).
  Không đổi server, không đổi Android. Fixture: 2 valid, 5 invalid (gồm dạng cũ `error/purpose` ⇒ bị từ chối).
- `tests/contract/test_error_schema.py`: bỏ test enum `purpose`; mã của `events`/`devices` ∈ `$defs.code`; câu `consents.UNKNOWN_TEXT` hợp lệ.
  `tests/integration/test_error_body_contract.py`: gỡ `xfail` ⇒ **PASSED** (403 thật của `POST /v1/events` khớp lược đồ).
- Verify: `uv run --directory backend pytest tests/contract tests/integration/test_error_body_contract.py -q` ⇒ 307 passed; ruff sạch.

## Lượt 7 — T017 (làn B, 24/10/2026)

- **T017 ĐẠT**: Low #6 `/v1/lookups` phía người giám hộ: sự cố của người cao tuổi chưa/đã rút `guardian_alerts` ⇒ cùng 404 (demo miễn; máy của chính người đó vẫn được); #7 `elder.py` `_own_incident` khóa thêm `member_id` (nhà nhiều người cao tuổi); #8 `get_action_view_data` chỉ nhận scope `incident_decision`. 3 test đỏ trước (`test_api_lookups`, `test_api_elder`, `test_action_token_service`) → xanh; `-k "action or elder or lookups or idor or token"` 162 passed; ruff sạch. (Ma trận IDOR không cần thêm ô: ba tuyến đã có, đổi là về quy tắc theo thành viên/đồng ý.)

## Lượt 7 — T018 (làn B, 24/10/2026)

- **T018 ĐẠT**: migration `0013` bảng `revoked_sessions(jti, expires_at)` (không PII); JWT người giám hộ nay mang `jti` (uuid4 hex); `DELETE /v1/guardian/session` (cookie hoặc Bearer) ghi `jti` thu hồi tới khi hết hạn rồi xóa cookie — không có token hợp lệ vẫn 204; `get_current_guardian` từ chối `jti` đã thu hồi (token phát trước thay đổi không có `jti` ⇒ không thu hồi riêng được, hết hạn tự nhiên ≤ 7 ngày). Job `retention` xóa dòng quá hạn (`purge_revoked_sessions`, ngoài `RETENTION` vì §6 là dữ liệu thật); `privacy_report` có dòng cho bảng mới.
  Test (`test_guardian_session.py`, 40 passed): token đã đăng xuất ⇒ 401 dù giữ bản sao; đăng xuất phiên này không giết phiên kia của cùng người; đăng xuất không token vẫn 204; retention chỉ xóa dòng quá hạn. Đột biến: bỏ kiểm `revoked` ⇒ 2 test đỏ. Lần "đỏ trước" đầu vô nghĩa (gọi nhầm `GET /session` ⇒ 405) nên đã sửa sang `/v1/guardian/me` rồi kiểm lại bằng đột biến. `-k "guardian_session or retention or privacy or schema or purge or idor"` 282 passed. Client TS sinh lại, typecheck sạch.
- Dev DB đã áp `0013` (cần áp ở prod trước khi triển khai; `roles.sql` có `ALTER DEFAULT PRIVILEGES` nên role app tự có quyền bảng mới). `docs/DATA-MODEL.md` §6 chưa có bảng này (ngoài quyền): thêm dòng "revoked_sessions — tới khi token hết hạn".

## Lượt 7 — T019 (làn B, 24/10/2026)

- **T019 ĐẠT**: `ops.backup restore` kiểm `REQUIRED_TRIGGERS` ở chế độ ALWAYS trên DB đích (hàm dùng chung `trigger_problems` với `restore-check`); thiếu ⇒ `BackupError` nêu tên trigger. Sau khôi phục, báo cáo có `deletions_since_backup` = id gia đình có `data_requests` `done` hoàn tất SAU `manifest.created_at` (đọc DB đang chạy; id không phải PII) và CLI in cảnh báo kèm lệnh `request-delete --family <id> --now`; không có ⇒ in dòng "không có yêu cầu xóa nào". Lệnh CLI chỉ in, không tự xóa (quyết định của con người).
  Test đỏ trước (3 đỏ) → `test_backup_restore.py` **39 passed** (Docker): `trigger_problems` (thiếu/không ALWAYS), `run_restore` trả `triggers_always` đủ + danh sách xóa, `deletions_since` tìm đúng theo thời điểm hoàn tất. Ruff sạch.

## Lượt 7 — T020 (làn B, 24/10/2026)

- **T020 ĐẠT**: `infra/compose.prod.yml` chuyển `HOICON_CONSENT_STRICT: ${HOICON_CONSENT_STRICT:-true}` vào backend (không đặt biến ⇒ `true`, đúng hành vi cũ vì ngoài dev mã đã bật mặc định); đặt `false` trong tệp biến prod ⇒ container nhận `false` (chú thích trong `env.prod.example` cập nhật cho đúng sự thật). Test đỏ trước (2 test mới ở `scripts/tests/test_deploy_vps.py::ComposeInvariants`) → `unittest test_deploy_vps` 33 OK; `pytest -k "compose or prod_config or production_compose"` 3 passed. Chưa có văn bản `approved` (011 T010) nên ở prod mọi lần CẤP đồng ý vẫn bị 422 cho tới khi Minh duyệt hoặc đặt `false` có chủ đích.

## Lượt 7 — T021: tài liệu (037 T012, T015; 033 T018 một phần) (làn B, 24/10/2026)

- **037 T012 ĐẠT**: `docs/PRIVACY-DPIA.md` thêm mục "Đồng ý lúc gửi, độ trễ đệm và liên kết cũ" (điều kiện lúc gửi kể cả trả lời "3" trên Zalo; đệm đồng ý ≤ 60 giây khi đổi ngoài `/v1/consents`; chính sách link cũ D2 theo hành vi THẬT: đọc ⇒ 404, quyết định vẫn ghi và vẫn trả `state`/`outcome`; đăng xuất thu hồi `jti`) và mục "Bảng dữ liệu ↔ mục đích ↔ hạn lưu" (bản chụp 21 bảng từ `privacy_report`, lệnh sinh lại; 0 bảng chưa ánh xạ). `docs/setup/BACKUP.md`: định dạng v2 (HKDF theo tệp, v1 vẫn đọc được), lệnh `restore`, quy trình khôi phục thật gồm phát lại yêu cầu xóa.
- **037 T015 ĐẠT**: `docs/setup/STABILITY.md` — đọc Android vitals ở Play Console, ngưỡng hành vi xấu (tổng 1,09% sự cố / 0,47% ANR, 8% theo kiểu máy; **ghi rõ là số tại thời điểm viết, kiểm lại trước khi dùng**), điều kiện cỡ mẫu, mẫu dòng ghi vào báo cáo thí điểm. SC-006 vẫn BLOCKED (Play Console).
- **033 T018 CHƯA TICK (làm 1/3)**: `docs/setup/SIM.md` đã cập nhật và **chạy thử từ DB trống** (Postgres tạm 15435): migration → head 0013; API với `HOICON_SIM_ENABLED=true`: `/healthz` 200, `/readyz` 200; `guardian_link --seed` in liên kết; đổi token lấy phiên 200; `/v1/sim/scenarios` 110 kịch bản có `title_vi`; `POST /v1/sim/runs` `llm: replay` ⇒ `replay`, có câu hỏi, `is_demo: true`. Chưa làm: `specs/033-web-sim-eval/quickstart.md` (ngoài danh sách tệp làn B được ghi) và `docs/DESIGN-SYSTEM.md` mục 3 trang web (ngoài quyền) — kịch bản quay video 1280×720 đã đặt tạm trong `SIM.md`; cần chuyển sang `quickstart.md` + DESIGN-SYSTEM.
- Ghi nhận: `docs/DATA-MODEL.md` §6 vẫn chưa có dòng `revoked_sessions` và thiết bị `sim:` 24 giờ (ngoài quyền lượt này).

## Lượt 7 — bộ kiểm cuối (làn B, 24/10/2026)

- pytest **2892 passed, 22 skipped, 0 xfail** (xfail của T013 đã được điều phối gỡ); `ruff check` + `format --check` sạch; `check-spec-trace` 25 spec 0 lỗi; `unittest scripts/tests` 116 OK (7 skipped); web e2e **124 passed**; gitleaks `docs/setup` sạch. Migration mới `0013` (đã áp dev; áp prod cùng 012 T013).
- **T021 tick (nhà điều phối 25/10/2026)**: PRIVACY-DPIA/BACKUP/STABILITY (e28e63b, lượt 7 làn B) + SIM.md/quickstart/DESIGN-SYSTEM (033 T018, d5f1b29) đều đã có.
