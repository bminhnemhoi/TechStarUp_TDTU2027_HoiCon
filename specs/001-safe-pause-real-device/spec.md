# Feature Specification: Dừng an toàn — số đo máy thật và hoàn tất spike S1/S2

**Feature Branch**: `feat/001-safe-pause-real-device`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Spec 001 (docs/MASTER-PLAN.md §3, Đợt 1, làn A): hoàn tất phần còn lại của P1-S1/P1-S2 — đo độ
trễ mở app ngân hàng → màn dừng an toàn trên máy thật (Firebase Test Lab, ≥ 2 máy), kiểm đường dự phòng khi không có
quyền hiển thị trên ứng dụng khác (full-screen intent) trên AVD 34/36, sửa tiêu đề demobank chồng dòng, sửa
tts_unavailable trên AVD, ảnh cho ux-elder-reviewer, đóng phần chưa chốt của ADR-007/008."

<!--
  HỎICON (brownfield): spec này chỉ mô tả PHẦN CHÊNH LỆCH. Cơ chế cảm biến đã chốt ở ADR-007; quyết định dừng an toàn
  và app ngân hàng ở ADR-008; số đo máy ảo ở docs/spikes/P1-S1-cam-bien.md và docs/spikes/device-matrix.md.
-->

## Truy vết *(mandatory)*

- **Mã ROADMAP**: P1-S1 (phần "p95 ≤ 3 s chưa đạt — đo máy thật"), P1-S2 (bảng kết quả hạng mục 2, 4, 5 và §6)
- **User story PRD**: US-02 (đang nghe số lạ mà mở app ngân hàng ⇒ được nhắc dừng bằng giọng nói, p95 ≤ 3 s, offline)
- **ADR liên quan**: ADR-007 (mục "Chưa chốt — điều kiện để đóng gate P1-S1"), ADR-008 (quyết định 1 về full-screen
  intent, quyết định 3 về đo bằng `:latency`). Spec này **không đổi quyết định**; chỉ điền số đo vào phần chưa chốt và
  đề xuất cập nhật qua PR để Minh duyệt.
- **Gate nghiệm thu**: G1 (08/11/2026) — "5 báo cáo spike … có số đo"; tiền đề cho M1 ("SafePause p95 ≤ 3 s")
- **Phụ thuộc spec**: không có spec trước. Phụ thuộc ngoài: **tài khoản Firebase (W0-3, Minh)** cho phần máy thật.
- **Làn**: A (Android)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Biết chắc màn dừng hiện kịp trên máy thật (Priority: P1)

Đội cần một con số đo trên **máy Android thật** (không phải máy ảo) cho khoảng thời gian từ lúc app ngân hàng hiện lên
trong khi đang có cuộc gọi lạ tới lúc màn "Khoan chuyển tiền đã" hiện ra, để biết lời hứa "≤ 3 giây" với người cao
tuổi có giữ được không và ghi trung thực vào thuyết minh Vòng 1.

**Why this priority**: Đây là điều kiện chưa đóng của gate P1-S1 và là con số trung tâm của US-02 và gate M1. Máy ảo
trên máy dev bị quá tải nên không dùng để kết luận được.

**Independent Test**: Chạy bộ đo trên ít nhất hai máy thật của Firebase Test Lab, đọc kết quả p50/p95 cho lượt nguội
và lượt ấm; so với ngưỡng 3 s.

**Acceptance Scenarios**:

1. **Given** bản debug của Lính gác và Ngân hàng Mẫu được cài trên một máy thật Samsung dòng A (Android 14),
   **When** bộ đo mô phỏng cuộc gọi lạ rồi mở Ngân hàng Mẫu 10 lần nguội và 10 lần ấm,
   **Then** có kết quả p50/p95 cho từng lượt, ghi vào ma trận thiết bị với nhãn "máy thật", model, phiên bản, ngày, n.
2. **Given** cùng bộ đo trên một máy Pixel (Android 15 hoặc 16), **When** chạy như trên, **Then** có kết quả tương tự.
3. **Given** p95 của một máy vượt 3 s, **When** đội đọc kết quả, **Then** cùng lượt đo có số của biến thể màn dừng
   còn lại (View thuần hoặc Compose) để có cơ sở chọn ở P2-05, và kết luận "không đạt" được ghi rõ, không làm tròn.

---

### User Story 2 - Khi không có quyền "hiển thị trên ứng dụng khác", người dùng vẫn được nhắc (Priority: P2)

Nếu người dùng chưa cấp hoặc đã thu hồi quyền "hiển thị trên ứng dụng khác", Lính gác không mở được màn dừng toàn màn
hình; khi đó thông báo nổi kèm giọng nói phải xuất hiện thay thế. Đội cần xác nhận hành vi này trên Android 14 và 16
(gồm việc full-screen intent có thay đổi gì không) để đóng hạng mục 4 của spike S2.

**Why this priority**: Đây là đường an toàn khi quyền bị thiếu. ADR-008 đã chọn không dùng full-screen intent ở bản
phát hành dựa trên tài liệu; cần một lần kiểm thực tế để xác nhận.

**Independent Test**: Trên máy ảo API 34 và 36, thu hồi quyền hiển thị trên ứng dụng khác, chạy kịch bản cuộc gọi lạ →
Ngân hàng Mẫu, ghi lại thông báo hay màn hình nào xuất hiện và sau bao lâu.

**Acceptance Scenarios**:

1. **Given** quyền hiển thị trên ứng dụng khác bị thu hồi, **When** người dùng mở Ngân hàng Mẫu trong lúc có cuộc gọi
   lạ, **Then** thông báo nổi có phụ đề "Trợ lý AI HỏiCon" và câu nói đầu tiên xuất hiện, thời gian được ghi lại.
2. **Given** máy đang mở khóa, **When** thông báo dự phòng có gắn full-screen intent (chỉ bản debug), **Then** kết quả
   (thông báo nổi hay màn hình) được ghi lại để xác nhận hoặc điều chỉnh ADR-008 quyết định 1.

---

### User Story 3 - Màn hình demo đọc được với người cao tuổi (Priority: P2)

Ngân hàng Mẫu và màn dừng an toàn sẽ xuất hiện trong video Vòng 1 và gian trưng bày, nên phải đọc được ở cỡ chữ lớn
và qua được người review trải nghiệm người cao tuổi.

**Why this priority**: Video Vòng 1 quay trong tuần 05–08/11; lỗi hiển thị phải sửa trước đó.

**Independent Test**: Chụp màn hình các màn chính ở cỡ chữ 100% và 200% trên API 36 và 34, gửi `ux-elder-reviewer`.

**Acceptance Scenarios**:

1. **Given** cỡ chữ hệ thống 200%, **When** mở màn chuyển tiền của Ngân hàng Mẫu, **Then** tiêu đề "Chuyển tiền đến tài
   khoản khác" không chồng dòng và không bị cắt.
2. **Given** bộ ảnh 100% và 200%, **When** `ux-elder-reviewer` đánh giá, **Then** không còn vấn đề mức High.

---

### User Story 4 - Giọng nói hoạt động trên máy ảo dùng để quay demo (Priority: P3)

Trên máy ảo Linux của đội, màn dừng hiện nhưng không đọc to (`tts_unavailable`), nên video demo và kiểm thử đầu–cuối
thiếu phần giọng nói.

**Why this priority**: Không ảnh hưởng máy thật (đã có giọng trên AVD Windows), nhưng chặn quay video và kịch bản E2E
trên máy của Tiến.

**Independent Test**: Chạy kịch bản cuộc gọi lạ trên AVD API 36 và 34 ở máy Linux; log phải có `tts_started`.

**Acceptance Scenarios**:

1. **Given** máy ảo đã được chuẩn bị theo hướng dẫn môi trường, **When** màn dừng hiện, **Then** câu nói đầu tiên được
   phát bằng giọng tiếng Việt không cần mạng.
2. **Given** máy không có giọng tiếng Việt offline, **When** màn dừng hiện, **Then** ứng dụng vẫn im lặng và ghi
   `tts_unavailable` (không chuyển sang giọng cần mạng).

---

### Edge Cases

- Firebase Test Lab trả lỗi hoặc hết lượt (gói Spark 5 lượt máy thật/ngày) ⇒ ghi lần chạy thất bại, chạy lại hôm sau;
  không dùng số của lần chạy thiếu mốc.
- Một lần đo thiếu mốc (`app_foreground` hoặc `pause_shown`) ⇒ tính là trượt, ghi nguyên nhân; không loại khỏi mẫu
  trừ khi có bằng chứng lỗi môi trường (như lỗi modem giả lập ở spike S1).
- Telecom hết hạn sàng lọc 5 s khi khởi động nguội ⇒ không có cửa sổ rủi ro ⇒ ghi là "không bắt được", không phải độ trễ.
- Máy thật có giao diện hãng tắt tối ưu pin khác Pixel ⇒ ghi trạng thái quyền và miễn tối ưu pin trước mỗi lượt.
- Màn hình nhỏ 720×1280 ở cỡ chữ 200% (đã biết: tiêu đề màn dừng phải cuộn) ⇒ ghi lại, xử lý bố cục ở P2-05.
- Máy ảo Linux chạy không cửa sổ (`-no-window`) không có âm thanh ⇒ kiểm giọng nói bằng log, không bằng tai.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bộ đo độ trễ MUST chạy trọn trên máy ảo API 36 và API 34 trước khi dùng lượt máy thật, cho đủ mốc ở
  ≥ 10 lần nguội và ≥ 10 lần ấm, và xuất kết quả dạng tệp + log.
- **FR-002**: Đội MUST có số đo độ trễ `app_foreground → pause_shown` (p50, p95, n, nguội/ấm) trên ít nhất **hai máy
  thật**: một Samsung dòng A chạy Android 14 và một Pixel chạy Android 15 hoặc 16.
- **FR-003**: Mỗi lượt đo máy thật MUST có số của **cả hai biến thể** màn dừng (View thuần và Compose) để làm cơ sở
  chọn E7 ở P2-05.
- **FR-004**: Mọi số đo MUST được ghi vào `docs/spikes/device-matrix.md` và §7 của báo cáo spike S2, mỗi dòng có loại
  thiết bị (máy ảo / máy thật), model, phiên bản Android, ngày, n và nguồn (FTL / AVD).
- **FR-005**: Đội MUST kết luận gate P1-S1 bằng số máy thật: đạt (p95 ≤ 3 s trên mọi máy đã đo) hoặc không đạt kèm
  phương án tiếp theo; phần "Chưa chốt" của ADR-007 MUST được đề xuất cập nhật bằng số đo qua PR.
- **FR-006**: Đội MUST kiểm đường dự phòng khi thu hồi quyền hiển thị trên ứng dụng khác trên API 34 và API 36 (≥ 5 lần
  mỗi máy), ghi loại hiển thị, giá trị full-screen intent trong log, thời gian tới thông báo và tới câu nói đầu tiên.
- **FR-007**: Màn chuyển tiền của Ngân hàng Mẫu MUST hiển thị tiêu đề không chồng dòng, không bị cắt ở cỡ chữ 200%.
- **FR-008**: Đội MUST có bộ ảnh 100% và 200% (API 36 và 34) của các màn Ngân hàng Mẫu (đăng nhập, trang chủ, chuyển
  tiền, mã OTP mô phỏng, kết quả) và màn dừng an toàn, và kết quả `ux-elder-reviewer` không còn mục High.
- **FR-009**: Máy ảo Linux của đội MUST phát được câu nói tiếng Việt offline ở màn dừng; nếu không thể, nguyên nhân và
  cách khắc phục MUST được ghi vào hướng dẫn môi trường. Ứng dụng MUST NOT chuyển sang giọng cần mạng.
- **FR-010**: Mọi thay đổi MUST giữ nguyên đường găng: không thêm quyền mạng hay LLM vào đường dừng an toàn; kịch bản
  cuộc gọi lạ trên AVD 36 và 34 vẫn bắt được 10/10 sau thay đổi.
- **FR-011**: Bộ đo và mọi chỗ cho phép mô phỏng cuộc gọi MUST chỉ có ở bản debug; manifest bản release MUST NOT chứa
  quyền full-screen intent hay receiver mô phỏng.

### Key Entities

- **Lượt đo độ trễ**: thiết bị (model, Android, loại máy), biến thể màn dừng, chế độ (nguội/ấm), n, p50, p95, số lần
  trượt kèm nguyên nhân, ngày, nguồn. Không chứa dữ liệu cá nhân.

## Bất biến an toàn *(mandatory)*

- **Dừng an toàn** (Hiến chương I): không đổi cơ chế. Thay đổi chỉ ở bố cục Ngân hàng Mẫu, chuẩn bị môi trường giọng
  nói và tài liệu; FR-010 bảo vệ đường găng bằng kịch bản hồi quy.
- **LLM chỉ nâng** (III): không đụng tới.
- **Công khai AI** (IV): thông báo dự phòng giữ phụ đề "Trợ lý AI HỏiCon"; `AiDisclosureCopyTest` phải xanh.

## Quyền riêng tư & đồng ý *(mandatory)*

| Dữ liệu mới / thay đổi | Dạng lưu (băm/che/không lưu) | Mục đích đồng ý (enum) | Hạn lưu | Gửi LLM? |
|---|---|---|---|---|
| Kết quả đo độ trễ (mốc thời gian, model máy) | tệp kết quả FTL + bảng trong docs | không cần — máy thử, không có người dùng | lâu dài (tài liệu) | Không |

Quyền Android mới: không có. Máy FTL không có SIM, cuộc gọi là mô phỏng (bản debug) với số hư cấu; không có số điện
thoại thật nào trong log hay kết quả. Không thử app ngân hàng thật (giao thức §5 của spike S2 thuộc sau P1-08).

## UX người cao tuổi *(mandatory nếu có màn hình hoặc câu chữ mới)*

- Màn hình: Ngân hàng Mẫu (dùng cho demo) và E7 SafePause bản nháp — theo `docs/DESIGN-SYSTEM.md`
- Kiểm ở cỡ chữ 100% và 200%; màn nhỏ 720×1280 ghi nhận để xử lý ở P2-05
- Không đổi câu chữ của màn dừng trong spec này

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: p95 `app_foreground → pause_shown` ≤ 3 000 ms ở lượt nguội và lượt ấm — đo trên: máy thật FTL (Samsung
  dòng A Android 14 và Pixel Android 15/16), n ≥ 10 mỗi lượt. Không đạt thì ghi đúng số, kèm số của biến thể còn lại.
- **SC-002**: Bộ đo cho đủ mốc ở ≥ 19/20 lần (nguội + ấm) mỗi biến thể trên mỗi AVD — đo trên: AVD hc-api36 và hc-api34 (máy Linux của Tiến).
- **SC-003**: Khi không có quyền hiển thị trên ứng dụng khác, thông báo dự phòng và câu nói đầu xuất hiện trong ≤ 3 000 ms
  tính từ `app_foreground` ở ≥ 4/5 lần — đo trên: AVD hc-api34 và hc-api36.
- **SC-004**: `ux-elder-reviewer` không còn vấn đề mức High với bộ ảnh 100%/200% — đo trên: AVD hc-api36 và hc-api34.
- **SC-005**: Kịch bản cuộc gọi lạ → Ngân hàng Mẫu bắt được 10/10 và `:rules:test` xanh sau mọi thay đổi — đo trên:
  AVD hc-api36 và hc-api34.
- **SC-006**: `tts_started` xuất hiện ở ≥ 9/10 lần màn dừng hiện — đo trên: AVD hc-api36 và hc-api34 (máy Linux).

## Kế hoạch bằng chứng *(mandatory)*

- `latency.json` + log `HC_LATENCY` của mỗi lượt FTL (đường dẫn kết quả trên Cloud Storage, model, version, ngày)
- Output `connectedDebugAndroidTest` của `:latency` trên AVD 36 và 34
- Log kịch bản dự phòng (thu hồi quyền) với các mốc thời gian và giá trị `fsi=`
- Ảnh 100%/200% (đường dẫn ngoài repo) + báo cáo `ux-elder-reviewer`
- Output `python scripts/emu-scenario.py --scenario fake_police --runs 10` trên AVD 36 và 34; `:rules:test`;
  `:app:lintDebug :demobank:lintDebug`
- Bảng cập nhật trong `docs/spikes/device-matrix.md`, `docs/spikes/P1-S2-dung-an-toan.md` §3/§7

## Ngoài phạm vi & mốc cắt

- Ngoài phạm vi: thử app ngân hàng thật (giao thức §5 của spike S2 — sau P1-08, P2-02, P2-05); chuyển hẳn E7 sang View
  hay Compose (P2-05, spec 022); R8/baseline profile (spec 012); bố cục màn dừng cho màn nhỏ (P2-05).
- Nếu trễ, cắt trước: US4 (giọng nói trên AVD Linux) — ghi là giới hạn môi trường; giữ US1 vì là điều kiện gate G1.
- Nếu tới 05/11 vẫn chưa có Firebase: SC-001 ghi `BLOCKED: chưa có tài khoản Firebase` trong evidence.md; spec không
  được đánh ☑; thuyết minh chỉ dùng số máy ảo kèm nhãn "máy ảo".

## Assumptions

- Firebase Test Lab gói Spark (5 lượt máy thật/ngày) đủ cho 2 máy × 2 biến thể trong 1–2 ngày.
- Model Samsung dòng A và Pixel nêu trên có trong danh sách máy thật của FTL tại thời điểm chạy; nếu không, chọn model
  gần nhất cùng hãng và ghi lý do.
- Bộ đo `:latency` dùng cuộc gọi mô phỏng (máy FTL không có SIM); phần còn lại là đường găng thật.
- Số đo FTL là bản debug đã biên dịch AOT (`compile=speed`); bản release có R8 đo lại ở spec 012.
