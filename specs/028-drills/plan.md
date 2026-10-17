# Kế hoạch Spec 028: Diễn tập nhận biết lừa đảo v1

**Mã**: `028-drills` · **ROADMAP**: `P2-13` · **Làn**: A + B · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| I. Dừng an toàn | Diễn tập không đụng đường cảm biến/SafePause; lời mời không hiện khi cửa sổ rủi ro mở; không full-screen |
| II. Riêng tư | Không số thật trong kịch bản (kiểm tự động); kết quả chỉ là mã lựa chọn; không quyền Android mới |
| III. LLM | Không có lời gọi LLM nào; nội dung là kịch bản đã duyệt |
| IV. Công khai AI + đồng ý | Debrief và tin Zalo có câu công khai; dùng mục đích `drills` có sẵn |
| V. Hợp đồng trước | 3 schema mới viết trước; migration mới, không sửa cũ |
| VI. UX | E11: ≥ 20sp, ≥ 64dp, 200%, ≤ 2 hành động chính, màu `drill.*` + `[DIỄN TẬP]` + biểu tượng `school`, tự đọc to |
| VII. Bằng chứng | Số E2E là máy ảo; nội dung chưa duyệt ghi rõ |
| VIII. Tái sử dụng | `HeartbeatWorker`, mẫu `ElderAnswerWorker`, `Speaker`, `ConsentLedger`, `deliver`, `texts._message`, `enqueue` có khóa, `_lock` |

## 2. Quyết định kiến trúc

### D1. Diễn tập công khai trong app (lựa chọn A ở spec §2)

Không có cách nào để "cuộc gọi thật nhưng là diễn tập" mà không phải phát `h1` của người gọi xuống máy, và không có nguy
cơ dán nhãn nhầm một vụ thật. Bài trong app luôn mang màu `drill.*`, đúng luật 15 và PILOT-PROTOCOL ("không gây hoảng
sợ"). Chỉ số đo được thay từ "tỷ lệ phát hiện" sang "tỷ lệ vượt qua / hoàn thành / từ chối". Đây là một mục cần Minh xác
nhận (★).

### D2. Cờ diễn tập chỉ do máy chủ cấp (đóng mục #5 của 021)

Trong `POST /v1/events`, trước `correlate_event`:

```
if event.is_drill or event.drill_id:
    drill = SELECT … FROM drills WHERE id = :drill_id AND family_id = :family AND status = 'in_progress'
            AND :occurred_at BETWEEN window_start AND window_end
    if drill is None:  event.is_drill = False; event.drill_id = None; logger.warning("drill flag rejected")
```

- **Ưu tiên an toàn:** nghi ngờ thì xử lý như sự cố thật. Một cảnh báo thật thừa ít hại hơn một vụ thật bị coi là diễn
  tập.
- **Ảnh hưởng tới test cũ:** các test 021/023 đang gửi sự kiện `is_drill=true` phải tạo dòng `drills` hợp lệ trước
  (`tests/integration/test_api_events.py`, `test_api_incidents.py`, `test_incident_service.py`). Đây là thay đổi chủ ý,
  ghi trong evidence.
- Ở v1 (lựa chọn A), máy không sinh sự kiện cảm biến cho bài diễn tập. FR-003 chủ yếu để chặn lạm dụng.

### D3. Máy nhận bài bằng cách hỏi, theo nhịp heartbeat

- Chưa có FCM, mà nhịp heartbeat 15 phút đã có. Khung giờ tối thiểu 30 phút (`window_end - window_start ≥ 30 phút`)
  bảo đảm máy hỏi ít nhất một lần trong khung.
- `offer` trả kịch bản nhúng sẵn, nên máy không cần tải tệp riêng. Bài làm được cả khi mất mạng giữa chừng; kết quả gửi
  sau qua WorkManager.

### D4. Chấm điểm tất định, chạy được trên JVM

`DrillEngine` (JVM thuần, đặt ở module `:rules` hoặc gói `domain/drill` của `:app`) nhận kịch bản + các lựa chọn, trả bước
kế tiếp, điểm và danh sách `red_flags` cần nhắc. Máy chủ chấm lại độc lập trong `record_result` (không tin điểm do máy
gửi lên).

### D5. Nội dung: tệp YAML riêng, duyệt riêng, "đóng khi chưa duyệt"

- Kịch bản diễn tập khác kịch bản eval: eval cần tín hiệu thiết bị và câu trả lời E8; diễn tập cần lựa chọn và phản hồi.
- `drill_script` trỏ về kịch bản eval qua `scenario_ref` để dùng chung `red_flags`/`teach_points` khi phù hợp.
- `approved` là cổng duy nhất ở bản prod: chưa duyệt thì `schedule` báo lỗi `script_not_approved`.

## 3. Máy trạng thái của một bài diễn tập

```
scheduled ─offer─► offered ─start─► in_progress ─┬─ đúng hết ─► passed
    │                 │                           ├─ có sai ───► failed
    │                 └─ "Để lúc khác" ─► declined └─ "Dừng" ───► aborted
    └──── quá window_end (job expire) ─► expired   (offered/in_progress quá window_end + 1 giờ ⇒ expired)
```

Cạnh hợp lệ nằm trong `DrillService.ALLOWED`. Các trạng thái cuối (`passed`, `failed`, `aborted`, `declined`,
`expired`) không có cạnh đi ra. `record_result` gửi lặp cùng nội dung thì trả 200 (lũy đẳng); khác nội dung thì 409.

## 4. Phác thảo hợp đồng (Draft 2020-12, `additionalProperties: false`)

```json
// drill_script.v1.json (YAML trong data/drills/)
{"required": ["id","scenario_ref","title","agency_fictional","steps","debrief","approved"],
 "properties": {"id": {"pattern": "^drill_[a-z0-9_]{3,40}$"},
   "caller_last3_fictional": {"pattern": "^[0-9]{3}$"},
   "steps": {"minItems": 2, "maxItems": 5, "items": {"required": ["line_vi","choices"],
     "properties": {"line_vi": {"maxLength": 400},
       "choices": {"minItems": 2, "maxItems": 2, "items": {"required": ["id","label_vi","correct","feedback_vi"],
         "properties": {"id": {"pattern": "^[a-z]$"}, "label_vi": {"maxLength": 40}}}}}}},
   "debrief": {"required": ["red_flags_vi","praise_vi"]}, "approved": {"type": "boolean"}}}
// drill_offer.v1.json
{"required": ["drill"], "properties": {"drill": {"oneOf": [{"type": "null"},
  {"required": ["drill_id","window_end","script","is_drill"], "properties": {"is_drill": {"const": true}}}]}}}
// drill_result.v1.json
{"required": ["drill_id","status","answers"], "properties": {
  "status": {"enum": ["declined","aborted","completed"]},
  "answers": {"maxItems": 5, "items": {"required": ["step","choice_id"], "properties": {"choice_id": {"pattern": "^[a-z]$"}}}}}}
```

Máy chỉ báo `completed`; máy chủ tự quyết `passed`/`failed` sau khi chấm lại.

## 5. Bản đồ file

| Làn | File | Thay đổi |
|---|---|---|
| chung | `docs/schemas/{drill_script,drill_offer,drill_result}.v1.json` + fixtures; `data/drills/*.yaml` (3 bài) | mới |
| B | `backend/migrations/versions/<ngày>_<số>_drills.py`, `db/models.py` | mới/sửa |
| B | `services/drill_service.py`, `api/routers/drills.py`, `api/routers/events.py` (D2), `agents/texts.py` (`drill_debrief`), `jobs/worker.py` (`drill_expire`), `ops/drills.py`, `domain/drill.py` (chấm điểm, nạp YAML) | mới/sửa |
| B | tests: `contract/test_drill_schemas.py`, `unit/test_drill_scoring.py`, `integration/test_api_drills.py`, `integration/test_drill_flag_guard.py`, `integration/test_schema_<số>.py`; sửa các test cũ gửi `is_drill` | mới/sửa |
| A | `domain/drill/DrillEngine.kt` (+ test JVM), `data/remote/DrillApiClient.kt`, `work/Workers.kt` (`HeartbeatWorker` hỏi bài, `DrillResultWorker`), `ui/DrillScreen.kt`, `DrillActivity.kt`, `sensing/Notifications.kt` (kênh "Luyện tập"), `res/values/strings.xml` | mới/sửa |
| docs | `docs/API.md`, `docs/DATA-MODEL.md`, `docs/DESIGN-SYSTEM.md` (E11), `docs/ROADMAP.md` | sửa |

## 6. Giai đoạn

| Giai đoạn | Nơi làm | Nội dung |
|---|---|---|
| 0 | checkout chính | 3 schema + fixture + 3 kịch bản YAML (`approved: false`) + test hợp đồng |
| B1 | server | migration + model + `DrillService` + chấm điểm |
| B2 | server | D2 (chặn cờ diễn tập tự khai) + sửa test cũ |
| B3 | server | API thiết bị + debrief Zalo + job hết hạn + lệnh ops |
| A1 | android | `DrillEngine` + client + worker (dùng fixture hợp đồng, chưa cần server) |
| A2 | android | E11 + thông báo + ảnh + `ux-elder-reviewer` |
| Z | checkout chính | E2E AVD 36, `security-privacy-reviewer`, tài liệu, evidence |

## 7. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Minh chưa duyệt kịch bản ⇒ prod không mở được diễn tập | Cao (chặn M3/G3: ≥ 20/50 buổi) | "Đóng khi chưa duyệt" là chủ ý. Báo sớm để Minh duyệt 3 bài trước thí điểm |
| D2 làm hỏng luồng diễn tập cũ trong test 021/023 | TB | Sửa test cùng PR; evidence ghi số test đã đổi |
| Người cao tuổi bị làm phiền | TB | ≤ 2 bài/tháng; "Để lúc khác" kết thúc bài; không âm thanh khẩn; không hiện khi đang có cửa sổ rủi ro |
| Kịch bản lỡ dùng tên cơ quan thật | TB | Kiểm tự động bằng danh sách từ cấm (Bộ Công an, VKSND, tên ngân hàng trong `bank_apps.vn.json`…) trong test hợp đồng |
| Khung giờ ngắn hơn nhịp heartbeat | Thấp | CHECK khung ≥ 30 phút; heartbeat 15 phút |
