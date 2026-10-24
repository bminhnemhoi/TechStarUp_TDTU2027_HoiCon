# Bằng chứng nghiệm thu Spec 032: Coach hằng tuần + báo "mất bảo vệ"

- **Trạng thái (22/10/2026, Wave 3 làn B)**: T001–T009 xong (mã server + test + tài liệu); T010/T011 (Android, làn A), T012 (reviewer), T013 (cổng cuối) chưa; T014/T015 BLOCKED. Không có hợp đồng mới trong `docs/schemas/` (xem tasks.md).
- **Nguồn số dự kiến**: pytest (đồng hồ giả) + AVD `hc-api36` cho khoảng trống heartbeat (máy ảo ≠ máy thật); máy thật BLOCKED.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 phát hiện đúng | `silent` 24 giờ ± 1; `permission_off` 2 khung; 0 tin khi không đủ điều kiện | pytest | `test_protection_watch.py` (11, đồng hồ giả): 23 giờ ⇒ 0, 25 giờ ⇒ 1; 1 khung `false` ⇒ 0, 2 khung ⇒ 1 (mốc = khung `false` đầu tiên của đợt); thu hồi/demo/chưa đồng ý/chưa từng heartbeat/cờ tắt ⇒ 0; 22:30 hoãn tới 07:05; hạng 2 khi hạng 1 không có chat. Máy dev, DB dev, n = 1 lượt/ca | ĐẠT |
| SC-002 một tin mỗi đợt | 48 lần chạy ⇒ 1 tin | pytest | 48 lượt cùng đợt ⇒ 1 tin; máy báo về rồi mất lại (> 24 giờ sau) ⇒ tin thứ hai; đợt mới trong 24 giờ ⇒ không tin thêm; `coach_weekly` chạy hai lần cùng tuần ⇒ 1 tin/người giám hộ | ĐẠT |
| SC-003 bản tin đúng số | khớp seed; 0 câu "an toàn" khẳng định | pytest | `test_coach_weekly.py` (10): số lần nhắc (loại diễn tập/demo/ngoài 7 ngày) = 2, đã xử lý = 1, bài luyện tập = 1, độ phủ làm tròn 5%; opt-out theo người; `test_coach_texts.py` (36): không chuỗi "an toàn" ở mọi biến thể | ĐẠT |
| SC-004 hạn mức | 80% / 95% đúng hành vi; tin sự cố không ảnh hưởng | pytest | `test_coach_quota.py` (3): 75% ⇒ cả hai đi; ≥ 80% ⇒ bản tin `held_quota` (không thử lại), tin mất bảo vệ vẫn đi; ≥ 95% ⇒ cả hai giữ, tin sự cố khẩn vẫn `sent`. Hạn mức test = 20 tin | ĐẠT |
| SC-005 công khai AI + PII | 100% công khai; 0 PII | pytest | mọi mẫu mở đầu "Đây là trợ lý AI HỏiCon"; không dãy ≥ 4 chữ số, `mask_text` không đổi gì; quét `jobs`/`agent_steps` không có số/tên gói/h1; trace không chứa chữ tin | ĐẠT |
| SC-006 ngưỡng 24 giờ | khoảng trống dài nhất trên AVD < 24 giờ | AVD | chưa chạy (task T011 làn A) | CHƯA ĐO (làn A) |
| SC-007 máy thật | tỷ lệ báo nhầm 7 ngày thí điểm | thí điểm | — | BLOCKED (029 giai đoạn 2) |

## Wave 3 làn A (22/10/2026) — T011 chưa làm

Task cần 5 điều kiện đo liên tục (2 giờ + 2 giờ + 4 giờ + khởi động lại + kill) trên máy ảo với backend dev chạy suốt, tổng ≳ 8 giờ máy chạy; ngoài khả năng một phiên làm việc. Điều kiện tiên quyết
của task không nêu gì khác. Chưa đo, không tick T011; việc cho một phiên chạy dài (hoặc `adb shell cmd jobscheduler` ép nhịp không áp dụng được cho WorkManager định kỳ, xem evidence 028).

## Wave 3 — ghi chú thi công (làn B, 22/10/2026)

- **Migration `0012`** (`members.weekly_digest_enabled`) áp lên DB dev sau `0011` của 031 (head = 0012). Hạ tầng: `data/coach` thêm vào `backend/Dockerfile` + test; `roles.sql` cần chạy lại sau migration (cấp theo vòng lặp mọi bảng).
- **Lệch so với chữ của tasks (cần Opus):**
  1. `send_to_guardian` mở rộng cho tin Coach: `job_key`, `urgent`, `member_id`, `quota_class` trong payload (tin sự cố giữ hành vi cũ); `quota_class = digest` ⇒ ngưỡng giữ = `warn_pct`.
  2. Chống trùng 24 giờ dựa vào `payload.queued_at` (đồng hồ của lượt chạy), không `jobs.created_at` (đồng hồ DB) để test đồng hồ giả đúng.
  3. Giờ trong tin mất bảo vệ viết "07:30 ngày 20 tháng 10" (dạng "20/10" bị `mask_text` che thành `[MÃ]`).
  4. Test hạn mức đặt chung ở `test_coach_quota.py`, không tách vào hai tệp `-k quota` như Verify; các hàm `find_protection_lapses`/`run_*` nhận `family_id` tùy chọn **chỉ để test** (DB dev dùng chung).
  5. T008: văn bản đồng ý đã vào ở 031 T011 và được sửa theo `ux-elder-reviewer` (khác chữ Opus soạn; xem evidence 031); ý I4 chưa quyết ⇒ giữ câu "Họ được báo nếu HỏiCon bị tắt"; `docs/PILOT-PROTOCOL.md` §4 đã thêm lại dòng.
  6. Hướng dẫn mẹo `tips.vi.yaml` có tệp (`approved: false`) và test hai chế độ; T015 (Minh duyệt) BLOCKED.
- **Chưa làm / ngoài quyền:** `ux-elder-reviewer` cho 5 mẫu tin và `security-privacy-reviewer` cho 032 (T012 không nằm trong phạm vi lượt này); dòng ROADMAP "Ghi chú" về trace của lượt `coach` (cấm sửa ROADMAP) — **việc cho Tiến/Opus**; chưa có route web cho người giám hộ xem trace lượt `coach`.
- **Rủi ro đã biết:** tin mất bảo vệ phụ thuộc heartbeat 15 phút; cho tới khi T011 (đo Doze/Standby trên AVD) có số, ngưỡng 24 giờ chưa được kiểm chứng.

## Wave 4 làn A (23/10/2026) — T011: bộ đo heartbeat ĐANG CHẠY NỀN (chưa có số đo, KHÔNG tick)

**Bắt đầu 23/10/2026 00:42 (+07)** = 22/10 17:42 UTC, trên `hc-api36` (headless) + backend dev cổng 18001, DB `hoicon_android`, thiết bị đã ghép đôi và đã đồng ý E3 bản `2026.10-v4`
(`guardian_alerts` v4 trong sổ), quyền lõi đã cấp (`protected`). Máy ảo ≠ máy thật.

Trình điều khiển `heartbeat-gap/driver.py` (**ngoài repo**: `~/hoicon-evidence/032-coach-weekly/heartbeat-gap/`), chạy tiếp được nếu bị ngắt (`state.json`), tự bật lại API 18001 nếu tắt. Năm điều kiện nối tiếp, tổng 10 giờ dự kiến (**dự kiến xong ≈ 10:45 +07 cùng ngày, 03:42 UTC**):

| # | Điều kiện | Cách áp dụng | Đo |
|---|---|---|---|
| a | bình thường | không can thiệp | 2 giờ |
| b | Doze | `dumpsys deviceidle force-idle` (đặt lại mỗi 15 phút; `unforce` khi hết) | 2 giờ |
| c | standby bucket `rare` | `am set-standby-bucket vn.hoicon.sentinel rare` (đặt lại mỗi 15 phút; trả `active` khi hết) | 4 giờ |
| d | khởi động lại máy | `adb reboot` | 1 giờ sau đó |
| e | tiến trình bị kill | `am kill vn.hoicon.sentinel` | 1 giờ sau đó |

d và e đo 1 giờ vì task không nêu thời lượng. Khoảng trống dài nhất = lớn nhất trong {đầu cửa sổ → khung đầu, giữa các khung liên tiếp, khung cuối → cuối cửa sổ}; bình thường ≈ 15 phút (WorkManager chu kỳ 15 phút).
Chỉ đọc cột `device_id`, `slot` của `device_heartbeats` (không định danh, không nội dung).

**Thu kết quả:** `cat ~/hoicon-evidence/032-coach-weekly/heartbeat-gap/results.json` (mỗi điều kiện: `so_khung_co_heartbeat`, `so_khung_ky_vong`, `khoang_trong_dai_nhat_phut`, cờ `emulator_lost` nếu máy ảo mất kết nối)
và `log.txt` (sự kiện: API/emulator tắt). Tiến độ: `cat state.json`. Điều kiện Verify: khoảng trống dài nhất mọi điều kiện < 24 giờ (1 440 phút); nếu không ⇒ đề xuất ngưỡng mới trong spec. **Không tick T011 tới khi results.json đủ 5 điều kiện.**
Nếu phiên làm việc đóng: driver là tiến trình `setsid` độc lập, không phụ thuộc phiên; nếu máy chủ bị khởi động lại, chạy lại lệnh `driver.py <device_id>` (không mất `state.json`).
Giới hạn đã biết: máy ảo không sạc/dùng pin thật nên Doze/standby không phản ánh Samsung/Xiaomi/Oppo; chỉ là trần trên của hành vi AOSP.

## Wave 6 — T012, T013 phần backend/web (làn B, 24/10/2026)

- **T012 ĐẠT**: `ux-elder-reviewer` (5 mẫu tin: `guardian_protection_silent`, `guardian_protection_permission_off`, `weekly_digest`, `digest_off_ack`, `digest_on_ack`; đều qua `_message` nên mở bằng câu công khai AI): 0 Chặn, 4 Cao, 4 Trung bình, 4 Thấp. **Cao đã sửa** trong `agents/texts.py`: bản tin "chưa thể nói gì" ⇒ "chưa có số liệu để tóm tắt"; bản tin thêm việc cụ thể (có sự cố ⇒ "hỏi thăm {alias}", độ phủ < 70% ⇒ "nhờ {alias} mở lại ứng dụng"); `digest_off_ack` hết câu sai nghĩa "HỏiCon vẫn nhận cảnh báo" (+ test đỏ→xanh, `test_coach_texts.py` 37 passed). **Cao chưa sửa — chủ Minh** (tệp `data/coach/tips.vi.yaml`, ngoài quyền làn B và đang chờ duyệt T015): mẹo viết cứng "bác" trong khi bí danh do người dùng đặt ⇒ dùng chỗ trống `{alias}` hoặc viết mẹo không nhắc người (cần thêm thay thế ở `texts.py`). Trung bình/Thấp còn lại (câu trấn an ở tin mất bảo vệ, "chiều Chủ nhật" vs gửi 19:00, "độ phủ" thuật ngữ, "chưa làm bài luyện tập" nghe trách): chủ Tiến.
  `security-privacy-reviewer` (job, `agent_steps`, lệnh Zalo, đồng ý, hạn mức): **0 Critical, 0 High, 3 Medium, 3 Low**. **Medium #2 ĐÃ SỬA**: `ack_digest_on/off` coi là khẩn và không nằm trong `QUIET_TEMPLATES` ⇒ lặp "tắt/bật tin tuần" đốt hạn mức Zalo; nay im lặng sau 10 tin/giờ và không khẩn (test `test_repeatable_replies_are_not_urgent…` đỏ→xanh). **Chưa sửa (chủ Tiến, hạn đề xuất 08/11/2026)**: #1 `protection_watch`/`coach_weekly` chưa kiểm `core_protection` (rút `core_protection` ⇒ heartbeat dừng ⇒ có thể sinh tin "mất bảo vệ" sai và bản tin tuần vẫn dùng heartbeat cũ); #3 bản tin tuần đếm sự cố theo gia đình nhưng đồng ý/thiết bị lấy theo thiết bị đầu tiên (nhà nhiều người cao tuổi) — cần xác nhận ràng buộc "một người cao tuổi/gia đình"; Low: lọc `deleted_at` lúc gửi, tên thật trong bí danh nằm ở `jobs.payload.text` 30 ngày (luật 1; nghi vấn luồng nhập bí danh), hạn mức heartbeat theo tiến trình (ADR-002).
- **T013 CHƯA TICK (phần [A] chờ làn A)**: phần backend/web đạt — pytest 2881 passed / 22 skipped / 1 xfailed; ruff sạch; eval smoke không lệch baseline; gitleaks `backend/src`, `backend/tests`, `data/coach`, `docs/legal`, `specs/032-coach-weekly` sạch; `check-spec-trace` 0 lỗi. Chờ làn A: `$GRADLE :app:testDebugUnitTest` và ROADMAP `P2-17`.

## Wave 6 — T011 đo khoảng trống heartbeat (làn A, 24/10/2026)

**Nguồn: máy ảo `hc-api36` (API 36), backend dev cổng 18001, DB `hoicon_android`, bảng `device_heartbeats` (chỉ đếm khung 15 phút, không in định danh). Máy ảo ≠ máy thật** — số ở máy thật (Doze/hãng) chưa đo. Bộ đo: `~/hoicon-evidence/032-coach-weekly/heartbeat-gap/` (driver.py, log.txt, results.json; ngoài repo).

| Điều kiện | Cách làm | Thời gian | Khung có heartbeat | Khoảng trống dài nhất |
|---|---|---|---|---|
| (a) bình thường | không can thiệp | 2 giờ | 8/8 | 15,0 phút |
| (b) Doze | `dumpsys deviceidle force-idle` (đặt lại mỗi 15 phút) | 2 giờ | 8/8 | 15,0 phút |
| (c) standby rare | `am set-standby-bucket vn.hoicon.sentinel rare` | 4 giờ | 16/16 | 15,0 phút |
| (d) khởi động lại | `adb reboot`, đo 60 phút sau | 1 giờ | 3/4 | 21,95 phút |
| (e) kill tiến trình | `am kill vn.hoicon.sentinel` | 1 giờ | 3/4 | 22,07 phút |

- **Kết luận:** khoảng trống dài nhất 22,07 phút ≪ 24 giờ (ngưỡng "mất bảo vệ", Q2) ⇒ **ĐẠT**, không cần ngưỡng mới. Sau reboot/kill thiếu đúng 1 khung (chờ WorkManager lập lại lịch, ≈ một chu kỳ + độ trễ khởi động), không phải mất heartbeat kéo dài; ngưỡng 24 giờ và "2 khung `protected=false`" không bị chạm ⇒ không báo nhầm cho người giám hộ ở các điều kiện này.
- **Giới hạn:** (a)–(c) đo 22–23/10; (d)/(e) đo lại 24/10 vì lần đo đầu của (d) hỏng khi máy chủ khởi động lại (heartbeat cuối 02:15Z 23/10, cửa sổ cũ bỏ). Một máy ảo, một lần mỗi điều kiện; `hc-api34` chưa đo. Chưa đo: hết pin/tắt máy qua đêm, tiết kiệm pin của hãng (Xiaomi/Oppo/Samsung) — cần máy thật.

## Wave 6 — T013 phần [A] (làn A, 24/10/2026)

- `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug` **xanh** trên `feat/w6-android` (gồm `ConsentManifestPinTest`); `python3 -m unittest discover -s scripts/tests` 121 OK; `check-spec-trace.py` 25 spec, 0 lỗi; gitleaks `specs/032-coach-weekly` và `docs/legal` (kết quả ở dòng lệnh cuối phiên). Phần [B] (`$PYTEST`, ruff, eval smoke, gitleaks backend/data, ROADMAP P2-17) do làn B — T013 chưa tick ở đây.

- **T013 tick (nhà điều phối 24/10/2026)**: phần B (lượt W6 làn B: pytest, ruff, eval smoke) + phần A (b2e75d3: Gradle xanh) đều đạt; ROADMAP P2-17 cập nhật cùng lượt.
