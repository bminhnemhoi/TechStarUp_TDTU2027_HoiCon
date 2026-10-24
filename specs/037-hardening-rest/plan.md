# Kế hoạch Spec 037: Gia cố phần còn lại

> **Đã đối soát 24/10/2026 (kiến trúc sư):** bản của làn B được giữ làm gốc vì mã đã thi công theo nó; bổ sung từ bản kiến trúc sư ở cuối `tasks.md` (T013–T016).

**Mã**: `037-hardening-rest` · **ROADMAP**: `P2-20` (phần còn lại) · **Làn**: A+B (chủ yếu B) · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Đây chính là spec rà soát: báo cáo chỉ đếm, không in dữ liệu; fixture chỉ số/tên hư cấu |
| III. LLM chỉ nâng | Không đụng đồ thị/router ngoài việc kiểm đồng ý lúc gửi (FR-002) |
| IV. Công khai AI | Giữ nguyên; FR-002 không đổi nội dung tin |
| V. Hợp đồng trước | **Không thêm hợp đồng mới**: thân 422/404 dùng lỗi chuẩn có sẵn; FR-003 *thu hẹp* thân phản hồi (tập con của lược đồ cũ) — nếu `action_view`/`incident_decision` cần trường tùy chọn thì **DỪNG, báo Opus** (đổi `docs/schemas`) |
| VI. UX | Không có màn hình mới; chữ của "liên kết hết hạn" dùng lại câu có sẵn của 023 |
| VII. Bằng chứng | Mọi số trong `evidence.md` kèm lệnh; Crashlytics không tuyên bố số khi BLOCKED |
| VIII. Ít code | Tái dùng `consent_texts.load_manifest`, `consent_gate`, `Base.metadata`, `security-privacy-reviewer` |

## 2. Quyết định

| # | Quyết định | Lý do | Phương án bỏ |
|---|---|---|---|
| D1 | Ép văn bản đồng ý bằng **manifest** (`docs/legal/consent/manifest.json`), cờ `HOICON_CONSENT_STRICT` (mặc định `true` ở `prod`, `false` ở `dev`) | Manifest là nguồn sự thật đã có test (011); chưa duyệt văn bản (011 T010) thì không được khóa cả hệ thống | Hard-code sha trong mã (lệch với Android) |
| D2 | FR-003 chính sách link cũ = **đề xuất** "ghi quyết định nhưng không trả dữ liệu"; hằng số `WITHDRAWN_DECISION_POLICY` | Người giám hộ phải dừng được sự cố đang mở (an toàn); nhưng không được đọc thêm dữ liệu của người đã rút. Minh quyết ★ | Chặn hẳn (người giám hộ không dừng được nhắc nhở); để nguyên (lộ dữ liệu) |
| D3 | Báo cáo quyền riêng tư **sinh từ `Base.metadata`** + bảng ánh xạ bảng → (mục đích, hạn lưu) ở một tệp Python | Bảng mới mà quên ánh xạ ⇒ lệnh thất bại (có đột biến); không chép tay vào tài liệu | Bảng trong `PRIVACY-DPIA.md` chép tay (đã lệch 3 bảng) |
| D4 | Ma trận IDOR **tham số hóa từ `app.routes`**: liệt kê route có path param/phụ thuộc xác thực, mỗi ô chạy 3 kiểu token | Route mới tự vào ma trận; không bỏ sót | Test viết tay từng route (đã bỏ sót `lookups`) |
| D5 | Sao lưu: dẫn xuất khóa con theo tệp bằng HKDF (`salt` ngẫu nhiên 16 byte trong phần đầu tệp), **đọc được cả định dạng cũ** (đầu tệp có phiên bản) | Nonce 32 bit của bản cũ có nguy cơ va chạm khi nhiều tệp; không được làm hỏng bản sao lưu đã có | Đổi khóa chính (làm mất khôi phục) |
| D6 | Crashlytics chỉ là task `[A]` BLOCKED; làn B không tạo cấu hình giả | Không có Firebase; tệp giả đánh lừa đo | Tự tạo project cá nhân |

## 3. Luồng chính (FR-001, FR-002)

```
POST /v1/consents ──▶ kiểm (purpose, version, sha) ∈ manifest (strict) ──▶ 422 không ghi | ghi sổ + invalidate đệm
đồ thị / worker ──▶ send_to_guardian(payload{protected_member_id}) ──▶ consent_gate.state_for(...).guardian_alerts
                                                                  ├─ false ⇒ không gửi, đánh dấu job xong, log (không PII)
                                                                  └─ true  ⇒ qua bộ kiểm hạn mức như cũ
```

## 4. Bản đồ file

| Nhóm | File | Thay đổi |
|---|---|---|
| B | `api/routers/consents.py`, `config.py` (`consent_strict`) | sửa |
| B | `channels/guardian.py`, `agents/incident_graph.py` (`notify` thêm `protected_member_id`), `services/coach_service.py`, `services/drill_service.py` (`_queue_debrief`) | sửa nhỏ |
| B | `api/routers/actions.py`, `api/routers/incidents.py` (FR-003) | sửa nhỏ |
| B | `ops/privacy_report.py` | mới |
| B | `ops/backup.py` | sửa (D5) |
| B | `jobs/queue.py` (log), `api/routers/consents.py` (hạn mức) | sửa nhỏ |
| B | `tests/integration/test_consent_manifest_enforcement.py`, `test_send_checks_consent.py`, `test_idor_matrix.py`; `tests/unit/test_privacy_report.py`, `test_backup_subkeys.py` | mới |
| A | `apps/android/**` (Crashlytics) | **BLOCKED** (FR-008) |
| tài liệu | `docs/PRIVACY-DPIA.md`, `docs/setup/BACKUP.md` | do Opus/Tiến (làn B không sửa `docs/`) |

## 5. Phân tích chéo (analyze, 23/10/2026)

Đối chiếu `spec.md` ↔ `plan.md` ↔ `tasks.md`: mọi FR-001…FR-009 có task; mọi SC có lệnh đo; không có hợp đồng mới. **0 CRITICAL, 0 HIGH.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| A1 | MEDIUM | FR-003 có thể cần trường tùy chọn mới trong `action_view`/`incident_decision` | Plan hiến chương V: nếu cần thì dừng, báo Opus; mặc định thu hẹp thân (không thêm trường) |
| A2 | MEDIUM | FR-001 ở `prod` khóa mọi văn bản nháp; thí điểm chưa có văn bản `approved` (011 T010) | `HOICON_CONSENT_STRICT` tắt được; ghi vào quyết định D1 |
| A3 | LOW | FR-008 (Crashlytics) là việc Android duy nhất, BLOCKED | Task `[A]` ghi tiêu chí gỡ chặn |
| A4 | LOW | FR-009 sửa `docs/` ngoài quyền làn B | Task ghi sẵn nội dung; người có quyền chép |
