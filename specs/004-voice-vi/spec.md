# Feature Specification: Giọng nói tiếng Việt trên máy — TTS offline, nhận dạng `SpeechRecognizer` vi-VN, chốt "nút bấm là chính" (spike P1-S5 thu nhỏ)

**Feature Branch**: `feat/004-voice-vi`

**Created**: 2026-10-15

**Status**: Draft — quyết định kỹ thuật chốt trong plan, Tiến duyệt trước `implement` (MASTER-PLAN §2.6)

**Input**: Tiến giao 15/10/2026: "Soạn Spec 004 (004-voice-vi) theo Master Plan: TTS offline, SpeechRecognizer vi-VN, nguyên tắc nút bấm là chính."

<!-- Spike: đo để QUYẾT ĐỊNH, không đổi hành vi app Lính gác. Mọi số ghi rõ môi trường (máy ảo ≠ máy thật). -->

## Truy vết *(mandatory)*

- **Mã ROADMAP**: P1-S5 (bản thu nhỏ theo danh sách cắt: "thu nhỏ P1-S5 → chỉ so 1 nhà cung cấp STT")
- **User story PRD**: US-02 (nhắc dừng lại **bằng giọng nói**, offline) · gián tiếp US-04/E8 (trả lời câu hỏi của tác tử)
- **ADR liên quan**: ADR-001 (luật tất định, cấm ghi âm cuộc gọi) · ADR-007 (TTS khởi động sẵn khi mở cửa sổ rủi ro;
  dự phòng heads-up + TTS) · ADR-008 (heads-up + TTS khi không có SAW). Không đổi quyết định đã chốt ⇒ không cần ADR mới;
  kết luận ghi ở `docs/spikes/P1-S5-giong-noi.md`
- **Gate nghiệm thu**: G1 (08/11) — báo cáo spike P1-S5 có số đo + quyết định
- **Phụ thuộc spec**: 001 (môi trường TTS AVD đã sửa — `docs/EMULATOR.md` §1.2; nhánh này nối tiếp nhánh 001).
  Phụ thuộc ngoài **không chặn** (§2.6): bản thu giọng của đội, người nghe chấm điểm, máy thật/FTL
- **Làn**: A (Android) — chỉ `apps/android/**`, `scripts/voice-*`, `scripts/tests/**`, `data/voice/**`, `docs/**` của spec

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Biết chắc giọng đọc tiếng Việt có sẵn offline và đủ nhanh cho SafePause (Priority: P1)

Đội cần biết: trên Android 14/16, giọng vi-VN của Google TTS có dùng được khi **không có mạng** không, từ lúc gọi
`speak()` tới lúc phát âm thanh mất bao lâu (nguội/ấm), và so với phát **âm thanh thu sẵn** thì nhanh hơn hay chậm hơn.
Đây là đầu vào cho E7 SafePause (đường găng ≤ 3 s) và cho dự phòng khi `tts_unavailable`.

**Why this priority**: US-02 hứa "nhắc bằng giọng nói" offline; 001 cho thấy TTS AVD từng hỏng (`tts_unavailable`). Không có số
thì không biết có cần âm thanh thu sẵn ở P2-05 hay không.

**Independent Test**: chạy bộ đo `:voicelab` trên hc-api36 và hc-api34 với mạng tắt ⇒ có bảng giọng + p50/p95 độ trễ.

**Acceptance Scenarios**:

1. **Given** AVD đã tắt Wi-Fi và dữ liệu di động, **When** chạy thăm dò giọng, **Then** liệt kê mọi giọng `vi` (tên, cần mạng
   hay không, chất lượng, độ trễ khai báo, đã cài hay chưa) và chọn đúng giọng offline như `Speaker.pickOfflineVietnamese`.
2. **Given** engine vừa khởi tạo (nguội) hoặc đã khởi tạo (ấm), **When** phát câu đầu của SafePause n ≥ 20 lần mỗi kiểu,
   **Then** ghi được độ trễ `speak()` → `onStart` (p50/p95) cho từng AVD.
3. **Given** một đoạn âm thanh thu sẵn trong `res/raw` của `:voicelab`, **When** phát n ≥ 20 lần (nguội/ấm), **Then** ghi được
   độ trễ lệnh phát → khung âm thanh đầu tiên.

---

### User Story 2 - Đo nhận dạng giọng nói tiếng Việt trên máy để quyết định có cho trả lời bằng giọng không (Priority: P2)

Người cao tuổi có thể muốn trả lời "có / không / không biết" bằng giọng thay vì bấm. Đội đo `SpeechRecognizer` vi-VN
(**ưu tiên nhận dạng trên máy**) trên 20 câu chuẩn: một bộ **tổng hợp bằng TTS** (tất định, chạy lại được) và một bộ
**đội tự thu** (giọng thật, có đồng ý), rồi áp **quy tắc quyết định đăng ký trước** (FR-011).

**Why this priority**: chỉ là tùy chọn; nút bấm vẫn là chính. Nhưng thuyết minh và BGK sẽ hỏi "có dùng giọng nói không" ⇒
cần số để trả lời trung thực.

**Independent Test**: `scripts/voice-wer.py` chạy trên kết quả nhận dạng ⇒ WER + độ chính xác ý định cho từng bộ, từng AVD.

**Acceptance Scenarios**:

1. **Given** AVD API 34/36, **When** thăm dò hỗ trợ nhận dạng vi-VN, **Then** ghi được: có nhận dạng trên máy không, ngôn ngữ
   đã cài/đang chờ/hỗ trợ, kết quả thử tải mô hình.
2. **Given** 20 tệp WAV của một bộ, **When** đưa từng tệp vào bộ nhận dạng qua nguồn âm thanh là tệp (không dùng micro),
   **Then** có bản chép + độ trễ cho từng câu; script tính WER và độ chính xác ý định.
3. **Given** chưa có bản thu của đội hoặc AVD không có bộ nhận dạng trên máy, **When** chạy, **Then** phần đó ghi
   `BLOCKED: <lý do>` trong evidence và các phần còn lại vẫn chạy hết (không dừng).

---

### User Story 3 - Chốt quyết định và ghi lại cho thuyết minh, P2-05, DESIGN-SYSTEM (Priority: P3)

Ban giám khảo và Minh đọc một trang báo cáo: TTS nào dùng, khi nào dùng âm thanh thu sẵn, giọng nói có được dùng để trả
lời không — kèm số đo và nguồn số.

**Why this priority**: là sản phẩm của spike (gate G1), nhưng cần số của US1–US2 trước.

**Independent Test**: đọc `docs/spikes/P1-S5-giong-noi.md` — mọi kết luận có số + môi trường + n; quyết định khớp quy tắc FR-011.

**Acceptance Scenarios**:

1. **Given** số đo US1–US2, **When** áp quy tắc FR-011, **Then** báo cáo ghi quyết định TTS (đường chính + dự phòng) và STT
   (tùy chọn hay chỉ nút bấm), không diễn giải lại sau khi thấy số.
2. **Given** quyết định, **When** cập nhật tài liệu, **Then** `docs/DESIGN-SYSTEM.md` ghi nguyên tắc "nút bấm là chính, giọng
   nói chỉ bổ trợ" và dòng P1-S5 trong ROADMAP trỏ tới spec + báo cáo.

### Edge Cases

- Mất mạng: mọi phép đo TTS chạy với mạng tắt; giọng chỉ có bản mạng ⇒ coi như **không có** (khớp `Speaker`, SEC-8).
- Gói giọng vi-VN hỏng như 001 (`Failed to load pipeline definitions`): thăm dò phải phân biệt "không có giọng" và "giọng hỏng"
  (`speak` trả lỗi / không `onStart` trong 5 s).
- AVD không có bộ nhận dạng trên máy cho vi-VN: ghi đúng như vậy; được phép đo thêm bộ nhận dạng mặc định (có thể dùng mạng)
  **chỉ** với bộ câu tổng hợp và bản thu của đội đã đồng ý, gắn nhãn "mạng — không dùng cho sản phẩm".
- Android 10 (API 29): API đưa tệp âm thanh vào bộ nhận dạng chỉ có từ API 33 ⇒ `:voicelab` minSdk 33; app sản phẩm không đổi.
- Đang có cuộc gọi: spike **không** đo micro trong cuộc gọi; ghi rõ là ngoài phạm vi (ADR-001 cấm ghi âm cuộc gọi).
- Cỡ chữ 200%/TalkBack: không có màn hình mới cho người cao tuổi; `:voicelab` là công cụ đo, không phát hành.
- Kết quả nhận dạng có thể chứa chữ số/tên: chỉ lưu trong thư mục bằng chứng ngoài repo; câu chuẩn là hư cấu, không PII.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST có module `:voicelab` (ứng dụng công cụ, `applicationId vn.hoicon.voicelab`, minSdk 33, chỉ bản
  debug) để đo giọng nói; `:app` **không** phụ thuộc `:voicelab`, không thêm quyền mới, không đổi hành vi. `:voicelab` không
  khai báo `INTERNET`; chỉ khai báo `RECORD_AUDIO` nếu research R1 chứng minh bộ nhận dạng đòi quyền này kể cả khi đọc từ tệp.
- **FR-002**: Bộ đo MUST thăm dò giọng TTS `vi` trên từng AVD khi tắt mạng: tên, `isNetworkConnectionRequired`, `quality`,
  `latency`, `KEY_FEATURE_NOT_INSTALLED`, engine mặc định; và chọn giọng theo **đúng** tiêu chí của `Speaker.pickOfflineVietnamese`.
- **FR-003**: Bộ đo MUST đo độ trễ TTS `speak()` → `onStart` của câu đầu SafePause (`R.array.pause_speech[0]`, chép nguyên văn
  sang `:voicelab`), nguội (engine mới) và ấm, n ≥ 20 mỗi kiểu mỗi AVD; xuất JSON qua logcat thẻ `HC_VOICE`.
- **FR-004**: Bộ đo MUST đo độ trễ phát âm thanh thu sẵn (`MediaPlayer` từ `res/raw`, nguội = tạo mới, ấm = đã `prepare`)
  từ lệnh phát tới khi `AudioTimestamp`/vị trí phát > 0, n ≥ 20 mỗi kiểu mỗi AVD. Đoạn âm thanh dùng để đo là **tệp tổng hợp**
  (không phải giọng người) nên được phép nằm trong repo.
- **FR-005**: Bộ đo MUST tổng hợp ra WAV (`synthesizeToFile`, tần số gốc của engine; `voice-lab.sh` chuyển sang 16 kHz mono 16-bit
  bằng `ffmpeg` cho bộ nhận dạng) đủ câu của `pause_speech` + 4 cụm khó (tên "HỏiCon", "3 giây",
  "con cháu", "ngân hàng") để người nghe chấm; tệp lấy về thư mục bằng chứng ngoài repo bằng `adb pull`.
- **FR-006**: Bộ đo MUST thăm dò hỗ trợ nhận dạng vi-VN: `isOnDeviceRecognitionAvailable`, `checkRecognitionSupport`
  (đã cài / đang chờ / hỗ trợ trên máy / trực tuyến), thử `triggerModelDownload` (ghi kết quả, không lặp vô hạn).
- **FR-007**: Bộ đo MUST chạy nhận dạng vi-VN trên từng tệp WAV 16 kHz mono qua nguồn âm thanh là tệp (`EXTRA_AUDIO_SOURCE`,
  API 33+), **ưu tiên bộ nhận dạng trên máy**; ghi bản chép tốt nhất, độ tin cậy (nếu có), độ trễ hết-tệp → kết quả, mã lỗi.
  Không bao giờ mở micro trực tiếp.
- **FR-008**: Repo MUST có `data/voice/sentences.v1.json`: 20 câu chuẩn hư cấu (12 câu trả lời ngắn gắn ý định `yes|no|unsure`,
  có biến thể ba miền; 8 câu kể ngắn kiểu "Họ xưng là công an…"), không số điện thoại/tài khoản/tên thật; kèm test kiểm cấu trúc.
- **FR-009**: Repo MUST có `scripts/voice-wer.py` (chỉ thư viện chuẩn): chuẩn hóa NFC, chữ thường, bỏ dấu câu (giữ dấu tiếng
  Việt), WER mức từ (Levenshtein), phân loại ý định bằng từ khóa, xuất bảng Markdown + JSON; test `unittest` trong `scripts/tests/`.
- **FR-010**: Dữ liệu giọng thật (bản thu của đội, điểm của người nghe) MUST nằm ngoài repo
  (`~/hoicon-evidence/004-voice-vi/`), chỉ người ≥ 18 tuổi đã đồng ý bằng lời (ghi "đã đồng ý" theo vai trò, không ghi tên);
  không đưa vào log ứng dụng, không gửi dịch vụ ngoài ngoài bộ nhận dạng của hệ thống được ghi nhãn ở FR-007.
- **FR-011**: Báo cáo MUST áp **quy tắc quyết định đăng ký trước**:
  - **TTS**: đường chính = giọng vi-VN offline của máy nếu có trên cả hai AVD **và** p95 ấm ≤ 1 000 ms **và** điểm nghe trung
    bình ≥ 3,5/5; dự phòng khi `tts_unavailable` = âm thanh thu sẵn (làm thật ở P2-05), kèm so sánh độ trễ FR-004.
  - **STT**: được ghi "tùy chọn ở MVP" chỉ khi có nhận dạng **trên máy** cho vi-VN **và** độ chính xác ý định ≥ 95% trên bản thu
    của đội **và** WER ≤ 20%; ngược lại "MVP chỉ nút bấm, giọng nói để sau". Trong mọi trường hợp **nút bấm là chính**.
  - **Mẫu số** (đăng ký trước): độ chính xác ý định = số câu `answer` (12 câu) × số người thu được phân loại đúng / tổng; với một
    người thu, 11/12 = 91,7% **không đạt**. WER tính trên cả 20 câu. Điểm nghe cần ≥ 3 người nghe.
  - **Thiếu dữ liệu** (đăng ký trước, không diễn giải lại sau khi thấy số): thiếu bản thu của đội ⇒ STT = "MVP chỉ nút bấm"
    (bộ tổng hợp chỉ là cận trên, không dùng để chốt "tùy chọn"); thiếu điểm nghe (< 3 người) ⇒ TTS đường chính **chưa chốt**
    (ghi `BLOCKED: chờ điểm nghe`), dự phòng âm thanh thu sẵn vẫn ghi; thiếu giọng offline trên một AVD ⇒ không đạt điều kiện
    "có trên cả hai AVD". Thiếu máy thật không đổi quyết định nhưng ghi rõ "chưa kiểm trên máy thật".
- **FR-012**: `docs/spikes/P1-S5-giong-noi.md` MUST có: bảng giọng, bảng độ trễ (nhãn môi trường + n), WER/ý định từng bộ,
  điểm nghe (n người nghe), quyết định theo FR-011, rủi ro còn lại, đề xuất nguồn âm thanh thu sẵn cho P2-05 (không mua gì).
  `docs/DESIGN-SYSTEM.md` thêm nguyên tắc "nút bấm là chính"; dòng P1-S5 trong ROADMAP cập nhật.
- **FR-013**: Có máy thật (FTL hoặc máy mượn) ⇒ MUST chạy lại FR-002/003/006 trên ≥ 1 máy; không có ⇒ `BLOCKED` trong
  evidence, không dừng spec.
- **FR-014**: Sau mọi thay đổi, `:app` MUST giữ nguyên: manifest release đã merge không có `RECORD_AUDIO`, `INTERNET`;
  `:rules:test :app:lintDebug` xanh; manifest `:voicelab` không có `INTERNET`.

### Key Entities

- **Câu chuẩn** (`data/voice/sentences.v1.json`): `id`, `text`, `kind` (`answer|story`), `intent` (`yes|no|unsure|null`),
  `region` (`north|central|south|any`).
- **Kết quả đo** (JSON qua logcat `HC_VOICE`, lưu ngoài repo): `avd`, `api`, `probe`, `n`, `values_ms[]`, `p50`, `p95`,
  `voice`, `network_off`, `error`.
- **Kết quả nhận dạng**: `sentence_id`, `set` (`synthetic|team`), `recognizer` (`on_device|default_network`), `transcript`,
  `latency_ms`, `error`.

## Bất biến an toàn *(mandatory)*

- **Dừng an toàn** (I): không đổi `:app`, `Speaker`, `SafePauseActivity`; đường găng giữ nguyên. Số đo chỉ là đầu vào cho P2-05.
- **LLM chỉ nâng** (III): không gọi LLM, không đụng máy chủ.
- **Công khai AI** (IV): không có tin/màn mới tới người cao tuổi. Câu đọc thử lấy nguyên văn `pause_speech` (đã có câu công khai ở E7).

## Quyền riêng tư & đồng ý *(mandatory)*

| Dữ liệu mới / thay đổi | Dạng lưu | Mục đích đồng ý | Hạn lưu | Gửi LLM? |
|---|---|---|---|---|
| Bản thu giọng của đội (20 câu hư cấu) | WAV ngoài repo `~/hoicon-evidence/004-voice-vi/audio/` | đồng ý bằng lời của thành viên đội ≥ 18 (ghi theo vai trò) — chưa phải người dùng nên chưa cần enum `consents` | xóa sau khi nộp Vòng 2 (10/01/2027) | Không |
| Điểm người nghe | bảng ngoài repo, chỉ "người nghe 1…n" + nhóm tuổi | đồng ý bằng lời | như trên | Không |
| WAV tổng hợp, kết quả đo | ngoài repo (tổng hợp) / số tổng hợp vào báo cáo | — | — | Không |

Quyền Android mới: **không có ở `:app`**. `:voicelab` (công cụ, không phát hành): `RECORD_AUDIO` **chỉ khi** R1 bắt buộc — kiểm với
`docs/PLAY-POLICY.md`: không áp dụng vì `:voicelab` không lên Play. Không quyền SMS/nhật ký cuộc gọi/danh bạ/Accessibility.

## UX người cao tuổi *(mandatory nếu có màn hình hoặc câu chữ mới)*

- Không có màn hình mới cho người cao tuổi. `:voicelab` chỉ là công cụ đo (một màn chữ đơn giản hoặc không màn hình).
- Câu chữ: dùng nguyên văn `pause_speech` hiện có; 20 câu chuẩn là câu **người cao tuổi nói**, không phải câu app nói.
- Kết luận "nút bấm là chính" bảo vệ người nói giọng địa phương, người khó phát âm, nơi ồn.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Có bảng giọng vi-VN khi tắt mạng cho hc-api36 và hc-api34 (giọng offline có/không, giọng được chọn) — đo trên:
  máy ảo AVD hc-api36 + hc-api34, n = 1 lần thăm dò mỗi AVD, sau boot nguội.
- **SC-002**: Độ trễ TTS `speak()` → `onStart` câu đầu SafePause có p50/p95 nguội và ấm; ngưỡng quyết định p95 ấm ≤ 1 000 ms —
  đo trên: máy ảo hc-api36 + hc-api34, mạng tắt, n ≥ 20 mỗi kiểu mỗi AVD.
- **SC-003**: Độ trễ phát âm thanh thu sẵn có p50/p95 nguội/ấm để so với SC-002 — đo trên: máy ảo hc-api36 + hc-api34, n ≥ 20.
- **SC-004**: WER và độ chính xác ý định cho bộ tổng hợp (20 câu) và bộ đội thu (20 câu × ≥ 1 người) trên mỗi AVD có bộ nhận
  dạng; ghi rõ "trên máy" hay "mạng" — đo trên: máy ảo hc-api36 + hc-api34, n = 20 câu mỗi bộ.
- **SC-005**: Điểm nghe trung bình (1–5, độ rõ + dễ chịu) cho giọng TTS được chọn, ≥ 3 người nghe (ROADMAP gốc 5 người — bản
  thu nhỏ), ít nhất 1 người ≥ 60 tuổi nếu có — đo trên: WAV tổng hợp từ hc-api36, nghe qua loa điện thoại.
- **SC-006**: Quyết định TTS + STT ghi trong báo cáo khớp 100% quy tắc FR-011 (reviewer đối chiếu) và `:app` release vẫn 0
  `RECORD_AUDIO`/0 `INTERNET`; repo có 0 tệp giọng người thật (`git ls-files` không có WAV/M4A ngoài đoạn tổng hợp của FR-004).

## Kế hoạch bằng chứng *(mandatory)*

- Log `HC_VOICE` của từng lần chạy (`~/hoicon-evidence/004-voice-vi/logs/`), lệnh đã chạy, ngày, AVD.
- Output `python3 scripts/voice-wer.py …` cho từng bộ × AVD; `python3 -m unittest discover -s scripts/tests`.
- `apps/android/gradlew -p apps/android :rules:test :app:lintDebug :voicelab:lintDebug :voicelab:assembleDebug` +
  grep manifest release đã merge của `:app`.
- Bảng điểm người nghe (ẩn danh) + ghi chú đồng ý; báo cáo `security-privacy-reviewer` (micro, dữ liệu giọng).
- Dòng FTL/máy thật: số đo hoặc `BLOCKED`.

## Ngoài phạm vi & mốc cắt

- Ngoài phạm vi: đổi `Speaker`/SafePause; âm thanh thu sẵn thật trong `:app` (P2-05); STT đám mây FPT.AI/Gemini (đã cắt);
  nhận dạng trong lúc đang gọi; màn E5 "Thử giọng" (P2-05/020); giọng con thu sẵn (I5 — chỉ thuyết minh); mua giọng đọc.
- Nếu trễ, cắt trước theo thứ tự: (1) bộ đội thu ⇒ chỉ bộ tổng hợp; (2) người nghe ⇒ chỉ số đo khách quan; (3) đo âm thanh
  thu sẵn ⇒ chỉ TTS. Không cắt: SC-001, SC-002, quyết định FR-011.

## Assumptions

- AVD hc-api36/hc-api34 là ảnh `google_apis_playstore` (có Google TTS; bộ nhận dạng trên máy có thể cần tải mô hình).
- Tiến thu 20 câu bằng điện thoại/máy tính, chuyển sang WAV 16 kHz mono (lệnh `ffmpeg` ở quickstart) trước khi chạy US2;
  thiếu thì phần đó `BLOCKED`, phần còn lại chạy tiếp.
- Firebase/FTL chưa có (W0-3) ⇒ máy thật nhiều khả năng `BLOCKED`.
