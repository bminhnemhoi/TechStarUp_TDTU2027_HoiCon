# Bằng chứng nghiệm thu Spec 029: Bộ thí điểm & Play internal v0.3

- **Trạng thái**: giai đoạn 1 xong: làn B (17/10/2026: T002, T003, T004, T006, T007, T010) và làn A Android (T001 phần Android, T005, T008; 18/10/2026). Còn lại: T009 (tài liệu, người duyệt), giai đoạn 2 (T011 mới xong phần cục bộ, T012–T014). Làn A: bản release 0.3.0 có R8 + gate ĐẠT cục bộ, AAB chưa ký, chưa tải lên Play (BLOCKED W0-3).
- **Điều kiện vào giai đoạn 2**: `012-release-and-hosting` (chưa có spec), `034-hardening-core` (chưa thi công), W0-3
  Play Console + Firebase (⏸). Giai đoạn 1 không phụ thuộc các mục này.
- **Nguồn số dự kiến**: pytest và máy ảo ở giai đoạn 1; VPS + máy thật + Android vitals (nhập tay, ghi cỡ mẫu) ở giai
  đoạn 2.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 heartbeat ở máy chủ | khớp thân Android; cập nhật thiết bị; từ chối khi chưa đồng ý/thu hồi; 429 ở lần 9/giờ | `test_heartbeat.py` + log AVD (200 thay vì 404) | `test_heartbeat.py` 21 test xanh (thân đúng, lặp trong khung ⇒ 1 dòng, trường lạ ⇒ 422 không lặp giá trị, thu hồi ⇒ 401, rút đồng ý ⇒ 403 `consent_withdrawn`, lần 9 ⇒ 429, DB không lưu ngoài hợp đồng, hạn lưu 90 ngày). AVD hc-api36 nối backend dev (18/10/2026): `POST /v1/heartbeat` 200 ngay sau ghép đôi và mỗi 15 phút, `last_heartbeat_at` đổi, `device_heartbeats` có dòng theo khung; app tách riêng 403 `consent_withdrawn` (Android T005, test xanh). **Chưa đo trên máy thật** | ĐẠT (máy chủ + AVD); máy thật CHƯA ĐO |
| SC-002 báo cáo sức khỏe | độ phủ đúng (100/50/0%), mẫu số đúng khi ghép giữa kỳ; không PII | `test_ops_pilot.py` | 24 test xanh: độ phủ 100/50/0%, ghép giữa kỳ (mẫu số 48 khung), thu hồi giữa kỳ, thiết bị chưa đủ 1 khung ⇒ `null` (không phải 0%), sự cố thật vs diễn tập/demo, JSON khớp `pilot_report.v1`, đầu ra không chứa bí danh thành viên/HMAC/UUID đầy đủ/dãy ≥ 8 chữ số, `enroll` thiếu `--confirm-adult` ⇒ lỗi, ngưỡng 90% và 5 gia đình, chỉ tiêu NHẬP TAY thiếu số ⇒ không đạt | ĐẠT |
| SC-003 `release-block` tự động | APK debug ⇒ TRƯỢT đúng mục; bản release của 012 ⇒ ĐẠT | `test_release_gate.py` + chạy trên AAB release | `test_release_gate.py` 14 test xanh (debug ⇒ thoát 1, TRƯỢT mục R8 kèm số lớp; bắt được CAMERA/READ_SMS/READ_CALL_LOG/READ_CONTACTS và dịch vụ Accessibility). 18/10/2026: AAB release 0.3.0 dựng bằng buildType release mới (R8 + shrinkResources) ⇒ `release-gate.sh` **thoát 0, mọi mục tự động ĐẠT**, kể cả `ConsentTextsPinTest` (mục "T011 cục bộ"). Chưa chạy trên bản release của spec 012 thật (spec 012 chưa có) | ĐẠT (cục bộ) |
| SC-004 tài liệu thí điểm | `PILOT-ONBOARDING` (≤ 5 phút, theo hãng), `PILOT-SUPPORT`; reviewer + Minh duyệt | review | chưa chạy | CHƯA ĐO |
| SC-005 Gate M2 | ≥ 5 gia đình, ≥ 1 máy thật, độ phủ heartbeat ≥ 90% (7 ngày), crash-free ≥ 99% (Play vitals, ghi cỡ mẫu), 0 High | `ops pilot gate-m2` + ảnh Play Console | BLOCKED (012, 034, W0-3) | CHƯA ĐO |
| SC-006 hồi quy | pytest, Gradle, eval smoke xanh; đường dừng an toàn không đổi | CI | chưa chạy | CHƯA ĐO |

## T011 cục bộ: bản release 0.3.0 có R8 (Làn A, 18/10/2026)

**Đã làm (`apps/android/app/build.gradle.kts`, `proguard-rules.pro`):** `versionName 0.3.0`, `versionCode 3`; buildType `release`:
`isMinifyEnabled` + `isShrinkResources`, `proguard-android-optimize.txt` + luật tối thiểu của HỏiCon; nhật ký chẩn đoán (HC_TIMING/HC_SPIKE) bị loại khỏi dex vì
`BuildConfig.DEBUG = false`; chỉ HTTPS. **Ký bằng biến môi trường** (`HOICON_KEYSTORE_FILE`, `HOICON_KEYSTORE_PASSWORD`, `HOICON_KEY_ALIAS`,
`HOICON_KEY_PASSWORD`): không có đủ bốn biến thì dựng **không ký** (AAB không chữ ký, APK `-unsigned`). Lần này không có khóa nên **AAB chưa ký**, chưa tải lên
Play được. Cấu hình build chạy được cả với configuration cache (đã bỏ khối `doFirst` gây lỗi ở release).

| Lệnh | Kết quả |
|---|---|
| `gradlew :app:assembleRelease :app:bundleRelease` (không cờ) | thành công; AAB 4 603 319 byte, sha256 `e060255e265bbc72347a4a00eeb1f9165df9fb2ae631543b258583cbd85c011b` (chưa ký); `aapt2 dump badging`: `versionCode=3 versionName=0.3.0` |
| `bash scripts/release-gate.sh apps/android/app/build/outputs/bundle/release/app-release.aab` (không bỏ qua bước Gradle) | **thoát 0**: quyền cấm ĐẠT, debuggable tắt, R8 ĐẠT (959/3 914 lớp = 24% tên rút gọn, có `proguard.map`), không còn HC_TIMING/HC_SPIKE, cleartext chặn, có câu công khai AI, `ConsentTextsPinTest` khớp; còn 2 mục [KIỂM TAY] (≥ 18 tuổi, privacy-audit) |
| `gradlew :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug` | xanh: 81 + 248 test, 0 lỗi |

**Chạy thử bản release trên hc-api34** (máy ảo; APK release ký tạm bằng khóa debug do AGP tự dùng, **chỉ để chạy thử cục bộ**, không phải bản phát hành):
- Khởi động nguội `MainActivity` (`am start -W` sau `force-stop`, n = 10): TotalTime 705–898 ms (p50 ≈ 750 ms).
- Sàng lọc cuộc gọi khi tiến trình app đã bị dừng (nguội), đo bằng log Telecom (`CallScreeningServiceFilter` "scheduled" → `FILTERING_COMPLETED`, n = 10): 72–108 ms
  (p50 ≈ 83 ms) so với hạn 5 s của Telecom. Số máy ảo, không kết luận về máy thật.
- Cuộc gọi lạ + app ngân hàng mẫu ⇒ SafePause hiện (có "Đây là trợ lý AI HỏiCon", "Cần cẩn thận", "Bác ơi, khoan chuyển tiền đã", "Hỏi con"); không có crash
  (`FATAL` 0), không thấy HC_TIMING/HC_SPIKE trong logcat. Chưa chạy luồng đầy đủ với backend (bản release trỏ `https://api.hoicon.vn`, chưa có máy chủ).

**Ghi chú phát hành (nháp, tiếng Việt, cho kênh internal testing):** "HỏiCon 0.3.0 — bản thử cho gia đình thí điểm. Nhắc bác khoan chuyển tiền khi có số lạ gọi
rồi mở ứng dụng ngân hàng; kiểm tra giúp số điện thoại/đường link lạ; luyện tập nhận biết lừa đảo (có chữ [DIỄN TẬP]); chữ lớn dễ đọc hơn ở màn hình nhỏ. Mọi tin
nhắn tới người thân đều ghi rõ do trợ lý AI HỏiCon gửi."

**BLOCKED / chưa làm:** tải lên Play internal testing (chờ W0-3 Play Console + khóa ký); T012 (máy thật) và T013 (≥ 5 gia đình) **không tick**; T011 **không tick**
vì còn phần "Tiến/Minh tải lên kênh internal testing" và AAB chưa ký; điều kiện vào giai đoạn 2 (spec 012, 034, W0-3) chưa đủ.

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` | 17 spec, 0 lỗi |
| `uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache` (toàn bộ) | 2017 passed |
| `ruff check` / `ruff format --check` | sạch (200 file) |
| `alembic upgrade head && downgrade -1 && upgrade head` (0009 ⇄ 0010) trên DB dev | ổn; `test_schema_0010.py` 8 test |
| `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck` | sinh lại xong, typecheck sạch |
| gitleaks (`.gitleaks.toml`) `backend/src`, `backend/tests`, `docs/schemas`, `docs/setup`, `specs/029-pilot-kit` | 0 rò rỉ |
| Đột biến 21 ca (cổng đồng ý, hạn mức 8/giờ, `extra=forbid`, `StrictBool`, `ON CONFLICT`, lọc thu hồi, quyền lõi, làm tròn khung, hạn lưu 90 ngày, `--confirm-adult`, lọc demo/diễn tập, ngưỡng 90%/5 gia đình, mẫu số ghép giữa kỳ/thu hồi, UUID rút gọn, crash-free thiếu nguồn) | 21/21 làm test đỏ; 2 ca sống ở lượt đầu (lọc thu hồi ở tầng dịch vụ, hạn lưu) đã siết test |

## Phát hiện khi thiết kế (16/10/2026)

- Android (022) gửi `POST /v1/heartbeat` mỗi 15 phút nhưng máy chủ **chưa có route này**. Thiết bị nhận 404 (Android ánh
  xạ thành `ServerError`), và `devices.last_heartbeat_at` chỉ được ghi lúc ghép đôi. T003 sửa việc này.
- Android ánh xạ mọi 403 thành "chưa xác thực" ⇒ T005.

## Quyết định khi thi công (17/10/2026)

- Nhánh `feat/029-pilot-server` tạo từ HEAD (`feat/034-hardening-core`, commit `2e8887e`), **không** từ `origin/tien-collab-dev`: nhánh đó chưa có 034 (chưa push) mà T003 cần `consent_gate` và migration 0009.
- `device_heartbeats(device_id, slot, protected)`: `protected` giữ giá trị của heartbeat ĐẦU TIÊN trong khung (đúng `ON CONFLICT DO NOTHING` theo spec); `slot` có CHECK chia hết 900 giây. Quyền lõi = `call_screening_role` + `usage_access` (plan D2).
- Hạn mức 8 lần/giờ dùng `api/rate_limit.SlidingWindowLimit` (mới). `events.py`/`drills.py` còn bản sao riêng của cùng thuật toán; gộp lại để việc khác.
- `threat_list_version` siết thành `^[0-9a-f]{16}$` (đúng `threat_list.v1`), `app_version`/`rules_version` dùng `VersionName` của `domain/events` (số đầu ≤ 4 chữ số, tổng ≤ 8 chữ số) nên số điện thoại không lọt vào.
- Độ phủ = số khung có heartbeat ÷ số khung ĐẦY ĐỦ trong `[max(created_at, đầu kỳ), min(revoked_at, nay))`. Khung đang chạy dở và khung lúc ghép đôi không tính, nên độ phủ không bao giờ vượt 100%. Thiết bị chưa đủ một khung ⇒ `coverage: null`.
- `gate-m2`: độ phủ tính GỘP mọi thiết bị (in kèm thiết bị thấp nhất); chỉ tiêu NHẬP TAY (crash-free kèm `--crash-source`, `--real-devices`, `--no-high-findings`) thiếu số ⇒ `CHƯA CÓ SỐ` và lệnh thoát 1, không bao giờ tính là đạt.
- `enroll` từ chối gia đình `is_demo` (luật 8: demo không trộn với thí điểm) và gia đình đã xóa.
- `docs/PLAY-POLICY.md` có mục Data safety cho heartbeat.

## Chưa làm / chưa kiểm được

- **Chưa có reviewer độc lập** (`security-privacy-reviewer`) cho route mới và `ops/pilot.py`.
- **Không đo** trên AVD hay máy thật; Android vẫn ánh xạ mọi 403 thành `Unauthorized` tới khi làm T005.
- Báo cáo mới tính bằng dữ liệu dựng sẵn, chưa có gia đình thí điểm thật. Doze có thể kéo độ phủ thật dưới 90% (plan D2).
- CI trên PR, Windows: chưa chạy. Giai đoạn 2 (T011–T014): BLOCKED bởi 012, W0-3.
