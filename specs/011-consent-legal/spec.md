# Spec 011: Văn bản đồng ý theo từng mục đích, DPIA rút gọn và quy trình thí điểm

**Mã ROADMAP**: `P1-06` · **Làn**: B (`docs/legal/**`, `docs/PRIVACY-DPIA.md`, `docs/PILOT-PROTOCOL.md`, `backend/**`)
· **Cột mốc**: điều kiện vào thí điểm (`029-pilot-kit`, Gate M2) · **Phụ thuộc**: 020 (sổ đồng ý), 034 (xóa dữ liệu, hạn
lưu) · **Nhánh**: `feat/w1-server` · **Luật**: CLAUDE.md luật 6, 7, 8; Luật BVDLCN 91/2025/QH15, Nghị định 356/2025,
Luật AI 134/2025/QH15 (tên và số hiệu lấy từ `docs/research/notes/09_agentic_ai_tech_feasibility.md`; **chưa đối chiếu
văn bản gốc, không trích số điều**).

> **Mọi văn bản trong spec này là BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Spec không tuyên bố
> "tuân thủ pháp luật"; nó tạo bản nháp có cấu trúc, kiểm được bằng máy, để Minh (và luật sư nếu cần) duyệt.

---

## 1. Bối cảnh

Sổ `consents` ghi `purpose` + `consent_version` + `text_sha256` nhưng **không có văn bản gốc nào trong repo để băm**: Android
tự ghép chuỗi giao diện rồi băm (`ConsentTexts.kt`), nên chuyện "người này đã đồng ý với chữ gì" chỉ truy được bằng cách đọc
mã Android theo từng phiên bản. Enum có 10 mục đích; Android mới có chữ cho 6 (`core_protection`, `guardian_alerts`,
`lookups`, ba trang quyền). `PRIVACY-DPIA.md` và `PILOT-PROTOCOL.md` mới là khung (P0-05).

| Mục đích (`consents.purpose`) | Chữ trong app hiện tại | Ai thực thi ở máy chủ |
|---|---|---|
| `core_protection` | có (E3, bốn thẻ) | `POST /v1/events` ⇒ 403 `consent_withdrawn` (034) |
| `call_screening`, `usage_monitoring`, `overlay_pause` | có (trang quyền E4) | không (quyền do Android thực thi) |
| `guardian_alerts` | có (hai thẻ trong E3) | không xếp tin Zalo nếu thiếu (034) |
| `lookups` | có (E10) | `POST /v1/lookups` ⇒ 403 (026) |
| `llm_processing`, `voice_input`, `drills`, `pilot_research` | **chưa có** | `drills`: lời mời diễn tập (028); còn lại **chưa thực thi** |

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-11.1 | **P1** | Là người cao tuổi, tôi đọc được chữ đồng ý ngắn, ấm áp, không thuật ngữ, và biết mình đồng ý chuyện gì, gửi gì cho ai, giữ bao lâu, rút thế nào |
| US-11.2 | **P1** | Là đội, với mỗi bản ghi trong `consents` tôi truy ra đúng văn bản đã đồng ý (phiên bản + sha256 → tệp) |
| US-11.3 | **P1** | Là Minh, tôi có một bộ văn bản nháp để duyệt, và máy cảnh báo ngay nếu có mục đích thiếu văn bản hoặc văn bản đổi mà chưa tăng phiên bản |
| US-11.4 | **P2** | Là người tham gia thí điểm, tôi biết quy trình: chỉ người ≥ 18 tuổi, diễn tập thế nào, rút lui và xóa dữ liệu ra sao, gọi ai khi cần |

## 3. Yêu cầu chức năng

- **(FR-001)** Mỗi giá trị của enum `Purpose` (`consents.py`) có **đúng một** văn bản tiếng Việt
  `docs/legal/consent/<purpose>.vi.md`; không có tệp thừa, không có mục đích thiếu.
- **(FR-002)** `docs/legal/consent/manifest.json` liệt kê từng văn bản với `version` (dạng `YYYY.MM-vN`, ≤ 16 ký tự, vừa cột
  `consent_version`), `sha256`, `status` (`draft`/`approved`). sha256 là băm UTF-8 của **chữ hiển thị chuẩn hóa**
  (các dòng khác rỗng giữa hai dấu `BEGIN-TEXT`/`END-TEXT`, nối bằng `\n`) — cùng cách Android băm chuỗi nối.
- **(FR-003)** Bất biến lịch sử: manifest có danh sách `released` (cặp mục đích + phiên bản + sha256 đã đưa cho người thật).
  Đổi chữ của một cặp đã `released` mà không tăng phiên bản ⇒ kiểm tra thất bại. Bảng `consents` chỉ ghi thêm (đã có trigger).
- **(FR-004)** Mọi văn bản mang dòng "BẢN NHÁP — chờ Minh duyệt" khi `status=draft` và có mục "Điểm chờ quyết" (cuối tệp,
  không hiển thị cho người dùng); không văn bản nào `approved` trong spec này.
- **(FR-005)** Chất lượng chữ hiển thị (kiểm bằng máy, thô; ngưỡng ở SC-004): giọng ấm áp xưng "bác"/"con bác"; không số điều luật, không
  thuật ngữ pháp lý nặng; không dãy số giống số điện thoại; văn bản về AI/tác tử mở đầu bằng "Đây là trợ lý AI HỏiCon".
- **(FR-006)** Mỗi văn bản nói rõ: làm gì, dữ liệu nào đi đâu, **không** làm gì (không nghe cuộc gọi, không đọc tin nhắn…),
  giữ bao lâu, rút lại bằng cách nào. Mọi con số (hạn lưu, 10 phút, 2 lần/tháng) khớp tài liệu nguồn (`DATA-MODEL.md` §6, spec 028).
- **(FR-007)** `docs/PRIVACY-DPIA.md` bản rút gọn hoàn chỉnh: mô tả xử lý theo từng mục đích, luồng dữ liệu, dữ liệu nhạy cảm,
  quyền chủ thể, rủi ro + biện pháp, công khai AI, thí điểm; giữ nguyên phần "quy trình vận hành đã cài đặt" của 034.
- **(FR-008)** `docs/PILOT-PROTOCOL.md`: chỉ người ≥ 18 tuổi; diễn tập ≤ 2 lần/tháng, trong khung giờ đã đồng ý; cơ quan và số
  điện thoại hư cấu; debrief; quyền rút lui/xóa dữ liệu; kênh hỗ trợ; điều kiện dừng; số liệu thu. Số liên hệ thật là chỗ trống
  `[CHỜ MINH ĐIỀN]`: được phép khi tài liệu còn "BẢN NHÁP", test cấm khi đã `approved`.
- **(FR-009)** Kiểm tra tự động (pytest, không cần DB): enum ↔ tệp ↔ manifest ↔ lược đồ `consent_record.v1.json` ↔ CHECK của
  `consents`; sha256 khớp; phiên bản hợp lệ; các luật chất lượng ở FR-005; DPIA nhắc đủ mọi mục đích; PILOT-PROTOCOL có đủ mục.
- **(FR-010)** Lệnh `python -m hoicon.ops.consent_texts check|write` tính lại sha256 (`write` chỉ ghi `manifest.json`).
- **(FR-011)** Báo cáo (không sửa) các chỗ Android hard-code chuỗi đồng ý cần đồng bộ cho làn A.

## 4. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Phủ mục đích | 10/10 giá trị enum có đúng 1 văn bản; 0 tệp thừa | `test_consent_texts.py` |
| **(SC-002)** | sha256 khớp | 10/10 `sha256` trong manifest = băm tính lại; đổi 1 ký tự ⇒ test đỏ | test + đột biến |
| **(SC-003)** | Bất biến phiên bản | đổi chữ của cặp `released` mà giữ phiên bản ⇒ đỏ; tăng phiên bản ⇒ xanh | test đơn vị trên dữ liệu giả |
| **(SC-004)** | Dễ đọc | ≤ 25 từ/câu trung bình; ≤ 160 từ/văn bản; 0 số điều luật; 0 dãy số ≥ 4 chữ số | test |
| **(SC-005)** | Công khai AI | 6/6 văn bản thuộc nhóm AI/tác tử mở đầu bằng câu công khai | test |
| **(SC-006)** | Duyệt độc lập | `privacy-audit` 0 mục High; `ux-elder-reviewer` 0 mục chặn | báo cáo reviewer |
| **(SC-007)** | Duyệt của Minh | Minh chuyển `draft` → `approved` | **BLOCKED** (Minh) |
| **(SC-008)** | Thử với người thật | Người cao tuổi thật đọc hiểu văn bản (hỏi lại bằng lời) | **BLOCKED** (cần thí điểm, 029 giai đoạn 2) |

## 5. Làm rõ (Spec Kit `clarify`, 18/10/2026 — tự quyết, không hỏi lại theo lệnh Tiến)

| # | Điểm mơ hồ | Quyết định | Lý do |
|---|---|---|---|
| Q1 | Băm tệp nguyên bản hay chữ hiển thị? | Chữ hiển thị chuẩn hóa (giữa `BEGIN-TEXT`/`END-TEXT`) | Ghi chú soạn thảo đổi không được làm đổi sha256 đã ghi vào sổ |
| Q2 | Khớp thế nào với cách Android băm? | Chuẩn hóa = các dòng khác rỗng nối `\n`, mỗi đoạn một dòng | Android băm `joinToString("\n")` các chuỗi tài nguyên; làn A chỉ cần mỗi đoạn một chuỗi |
| Q3 | Phiên bản cho văn bản mới? | `2026.10-v3` (bản Android đang dùng là `2026.10-v2`) | Chữ khác bản đang dùng ⇒ phải tăng (luật 7); chưa có bản nào `released` cho người thật |
| Q4 | Ai viết "kênh hỗ trợ"? | Văn bản đồng ý chỉ nói "người của HỏiCon đã hướng dẫn bác"; số liên hệ thật chỉ ở `PILOT-PROTOCOL.md` dưới dạng chỗ trống "[CHỜ MINH ĐIỀN]" | Không bịa số điện thoại/email; chữ đồng ý không đổi khi đổi số |
| Q5 | Người giám hộ xem lại lịch sử trên web có thuộc `guardian_alerts`? (câu hỏi mở của 027, ghi chú i) | Bản nháp **nói rõ có**; ghi là điểm chờ Minh quyết ở cuối tệp | Minh/DPIA phải quyết; nếu quyết "không" thì tách mục đích mới (luật 7) |
| Q6 | Có đưa `llm_processing`, `voice_input`, `pilot_research` vào ngay khi máy chủ chưa thực thi? | Có văn bản, và DPIA ghi rõ "chưa thực thi ở máy chủ" | Enum đã có 10 giá trị; thiếu chữ là thiếu bằng chứng khi dùng |
| Q7 | Có tạo skill `consent-copy`? | **Không** trong spec này | `.claude/**` ngoài quyền của lượt này; `ops.consent_texts` + test thay thế được một phần |
| Q8 | Server có từ chối cặp (phiên bản, sha256) lạ? | **Không** (ngoài phạm vi; đổi hành vi API khi Android chưa đồng bộ sẽ chặn thiết bị) | Mục #7 review 034 vẫn mở; manifest tạo nền cho việc đó |
| Q9 | Câu hỏi "hạn lưu" trong chữ: 90 ngày (app đang nói) hay theo từng loại? | Theo từng loại: dữ liệu cuộc gọi 90 ngày, hồ sơ vụ việc 12 tháng sau khi đóng | `DATA-MODEL.md` §6; chữ Android hiện tại "tối đa 90 ngày" chưa đủ ⇒ ghi vào danh sách đồng bộ |

## 6. Ngoài phạm vi

Sửa Android (`apps/android/**`), tạo màn E12 rút đồng ý, thực thi `llm_processing`/`voice_input`/`pilot_research` ở máy chủ,
kiểm (phiên bản, sha256) ở máy chủ, bản dịch tiếng Anh, nhờ luật sư rà soát, chấp nhận ADR-011.
