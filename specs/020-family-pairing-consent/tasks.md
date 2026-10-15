---

description: "Tasks list — Spec 020 Family Pairing & Consent Ledger (HỏiCon Đợt 4)"
---

# Tasks: Spec 020 — Ghép đôi gia đình & Sổ đồng ý bất biến

**Input**: `specs/020-family-pairing-consent/{spec.md, plan.md}`, `docs/schemas/{pair_request, pair_response, consent_record}.v1.json`

**Chế độ chạy**: Tự hành một mạch (MASTER-PLAN §2.6).

**Phân làn sở hữu**:
- **Làn B (Server)**: Tasks T001–T012 (`backend/**`, `docs/schemas/**`). Không đụng `apps/**`.
- **Làn A (Android)**: Tasks T013–T022 (`apps/android/**`). Không đụng `backend/**`.
- **Chung (Checkout chính)**: Tasks T023–T026 (Nghiệm thu, cổng chất lượng, merge).

---

## Phase 1: Setup & Contract Validation

- [x] T001 [P] Viết schema `docs/schemas/pair_request.v1.json`, `pair_response.v1.json`, `consent_record.v1.json` kèm fixtures valid/invalid — FR-012 · Verify: `uv run --directory backend pytest tests/contract/test_pairing_schemas.py -v`
- [x] T002 [P] Viết test hợp đồng `backend/tests/contract/test_pairing_schemas.py` chạy qua 12 ca kiểm thử schema — FR-012 · Verify: `uv run --directory backend pytest tests/contract/test_pairing_schemas.py -q`

---

## Phase 2: Foundational (Làn B — Database v1 & Trigger)

- [x] T003 [B] Viết test trước `backend/tests/integration/test_schema_0005.py`: kiểm tra bảng `devices`, `consents`, `trusted_contacts`, `action_tokens` đủ cột và ràng buộc; kiểm tra không có cột PII thô; kiểm tra trigger `prevent_consent_tamper` ném exception khi gọi UPDATE hoặc DELETE — FR-001, FR-002, FR-011, SC-002 · Verify: `uv run --directory backend pytest tests/integration/test_schema_0005.py -q` (đỏ)
- [x] T004 [B] Viết migration `backend/migrations/versions/20261016_0005_device_pairing_consent.py` (Alembic revision 0005, down 0004) + khai báo Models SQLAlchemy trong `backend/src/hoicon/db/models.py` (`Device`, `Consent`, `TrustedContact`, `ActionToken`) + Trigger PostgreSQL `prevent_consent_tamper` — FR-001, FR-002 · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head && uv run --directory backend pytest tests/integration/test_schema_0005.py -q` (xanh)

---

## Phase 3: User Story 1 — API Ghép đôi thiết bị (Làn B)

- [x] T005 [B] [US1] Viết test trước `backend/tests/integration/test_api_pairing.py`: gọi `POST /v1/pair` với mã 6 số hợp lệ $\rightarrow$ trả 200 kèm JWT thiết bị; mã hết hạn/sai/đã dùng $\rightarrow$ trả 400; mã hợp lệ bị đánh dấu `used_at`; gọi lại mã cũ $\rightarrow$ trả 400 — FR-003, SC-001 · Verify: `uv run --directory backend pytest tests/integration/test_api_pairing.py -q` (đỏ)
- [x] T006 [B] [US1] Hiện thực `DeviceAuth` trong `backend/src/hoicon/api/auth.py` (tạo access token JWT 30 ngày, hàm giải mã token `get_current_device`) và cấu hình `HOICON_DEVICE_JWT_SECRET` trong `backend/src/hoicon/config.py` — FR-004 · Verify: `uv run --directory backend pytest tests/unit/test_device_auth.py -q`
- [x] T007 [B] [US1] Hiện thực endpoint `POST /v1/pair` trong `backend/src/hoicon/api/routers/pairing.py`: xác thực mã nguyên tử với `SELECT ... FOR UPDATE`, tạo `devices`, cập nhật `used_at`, trả `pair_response.v1.json` — FR-003, SC-001 · Verify: `uv run --directory backend pytest tests/integration/test_api_pairing.py -q` (xanh)

---

## Phase 4: User Story 2 — Sổ đồng ý bất biến (Làn B)

- [x] T008 [B] [US2] Viết test trước `backend/tests/integration/test_api_consents.py`: không có JWT $\rightarrow$ 401; có JWT hợp lệ $\rightarrow$ ghi nhận các mục đồng ý vào DB; kiểm tra không thể cập nhật/xóa dòng consent đã ghi — FR-005, SC-002 · Verify: `uv run --directory backend pytest tests/integration/test_api_consents.py -q` (đỏ)
- [x] T009 [B] [US2] Hiện thực endpoint `POST /v1/consents` trong `backend/src/hoicon/api/routers/consents.py`: nhận `consent_record.v1.json`, lưu vào bảng `consents` với `recorded_at = now()` — FR-005, SC-002 · Verify: `uv run --directory backend pytest tests/integration/test_api_consents.py -q` (xanh)
- [x] T010 [B] [US2] Thêm endpoint `GET /v1/devices/me` trả về thông tin thiết bị và trạng thái đồng ý hiện tại — FR-004 · Verify: `uv run --directory backend pytest tests/integration/test_api_devices.py -q`
- [x] T011 [B] [P] Cập nhật tài liệu API trong `docs/API.md` và `docs/DATA-MODEL.md` — FR-013 · Verify: review
- [x] T012 [B] Cổng chất lượng Làn B: `ruff check` + `ruff format --check` sạch, `pytest` toàn bộ $\ge 615$ passed, `hoicon-eval --suite smoke --compare baseline` đạt +0.0% — SC-006 · Verify: `cd backend && uv run ruff check . && uv run pytest -q`

---

## Phase 5: User Story 3 — Màn hình Onboarding E1 & E2 (Làn A)

- [ ] T013 [A] [US3] Tạo module lưu trữ token bảo mật `TokenStorage.kt` trong `apps/android/app/src/main/java/vn/hoicon/sentinel/data/local/TokenStorage.kt` dùng EncryptedSharedPreferences lưu `device_id`, `access_token`, `refresh_token`, `family_name` — FR-004 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`
- [ ] T014 [A] [US3] Tạo `PairingApiClient.kt` trong `apps/android/app/src/main/java/vn/hoicon/sentinel/data/remote/PairingApiClient.kt` gọi `POST /v1/pair` và `POST /v1/consents` theo đúng hợp đồng JSON Schema — FR-003, FR-005 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`
- [ ] T015 [A] [US3] Thiết kế màn hình E1 `WelcomeScreen.kt` (Compose): Logo HỏiCon, lời chào ấm áp, font Be Vietnam Pro, nút "Bắt đầu ghép đôi" đạt WCAG AAA 7:1 và kích thước $\ge 64$dp — FR-006, FR-010, SC-004 · Verify: `./gradlew -p apps/android :app:compileDebugKotlin`
- [ ] T016 [A] [US3] Thiết kế màn hình E2 `PairingScreen.kt` (Compose): Ô nhập 6 chữ số cỡ lớn 32sp, bàn phím số, tự động gọi API ghép đôi khi đủ 6 số, hiển thị thông báo lỗi tiếng Việt thân thiện khi mã sai — FR-007, FR-010, SC-001 · Verify: `./gradlew -p apps/android :app:compileDebugKotlin`

---

## Phase 6: User Story 4 — Công bố nổi bật E3 & Cấp quyền E4 (Làn A)

- [ ] T017 [A] [US4] Thiết kế màn hình E3 `ProminentDisclosureScreen.kt` (Compose): Nêu rõ 4 cam kết về quyền Trợ năng, Thông báo và Cuộc gọi lạ theo đúng chính sách Google Play 2026; nút "Tôi hiểu và tiếp tục" — FR-008, SC-003, SC-004 · Verify: `./gradlew -p apps/android :app:compileDebugKotlin`
- [ ] T018 [A] [US4] Tích hợp màn hình E4 `PermissionsScreen.kt`: Nút cấp từng quyền hệ thống, sau khi người dùng cấp thì tổng hợp và gọi `PairingApiClient.recordConsents()` gửi lên `POST /v1/consents` — FR-009, SC-003 · Verify: `./gradlew -p apps/android :app:compileDebugKotlin`
- [ ] T019 [A] [US4] Điều hướng Onboarding `OnboardingActivity.kt`: Kết nối luồng E1 $\rightarrow$ E2 $\rightarrow$ E3 $\rightarrow$ E4 $\rightarrow$ Màn hình chính; kiểm tra trạng thái token lúc mở app — FR-006..FR-009 · Verify: `./gradlew -p apps/android :app:assembleDebug`
- [ ] T020 [A] [US4] Chụp ảnh kiểm chứng giao diện E1–E4 ở cỡ chữ 100% và 200% trên AVD `hc-api36` lưu vào `~/hoicon-evidence/020-family-pairing-consent/shots/` — SC-003, SC-004 · Verify: `ls ~/hoicon-evidence/020-family-pairing-consent/shots/`
- [ ] T021 [A] [P] Gọi `ux-elder-reviewer` đánh giá khả năng đọc và thao tác của người cao tuổi trên các màn hình E1–E4 — SC-004 · Verify: review evidence
- [ ] T022 [A] Cổng chất lượng Làn A: Gradle build debug & release manifest check 0 quyền lạ ngoài khai báo; kiểm tra không có mã hex chép tay ngoài `Tokens.kt` — SC-004, SC-006 · Verify: `./gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`

---

## Phase 7: Polish & Acceptance Evidence

- [ ] T023 Viết `specs/020-family-pairing-consent/evidence.md` tổng hợp toàn bộ số đo SC-001..SC-006 — SC-001..SC-006 · Verify: `python3 scripts/check-spec-trace.py`
- [ ] T024 Cập nhật dòng P2-01 và P2-02 trong `docs/ROADMAP.md` (chuyển sang `☑` nếu hoàn tất hoặc `◐` nếu còn chặn) — FR-013 · Verify: `python3 scripts/check-spec-trace.py`
- [ ] T025 Chạy toàn bộ các cổng kiểm tra: `python3 scripts/check-spec-trace.py` (0 lỗi), `unittest discover -s scripts/tests`, `ruff check`, `pytest` toàn bộ, `gitleaks` diff sạch — SC-006 · Verify: các lệnh trên
- [ ] T026 Tích hợp hai làn vào `tien-collab-dev`, push lên origin và kiểm chứng Draft PR #12 CI xanh — SC-006 · Verify: `gh run list -b tien-collab-dev`
