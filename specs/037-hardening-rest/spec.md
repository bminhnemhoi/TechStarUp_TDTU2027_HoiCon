# Spec 037: Gia cố phần còn lại (rà soát quyền riêng tư cuối, bảo mật cuối, Crashlytics)

> **BẢN NHÁP — Opus /speckit-analyze lại khi có quota.** Soạn 23/10/2026 bởi làn B (Sonnet) khi Opus nghỉ: đã chạy
> specify → clarify → plan → tasks → analyze (0 CRITICAL/HIGH, xem `plan.md` mục 5). Chưa qua mắt Opus; không sửa nội dung
> chữ của văn bản đồng ý ở đây.

**Mã ROADMAP**: `P2-20` (phần còn lại sau `034-hardening-core`) · **Làn**: A+B (`[B]` = `backend/**`, `infra/**`, `scripts/**`;
`[A]` = `apps/android/**`) · **Cột mốc**: Gate M3 (23/12/2026) cần "0 Critical/High chưa xử lý"; Vòng 2 đóng băng code 06/01/2027
· **Phụ thuộc**: 034 (lõi gia cố), 011 (thực thi đồng ý), 012 (`roles.sql`, VPS) · **US**: US-11 (đồng ý và quyền riêng tư),
US-12 (xóa dữ liệu) · **ADR**: ADR-002, ADR-006 (không đổi).

> **Chỉ nói phần chênh lệch.** 034 đã làm lõi (migration 0009, mặc định `prod`, `/readyz`, trần 256 KB, đồng ý ở máy chủ, hạn
> lưu, xóa gia đình, sao lưu mã hóa, `roles.sql`). Spec này gom **mọi mục còn mở** của 034 (`evidence.md`, mục "Medium chưa sửa"
> và "Low còn lại"), các mục nảy sinh ở 011/012/031/032, rà soát cuối và Crashlytics.

---

## 1. Bối cảnh

Trước Gate M3 và trước khi người thật dùng (thí điểm 029), phải rà lại toàn bộ lời hứa về quyền riêng tư và những chỗ bảo mật
đã biết còn hở. Danh sách đã có, rải ở `034/evidence.md`, `011/evidence.md` (reviewer bảo mật Wave 5), `012/evidence.md`:

| Mục | Nguồn | Tình trạng |
|---|---|---|
| Máy chủ chưa ép `consent_version`/`text_sha256` thuộc danh sách văn bản đã duyệt | 034 Medium #7 | mở |
| `send_to_guardian` và tin tổng kết diễn tập không kiểm đồng ý lúc gửi | 034 Medium #4 | mở |
| Link Zalo cũ (`/action/{token}`) và `POST /incidents/{id}/decision` vẫn dùng được sau khi người cao tuổi rút `guardian_alerts` | 011 Wave 5 High #1 | mở — **cần quyết định chính sách** |
| Thiếu test IDOR đầy đủ (`POST /v1/lookups`, token chéo audience, token của gia đình đã xóa) | 034 reviewer | mở |
| `/v1/consents` không có giới hạn tần suất; nonce 32 bit của sao lưu; `exc_info` của `queue.py` có thể kèm tham số SQL; fixture dùng số `0912345678` | 034 Low #9, #12, #14, #15 | mở |
| Bảng mới sau 034 (`case_files`, `device_heartbeats`, `members.weekly_digest_enabled`) chưa có hàng trong bảng dữ liệu ↔ mục đích ↔ hạn lưu | 031, 032, 029 | mở |
| Crashlytics (đo crash-free cho Gate M2/M3) | 034, 012 | **BLOCKED**: chưa có Firebase (W0-3/P0-08) |

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-37.1 | **P1** | Là người cao tuổi (hoặc con cháu thay mặt), khi tôi rút một đồng ý thì **mọi** đường dữ liệu liên quan dừng lại, kể cả link cũ và tin tổng kết |
| US-37.2 | **P1** | Là Tiến/Minh, tôi chạy một lệnh và nhận báo cáo quyền riêng tư cuối: số điện thoại thô, bảng dữ liệu ↔ mục đích ↔ hạn lưu, văn bản đồng ý ↔ mã |
| US-37.3 | **P1** | Là BGK hỏi "app bảo mật thế nào", tôi trả lời bằng báo cáo rà soát bảo mật cuối (0 Critical/High) và danh sách việc còn mở có chủ |
| US-37.4 | **P2** | Là đội, tôi đo được tỷ lệ không-sập (crash-free) của bản chạy thật — **BLOCKED** tới khi có Firebase |

## 3. Yêu cầu chức năng

- **(FR-001)** *[B]* Máy chủ ép văn bản đồng ý: `POST /v1/consents` từ chối (422, không ghi) bản ghi có cặp
  (`purpose`, `consent_version`, `text_sha256`) không thuộc `docs/legal/consent/manifest.json` (nguồn có sẵn: `ops/consent_texts.load_manifest`).
  Lỗi không nêu sha mong đợi. Bản nháp (`draft`) vẫn được nhận ở môi trường `dev`; ở `prod` chỉ nhận bản `approved`/`released` — nếu Minh chưa duyệt (011 T010) thì **tắt cờ** `HOICON_CONSENT_STRICT` (mặc định `true` ở `prod`).
- **(FR-002)** *[B]* Kiểm đồng ý lúc gửi: `send_to_guardian` (và mọi tin do máy chủ soạn: bản tin tuần, tổng kết diễn tập, hồ sơ vụ việc)
  đọc `consent_gate` ngay trước khi gửi, không dựa vào cờ đóng băng trong state đồ thị. Payload `notify_guardian` mang `protected_member_id`.
- **(FR-003)** *[B]* Đường liên kết cũ: chính sách sau khi rút `guardian_alerts` — **mặc định (đề xuất)**: `GET /action/{token}` trả
  "liên kết hết hạn" không kèm dữ liệu; `POST /incidents/{id}/decision` và `POST /action/{token}/decision` vẫn **ghi** quyết định
  (đóng sự cố, dừng nhắc) nhưng không trả `state`/`outcome`/mức rủi ro (thân tối thiểu). *Chờ Minh xác nhận* (★ MASTER-PLAN §8); mã đặt sau một hằng số `WITHDRAWN_DECISION_POLICY`.
- **(FR-004)** *[B]* Ma trận IDOR: một test tham số hóa chạy **mọi** route có `{id}` hoặc token với (a) token của gia đình khác,
  (b) token sai audience (thiết bị ↔ người giám hộ ↔ hành động), (c) token của gia đình đã bị xóa. Kỳ vọng: cùng một 404/401, không phân biệt "không có" và "không thuộc nhà".
- **(FR-005)** *[B]* Các mục Low: giới hạn tần suất `/v1/consents` theo thiết bị; sao lưu dẫn xuất khóa phụ theo từng tệp (nonce 96 bit hoặc khóa con) — **bản sao lưu cũ vẫn khôi phục được**; `queue.py` không đưa tham số SQL vào log (`exc_info` chỉ tên lớp lỗi); fixture dùng số hư cấu đã đăng ký.
- **(FR-006)** *[B]* Báo cáo quyền riêng tư cuối: lệnh `uv run --directory backend python -m hoicon.ops.privacy_report` in (a) bảng
  dữ liệu ↔ mục đích ↔ hạn lưu **sinh từ metadata của model** (mọi bảng phải có dòng, bảng mới mà thiếu ⇒ thoát khác 0), (b) quét số điện thoại
  thô trong mã nguồn + fixture, (c) văn bản đồng ý ↔ mã (`consent_texts check`), (d) `jobs`/`agent_steps` không chứa PII (mẫu số điện thoại, CCCD, OTP).
  Không in dữ liệu thật (chỉ đếm). Test chạy được không cần DB người dùng.
- **(FR-007)** *[B]* Rà soát bảo mật cuối: `security-privacy-reviewer` đọc toàn bộ diff từ `main` + danh sách ở mục 1; kết quả vào
  `evidence.md`; sửa hết Critical/High; Medium còn lại có chủ + ngày. Quét phụ thuộc (`uv pip audit`/`osv-scanner` nếu có trên máy; không có ⇒ ghi `UNAVAILABLE`, không tính là sạch).
- **(FR-008)** *[A]* Crashlytics: thêm SDK + khai báo mục đích trong văn bản đồng ý (`consent-copy`: mục đích mới ⇒ enum + phiên bản — luật 7) + `play-policy` kiểm dữ liệu thu. **BLOCKED**: chưa có Firebase; ghi tiêu chí gỡ chặn (project Firebase + `google-services.json` ngoài git). Không tạo tệp giả.
- **(FR-009)** *[B]* Tài liệu: cập nhật `docs/PRIVACY-DPIA.md` (bảng dữ liệu, độ trễ đệm đồng ý ≤ 60 giây, chính sách link cũ), `docs/setup/BACKUP.md` (khóa con) — **do Opus/Tiến** (làn B không sửa `docs/`); task ghi sẵn nội dung cần thêm.

## 4. Tiêu chí thành công

- **(SC-001)** FR-001: mọi cặp (purpose, version, sha) ngoài manifest bị từ chối ở `prod`; mọi cặp trong manifest được nhận; 0 thay đổi cho `dev`. Đo: `test_consent_manifest_enforcement.py`.
- **(SC-002)** FR-002: rút `guardian_alerts` ⇒ 0 tin `notify_guardian` mới được gửi (kể cả sự cố mở từ trước và bản tin tuần). Đo: test tích hợp với client Zalo giả đếm lời gọi.
- **(SC-003)** FR-004: ma trận IDOR 100% cùng mã trả về cho "không có" và "không thuộc nhà". Đo: số ô ma trận / số ô đạt.
- **(SC-004)** FR-006: báo cáo quyền riêng tư thoát 0 và liệt kê 100% bảng; thêm bảng giả không có metadata ⇒ thoát khác 0 (đột biến).
- **(SC-005)** FR-007: 0 Critical, 0 High chưa xử lý trên toàn codebase; số Medium còn lại có chủ + ngày. Đo: báo cáo reviewer trong `evidence.md`.
- **(SC-006)** FR-008: crash-free ≥ 99% đo bằng Crashlytics trên máy thật — **BLOCKED** (Firebase), ghi nguồn số liệu khi đo được; không tuyên bố trước.

## 5. Ngoài phạm vi

Áp `roles.sql` ở prod và lịch sao lưu trên VPS (012 T013), thay mật khẩu/khóa thật, thuê pentest, chứng nhận (ISO/SOC), WAF.
Quyết định chính sách FR-003 (Minh); văn bản đồng ý (011 T010).
