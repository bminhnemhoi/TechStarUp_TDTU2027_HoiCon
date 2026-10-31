# Bằng chứng nghiệm thu: Spec 020 — Ghép đôi gia đình & Sổ đồng ý bất biến (Family Pairing & Consent Ledger)

**Spec**: `specs/020-family-pairing-consent/spec.md` · **Mã ROADMAP**: P2-01 + P2-02 · **Nhánh tích hợp**: `tien-collab-dev` · **Ngày**: 16/10/2026

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Môi trường (máy ảo / FTL / DB dev) | Đạt? | Bằng chứng |
|---|---|---|---|---|---|
| SC-001 | Ghép đôi thành công < 5 phút; mã quá 15' bị chặn | Mã hợp lệ ghép trong 1,2 s; mã sai/hết hạn ném 400 trong 12 ms; mã hết hạn sau 15' bị từ chối; 100% atomic (50 request đua 1 mã chỉ 1 trúng) | Postgres Docker 15432, pytest integration | ✓ | `test_api_pairing.py` (17 tests) |
| SC-002 | Sổ đồng ý bất biến: chặn 100% UPDATE/DELETE | 100% câu lệnh UPDATE, DELETE, TRUNCATE bị Postgres Trigger chặn đứng; trigger đặt `ENABLE ALWAYS` chống lách replica | DB dev Postgres 17, pytest live DB | ✓ | `test_schema_0005.py` (10 tests) |
| SC-003 | Prominent Disclosure hiển thị trước mọi hộp thoại quyền | E3 hiển thị 100% trước E4; E3 có nút "Chưa đồng ý" và giải thích rõ; 0 Accessibility | AVD `hc-api36` + kiểm tra Compose State | ✓ | 16 ảnh chụp `~/hoicon-evidence/020-family-pairing-consent/shots/` |
| SC-004 | Tương phản & Khả năng đọc người già | 100% màu từ `Tokens.kt` WCAG AAA $\ge 7:1$; cỡ chữ $\ge 20$sp; font Be Vietnam Pro đóng gói | Unittest tokens.json & UX elder reviewer | ✓ | `test_design_tokens.py` 67 tests OK |
| SC-005 | Bảo vệ PII | 0 số điện thoại thô; 0 PII trong log; `device_label` tự động che số/email | `privacy-audit` & gitleaks sạch 100% | ✓ | `gitleaks detect` no leaks found |
| SC-006 | Hồi quy & Ổn định | Backend: 706 passed (100%); Android: 32 unit tests mới + 54 rules tests OK; Lint 0 lỗi; Eval smoke +0.0% | Dev Linux & CI GitHub Actions | ✓ | `pytest tests/` 706 passed |

---

## Yêu cầu chức năng (FR) ↔ kiểm chứng

| FR | Nội dung | Kết quả |
|---|---|---|
| FR-001 | Migration 0005 tạo `devices`, `consents`, `trusted_contacts`, `action_tokens` đủ ràng buộc CHECK | ✓ `test_schema_0005.py` |
| FR-002 | PostgreSQL Trigger `prevent_consent_tamper` append-only, chống UPDATE/DELETE | ✓ `test_consents_are_append_only_update_is_blocked`, `test_consents_are_append_only_delete_is_blocked` |
| FR-003 | API `POST /v1/pair` nhận mã 6 số (15 phút), trả token thiết bị | ✓ `test_api_pairing.py` |
| FR-004 | DeviceAuth JWT HS256 30 ngày, hash secret refresh token | ✓ `test_device_auth.py` |
| FR-005 | API `POST /v1/consents` lưu sổ đồng ý append-only | ✓ `test_api_consents.py` |
| FR-006 | Màn E1 WelcomeScreen ấm áp, thân thiện gia đình | ✓ `e1-welcome-100.png`, `e1-welcome-200.png` |
| FR-007 | Màn E2 PairingScreen ô nhập 6 số 32sp ghim trên bàn phím | ✓ `e2-pairing-100.png`, `e2-pairing-200.png`, `e2-pairing-loi-*.png` |
| FR-008 | Màn E3 ProminentDisclosureScreen chuẩn Google Play 2026 | ✓ `e3-disclosure-*.png`, `e3-tu-choi-*.png` |
| FR-009 | Màn E4 PermissionsScreen hướng dẫn từng quyền, gửi consent lên server | ✓ `e4-permission-*.png`, `e4-thieu-*.png`, `e4-thongbao-*.png` |
| FR-010 | Áp dụng 100% token màu từ `Tokens.kt` và font Be Vietnam Pro | ✓ Lint 0 hex lạ, 67 token tests OK |
| FR-011 | Chống rò rỉ PII: băm theo ADR-006, che `device_label` | ✓ `test_device_label_is_masked_and_versions_are_constrained` |
| FR-012 | Hợp đồng JSON Schema cho pair_request, pair_response, consent_record, device_me | ✓ `test_pairing_schemas.py` & `test_device_me_schema.py` |
| FR-013 | Cập nhật tài liệu DATA-MODEL, API, ROADMAP | ✓ `docs/API.md`, `docs/DATA-MODEL.md`, `docs/ROADMAP.md` |

---

## Cổng các tầng (lệnh đã chạy)

| Tầng | Lệnh | Kết quả |
|---|---|---|
| Truy vết | `python3 scripts/check-spec-trace.py` | **7 spec, 0 lỗi** |
| Scripts | `python3 -m unittest discover -s scripts/tests` | **67 tests OK** (WCAG AAA $\ge 7:1$) |
| Generator | `python3 scripts/gen-design-tokens.py --check` | **exit 0** |
| Backend Lint | `uv run ruff check . && uv run ruff format --check .` | **All checks passed (118 files)** |
| Backend Test | `uv run pytest tests/` | **706 passed, 1 warning (34.39s)** |
| Eval Smoke | `hoicon-eval --suite smoke --compare baseline` | **ĐẠT, lệch baseline +0.0 điểm %** |
| Android Test | `:rules:test` + `:app:testDebugUnitTest` | **86 tests OK (54 rules + 32 app)** |
| Android Build | `:app:assembleDebug` + `:app:processReleaseMainManifest` | **BUILD SUCCESSFUL, lintDebug 0 lỗi** |
| Quét bí mật | `gitleaks detect --log-opts="origin/tien-collab-dev..HEAD"` | **no leaks found** |

---

## Review độc lập đã hoàn tất

1. **Bảo mật & Quyền riêng tư (`security-privacy-reviewer`)**:
   - 0 Critical, 4 High (2 Android + 2 Server).
   - Đã sửa toàn bộ High:
     - Android: Chống sập Keystore khi máy cũ reset; Quản lý sổ đồng ý theo `purpose|version|hash` để đổi bản văn là sinh dòng mới.
     - Server: Giữ chỗ rate-limit trước khi vào DB để chặn burst 1500 request lọt ngưỡng; Trigger đặt `ENABLE ALWAYS` để chống lách bằng replication role.
2. **UX Người cao tuổi (`ux-elder-reviewer`)**:
   - 4 High trên Android E1–E4 đã sửa: E2 ghim ô nhập không bị bàn phím che ở 200%; E3 có tùy chọn "Chưa đồng ý"; E4 hướng dẫn từng quyền riêng và không báo sẵn sàng nếu thiếu quyền cốt lõi; Bỏ câu nói quá "không thể đọc ngược số điện thoại".

---

## Còn tồn & Chuyển giao các đợt sau

- **Ngưỡng toàn cục 60 sai / 15 phút**: Đánh đổi có chủ đích nhằm chống botnet quét vét mã 6 số.
- **Quyền Trợ năng (Accessibility)**: Cố tình KHÔNG dùng để tuân thủ chính sách Google Play Store.
- **Refresh token & Hủy ghép đôi**: Sẽ hiện thực ở P2-05/P2-06 và màn E12.
- **Tên miền API**: Release tạm thời dùng `https://api.hoicon.vn`, sẽ chốt ở spec 012 khi dựng Caddy VPS.
