# Kế hoạch Spec 032: Coach hằng tuần + báo "mất bảo vệ"

**Mã**: `032-coach-weekly` · **ROADMAP**: `P2-17` · **Làn**: B (+ 1 task đo của A) · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Tin chỉ có bí danh, giờ, số đếm, phần trăm; `agent_steps` chỉ số đếm + khóa mẫu; lệnh Zalo không lưu chữ thô |
| III. LLM | Không dùng LLM (cá nhân hóa Coach bị cắt đầu tiên) |
| IV. Công khai AI | Mọi tin mở đầu "Đây là trợ lý AI HỏiCon." (test luật 6) |
| IV. Đồng ý | Kiểm `guardian_alerts` của người cao tuổi trước mỗi tin; câu mới vào văn bản cùng PR với mã — ★ Minh |
| Luật 9 | Mọi tin qua `deliver` → `messages_out`; ưu tiên tin mất bảo vệ hơn bản tin (FR-006) |
| VII. Bằng chứng | Ngưỡng 24 giờ có số đo AVD (FR-010); máy thật BLOCKED |
| VIII. Ít code | Dùng lại `enqueue` + khóa lũy đẳng (mẫu `retention`), hàm độ phủ của `ops pilot`, `deliver`, `classify` |

## 2. Quyết định

| # | Quyết định | Lý do | Phương án bỏ |
|---|---|---|---|
| D1 | Coach = hai job (`coach_weekly`, `protection_watch`) + `services/coach_service.py`, ghi `agent_runs(graph='coach')` + `agent_steps`; **không** LangGraph | Không interrupt, không LLM, không trạng thái dài; LangGraph thêm checkpoint vô ích. Trace vẫn có (`agent_steps`) | Đồ thị LangGraph 3 nút |
| D2 | Chống trùng bằng khóa `jobs.idempotency_key`/`messages_out` theo đợt/tuần; không bảng `protection_alerts` | Khóa đã có, đã test "gửi đúng một lần" (002) | Bảng trạng thái đợt mất bảo vệ |
| D3 | Độ phủ tuần = cùng hàm độ phủ của `ops/pilot.py` (tách ra `services/heartbeat_service.py` nếu cần) | Một định nghĩa độ phủ cho Gate M2 và cho con cháu | Công thức thứ hai |
| D4 | Lịch: job tự xếp lần kế tiếp khi chạy xong (`run_at` = Chủ nhật 19:00 VN kế tiếp; giờ 07:00 cho tin bị hoãn) + xếp lúc khởi động (mẫu `schedule_daily`) | Không cần cron ngoài; một tiến trình (ADR-002) | cron hệ điều hành trong container |
| D5 | Ngưỡng hạn mức riêng cho bản tin (dừng ở `warn_pct` 80%) | Bản tin là tin "có cũng được"; không được ăn vào phần dành cho cảnh báo | Dùng chung `hold_pct` |
| D6 | Opt-out theo **người giám hộ** (`members.weekly_digest_enabled`), không theo gia đình | Hai người giám hộ có thể muốn khác nhau; tin mất bảo vệ không opt-out được (an toàn) | Cột trên `families` |
| D7 | Cờ `HOICON_PROTECTION_WATCH` (mặc định bật) cho phần I4 | I4 chưa có duyệt phạm vi của Minh; tắt được mà không gỡ mã | Không cờ |

## 3. Ước lượng hạn mức

Mỗi bot ≤ 50 người giám hộ ⇒ bản tin tuần ≈ 50 × 4,35 ≈ **218 tin/tháng/bot** (7% của 3.000). Tin mất bảo vệ: ước lượng ≤ 2/người/tháng
⇒ ≤ 100. Tin xác nhận "tắt/bật tin tuần": không đáng kể. Tổng ≤ 11% hạn mức, còn > 85% cho cảnh báo sự cố. Số thật đo ở thí điểm.

## 4. Bản đồ file

| Làn | File | Thay đổi |
|---|---|---|
| B | migration `<số>_member_weekly_digest`, `db/models.py`, `tests/integration/test_schema_<số>.py` | mới |
| B | `services/coach_service.py`, `jobs` (handler `coach_weekly`, `protection_watch`, lịch), `agents/texts.py` (2 mẫu tin + xác nhận) | mới / sửa |
| B | `channels/inbound.py` (`classify`), handler `zalo_update` | sửa |
| B | `config.py` (`protection_watch`, ngưỡng 24 giờ, giờ im lặng) | sửa |
| B | `data/coach/tips.vi.yaml` (`approved: false`) + test hợp lệ | mới |
| B | `tests/integration/test_protection_watch.py`, `test_coach_weekly.py`, `tests/unit/test_inbound_classify.py` (mở rộng) | mới / sửa |
| A | `specs/032-coach-weekly/evidence.md` (số đo Doze/standby); không sửa mã Android (trừ ghim sha văn bản) | đo |
| docs | `guardian_alerts.vi.md` + `manifest.json`, `AGENTS.md`, `DATA-MODEL.md`, `PRIVACY-DPIA.md`, `PILOT-PROTOCOL.md` | sửa |

## 5. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Báo nhầm "mất bảo vệ" do Doze/hãng diệt nền (Xiaomi, Oppo) | **Cao** (mất niềm tin) | 24 giờ + đo FR-010; câu chữ "có thể" không khẳng định; số thật ở thí điểm (SC-007) |
| `guardian_alerts` vượt 160 từ khi 031 và 032 cùng thêm câu | TB | Gộp một câu chung "HỏiCon cũng báo khi máy bác không còn được bảo vệ, gửi tóm tắt mỗi tuần, và soạn sẵn hồ sơ khi con bác nghi bác bị lừa"; rút gọn câu khác |
| Bản tin làm người giám hộ chủ quan ("tuần nào cũng yên") | Thấp | Luôn kèm độ phủ; không dùng chữ "an toàn" |
| Lệnh "tắt tin tuần" bị hiểu nhầm là tắt mọi cảnh báo | TB | Câu xác nhận nói rõ "Anh/chị vẫn nhận cảnh báo khi có chuyện" |

## 6. Rà soát `/speckit-analyze` (18/10/2026, vòng 1)

Phủ FR: 11/11 có task. **0 CRITICAL, 0 HIGH, 3 MEDIUM, 1 LOW.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| K1 | MEDIUM | `backend/Dockerfile` chỉ chép `data/` được liệt kê ⇒ `data/coach` không có trong ảnh | T005 thêm `COPY` + test hạ tầng |
| K2 | MEDIUM | I4 chưa có ý kiến Minh (MASTER-PLAN §8 mục 1) | Cờ `HOICON_PROTECTION_WATCH` (D7); ghi §8 mục 5 |
| K3 | MEDIUM | Ngưỡng 24 giờ chưa có số đo | T011 đo AVD; SC-007 thí điểm |
| K4 | LOW | Lượt `coach` không hiện ở `/trace` của người giám hộ (`_visible_run` dựa vào sự cố) | Ngoài phạm vi; ROADMAP "Ghi chú" (T009) |
