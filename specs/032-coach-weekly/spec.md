# Spec 032: Coach hằng tuần + báo "mất bảo vệ" (ý tưởng I4)

**Mã ROADMAP**: `P2-17` · **Làn**: B (`backend/**`, `data/coach/**`) + một task đo của A · **Cột mốc**: MVP Vòng 2 (M3) ·
**Phụ thuộc**: 022 (heartbeat Android), 023 (kênh Zalo, `messages_out`), 029 (`device_heartbeats`, độ phủ), 028 (diễn tập), 034
(hạn lưu) · **US**: I4 (MASTER-PLAN §4: "Tin Zalo hằng tuần + báo mất bảo vệ — gộp vào 032"; **★ Minh chưa duyệt I1–I5**, xem
MASTER-PLAN §8) · **ADR**: ADR-010 (hạn mức Zalo), ADR-002 (một tiến trình) · **Danh sách cắt**: "cá nhân hóa Coach" là mục
**đầu tiên** ⇒ spec này **không** dùng LLM.

---

## 1. Bối cảnh

Người giám hộ chỉ nghe từ HỏiCon khi có sự cố. Hai khoảng trống:
1. Không có tin nào nói "HỏiCon vẫn đang chạy" ⇒ con cháu không biết khi app bị tắt, gỡ, hết pin hay bị hãng điện thoại diệt
   nền. Máy chủ đã có dữ liệu để biết (heartbeat 15 phút, `device_heartbeats.protected`, 029), nhưng không dùng.
2. Thuyết minh hứa tác tử "Huấn luyện (Coach)" gửi bản tin tuần. Bảng `agent_runs` đã cho `graph = 'coach'` nhưng chưa có gì.

Văn bản `guardian_alerts` (011) đã **bỏ** câu "thỉnh thoảng báo họ biết bác còn bật các quyền bảo vệ" vì mã chưa làm, với ghi chú
"thêm lại CHỈ KHI mã làm thật, kèm tăng version". Spec này làm thật phần đó.

Hạn mức Zalo: 3 bot × 50 người, 3.000 tin/tháng/bot; tin không gắn sự cố bị giữ lại khi đã dùng ≥ 95% (`zalo_quota_hold_pct`).

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-32.1 | **P1** | Là con, nếu điện thoại của mẹ không báo về HỏiCon hơn 24 giờ, hoặc quyền bảo vệ bị tắt, tôi nhận **một** tin Zalo nói rõ chuyện gì và nên làm gì |
| US-32.2 | **P1** | Là con, mỗi tối Chủ nhật tôi nhận một tin ngắn: tuần này HỏiCon có nhắc mẹ lần nào không, máy được bảo vệ bao nhiêu phần thời gian, có bài luyện tập nào, và một mẹo nhỏ |
| US-32.3 | **P1** | Là con, tôi nhắn "tắt tin tuần" để ngừng bản tin (và "bật tin tuần" để nhận lại); tin "mất bảo vệ" vẫn đến |
| US-32.4 | **P2** | Là đội, tôi biết bản tin tuần không bao giờ đẩy hạn mức Zalo tới mức chặn tin cảnh báo sự cố |

## 3. Yêu cầu chức năng

- **(FR-001)** Migration (số kế tiếp sau head, chỉ làn B): cột `members.weekly_digest_enabled boolean NOT NULL DEFAULT true`. Không
  bảng mới (chống trùng dựa vào khóa `messages_out`/`jobs`). Test lên/xuống.
- **(FR-002)** Phát hiện mất bảo vệ — job `protection_watch` mỗi giờ (khóa theo giờ VN, lũy đẳng như `retention`), với mọi thiết bị
  chưa thu hồi của gia đình **không** demo, có người cao tuổi đang đồng ý `guardian_alerts`:
  - `silent`: `last_heartbeat_at` cũ hơn **24 giờ** (thiết bị đã từng gửi ít nhất một heartbeat);
  - `permission_off`: **2 khung liên tiếp** gần nhất của `device_heartbeats` có `protected = false`.

  Mỗi **đợt** mất bảo vệ chỉ một tin: khóa `protection:{device_id}:{mốc bắt đầu đợt}` (mốc = `last_heartbeat_at` cho `silent`, khung
  `false` đầu tiên cho `permission_off`), và tối đa 1 tin/thiết bị/24 giờ. Không gửi 21:00–07:00 giờ VN (xếp lại lúc 07:00).
- **(FR-003)** Tin mất bảo vệ (mẫu, không LLM, `texts.py`): mở đầu "Đây là trợ lý AI HỏiCon."; nói **điều đã biết** ("điện thoại
  của {bí danh} chưa báo về từ {giờ}", "quyền nhắc dừng lại đang tắt"), **nguyên nhân có thể** (hết pin, tắt máy, mất mạng, máy diệt
  app chạy nền) không khẳng định, và **một việc** nên làm (gọi hỏi thăm; mở HỏiCon trên máy của {bí danh}). Không gây hoảng sợ, không
  nói "bị hack". Gửi người giám hộ hạng 1; không có người giám hộ hạng 1 có chat ⇒ hạng 2.
- **(FR-004)** Bản tin tuần — job `coach_weekly` 19:00 Chủ nhật giờ VN (khóa `coach_weekly:{năm}-W{tuần ISO}`), mỗi gia đình không
  demo có ≥ 1 thiết bị hoạt động, ≥ 1 người giám hộ `weekly_digest_enabled`, người cao tuổi đồng ý `guardian_alerts`. Một tin cho
  mỗi người giám hộ đủ điều kiện, khóa `weekly:{member_id}:{năm}-W{tuần}`.
- **(FR-005)** Nội dung bản tin (mẫu, tất định, không LLM): mở đầu công khai AI; số lần HỏiCon nhắc dừng lại trong tuần (sự cố thật,
  không diễn tập, không demo) và kết cục ngắn; độ phủ bảo vệ 7 ngày (dùng **cùng hàm** độ phủ của `ops pilot`, làm tròn tới 5%, "chưa
  đủ dữ liệu" khi chưa có khung kỳ vọng); số bài luyện tập đã làm; một mẹo từ `data/coach/tips.vi.yaml` (`approved: false` tới khi
  Minh duyệt; bản prod bỏ dòng mẹo nếu chưa duyệt), xoay vòng theo tuần; dòng cuối "Nhắn TẮT TIN TUẦN để ngừng nhận bản tin này."
  **Không bao giờ** viết "an toàn" như một khẳng định: câu cho tuần không có sự cố là "Tuần này HỏiCon không thấy dấu hiệu đáng ngờ
  nào trên điện thoại của {bí danh}", kèm độ phủ (vì máy không được bảo vệ thì "không thấy" không có nghĩa).
- **(FR-006)** Hạn mức: mọi tin của spec này đi `deliver(..., urgent=False)` qua `messages_out` (luật 9). Đã dùng ≥ `hold_pct` ⇒ bản
  tin tuần bị giữ (`held`), không thử lại trong tuần đó; tin mất bảo vệ cũng `urgent=False` nhưng **ưu tiên** hơn bản tin: khi dùng
  ≥ `warn_pct` (80%) thì ngừng bản tin tuần của tháng đó, vẫn gửi tin mất bảo vệ tới `hold_pct`. Test đếm bằng `messages_out`.
- **(FR-007)** Lệnh Zalo: `channels/inbound.py::classify` nhận "tắt tin tuần" / "bật tin tuần" (bỏ dấu, không phân biệt hoa thường)
  ⇒ `("digest_off"|"digest_on", None)`; job `zalo_update` cập nhật `weekly_digest_enabled` của người giám hộ khớp `user_hmac` và trả
  lời một câu xác nhận (đếm `messages_out`). Văn bản thô không lưu (giữ nguyên quy tắc của 002).
- **(FR-008)** Trace: mỗi lượt `coach_weekly` cho một gia đình ghi một dòng `agent_runs` (`graph = 'coach'`, `incident_id` null) và
  `agent_steps` (`collect`, `compose`, `send`) chỉ có số đếm và khóa mẫu, không văn bản tin. `protection_watch` ghi `agent_steps`
  vào cùng lượt `coach` của ngày đó.
- **(FR-009)** Văn bản đồng ý: thêm lại câu báo khi máy không còn được bảo vệ + bản tin tuần vào `guardian_alerts.vi.md` (≤ 160 từ,
  test 011), `consent_texts write`; làn A ghim lại sha. Chỉ thêm **cùng PR** với mã; nếu 031 đã đổi văn bản này trước thì gộp.
- **(FR-010)** Đo trên máy ảo (làn A): khoảng trống heartbeat dài nhất khi máy ở Doze (`dumpsys deviceidle force-idle`) và ở nhóm
  App Standby `rare`, sau khởi động lại máy, sau `am kill`; kết quả quyết định ngưỡng 24 giờ có hợp lý không (ghi vào evidence; đổi
  ngưỡng ⇒ sửa spec, không sửa âm thầm).
- **(FR-011)** Kiểm chứng & tài liệu: pytest (phát hiện, chống trùng, giờ im lặng, hạn mức, đồng ý, opt-out, demo bị loại, công khai
  AI), `ux-elder-reviewer` (câu chữ 2 loại tin, hướng tới người giám hộ nhưng nói về người cao tuổi), `security-privacy-reviewer`;
  `docs/AGENTS.md` (Coach không dùng LangGraph — plan D1), `docs/DATA-MODEL.md`, `docs/PRIVACY-DPIA.md`, `docs/PILOT-PROTOCOL.md` §4
  (thêm lại dòng đã bỏ).

## 4. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Phát hiện đúng | `silent` sau 24 giờ ± 1 giờ; `permission_off` sau 2 khung; 0 tin khi thiết bị thu hồi, gia đình demo, không đồng ý | pytest đồng hồ giả |
| **(SC-002)** | Một tin mỗi đợt | chạy job 48 lần trong một đợt ⇒ 1 tin; đợt mới (heartbeat trở lại rồi mất) ⇒ thêm 1 tin | pytest |
| **(SC-003)** | Bản tin đúng số | số lần nhắc, độ phủ, bài luyện tập khớp dữ liệu seed; 0 câu "an toàn" khẳng định | pytest + quét chữ |
| **(SC-004)** | Hạn mức | ≥ 80% ⇒ 0 bản tin mới, tin mất bảo vệ vẫn đi; ≥ 95% ⇒ cả hai giữ; tin sự cố (`urgent`) không bị ảnh hưởng | pytest đếm `messages_out` |
| **(SC-005)** | Công khai AI + PII | 100% tin mở đầu câu công khai; 0 số điện thoại/h1/tên thật trong tin, job, `agent_steps` | test luật 6 + quét |
| **(SC-006)** | Ngưỡng 24 giờ hợp lý | khoảng trống heartbeat dài nhất trên AVD (Doze, `rare`, khởi động lại) < 24 giờ, ghi số + điều kiện | AVD `hc-api36` (máy ảo ≠ máy thật) |
| **(SC-007)** | Máy thật | tỷ lệ báo nhầm "mất bảo vệ" trong 7 ngày thí điểm | **BLOCKED** (029 giai đoạn 2) |

## 5. Làm rõ (clarify, 18/10/2026 — tự quyết)

| # | Điểm mơ hồ | Quyết định | Lý do |
|---|---|---|---|
| Q1 | Câu "Tuần này nhà mình an toàn" (I4)? | Không khẳng định "an toàn"; dùng "không thấy dấu hiệu đáng ngờ" + độ phủ | Cùng tinh thần 026 ("số không bao giờ kết luận an toàn"); máy tắt thì "không thấy" vô nghĩa |
| Q2 | Ngưỡng "mất bảo vệ"? | 24 giờ không heartbeat; 2 khung `protected=false` | Đêm tắt máy/hết pin ≤ 12 giờ là thường; Doze có thể dồn WorkManager vài giờ; đo ở FR-010 |
| Q3 | Dùng LangGraph cho Coach? | Không (plan D1) | Ba bước tất định, không interrupt, không LLM; "cá nhân hóa Coach" bị cắt đầu tiên |
| Q4 | Báo khi bảo vệ trở lại? | Không ở v1 | Tốn hạn mức; bản tin tuần đã cho thấy độ phủ |
| Q5 | Mục đích đồng ý mới? | Không; thêm câu vào `guardian_alerts` (đúng chỗ đã bỏ ở 011) — **★ Minh xác nhận phạm vi DPIA** | Cùng người nhận, cùng dữ liệu đã thu theo `core_protection` |
| Q6 | I4 chưa được Minh duyệt (MASTER-PLAN §8 mục 1)? | Vẫn viết spec (ROADMAP P2-17 có sẵn, I4 chỉ thêm phần "mất bảo vệ"); phần "mất bảo vệ" có cờ `HOICON_PROTECTION_WATCH` mặc định **bật** — nếu Minh từ chối I4 thì tắt cờ, không cần gỡ mã | Không chặn cả spec vì một quyết định phạm vi; quyết định ghi ở MASTER-PLAN §8 |

## 6. Ngoài phạm vi

Cá nhân hóa bằng LLM (danh sách cắt), diễn tập cá nhân hóa, tin cho người cao tuổi, báo khi bảo vệ trở lại, trace của lượt `coach`
trong `/trace` của người giám hộ (`_visible_run` dựa vào sự cố; ghi vào ROADMAP "Ghi chú"), tin qua kênh khác Zalo.
