# Spike P1-S5: Giọng nói tiếng Việt trên máy (thu nhỏ)

- Spec: `specs/004-voice-vi` (nhánh `feat/004-voice-vi`) · Liên quan: ADR-001, ADR-007, ADR-008, `docs/spikes/P1-S2-dung-an-toan.md`,
  `docs/EMULATOR.md` §1.2
- Trạng thái: **đã đo trên 2 máy ảo (15/10/2026); thiếu bản thu của đội, điểm người nghe và máy thật** — xem §6 (quyết định) và "BLOCKED".
- Thứ tự thời gian: quy tắc §0 ghi lúc 15:11 (giờ máy dev, 15/10/2026); phép đo đầu tiên chạy lúc 15:17 — sau quy tắc.
- Mọi số dưới đây đo trên **máy ảo** hc-api36 (Android 16) và hc-api34 (Android 14), Linux headless `-no-audio`, mạng tắt trừ khi ghi khác; **máy ảo ≠ máy thật**. Bằng chứng thô: `~/hoicon-evidence/004-voice-vi/logs/` (ngoài repo).

## 0. Quy tắc đăng ký trước (FR-011)

> Ghi ngày **15/10/2026**, trước khi chạy bất kỳ phép đo nào của spec 004. Không sửa sau khi thấy số; nếu thấy quy tắc sai thì
> ghi một mục "đính chính" riêng kèm lý do, giữ nguyên bản gốc.

**TTS (giọng đọc SafePause)**
- Đường chính = giọng vi-VN **offline của máy** khi cả ba điều sau cùng đúng:
  1. có giọng offline (không cần mạng, đã cài, dùng được) trên **cả hai** AVD (hc-api36, hc-api34);
  2. p95 độ trễ `speak()` → `onStart` **ấm** ≤ **1 000 ms** (mạng tắt, n ≥ 20 mỗi AVD);
  3. điểm nghe trung bình ≥ **3,5/5** với ≥ 3 người nghe.
- Dự phòng khi `tts_unavailable` = âm thanh thu sẵn (làm thật ở P2-05); báo cáo kèm so sánh độ trễ với `MediaPlayer`.

**STT (trả lời bằng giọng)**
- Ghi "**tùy chọn ở MVP**" chỉ khi cả ba điều sau cùng đúng:
  1. có nhận dạng **trên máy** cho vi-VN;
  2. độ chính xác ý định ≥ **95%** trên **bản thu của đội**;
  3. WER ≤ **20%** trên bản thu của đội.
- Ngược lại: "**MVP chỉ nút bấm, giọng nói để sau**". Trong mọi trường hợp **nút bấm là chính**.

**Mẫu số**
- Độ chính xác ý định = (số câu `answer` — 12 câu — × số người thu) được phân loại đúng / tổng. Với một người thu, 11/12 = 91,7% **không đạt**.
- WER tính trên cả 20 câu của bộ.
- Bộ tổng hợp (TTS đọc lại) chỉ là cận trên lạc quan; **không** dùng để chốt "tùy chọn".

**Thiếu dữ liệu (không diễn giải lại sau khi thấy số)**
- Thiếu bản thu của đội ⇒ STT = "MVP chỉ nút bấm".
- Thiếu điểm nghe (< 3 người) ⇒ TTS đường chính **chưa chốt** (`BLOCKED: chờ điểm nghe`); dự phòng âm thanh thu sẵn vẫn ghi.
- Thiếu giọng offline trên một AVD ⇒ không đạt điều kiện 1 của TTS.
- Thiếu máy thật ⇒ không đổi quyết định nhưng ghi rõ "chưa kiểm trên máy thật".

**Nhãn môi trường:** mọi số ghi AVD/máy thật + ngày + n; máy ảo ≠ máy thật.

> Ghi chú (không sửa nguyên văn quy tắc): §0 **siết chặt hơn một chút** so với `spec.md` FR-011 — thêm "không cần mạng, đã cài, dùng được" và
> "n ≥ 20 mỗi AVD". Kết quả §6 không đổi nếu áp bản FR-011 gốc. Trình tự thời gian chỉ chứng minh được bằng giờ sửa tệp (chưa commit
> theo lệnh "không commit"): spec 15:10, §0 15:11, phép đo đầu 15:17 — Tiến nên commit §0 nguyên trạng nếu cần bằng chứng mạnh hơn.

## 1. Giọng TTS tiếng Việt (FR-002 · SC-001) — mạng tắt, n = 1 lần thăm dò mỗi AVD

| AVD | Giọng `vi` | Offline | Cần mạng | Chất lượng / độ trễ khai báo | Giọng được chọn | Kết luận thử nói |
|---|---|---|---|---|---|---|
| hc-api36 | 11 | 6 (`vi-VN-language`, `vi-vn-x-gft/vic/vid/vie/vif-local`) | 5 (`…-network`) | tất cả 400 / 200 | `vi-VN-language` | `ok` (nói được, `onStart` 68 ms) |
| hc-api34 | 11 | 6 (như trên) | 5 | tất cả 400 / 200 | `vi-VN-language` | `ok` (`onStart` 116 ms) |

- Engine mặc định `com.google.android.tts` trên cả hai. Gói vi-VN trên hc-api34 là gói đã sửa theo `docs/EMULATOR.md` §1.2 (001).
- **Cảnh báo chọn giọng:** mọi giọng cùng `quality=400, latency=200` nên tiêu chí của `Speaker.pickOfflineVietnamese`
  (`maxWith(quality, -latency)`) **hòa**; kết quả phụ thuộc thứ tự duyệt của `Set<Voice>` do engine trả, không do chất
  lượng. `vi-VN-language` là tên chung, chưa biết ánh xạ sang giọng nào. P2-05 nên **chọn giọng theo tên** sau buổi nghe.
- Phân biệt "không có giọng" với "giọng hỏng": bộ đo ghi `no_voice` / `broken_voice` (không `onStart` trong 5 s); cả hai AVD ra `ok`.

## 2. Độ trễ TTS và âm thanh thu sẵn (FR-003/004 · SC-002/003) — mạng tắt, n = 20 mỗi ô

Mốc **quyết định** (đăng ký trước): `speak()` → `onStart` của câu đầu "Đây là trợ lý AI HỏiCon." (cùng mốc `tts_started` của spec 001).

| AVD | Kiểu | `speak→onStart` p50 / p95 / max (ms) | Khởi tạo engine `onInit` p50 / p95 (ms) | Tới khung âm thanh đầu `onAudioAvailable` p50 / p95 (ms) |
|---|---|---|---|---|
| hc-api36 | nguội (engine mới mỗi lượt) | 59 / **64** / 68 (cộng `onInit`: 328 / 370 / 377) | 268 / 308 | 59 / 64 |
| hc-api36 | ấm (1 engine, cách 1 s) | 1 / **3** / 3 | — | 1 / 3 |
| hc-api34 | nguội | 355 / **404** / 409 (cộng `onInit`: 360 / 411 / 415) | 5 / 8 | 355 / 405 |
| hc-api34 | ấm | 1 / **1** / 1 | — | 1 / 1 |

Âm thanh thu sẵn — `MediaPlayer` phát `clip_pause_0.wav` (tổng hợp, 24 kHz, 112 KB), từ lệnh phát tới khi `currentPosition > 0`
("pos", độ phân giải 1 ms). Mốc `getTimestamp()` ("ts") **suy biến** (đồng hồ media chạy ngay khi `start()`), chỉ ghi để tham khảo:

| AVD | Kiểu | pos p50 / p95 (ms) | ts p50 / p95 (ms) |
|---|---|---|---|
| hc-api36 | nguội (tạo player + `prepare` + `start`) | 40 / 42 | 4 / 5 |
| hc-api36 | ấm (đã `prepare`, tua về 0) | 33 / 35 | 0 / 0 |
| hc-api34 | nguội | 40 / 50 | 6 / 8 |
| hc-api34 | ấm | 34 / 36 | 0 / 0 |

**Dao động giữa các lượt (cùng máy ảo, mã đo gần như không đổi):** hc-api36 lượt sớm (15:20 TTS, 15:25 clip, lúc RAM khả dụng ~2,6 GB) cho TTS nguội
p95 65 ms (+`onInit` 345 ms), ấm p95 6 ms; clip nguội pos p95 69 ms, ấm 38 ms. Lượt cuối (16:0x, bảng trên) thấp hơn — chênh vài chục ms cho thấy sai số
của máy ảo; **kết luận chỉ dựa trên thứ bậc độ lớn** (mọi đường ≪ 1 000 ms), không dựa chênh lệch nhỏ.

Giới hạn cần đọc kèm (R5, đã nêu từ T001):
- `onStart` theo tài liệu là lúc "soon before audio is played", không phải lúc ra loa; trên cả hai AVD khung âm thanh đầu
  (`onAudioAvailable`) đến gần như cùng lúc `onStart` ⇒ số trên là cận dưới của "thời gian tới tiếng", chưa tính bộ đệm phát.
- Ô **ấm** lặp lại đúng một câu nên rất có thể engine dùng bộ nhớ đệm (1 ms) — lạc quan; ô nguội mới gần với lần đầu mở cửa sổ rủi ro.
- Máy ảo chạy `-no-audio` (không có loa thật): độ trễ của đường âm thanh ra thiết bị không được đo.
- Thứ tự thực hiện: đoạn mẫu `clip_pause_0.wav` sinh từ chính TTS (SynthesizeTest) nên T012 chạy trước T011.

## 3. Nhận dạng giọng nói vi-VN (FR-006/007 · SC-004)

**Thăm dò hỗ trợ** (`SpeechRecognizer`, mạng tắt):

| AVD | Dịch vụ nhận dạng | Trên máy (`isOnDeviceRecognitionAvailable`) | vi-VN đã cài trên máy | Hỗ trợ trên máy | Thử `triggerModelDownload` |
|---|---|---|---|---|---|
| hc-api36 | `com.google.android.as` (AiAi), GoogleTTSRecognitionService | có | **có** (`vi-VN`) | 30 ngôn ngữ | không cần (đã có) |
| hc-api34 | như trên | có (dịch vụ) | **không** | 10 ngôn ngữ, **không có vi** | 1 lần, chờ 120 s: có mạng và tắt mạng đều **không cài được** |

⇒ "Có bộ nhận dạng trên máy" **không đồng nghĩa** có tiếng Việt: trên hc-api34 chỉ có bộ mặc định (dùng mạng).

**Chạy trên 20 câu chuẩn bộ tổng hợp** (TTS hc-api36 đọc lại; âm thanh qua đường ống từ tệp, không micro; mạng như ghi):

| AVD | Bộ nhận dạng | Mạng | n | WER | Ý định đúng | Độ chính xác ý định |
|---|---|---|---|---|---|---|
| hc-api36 | trên máy (`on_device`) | tắt | 20 | 7,2 % | 12/12 | 100 % |
| hc-api34 | mặc định (`default_network`) — **không dùng cho sản phẩm** | bật | 20 | 8,6 % | 11/12 | 91,7 % |

- Câu sai ý định ở hc-api34: `a03` "Dạ có nha…" nghe thành "giả con nha…" ⇒ không có từ khóa "có" ⇒ ý định `none`.
- Biến thể miền Nam "hông" bị bộ nhận dạng chuẩn hóa thành "không" (WER của `a07`, `a11` ≈ 0,3) nhưng **không đổi ý định**.
- Bộ tổng hợp là **cận trên lạc quan**: giọng TTS rõ, đều, không ồn, không phải giọng người già vùng miền. Không dùng để chốt "tùy chọn".
- Phát hiện kỹ thuật: bộ nhận dạng trên máy ở hc-api36 trả chữ **chỉ qua `onPartialResults`**; gói kết quả cuối (`onResults`)
  **rỗng**. Bộ đo dùng bản nháp cuối làm bản chép (ghi `transcript_source`). Lần thử đầu đưa thẳng descriptor tệp (kèm `EXTRA_PARTIAL_RESULTS=false`)
  cho kết quả rỗng và log của dịch vụ cho thấy âm thanh bị đẩy hết trong ~1 ms; bộ đo vì vậy đưa qua đường ống đúng nhịp 100 ms/khối.
  **Chưa thử riêng** "tệp + partial=true", nên chưa kết luận lỗi do nhịp hay do thiếu kết quả từng phần. Sản phẩm (nếu giữ STT) phải xử lý đặc điểm này.
- Độ trễ nhận dạng đo từ **byte cuối** tới kết quả: p50/p95 = 2 / 3 ms (hc-api36), 279 / 2 434 ms (hc-api34, mạng); phần lớn chữ đã có
  khi âm thanh còn đang phát (600 ms im lặng cuối) nên số này không đo "độ trễ người dùng cảm nhận".
- **R1 (thực nghiệm)**: thu hồi `RECORD_AUDIO` ⇒ hc-api36 (trên máy) vẫn nhận dạng 20/20; hc-api34 (mặc định) lỗi `ERROR_INSUFFICIENT_PERMISSIONS` (9) 20/20.
  Quyền chỉ cần cho bộ mặc định ⇒ giữ ở `:voicelab` (K2); `:app` không đổi.

**Bộ đội thu (giọng người thật):** `BLOCKED: chờ Tiến thu âm (data/voice/sentences.v1.json)` — chưa có tệp; không đo.

## 4. Điểm nghe (FR-010/011 · SC-005)

`BLOCKED: chờ người nghe chấm điểm MOS` — chưa có người nghe (cần ≥ 3, ≥ 1 người ≥ 60 tuổi nếu có). WAV để nghe đã sẵn
(28 tệp tại `~/hoicon-evidence/004-voice-vi/wav/`, sinh từ hc-api36: 4 câu SafePause, 4 cụm khó, 20 câu chuẩn). Điểm 0 người nghe.

## 5. Máy thật (FR-013)

`BLOCKED: chờ Firebase/máy thật (W0-3)` — chưa chạy TtsProbe/TtsLatency/SttProbe trên máy thật. Chưa biết giọng/STT trên máy Samsung,
Xiaomi, Oppo (nhiều máy không dùng Google TTS mặc định) và Android 10–12 (minSdk của app là 29, `:voicelab` là 33).

## 6. Quyết định theo quy tắc §0 (không diễn giải lại)

**TTS**
- Điều kiện 1 (có giọng offline trên cả hai AVD): **đạt** (6 giọng offline mỗi AVD, `ok`).
- Điều kiện 2 (p95 ấm ≤ 1 000 ms): **đạt** (3 ms và 1 ms; lượt sớm hc-api36: 6 ms; nguội cộng khởi tạo 370 / 411 ms).
- Điều kiện 3 (điểm nghe ≥ 3,5, ≥ 3 người): **chưa có dữ liệu** ⇒ theo mục "Thiếu dữ liệu": đường chính **chưa chốt**
  (`BLOCKED: chờ điểm nghe`). Hai điều kiện khách quan đã đạt; việc còn lại là nghe.
- Dự phòng khi `tts_unavailable` = âm thanh thu sẵn (làm thật ở P2-05). So độ trễ: phát clip nguội p95 42 / 50 ms, ấm 35 / 36 ms (hc-api36 / hc-api34)
  — nhanh hơn TTS nguội cộng khởi tạo (370 / 411 ms) nhưng mọi đường đều ≪ ngân sách 3 s; lợi ích của clip là **chắc chắn có tiếng**, không phải tốc độ.

**STT**
- Thiếu bản thu của đội ⇒ "**MVP chỉ nút bấm, giọng nói để sau**". Trong mọi trường hợp **nút bấm là chính**.
- Dữ kiện thêm (không đổi quyết định): vi-VN trên máy chỉ có ở hc-api36 chứ không ở hc-api34; muốn dùng STT trên máy phải có luồng
  cài mô hình, và kết quả tùy phiên bản Android/Google; bộ tổng hợp (cận trên) chỉ đạt ý định 100 % / 91,7 %.

## 7. Rủi ro còn lại

1. Điểm nghe và bản thu của đội chưa có ⇒ TTS đường chính và STT chưa kiểm bằng giọng người; cần Tiến thu 20 câu và 3 người nghe.
2. Hòa điểm khi chọn giọng (§1): chọn theo tên sau khi nghe, tránh phụ thuộc thứ tự `Set`.
3. `onStart` ≠ ra tiếng; máy ảo không có loa ⇒ cần đo ở máy thật (dùng `AudioTrack`/loopback nếu có).
4. Bộ nhận dạng trên máy không đồng nhất giữa API 34 và 36 (có/không vi-VN); `onResults` rỗng ở hc-api36 ⇒ mã sản phẩm phải dùng kết quả từng phần.
5. Bộ mặc định dùng mạng và `RECORD_AUDIO` (lỗi 9 nếu thiếu) — trái bất biến "không mạng" của đường dừng an toàn; chỉ được dùng cho tùy chọn ngoài đường găng, nếu có.
6. Máy chủ phụ thuộc Google TTS/Google app: máy không có Google Mobile Services sẽ không có giọng này (ADR-007/008 đã có dự phòng).

## 8. Đề xuất nguồn âm thanh thu sẵn cho P2-05 (không mua gì)

1. **Tự thu** 4 câu SafePause + câu nhắc E5 bằng giọng thành viên đội ≥ 18 tuổi, đồng ý bằng văn bản (enum đồng ý + phiên bản, skill `consent-copy`);
   lưu tệp trong `:app` chỉ sau khi chốt giọng và qua P1-08 (tệp giọng người thật hiện **không** vào repo).
2. Tạm dùng đoạn **tổng hợp** như `clip_pause_0.wav` làm dự phòng kỹ thuật; **chưa kiểm điều khoản sử dụng** đầu ra của Google TTS khi phát hành —
   phải kiểm trước khi đưa vào bản phát hành.
3. Hoãn "giọng con" (I5): chỉ đưa vào thuyết minh, không làm trong spike.

## 9. Đề xuất cho ADR (không sửa ADR trong spec này)

- ADR-007/008: nếu giữ "TTS khởi động sẵn", ghi thêm số nguội cộng khởi tạo 370 / 411 ms (máy ảo) và rằng `tts_started` ≠ ra tiếng; chờ số máy thật.

## 10. Lượt chạy chính thức và lượt bị loại (minh bạch)

Có nhiều lượt chạy vì bộ đo được sửa trong lúc đo; số trong §1–§3 lấy từ **lượt cuối dùng mã cuối** (sau mọi sửa), quy tắc chọn đặt trước là
"lượt hợp lệ gần nhất, mã không đổi", không chọn theo kết quả:

| Phép đo | Lượt dùng (log trong `~/hoicon-evidence/004-voice-vi/logs/`) | Lượt khác và lý do không dùng |
|---|---|---|
| TTS api36 | `tts-hc-api36-20261015-160107` (quickstart T023, mã cuối) | `-151755` (chưa đo `onAudioAvailable`), `-152010` (số xem §2 "dao động") — cùng kết luận |
| TTS api34 | `tts-hc-api34-20261015-153911` | — |
| Clip api36 / api34 | `clip-hc-api36-20261015-160244` / `clip-hc-api34-20261015-154103` | `clip-hc-api36-20261015-152542` (số xem §2 "dao động") |
| STT thăm dò | `stt-hc-api36-20261015-152736`, `stt-hc-api34-20261015-154156` (tắt mạng) và `-154414` (bật mạng) | — |
| STT bộ tổng hợp api36 | `stt-synthetic-hc-api36-20261015-160649` (sau cứng hóa script, quyền micro thu hồi, WER 7,2 %, 12/12; trùng `-153436` và `-160340`) | 15:27 (kết quả rỗng: đưa thẳng tệp), 15:29 (lỗi 5: đóng đầu ống sớm), 15:29 (cuối rỗng: chưa lấy partial) — lỗi công cụ, đã chẩn đoán; 15:36 (thí nghiệm R1, thu hồi quyền; cũng 20/20) |
| STT bộ tổng hợp api34 | `stt-synthetic-hc-api34-20261015-154850` | 15:46 (BLOCKED: không có vi-VN trên máy, đúng thiết kế); 15:52 (thí nghiệm R1: lỗi 9 ×20) |

Chưa thấy chữ đã nhận dạng trong logcat hệ thống: 0/4 480 dòng chứa câu chuẩn (kiểm trên hc-api36 sau lượt chạy, 15/10/2026).

## 11. Cứng hóa sau review bảo mật (15/10/2026)

Reviewer báo 2 High, 4 Medium (đã sửa trong `scripts/voice-lab.sh` và `SttRunTest`): giọng thật của đội không qua bộ nhận dạng mạng trừ khi có
`--confirm-team-audio-to-cloud`; `RECORD_AUDIO` mặc định thu hồi (chỉ cấp cho bộ mặc định); `-no-audio` kiểm trên đúng tiến trình của AVD;
dọn bản sao WAV/kết quả trên máy chủ và máy ảo ở mọi đường thoát; thư mục bằng chứng quyền 700; `.gitignore` chặn âm thanh trong
`apps/android/voicelab/` và `data/voice/`. **Đề xuất cho checkout chính** (ngoài làn A): thêm mẫu `*.wav|*.m4a|*.mp3` vào `.gitignore` gốc và kiểm
âm thanh trong hook `guard-privacy`; thêm câu "âm thanh có thể được gửi tới Google" vào mẫu đồng ý bằng lời cho người thu.
