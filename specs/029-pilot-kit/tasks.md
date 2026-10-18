# Công việc Spec 029: Bộ thí điểm & Play internal v0.3

## Cách chạy

- Giai đoạn 1 chạy một mạch ngay.
- Giai đoạn 2 có **điều kiện vào**: `012-release-and-hosting` đã merge (buildType release/demo + R8 + Play internal +
  VPS), `034-hardening-core` đã merge với 0 High, và W0-3 xong (Play Console + Firebase). Nếu thiếu thì đánh BLOCKED kèm
  lý do trong `evidence.md`, không làm vòng.
- **Thẻ làn:** `[A]`, `[B]`, `[H]` (hồ sơ/vận hành), `[AB]`.
- **Biến dùng trong lệnh:**
  - `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`
  - `GRADLE = ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/opt/android-studio/jbr PATH="/opt/android-studio/jbr/bin:$PATH" ./apps/android/gradlew -p apps/android`
- Số migration là số kế tiếp sau head lúc thi công.

## Giai đoạn 1: Làm được ngay

- [x] T001 [AB] (phần B xong 17/10: 2 schema + fixture + `test_heartbeat_schema.py`; test Android ghim fixture `HeartbeatContractTest` xong, làn A) [FR-001] Viết `docs/schemas/heartbeat.v1.json` (đúng thân `PairingApiClient.sendHeartbeat`, dùng `$ref`
  tới mẫu phiên bản của `risk_event.v1`) và `pilot_report.v1.json`, kèm fixture. Fixture valid của heartbeat sinh từ
  chính hàm dựng thân của Android; thêm test Android ghim fixture đó.
  · Verify: `$PYTEST tests/contract/test_heartbeat_schema.py && $GRADLE :app:testDebugUnitTest`
- [x] T002 [B] [FR-003] Viết migration bảng `device_heartbeats` (PK `(device_id, slot)`, FK `CASCADE`), cập nhật model,
  và test lược đồ.
  · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head && $PYTEST tests/integration/test_schema_<số>.py`
- [x] T003 [B] [FR-002] Thêm `POST /v1/heartbeat` vào `api/routers/devices.py`:
  - cập nhật `devices`;
  - chèn `device_heartbeats` theo khung 15 phút, `ON CONFLICT DO NOTHING`;
  - kiểm `core_protection` (dùng hàm của 034 nếu đã có);
  - hạn mức 8 lần/giờ;
  - đăng ký hạn lưu 90 ngày với job `retention` nếu 034 đã merge, không thì ghi TODO vào ROADMAP "Ghi chú".

  · Verify: `$PYTEST tests/integration/test_heartbeat.py tests/integration/test_api_devices.py`
- [x] T004 [B] [FR-002] Viết `backend/tests/integration/test_heartbeat.py`. Các ca:
  - thân đúng ⇒ 200, `last_heartbeat_at` đổi;
  - gửi lặp trong cùng khung ⇒ 1 dòng;
  - trường lạ ⇒ 422 (lỗi không lặp lại giá trị);
  - thiết bị bị thu hồi ⇒ 401;
  - chưa đồng ý ⇒ 403 `consent_withdrawn`;
  - lần thứ 9 trong giờ ⇒ 429;
  - quét DB: không lưu trường ngoài hợp đồng.

  · Verify: như T003
- [x] T005 [A] [FR-001] Trong `PairingApiClient`, phân biệt 403 có mã `consent_withdrawn` cho `sendHeartbeat` và
  `sendEvents` thành trạng thái "cần đồng ý lại" (không xóa token, không hiện "Kết nối lại"). Test ánh xạ.
  · Verify: `$GRADLE :app:testDebugUnitTest`
- [x] T006 [B] [FR-004] Viết `ops/pilot.py` (`enroll --confirm-adult`, `report --days --json`, `gate-m2`) theo plan D2/D4.
  Đầu ra không có PII. `gate-m2` đánh dấu "NHẬP TAY" cho chỉ tiêu do người nhập.
  · Verify: `$PYTEST tests/integration/test_ops_pilot.py`
- [x] T007 [B] [FR-004] Viết `backend/tests/integration/test_ops_pilot.py`. Các ca:
  - độ phủ 100% / 50% / 0% với dữ liệu dựng sẵn;
  - thiết bị ghép giữa kỳ (mẫu số đúng);
  - thiết bị bị thu hồi;
  - JSON khớp `pilot_report.v1`;
  - `enroll` thiếu `--confirm-adult` ⇒ lỗi;
  - đầu ra không chứa bí danh thành viên, HMAC hay số.

  · Verify: như T006
- [x] T008 [AB] [FR-005] Viết `scripts/release-gate.sh` theo plan D3 và `scripts/tests/test_release_gate.py`. Test: chạy
  trên APK debug dựng bằng `$GRADLE :app:assembleDebug` ⇒ TRƯỢT ở mục R8 và log chẩn đoán; manifest không có quyền cấm ⇒
  mục quyền ĐẠT; script thoát ≠ 0.
  · Verify: `$GRADLE :app:assembleDebug && python3 -m unittest scripts/tests/test_release_gate.py`
- [ ] T009 [H] [FR-006] Soạn `docs/setup/PILOT-ONBOARDING.md` và `docs/setup/PILOT-SUPPORT.md`, rồi bổ sung phần thí
  điểm của `docs/PILOT-PROTOCOL.md` (ghi rõ phần chờ 011). Gửi `ux-elder-reviewer` duyệt câu chữ; Minh duyệt bản cuối.
  · Verify: báo cáo reviewer không còn mục chặn; evidence ghi trạng thái Minh duyệt
- [x] T010 [AB] [FR-010] Sinh lại client TS; cập nhật `docs/API.md` (heartbeat, 403 `consent_withdrawn`),
  `docs/DATA-MODEL.md` (`device_heartbeats`, hạn lưu), `docs/PLAY-POLICY.md` (Data safety khớp các trường heartbeat).
  · Verify: `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck`

## Giai đoạn 2: Có điều kiện vào (012 + 034 + W0-3)

- [ ] T011 [A] [FR-007] (**MỘT PHẦN 18/10/2026**: bản release 0.3.0 + R8 + gate ĐẠT cục bộ, AAB chưa ký, chưa tải lên Play; xem evidence.md "T011 cục bộ") Đặt `versionName 0.3.0` và tăng `versionCode`. Build AAB bằng buildType của 012 và chạy
  `scripts/release-gate.sh` ⇒ mọi mục tự động phải ĐẠT. Soạn ghi chú phát hành tiếng Việt. Tiến/Minh tải lên kênh
  internal testing.
  · Verify: `scripts/release-gate.sh apps/android/app/build/outputs/bundle/release/app-release.aab` thoát 0
- [ ] T012 [A] [FR-008] Chạy trên ≥ 1 máy thật (mượn/mua, hoặc FTL): ghép đôi với VPS, kịch bản cuộc gọi lạ → app ngân
  hàng (`:demobank`), đo SafePause, kiểm heartbeat 200 trên VPS. Ghi model, phiên bản Android và số đo vào evidence.
  · Verify: evidence có bảng máy thật với số đo
- [ ] T013 [H] [FR-009] Ghi danh ≥ 5 gia đình theo `PILOT-ONBOARDING` (`ops pilot enroll --confirm-adult`). Sau 7 ngày
  chạy `ops pilot gate-m2 --days 7 --crash-free <số> --crash-source "Play vitals, n=…" --real-devices <số>`. Đính kèm ảnh
  Play vitals và kết quả 034.
  · Verify: đầu ra `gate-m2` trong evidence
- [ ] T014 [AB] [FR-010] Chạy đủ bộ lệnh kiểm:
  - `$PYTEST`; `ruff check` và `ruff format --check`;
  - `$GRADLE :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`;
  - `hoicon-eval --suite smoke --compare baseline`;
  - gitleaks **từng thư mục**: `backend/src`, `backend/tests`, `apps/android/app/src`, `docs/schemas`, `scripts`,
    `specs/029-pilot-kit`;
  - `python3 scripts/check-spec-trace.py`.

  Điền `evidence.md`. ROADMAP `P2-14` ☑ **chỉ** khi `gate-m2` ĐẠT mọi chỉ tiêu; nếu không thì ◐ và ghi rõ chỉ tiêu thiếu.
  · Verify: mọi lệnh xanh; `python3 scripts/check-spec-trace.py` ⇒ 0 lỗi
