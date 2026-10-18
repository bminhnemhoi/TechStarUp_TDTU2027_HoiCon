# Bằng chứng nghiệm thu Spec 028: Diễn tập nhận biết lừa đảo v1

- **Trạng thái**: Làn A (Android) và Làn B (server) đã xong; E2E máy ảo T019 chạy ngày 18/10/2026 (mục "E2E máy ảo" bên dưới).
- **Phụ thuộc nội dung**: 3 kịch bản diễn tập sẽ ở `approved: false` cho tới khi Minh duyệt (P1-07). Bản prod từ chối
  kịch bản chưa duyệt.
- **Môi trường dự kiến**: Linux CachyOS, Postgres dev (cổng 15432), uvicorn, AVD `hc-api36`, Zalo **mock**.
- **Nguồn số**: máy dev và máy ảo (máy ảo ≠ máy thật).

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 `is_drill` ở mọi nơi | 100% đối tượng diễn tập mang `is_drill` / `[DIỄN TẬP]`; tin Zalo có câu công khai AI | `test_api_drills.py`, `test_drill_debrief_delivery.py`, `test_drill_schemas.py` | 100% đối tượng mang nhãn và cờ `is_drill`; tin tổng kết Zalo có `[DIỄN TẬP]` + công khai AI | ĐẠT |
| SC-002 không hạ cấp sự cố thật | `drill_id` không hợp lệ ⇒ sự cố thật; 0 đường hạ cấp | `test_drill_flag_guard.py` (ma trận 6 ca) | 19/19 test passed; ca sai đều bị hạ cờ diễn tập thành sự cố thật | ĐẠT |
| SC-003 giới hạn & đồng ý | chưa đồng ý / quá 2 bài/tháng / ngoài khung / chưa duyệt ⇒ từ chối; "Để lúc khác" ⇒ `declined` | `test_api_drills.py` (91 passed), `test_drill_scoring.py` | Bị từ chối đúng lý do (`monthly_limit`, `consent_required`...); "Để lúc khác" ⇒ `declined` | ĐẠT |
| SC-004 E11 | 8 ảnh (4 màn × 100/200%); ≥ 20sp, ≥ 64dp, ≤ 2 hành động, ≥ 7:1, `[DIỄN TẬP]` luôn hiện, đọc to | ảnh `~/hoicon-evidence/028-drills/shots/` + `DrillScreen.kt` | Đủ 14 ảnh thực địa AVD hc-api36 (100% và 200%), vùng chạm ≥ 64dp, token `drill.*`, tự ngắt khi có cuộc gọi lạ | ĐẠT (Làn A) |
| SC-005 E2E máy ảo | đặt lịch ⇒ nhận ≤ 1 nhịp heartbeat ⇒ hoàn thành ⇒ kết quả lên máy chủ (cả khi mất mạng) ⇒ tin `[DIỄN TẬP]` | E2E AVD API 36 (T019) | Đặt lịch 02:54:11Z ⇒ mời 03:08:59Z (nhịp heartbeat kế tiếp, 14 phút 48 giây sau) ⇒ làm xong 03:10:32Z khi đang mất mạng ⇒ bật mạng 03:10:53Z, máy chủ nhận kết quả ngay (tin tổng kết ghi 03:10:53.727, đồng hồ lệnh bật mạng chỉ chính xác tới giây) ⇒ `messages_out` có 1 tin `debrief`. Chi tiết ở mục E2E bên dưới | ĐẠT (máy ảo; nhánh `failed`) |
| SC-006 chỉ dữ liệu tất định | chỉ mã lựa chọn; 0 văn bản tự do / ghi âm; 0 lời gọi LLM | test hợp đồng + quét DB `test_schema_0008.py` (30 passed) + grep `llm_router` | Không cột nào chứa văn bản tự do, 0 lời gọi LLM, chỉ lưu mã `choice_id` | ĐẠT |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `uv run --directory backend pytest` | 1.783 passed (100% toàn bộ backend test suite) |
| `uv run --directory backend ruff check .` & `ruff format --check .` | Sạch 100% (178 file đúng định dạng) |
| `uv run --directory backend hoicon-eval --suite smoke --compare baseline` | 20/20 ca đạt, recall 100%, báo nhầm 0%, vi phạm 0, lệch baseline +0.0% |
| `pnpm --dir apps/web typecheck` | Sạch 100% (sau khi sinh lại client TS qua `gen-api-client.sh`) |
| `gitleaks dir` (từng thư mục src/tests/migrations/schemas/drills) | 0 rò rỉ mã nguồn (ADR-006 tuân thủ 100%) |
| `python3 scripts/check-spec-trace.py` | 17 spec, 0 lỗi |

## E2E máy ảo (T019, 18/10/2026)

**Môi trường**: AVD `hc-api36` (API 36, headless, máy ảo ≠ máy thật), bản debug của nhánh `tien-collab-dev` @ `1ec9c59`;
backend uvicorn cổng 18000 (bản debug của app mặc định gọi `10.0.2.2:18000`) trỏ vào database riêng `hoicon_e2e028`
(Postgres dev 15432, migration head `0010`); Zalo **mock**. Gia đình `e2e-028` và người giám hộ hư cấu (`fixture-…`).
Giờ dưới đây là UTC (đồng hồ máy ảo hiển thị UTC+7).

| Giờ (UTC) | Mốc | Nguồn |
|---|---|---|
| 02:52:27 | API lên, `/healthz` 200 | log uvicorn |
| 02:52:38 | Người giám hộ mock ghép qua `/start <mã>`; tin `pairing_confirmed` ở `messages_out` | `zalo_simulate`, DB |
| 02:53:37 | App ghép đôi mã 6 số: `POST /v1/pair` 200, rồi `POST /v1/consents` 200 (5 mục đích). Heartbeat đầu 200 ngay sau đó (slot 02:45) | log, DB |
| 02:54:11 | `ops drills schedule --at now --minutes 30 --script drill_police_safe_account` ⇒ `scheduled`, khung 02:54:11 → 03:24:11 | CLI |
| 02:54:58 | Ép `HeartbeatWorker` (`cmd jobscheduler run -f -n androidx.work.systemjobscheduler vn.hoicon.sentinel 0`): **WorkManager từ chối** ("executed before schedule"), dời sang job 6; không có yêu cầu nào lên máy chủ | logcat `WM-WorkerWrapper` |
| 03:08:58 | Nhịp heartbeat tự nhiên (15 phút): `POST /v1/heartbeat` 200, `last_heartbeat_at` đổi | log, DB |
| 03:08:59 | `GET /v1/drills/offer` 200 ⇒ `offered` (`offered_at`); thông báo kênh `drills` "[DIỄN TẬP] Đến giờ luyện tập nhận biết lừa đảo" hiện trên AVD | log, `dumpsys notification` |
| 03:09:21 | Chạm thông báo ⇒ `DrillActivity` (E11) mở: "Đây là diễn tập, không phải cuộc gọi thật", `[DIỄN TẬP]`, "Đây là trợ lý AI HỏiCon" | `dumpsys activity`, ảnh 03 |
| 03:09:26 | "Bắt đầu luyện tập" ⇒ `started_at` | DB |
| 03:09:37 → 03:10:20 | Làm 3 câu: câu 1 `b` (đúng), câu 2 `a` (đúng), câu 3 `a` (**sai**, do chạm nhầm) | ảnh 04–09 |
| 03:10:07 | **Ngắt mạng** (`svc wifi disable` + `svc data disable`; `Active default network: none`) trước khi trả lời câu 3 | adb |
| 03:10:25 | Màn tổng kết khi đang offline: "ĐÂY LÀ DIỄN TẬP", "Bác đã nhận ra được 2 trong 3 tình huống", 3 dấu hiệu lừa đảo | ảnh 10 |
| 03:10:32 | Bấm "Đã hiểu — Xong" ⇒ `completed_at`. Sau 20 giây offline: 0 yêu cầu `POST /v1/drills`, bài còn `offered` | log, DB |
| 03:10:53 | **Bật lại mạng**. `DrillResultWorker` gửi lại: `POST /v1/drills/<id>/result` 200 ⇒ `failed` (điểm 2/3); tin `debrief` ở `messages_out` ghi 03:10:53.727 | log, DB |

**Kết quả ở máy chủ** (`drills`): `status = failed`, `score = 2`, `is_demo = true`,
`answers = [{"step":0,"choice_id":"b"},{"step":1,"choice_id":"a"},{"step":2,"choice_id":"a"}]` (chỉ mã lựa chọn, không văn bản tự do).
`messages_out`: đúng 1 dòng `template_id = debrief`, `status = sent`, `channel = zalo`, `error = mock` (mock đánh dấu không gửi thật),
`job_key = <drill_id>:msg:debrief` (khóa chống gửi trùng). `messages_out` không lưu nội dung tin; văn bản tin được sinh lại từ
cùng hàm máy chủ dùng (`texts.drill_debrief`, nhánh chưa đạt) và có đủ "Đây là trợ lý AI HỏiCon" lẫn "[DIỄN TẬP]".
Log API không chứa số điện thoại.

**Ảnh**: `~/hoicon-evidence/028-drills/e2e/01…10-*.png` (thông báo, 3 câu, tổng kết khi offline).

**Điều cần biết**
1. **Không ép được `HeartbeatWorker` bằng `jobscheduler run`.** WorkManager chặn chạy sớm hơn chu kỳ của công việc định kỳ, nên
   task yêu cầu "ép chạy ngay" không làm được trên bản hiện tại. Bài được nhận ở nhịp tự nhiên kế tiếp (14 phút 48 giây sau
   khi đặt lịch, trong khung 30 phút). Nếu muốn kiểm thử nhanh hơn cần một móc debug (ví dụ `OneTimeWorkRequest` trong
   `ScenarioReceiver`); chưa làm vì ngoài phạm vi T019.
2. **Đồng ý `drills` chưa có đường vào từ app v1** (`ConsentLedger` chỉ ánh xạ quyền cảm biến). Để đặt lịch được, dòng đồng ý
   `drills` của người cao tuổi hư cấu được **chèn thẳng vào DB E2E** (kênh `app`, hash giả `sha256("e2e-028-fixture-drills-consent")`).
   Đây là bước dựng dữ liệu thử, không phải hành vi sản phẩm; cần quyết định nơi người cao tuổi đồng ý `drills` trước thí điểm.
3. **Nhánh `passed` chưa chạy E2E**: lần chạy này chấm 2/3 ⇒ `failed` (tôi chạm nhầm đáp án rủi ro ở câu 3, giữ nguyên làm bằng
   chứng nhánh `failed`). Nhánh `passed` mới được kiểm bằng test tích hợp (`test_api_drills.py`, `test_drill_debrief_delivery.py`).
4. **`drills.debriefed_at` luôn NULL**: không có mã nào ghi cột này (chỉ khai báo trong `models.py`). Việc tổng kết đã gửi được
   suy ra từ `messages_out`. Cần quyết định ghi cột khi gửi tin xong, hoặc bỏ cột khỏi DATA-MODEL.
5. DB dev dùng chung đang ở `0010`; E2E dùng database riêng nên không đụng dữ liệu của người khác.

## Review bảo mật/riêng tư Android (T020, 18/10/2026)

`security-privacy-reviewer` đọc `DrillFlow`, `DrillModel`, `DrillActivity`, `DrillScreen`, `DrillInvitation`, `DrillStore`,
`DrillApiClient`, `Notifications`, `Workers` (heartbeat + worker kết quả), manifest: **0 Critical, 0 High, 4 Medium, 8 Low**
(reviewer chỉ đọc mã, không chạy máy ảo). Đã ổn: `DrillActivity` `exported=false` không intent-filter; `PendingIntent` immutable
không extras; Bearer chỉ ở header, không redirect, release bắt buộc HTTPS; thân kết quả chỉ có `drill_id`, trạng thái, chữ cái
lựa chọn và hai mốc giờ; `is_drill`/`[DIỄN TẬP]` ở cả 4 màn; công khai AI; đồng ý kiểm lại ở worker kết quả; gửi lại `KEEP` theo `drill_id`.

| # | Mức | Xử lý |
|---|---|---|
| 2 | Medium | **Đã sửa.** Cuộc gọi lạ thật khi người cao tuổi mới thấy lời mời không còn báo `aborted` (và không tốn tin Zalo): bài ở lại, thông báo được gỡ và nhịp heartbeat kế tiếp mời lại. Khi đang làm bài vẫn `aborted` kèm các câu đã trả lời. Màn dừng vì cuộc gọi có chữ riêng ("Có cuộc gọi tới… bác cứ lo cuộc gọi trước"), không còn nói "chưa có ai gọi bác thật". Lời đọc to khớp chữ trên màn. Test: `DrillFlowTest` (reason `CALL`, `interrupt()` trả có/không cần gửi kết quả) |
| 3 | Medium | **Đã sửa.** Màn không đọc to trước khi biết cửa sổ rủi ro (`riskWindowKnown`); khi cuộc gọi bắt đầu lúc màn này đang đọc thì dừng chính giọng của nó (an toàn vì SafePause chỉ nói sau khi cửa sổ mở). Chưa có test tự động cho phần âm thanh/TTS (chỉ đọc mã) |
| 4 | Medium | **Đã sửa.** Back ở phản hồi của câu cuối đi tới màn tổng kết thay vì hủy kết quả (`DrillFlow.back()`). Test: `DrillFlowTest` ×2 |
| 1 | Medium | **Chưa sửa, cần Tiến/Minh quyết** (không phải lỗi mã): app chưa có mục đích `drills` (văn bản, phiên bản, ghi/rút). Đồng ý hiện chỉ do máy chủ kiểm; thí điểm ghi bằng văn bản theo PILOT-PROTOCOL. Cần chốt nơi đồng ý (app/Zalo/văn bản) trước khi thí điểm; khi thêm vào `ConsentLedger` phải đưa `drills` vào `granted`/`texts`, nếu không `changes()` sẽ tự sinh dòng rút đồng ý |
| 5–13 | Low | Để lại, ghi để theo dõi: race hẹp `markHandled`/`savePending` (#5); worker kết quả thử lại vô hạn (#6); `reconnect()` chưa hủy công việc gửi kết quả đang chờ (#7); `ConsentWithdrawn` chưa xóa thông báo/script đã lưu (#8); thông báo không hết hạn khi đồng hồ máy sai (#9); thông báo bị vuốt đi thì không còn lối vào bài (#10); xoay màn hình ngắt giọng (#11); `optString` với `null` (#12, hiện không xảy ra vì schema và 3 kịch bản đều có giá trị); chưa `setHideOverlayWindows` (#13) |

**Kiểm lại trên máy ảo sau khi sửa (18/10/2026, hc-api36 nối backend thật cổng 18001, DB `hoicon_android`):**
- #2: mở lời mời rồi giả lập cuộc gọi lạ thật (04:07): không có `POST /v1/drills/…/result`, bài vẫn `offered`, thông báo bị gỡ,
  dấu "đã mời" được xóa; nhịp heartbeat kế tiếp (04:22:14) mời lại. Chưa chụp được màn "Có cuộc gọi tới…" (bị che bởi bảng cuộc gọi); chỉ có test JVM cho lý do `CALL`.
- #4: làm đủ 3 câu, bấm Back ở phản hồi câu cuối ⇒ sang màn tổng kết "3 trong 3" (ảnh `12`, `13` ở `~/hoicon-evidence/028-drills/e2e/`), không hủy kết quả.
- **Nhánh `passed` đã chạy E2E:** "Đã hiểu — Xong" 04:23:03 ⇒ `POST …/result` 200, `drills.status = passed`, `score = 3`, 1 tin `debrief` ở `messages_out` (`error = mock`). Đóng điểm 3 của mục "Điều cần biết" ở trên.

## Bộ lệnh T022 (18/10/2026)

| Lệnh | Kết quả |
|---|---|
| `uv run --directory backend pytest` | lần 1: 2001 passed, 1 failed (`test_trace_sse_live`, thời gian) + 1 error (`test_db_roles` teardown) khi DB dev dùng chung bị chạy song song; chạy lại 2 tệp đó: 5 passed; chạy lại toàn bộ: **1996 passed, 21 skipped, 0 failed** |
| `ruff check` / `ruff format --check` | sạch / 200 tệp đúng định dạng |
| `hoicon-eval --suite smoke --compare baseline` (DB riêng `hoicon_e2e028`) | 20/20 ca, recall 100%, báo nhầm 0%, vi phạm 0, công khai AI 100%, p50/p95 191/291 ms, lệch baseline +0,0 |
| `gradlew :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug` | xanh; 313 test (trước khi thêm test review), 0 lỗi |
| `gitleaks dir --config .gitleaks.toml` từng thư mục `backend/src`, `backend/tests`, `apps/android/app/src`, `docs/schemas`, `data/drills`, `specs/028-drills` | không rò rỉ (không dùng `--config` thì `docs/schemas` báo 1 dương tính giả: SHA-256 của chuỗi rỗng trong fixture `device_me.v1.invalid.json`) |
| `python3 scripts/check-spec-trace.py` | 17 spec, 0 lỗi |

## Cần Minh/Tiến quyết (★)

- Chỉ số PILOT-PROTOCOL: v1 đo tỷ lệ vượt qua / hoàn thành / từ chối, không đo "tỷ lệ phát hiện bằng cảm biến" (spec §2).
- Duyệt 3 kịch bản diễn tập trước thí điểm.
- Nơi người cao tuổi đồng ý `drills` (app v1 chưa có) và số phận cột `drills.debriefed_at` (xem mục E2E, điểm 2 và 4).
