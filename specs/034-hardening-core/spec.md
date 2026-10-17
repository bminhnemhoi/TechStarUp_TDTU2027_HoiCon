# Spec 034: Gia cố lõi trước khi có người dùng thật (hạn lưu, xóa dữ liệu, sao lưu, bảo mật)

**Mã ROADMAP**: `P2-20` (phần lõi; phần còn lại là `037-hardening-rest`) · **Làn**: B (`backend/**`, `infra/**`,
`scripts/**`) · **Cột mốc**: Gate M2 ("0 lỗi bảo mật High") · **Phụ thuộc**: `012-release-and-hosting` (**chưa có
spec**, ☐) cho phần chạy theo lịch trên VPS và nơi lưu bản sao ngoài máy; mọi phần khác chạy được trên máy dev
· **Nhánh**: `feat/034-hardening-core` · **Luật**: Luật BVDLCN 91/2025/QH15, Nghị định 356/2025 (lưu bằng chứng đồng ý),
CLAUDE.md luật 1, 7 và 9

---

## 1. Bối cảnh

MASTER-PLAN đặt 034 **trước** khi có người thật (029 phụ thuộc 034). Hiện trạng đã đọc ngày 16/10/2026:

| Thành phần | Hiện trạng | Rủi ro |
|---|---|---|
| Hạn lưu (`DATA-MODEL.md` §6) | Đã quy định: `risk_events` 90 ngày; nội dung `agent_steps` 30 ngày; sự cố 12 tháng; checkpoint = sự cố đóng + 7 ngày; `jobs` 30 ngày sau `done_at`. **Chưa có job nào thực thi** | Dữ liệu giữ quá mục đích; `jobs.payload.text` giữ toàn văn tin gửi người giám hộ vô thời hạn |
| Xóa dữ liệu theo yêu cầu (US-09) | Không có hàm, không có bảng `data_requests`. `consents` → `families`/`members` là `ON DELETE RESTRICT` (020) | **Không xóa được gia đình**: luật đòi xóa theo yêu cầu, nhưng sổ đồng ý phải giữ |
| Sao lưu | Không có gì. Máy dev không có `psql`/`pg_dump`, chỉ có container Postgres | Mất dữ liệu thí điểm; chưa từng thử khôi phục |
| `HOICON_ENV` | Mặc định `"dev"` (`config.py:20`) | Quên đặt biến ở prod ⇒ các chặn "chỉ prod" (seed demo, kịch bản chưa duyệt…) bị tắt (mục còn mở của 003) |
| Rút đồng ý | Android có cổng `mayShareWithFamily`; máy chủ **không kiểm** đồng ý khi nhận sự kiện (mục #6 của 021) | Thiết bị cũ hoặc bị sửa vẫn gửi được sau khi rút đồng ý |
| Sổ đồng ý & nhật ký chuyển | Trigger chặn UPDATE/DELETE, nhưng chủ bảng/superuser tắt được trigger; app đang chạy bằng role chủ bảng (mục #5 của 020, L1 của 021) | Một lỗi SQL injection hoặc thao tác nhầm có thể sửa bằng chứng |
| Mục treo từ 003 | Chỉ mục `agent_steps(at)`; `/readyz` không báo thiếu pepper/khóa; tra cứu prod chưa lọc `is_demo`; chưa có lệnh gỡ số bị gắn cờ nhầm | Lỗi âm thầm, danh sách sai không sửa được |
| Thân yêu cầu | Không giới hạn ở tầng ứng dụng (021 dựa vào Caddy, mà 012 chưa có) | Từ chối dịch vụ bằng thân rất lớn |
| Thu hồi thiết bị | Có cột `devices.revoked_at`, chưa có lệnh/route thu hồi (mục #9 của 020) | Máy mất/bán lại vẫn gửi được dữ liệu |
| `privacy-audit` | Skill có sẵn (`.claude/skills/privacy-audit`), chưa chạy trên toàn bộ codebase sau 020–026 | Chưa có bằng chứng "0 High" cho Gate M2 |

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-20.1 | **P1** | Là gia đình thí điểm, dữ liệu của tôi tự xóa đúng hạn đã cam kết |
| US-20.2 | **P1** | Là mẹ/con, khi tôi yêu cầu xóa dữ liệu (qua đội thí điểm), mọi dữ liệu nhận diện được của gia đình bị xóa trong ≤ 72 giờ; chỉ còn sổ đồng ý ẩn danh theo luật |
| US-20.3 | **P1** | Là đội vận hành, mỗi ngày có bản sao lưu đã mã hóa, và tôi chứng minh được là khôi phục được |
| US-20.4 | **P1** | Là người cao tuổi, khi tôi rút đồng ý thì máy chủ thôi nhận dữ liệu từ máy tôi, kể cả khi app cũ vẫn cố gửi |
| US-20.5 | **P2** | Là đội vận hành, tôi gỡ được một số bị gắn cờ nhầm, thu hồi được một thiết bị bị mất, và thấy ngay trên `/readyz` khi thiếu khóa |

## 3. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Hạn lưu | Job `retention` trên DB có dữ liệu "già" giả lập (đặt mốc thời gian lùi): 100% dòng quá hạn của mỗi loại trong `DATA-MODEL.md` §6 bị xóa hoặc làm rỗng đúng cách; 0 dòng trong hạn bị đụng; `consents` không bị đụng; chạy lại là lũy đẳng; mỗi lô ≤ 1.000 dòng, không khóa bảng lâu | pytest tích hợp |
| **(SC-002)** | Xóa theo yêu cầu | Sau `purge`: 0 dòng nhận diện gia đình trong mọi bảng nghiệp vụ, `jobs`, `messages_out`, checkpoint LangGraph và `agent_steps` của gia đình; `consents` còn nguyên nhưng `families`/`members` đã ẩn danh (bí danh, HMAC Zalo, `chat_enc` rỗng); thiết bị bị thu hồi; có dòng `data_requests` hoàn tất | pytest (quét mọi bảng có `family_id` + checkpoint) |
| **(SC-003)** | Sao lưu & khôi phục | `backup` tạo tệp mã hóa AES-256-GCM (không đọc được nếu thiếu khóa, sửa 1 byte ⇒ giải mã hỏng); `restore-check` khôi phục vào DB tạm và xác nhận: `alembic_version` = head, số dòng từng bảng khớp manifest, trigger `consents`/`incident_transitions` còn và ở chế độ `ALWAYS`; thời gian khôi phục được đo | script + pytest; số đo trên máy dev |
| **(SC-004)** | Đồng ý được thực thi ở máy chủ | Thiết bị có dòng đồng ý `core_protection` mới nhất là `granted=false` (hoặc không có) ⇒ `POST /v1/events` trả 403 `consent_withdrawn`, không ghi gì; đồng ý lại ⇒ nhận bình thường | pytest |
| **(SC-005)** | Mặc định an toàn & tín hiệu vận hành | Không đặt `HOICON_ENV` ⇒ ứng dụng chạy ở chế độ `prod` (chặn demo, đòi khóa); `/readyz` trả 503 kèm tên khóa thiếu (không giá trị) khi thiếu pepper, khóa dữ liệu hoặc khóa JWT; thân > 256 KB ⇒ 413 trước khi phân tích | pytest |
| **(SC-006)** | Review bảo mật | `privacy-audit` + `security-privacy-reviewer` trên toàn bộ codebase: **0 Critical, 0 High** chưa xử lý; mọi Medium có quyết định ghi lại | báo cáo reviewer trong evidence |

## 4. Yêu cầu chức năng

- **(FR-001)** Migration (số kế tiếp sau head; chỉ làn B tạo):
  - Bảng `data_requests`: `id`, `family_id` (FK `RESTRICT`, giữ làm vết), `kind` ∈ {`delete`}, `requested_via` ∈
    {`ops`, `app`, `web`}, `status` ∈ {`pending`, `done`, `failed`}, `requested_at`, `completed_at`, `error_code`.
    Không có cột văn bản tự do.
  - Chỉ mục `agent_steps(at)` (mục treo của 003).
  - Chỉ mục `jobs(done_at)` và `risk_events(received_at)` phục vụ job hạn lưu, nếu chưa có.
  - `families.deleted_at`, `members.deleted_at` (tombstone).
- **(FR-002)** Job `retention` (`services/retention_service.py`, đăng ký trong worker, mỗi ngày một lần, khóa
  `retention:<ngày>`):
  - Áp đúng bảng §6 của DATA-MODEL: `risk_events` 90 ngày; `agent_steps.input_redacted/output` làm rỗng sau 30 ngày, giữ
    số đo; sự cố đã kết thúc 12 tháng (CASCADE nhật ký chuyển); checkpoint của sự cố đóng quá 7 ngày qua
    `adelete_thread`; `jobs` 30 ngày sau `done_at`.
  - Thêm cho bảng mới:
    - `messages_out.text` làm rỗng sau 30 ngày; giữ dòng để đếm hạn mức tháng.
    - `action_tokens` hết hạn quá 30 ngày thì xóa.
    - `verifications` (026) và `drills` (028) theo hạn 90 ngày / 12 tháng nếu bảng tồn tại.
  - Mỗi loại xóa theo lô 1.000 dòng, mỗi lô một giao dịch. Log số dòng theo loại, không log nội dung.
  - Hằng số hạn lưu đặt một chỗ (`RETENTION`), test so khớp với `DATA-MODEL.md`.
- **(FR-003)** Xóa dữ liệu gia đình theo yêu cầu (`services/purge_service.py`):
  - `request_delete(family_id, via)` ghi `data_requests`; job `purge_family` thực thi:
    1. thu hồi mọi thiết bị;
    2. xóa sự cố, `risk_events`, `agent_runs`/`agent_steps` (theo `thread_id` = id sự cố), checkpoint (`adelete_thread`),
       `jobs` mang `family_id` hoặc khóa có tiền tố id sự cố, `messages_out` của gia đình, `action_tokens`,
       `pairing_codes`, `trusted_contacts`, `verifications`, `drills`;
    3. ẩn danh `members` (bí danh = "[đã xóa]", `zalo_user_hmac`/`zalo_chat_enc` = NULL, `deleted_at`) và `families`
       (`display_name` = "[đã xóa]", `deleted_at`);
    4. giữ nguyên `consents`;
    5. đánh `done`.

    Lũy đẳng: chạy lại không lỗi.
  - Lệnh `python -m hoicon.ops.data request-delete --family <id>` và `status --request <id>`.
  - Sau khi xóa, mọi route với gia đình đó trả 404/401 (token người giám hộ hết hiệu lực vì thành viên đã ẩn danh).
- **(FR-004)** Sao lưu & khôi phục (`ops/backup.py` + `scripts/backup.sh`):
  - `backup`:
    - chạy `pg_dump -Fc` trong container Postgres (`docker exec`, vì máy chủ dev không có `pg_dump`);
    - mã hóa từng khối bằng AES-256-GCM với `HOICON_BACKUP_KEY_<kid>` (khác khóa dữ liệu, sinh bằng `init_env`);
    - ghi `*.dump.enc` + manifest JSON (số dòng từng bảng, `alembic_version`, sha256 của bản mã, kid);
    - xoay vòng: giữ 7 bản ngày + 4 bản tuần.
  - `restore-check`: giải mã, `pg_restore` vào DB tạm `hoicon_restore_check`, kiểm theo SC-003, đo thời gian, xóa DB
    tạm.
  - Lịch chạy (cron/systemd timer) và nơi lưu ngoài máy thuộc **012**: 034 chỉ cung cấp lệnh và tài liệu.
- **(FR-005)** Thực thi đồng ý ở máy chủ:
  - `POST /v1/events` và `POST /v1/heartbeat` (nếu có) kiểm dòng `consents` mới nhất của `(member, core_protection)`;
    không `granted` ⇒ 403 `consent_withdrawn`, không ghi gì.
  - Sự kiện lên tới máy chủ thì nhóm cảnh báo cũng đi tới người giám hộ, nên kiểm thêm `guardian_alerts`. Nếu chưa đồng ý
    thì vẫn nhận sự kiện (an toàn của người cao tuổi), nhưng không gửi Zalo; hành vi này được ghi rõ trong `API.md`.
  - Có bộ nhớ đệm 60 giây theo thiết bị để không thêm truy vấn mỗi lô.
- **(FR-006)** Mặc định an toàn & vận hành:
  - `Settings.env` mặc định `prod`. `.env.example`, CI và test đặt `HOICON_ENV=dev`/`test` tường minh.
  - `/readyz` kiểm có pepper `kid` hiện hành, `HOICON_DATA_KEY_<kid>` và khóa JWT đủ dài; thiếu ⇒ 503 với
    `{"missing": ["phone_pepper", …]}` (tên, không giá trị).
  - Middleware giới hạn thân 256 KB, cho cả `Content-Length` và thân chunked, đặt trước mọi router; webhook Zalo giữ giới
    hạn riêng nếu cần lớn hơn.
- **(FR-007)** (P2) Lệnh vận hành:
  - `ops devices revoke --device <id>` (đặt `revoked_at`; `get_current_device` đã từ chối thiết bị bị thu hồi).
  - `ops threat_list unflag --h1-file <tệp>` (gỡ số bị gắn cờ nhầm theo h1 trong tệp; không in h1) + thủ tục trong
    `PRIVACY-DPIA.md`.
  - Tra cứu đe dọa ở prod bỏ dòng `is_demo`.
- **(FR-008)** (P2) Tách role DB:
  - `infra/postgres/roles.sql`: role `hoicon_app` chỉ có `INSERT`/`SELECT` trên `consents` và `incident_transitions`,
    không sở hữu bảng; migration chạy bằng role chủ.
  - Test dev: kết nối bằng `hoicon_app` thì `UPDATE consents` bị từ chối bởi quyền (không chỉ bởi trigger), và
    `ALTER TABLE … DISABLE TRIGGER` bị từ chối.
  - Áp dụng ở prod thuộc 012.
- **(FR-009)** Rà soát bảo mật toàn bộ:
  - Chạy skill `privacy-audit` và `security-privacy-reviewer` trên toàn repo (không chỉ diff).
  - Bao gồm ma trận IDOR mọi route có `{id}` (thiết bị × người giám hộ × hai gia đình), quét log của bộ test đầy đủ tìm
    số điện thoại/h1/token, kiểm manifest Android.
  - Sửa mọi Critical/High; ghi quyết định cho Medium.
- **(FR-010)** Kiểm chứng & tài liệu:
  - pytest cho FR-001…FR-008; eval smoke (hồi quy).
  - Cập nhật `docs/DATA-MODEL.md` §6 (bảng mới + cơ chế đã có), `docs/PRIVACY-DPIA.md` (quy trình xóa, sao lưu, gỡ cờ),
    `docs/setup/BACKUP.md` (mới), `docs/API.md` (403 `consent_withdrawn`, 413).
  - `evidence.md` có số đo.
  - ROADMAP `P2-20`: ◐ (phần lõi xong, chờ 037 và phần lịch chạy của 012).

## 5. Bất biến & ranh giới

1. `consents` không bao giờ bị xóa hay sửa, kể cả khi xóa gia đình (Nghị định 356/2025). Ẩn danh làm trên
   `families`/`members`, không làm trên `consents`.
2. Migration đã lên `main` không sửa; mọi thay đổi lược đồ là migration mới.
3. Không đọc `.env`, keystore, `D:/secrets`. Khóa sao lưu sinh bằng `init_env`; tài liệu chỉ nêu tên biến.
4. Không log nội dung bị xóa; chỉ log số dòng theo loại.
5. Sao lưu chứa dữ liệu cá nhân ⇒ luôn mã hóa trước khi rời container; tệp tạm chưa mã hóa không bao giờ chạm đĩa máy chủ.
6. Không đổi hành vi nghiệp vụ ngoài những gì nêu ở FR (eval smoke giữ nguyên baseline).

## 6. Ngoài phạm vi (037 hoặc 012)

Crashlytics và crash-free (037) · lịch chạy sao lưu, lưu ngoài máy, Caddy, VPS (012) · màn E12 "xóa dữ liệu" trên app
(cần spec riêng, API `POST /v1/data-requests` để dành) · xuất dữ liệu (`kind=export`) · `/v1/auth/refresh`, xoay khóa JWT
bằng `kid` · giới hạn tần suất `/v1/consents` (cân nhắc ở 037).
