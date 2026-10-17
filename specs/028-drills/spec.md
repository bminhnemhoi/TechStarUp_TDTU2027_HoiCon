# Spec 028: Diễn tập nhận biết lừa đảo v1 (E11, bảng `drills`, debrief)

**Mã ROADMAP**: `P2-13` · **Làn**: A (Android) + B (server) · **User story PRD**: US-08 · **Cột mốc**: Gate M2
· **Phụ thuộc**:
- `022-sentinel-v1`: E6, `HeartbeatWorker`, `ConsentLedger`, `Speaker`.
- `024-risk-and-intervention`: mẫu `ElderAnswerWorker`, `texts._message`.
- `021`: `incidents.is_drill` / `drill_id`.
- `020`: đồng ý `drills`.
- `023`: `deliver`, `action_tokens` scope `drill_debrief`.
- `027` chỉ cho phần đặt lịch trên web (P2).

· **Nội dung phụ thuộc**: P1-07 (Minh duyệt kịch bản) · **Nhánh**: `feat/028-drills-server`, `feat/028-drills-android`
· **Tài liệu**: `docs/PILOT-PROTOCOL.md` §Diễn tập, CLAUDE.md luật 8 và 15

---

## 1. Bối cảnh

US-08: "Là gia đình, chúng tôi diễn tập lừa đảo an toàn." Hiện trạng đã đọc ngày 16/10/2026:

| Thành phần | Hiện trạng | Hệ quả |
|---|---|---|
| `PILOT-PROTOCOL.md` | Chỉ trong khung giờ người giám hộ đã đồng ý, tối đa 2 lần/tháng/gia đình; tên cơ quan và số điện thoại **hư cấu**; màu riêng; kết thúc bằng "ĐÂY LÀ DIỄN TẬP"; debrief; người cao tuổi từ chối được bất cứ lúc nào | Ràng buộc cứng của spec |
| CLAUDE.md luật 15 | "Diễn tập dùng màu riêng" (token `drill.*`: `#4C2A85` / `#F5F0FC` / `#7C4DBA`, biểu tượng `school`) | Màn diễn tập **công khai là diễn tập ngay từ đầu**, không giả làm cuộc gọi thật |
| `incidents.drill_id` (021) | Máy tự khai `drill_id` trong sự kiện; máy chủ **không đối chiếu** (mục #5 còn mở của 021) | Lỗ hổng an toàn: máy (hoặc kẻ có token thiết bị) dán nhãn diễn tập cho một sự cố thật thì cảnh báo bị hạ thành `[DIỄN TẬP]`. Spec này đóng lỗ hổng đó (FR-003) |
| Kịch bản `data/scenarios/` | 60 tệp, có `script_vi`, `red_flags`, `teach_points`; **0/60 đã duyệt** (`draft: true`, P1-07 chờ Minh) | Nội dung diễn tập ở bản prod phải được duyệt; chưa duyệt thì không mở diễn tập ("đóng khi chưa duyệt") |
| Đồng ý | Enum `drills` đã có (020); `ConsentLedger` trên máy | Chỉ mở diễn tập khi người cao tuổi đã đồng ý `drills` |
| `action_tokens` | Scope `drill_debrief` đã có, `incident_id` cho phép rỗng | Dùng cho liên kết debrief của người giám hộ (P2) |
| FCM | Chưa có (P0-08) | Máy biết có bài diễn tập bằng cách hỏi máy chủ theo nhịp `HeartbeatWorker` (15 phút), không chờ đẩy |
| Bảng `drills` | DATA-MODEL có khung (`scenario_id`, `scheduled_for`, `window`, `result`, `debriefed_at`), **chưa có migration** | Migration mới, số kế tiếp sau head lúc thi công (026 dự kiến `0007`) |

## 2. Quyết định phạm vi: luyện tập công khai trong app, không gọi điện thật

Bản giao việc không nói diễn tập diễn ra thế nào. Có hai cách:

| Cách | Mô tả | Kết luận |
|---|---|---|
| **A. Luyện tập công khai trong app (E11)** | Đến lượt, máy hiện thông báo "Đến giờ luyện tập". Người cao tuổi bấm vào thì app đọc lời "người gọi" hư cấu bằng TTS, mỗi bước có 2 lựa chọn lớn, cuối bài là debrief. Màn luôn mang màu `drill.*` và `[DIỄN TẬP]` | **chọn cho v1**: không thể nhầm với vụ thật, không cần số điện thoại, không cần FCM, đúng "màu riêng" và "không gây hoảng sợ" |
| B. Người nhà gọi thật từ số lạ, máy gắn nhãn diễn tập | Sát thực tế hơn, đo được "tỷ lệ phát hiện" | **để sau v1**: máy phải biết `h1` của người gọi diễn tập (máy chủ phải giữ và phát `h1`, trái ADR-006/ADR-011). Một vụ thật trùng khung giờ có nguy cơ bị dán nhãn diễn tập. Cần FCM |

Hệ quả cho chỉ số PILOT-PROTOCOL: v1 đo **tỷ lệ vượt qua** (chọn đúng ở mọi bước) và **tỷ lệ hoàn thành / từ chối**,
không đo "tỷ lệ phát hiện bằng cảm biến". Ghi vào ROADMAP "Ghi chú" để Minh cập nhật PILOT-PROTOCOL (★).

## 3. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-08.1 | **P1** | Là mẹ, đến giờ hẹn tôi nhận lời mời luyện tập, chọn "Bắt đầu" hoặc "Để lúc khác"; bài tập đọc to, chữ lớn, màu riêng, ghi rõ `[DIỄN TẬP]`; cuối bài tôi được khen chỗ làm đúng và chỉ ra dấu hiệu lừa đảo |
| US-08.2 | **P1** | Là con, sau khi mẹ tập xong, tôi nhận tin Zalo `[DIỄN TẬP]` tóm tắt kết quả và gợi ý gọi lại cho mẹ để cùng rút kinh nghiệm |
| US-08.3 | **P1** | Là đội thí điểm, tôi đặt lịch diễn tập cho một gia đình bằng lệnh ops, trong khung giờ đã đồng ý, không quá 2 lần/tháng |
| US-08.4 | **P1** | Là hệ thống, một sự cố **thật** không bao giờ bị dán nhãn diễn tập chỉ vì máy tự khai `drill_id` |
| US-08.5 | **P2** | Là con, tôi đặt lịch diễn tập trên web người giám hộ (cần 027) |

## 4. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | `is_drill` ở mọi nơi | 100% đối tượng phát sinh từ diễn tập (dòng `drills`, job, `messages_out`, tin Zalo, payload API, màn E11) mang `is_drill`/`[DIỄN TẬP]`; tin Zalo diễn tập mở đầu bằng câu công khai AI và có `[DIỄN TẬP]` | pytest quét bảng + test hợp đồng + test UI |
| **(SC-002)** | Không hạ cấp sự cố thật | Sự kiện mang `drill_id` không khớp một bài diễn tập đang chạy của **chính gia đình đó** ⇒ bị coi là sự cố **thật** (`is_drill=false`), có log cảnh báo; 0 đường nào khiến sự cố thật thành diễn tập | pytest tích hợp (ma trận: không có bài, bài nhà khác, bài đã hết hạn, bài đúng) |
| **(SC-003)** | Giới hạn & đồng ý | Đặt lịch ngoài khung giờ đã đồng ý, quá 2 lần/tháng/gia đình, người cao tuổi chưa đồng ý `drills`, hoặc kịch bản chưa duyệt (bản prod) ⇒ bị từ chối kèm lý do; người cao tuổi bấm "Để lúc khác" hoặc "Dừng" ⇒ ghi `declined`/`aborted`, không nhắc lại trong khung đó | pytest + test JVM |
| **(SC-004)** | E11 cho người cao tuổi | Ảnh AVD API 36 ở 100% và 200% cho 4 màn (lời mời, bước, debrief, đã dừng): chữ ≥ 20sp, vùng chạm ≥ 64dp, ≤ 2 hành động chính mỗi màn, tương phản ≥ 7:1 (`drill.*`), luôn có `[DIỄN TẬP]` + biểu tượng, tự đọc to; `ux-elder-reviewer` không còn mục chặn | ảnh + reviewer |
| **(SC-005)** | Đầu–cuối trên máy ảo | Ops đặt lịch ⇒ máy nhận trong ≤ 1 nhịp heartbeat (ép chạy ngay trong test) ⇒ thông báo ⇒ hoàn thành ⇒ kết quả lên máy chủ (gửi lại an toàn khi mất mạng) ⇒ tin `[DIỄN TẬP]` tới Zalo mock | log E2E trên AVD API 36 |
| **(SC-006)** | Chỉ dữ liệu tất định | Máy chủ chỉ nhận mã lựa chọn (`choice_id`) theo enum của kịch bản, không văn bản tự do, không ghi âm; không gọi LLM ở bất kỳ bước nào của diễn tập | test hợp đồng + grep `llm_router` trong mã mới |

## 5. Yêu cầu chức năng

- **(FR-001)** Hợp đồng trước, mỗi schema có fixture `valid`/`invalid` và test hợp đồng:
  - `drill_script.v1.json`: kịch bản diễn tập trong `data/drills/*.yaml`.
    - Trường: `id`, `scenario_ref`, `title`, `agency_fictional`, `caller_last3_fictional`, `steps[]` (`line_vi`,
      `choices[2]` gồm `id`, `label_vi`, `correct`, `feedback_vi`), `debrief`, `approved`.
    - Mọi chuỗi qua kiểm "không số điện thoại thật" (mẫu số hư cấu trong `data/fixtures/phones.json`).
  - `drill_offer.v1.json`: máy hỏi bài diễn tập; trả về bài kèm kịch bản đã nhúng, hoặc `null`.
  - `drill_result.v1.json`: máy gửi kết quả gồm `drill_id`, `status`, `answers[]` (`step`, `choice_id`), `started_at`,
    `completed_at`.
- **(FR-002)** Migration (số kế tiếp sau head; chỉ làn B tạo):
  - Bảng `drills`: `id`, `family_id` (FK `CASCADE`), `member_id` (người cao tuổi), `scheduled_by` (thành viên hoặc
    `ops`), `script_id`, `window_start`, `window_end`.
    - `status` ∈ {`scheduled`, `offered`, `in_progress`, `passed`, `failed`, `aborted`, `declined`, `expired`}.
    - `score` (số bước đúng), `answers` jsonb (chỉ mã), `offered_at`, `started_at`, `completed_at`, `debriefed_at`,
      `is_demo`, `created_at`.
    - CHECK khung giờ từ 30 phút tới 4 giờ (`window_end - window_start` trong [30 phút, 4 giờ]); 30 phút bảo đảm máy
      hỏi được ít nhất một lần theo nhịp heartbeat 15 phút.
    - Chỉ mục `(family_id, window_start)`.
  - `models.py` và `DATA-MODEL.md` cập nhật theo.
- **(FR-003)** Đóng lỗ hổng `drill_id` tự khai ở `POST /v1/events`:
  - Sự kiện mang `drill_id` chỉ được coi là diễn tập nếu `drill_id` thuộc gia đình của thiết bị, đang `in_progress`, và
    `occurred_at` nằm trong khung giờ của bài.
  - Ngược lại thì bỏ `drill_id`, đặt `is_drill=false` (xử lý như sự cố thật) và log `warning` (không có PII).
  - Áp ngay cả khi 028 chưa sinh sự kiện cảm biến nào (lựa chọn A), để đóng mục #5 của 021.
- **(FR-004)** `DrillService` (`services/drill_service.py`):
  - `schedule(family, elder, window, script_id, by)`: kiểm đồng ý `drills` mới nhất của người cao tuổi đang `granted`,
    tối đa 2 bài/tháng dương lịch theo giờ Việt Nam, khung giờ ≤ 4 giờ và ở tương lai, kịch bản tồn tại và (khi
    `HOICON_ENV=prod`) `approved`.
  - `offer(device)`: trả bài đang trong khung giờ mà chưa bị từ chối, chuyển sang `offered`.
  - `record_result(device, result)`: lũy đẳng theo `drill_id`; kiểm mã lựa chọn thuộc kịch bản; tính `score`;
    `passed` = mọi bước chọn đúng.
  - `expire()`: job đánh `expired` cho bài quá hạn.
  - Mọi chuyển trạng thái của bài đi qua một hàm duy nhất, có bảng cạnh hợp lệ.
- **(FR-005)** API thiết bị (JWT thiết bị):
  - `GET /v1/drills/offer` theo `drill_offer.v1`.
  - `POST /v1/drills/{id}/result` theo `drill_result.v1`: 404 nếu là bài của gia đình khác; 409 nếu chuyển trạng thái
    không hợp lệ.
  - Hạn mức 30 lần/giờ/thiết bị.
- **(FR-006)** Debrief cho người giám hộ:
  - Khi bài kết thúc (`passed`/`failed`/`aborted`), xếp job `notify_guardian` với mẫu
    `texts.drill_debrief(alias, passed, red_flags_vi)`, khóa `{drill_id}:msg:debrief`.
  - Tin mở đầu bằng "Đây là trợ lý AI HỏiCon." và có `[DIỄN TẬP]`, đi qua `deliver` (`is_drill=true`, nên không bao giờ
    hiện như thật).
  - Bài `declined` thì không gửi gì.
- **(FR-007)** Lệnh ops (P1, dùng cho thí điểm theo PILOT-PROTOCOL):
  - `python -m hoicon.ops.drills schedule --family <id> --at <ISO> --minutes <≤240> --script <id>`.
  - `list --family`; `cancel`.
  - Chỉ in id và trạng thái, không in PII.
- **(FR-008)** Android: nhận lời mời.
  - `HeartbeatWorker` gọi thêm `GET /v1/drills/offer` khi `mayShare()` đúng **và** đã có dòng đồng ý `drills`.
  - Có bài thì hiện thông báo thường (kênh "Luyện tập", không full-screen, không âm thanh khẩn): "[DIỄN TẬP] Đến giờ
    luyện tập nhận biết lừa đảo".
  - Không hiện khi cửa sổ rủi ro đang mở hoặc SafePause đang hiện; khi đó chờ nhịp sau.
- **(FR-009)** Android E11 (`DrillActivity`, `exported=false`, Compose, token `drill.*`):
  - Màn lời mời có "Bắt đầu" và "Để lúc khác".
  - Mỗi bước: `[DIỄN TẬP]` cố định ở đầu màn; `Speaker` đọc `line_vi`; 2 nút lựa chọn ≥ 64dp; nút phụ "Dừng luyện tập".
  - Debrief: câu công khai AI, khen chỗ đúng, chỉ dấu hiệu lừa đảo (`red_flags`), "ĐÂY LÀ DIỄN TẬP" và nút "Xong".
  - Kết quả gửi qua `DrillResultWorker` (WorkManager, cần mạng, backoff, `KEEP` theo `drill_id`).
  - Không quyền mới, không truy cập danh bạ/cuộc gọi; số điện thoại trong bài chỉ là `caller_last3_fictional`.
- **(FR-010)** Nội dung diễn tập v1:
  - 3 tệp `data/drills/*.yaml` soạn từ 3 kịch bản (giả công an, giả nhân viên ngân hàng, "con cháu cần tiền gấp").
  - Tên cơ quan hư cấu (không trùng cơ quan thật), giọng ấm áp, không đe dọa.
  - `approved: false` cho tới khi Minh duyệt. Bản dev/test chạy được với `approved: false`; bản prod từ chối.
  - Dùng skill `add-scam-scenario` / `vietnamese-scam-redteam` để soạn và `ux-elder-reviewer` để duyệt câu chữ.
- **(FR-011)** (P2, cần 027) Web người giám hộ có trang `/drills`: đặt lịch (khung giờ, kịch bản), xem lịch sử; gọi
  `POST /v1/guardian/drills` dùng chung `DrillService.schedule`.
- **(FR-012)** Kiểm chứng & tài liệu:
  - Test: pytest (dịch vụ, API, FR-003, debrief), contract, JVM (`DrillEngine` chấm điểm), Android unit.
  - Ảnh E11 + `ux-elder-reviewer`; `security-privacy-reviewer`.
  - E2E trên AVD API 36.
  - Cập nhật `docs/API.md`, `docs/DATA-MODEL.md`, `docs/DESIGN-SYSTEM.md` (E11), ROADMAP "Ghi chú" (chỉ số PILOT-PROTOCOL,
    lựa chọn B để sau).

## 6. Bất biến & ranh giới

1. **Luật 8:** `is_drill` ở mọi nơi; tên cơ quan và số hư cấu; debrief; không bao giờ báo như sự cố thật. **Cờ diễn tập
   chỉ do máy chủ cấp** (FR-003).
2. **Luật 6:** debrief trên máy và tin Zalo mở đầu bằng câu công khai AI.
3. **Luật 7:** dùng mục đích đồng ý `drills` có sẵn; người cao tuổi rút đồng ý thì không còn lời mời.
4. **Không LLM, không văn bản tự do, không ghi âm.** Kết quả chỉ gồm mã lựa chọn.
5. **Android:** không thêm quyền; thông báo dùng `POST_NOTIFICATIONS` đã có; không full-screen intent cho diễn tập; không
   đè lên SafePause.
6. Migration mới, không sửa `0001`…`0006`. Chỉ làn B tạo migration.

## 7. Ngoài phạm vi

Diễn tập bằng cuộc gọi thật (lựa chọn B) · cá nhân hóa kịch bản bằng LLM (Coach, 032) · trả lời bằng giọng nói (danh sách
cắt) · bảng xếp hạng/điểm thưởng · diễn tập qua Zalo cho người giám hộ.
