# Đánh giá tác động xử lý dữ liệu cá nhân (DPIA rút gọn)

> **BẢN NHÁP — chờ Minh duyệt** (spec 011, 18/10/2026). Chưa phải ý kiến pháp lý. Căn cứ (tên và số hiệu lấy từ
> `docs/research/notes/09_agentic_ai_tech_feasibility.md`, **chưa đối chiếu văn bản gốc, không trích số điều**): Luật Bảo vệ dữ liệu
> cá nhân 91/2025/QH15, Nghị định 356/2025, Nghị định 330/2026 (xử phạt thiếu nhật ký đồng ý), Luật Trí tuệ nhân tạo 134/2025/QH15.
> Nên nhờ người có chuyên môn pháp lý rà trước khi thí điểm với người thật. Văn bản đồng ý từng mục đích: `docs/legal/consent/`.

## 1. Mô tả xử lý

Cơ sở xử lý là **đồng ý** của từng người, ghi vào sổ `consents` (chỉ ghi thêm; mỗi dòng có mục đích, phiên bản, sha256 của đúng văn bản đã đọc).
Hạn lưu theo `docs/DATA-MODEL.md` §6. Cột "Máy chủ có thực thi?" nói **mã hiện tại đang làm gì**, không phải điều văn bản hứa.

| Mục đích (`consents.purpose`) | Dữ liệu | Hạn lưu | Máy chủ có thực thi? |
|---|---|---|---|
| `core_protection` | Sự kiện rủi ro từ máy: loại sự kiện, cuộc gọi tới/đi, thời lượng, gói ứng dụng tài chính, nút bấm, thời điểm; số điện thoại chỉ dưới dạng `HMAC(pepper, h1)` + 3 số cuối | `risk_events` 90 ngày; sự cố 12 tháng sau khi đóng | **Có**: rút đồng ý ⇒ `POST /v1/events` 403 `consent_withdrawn` (034) |
| `call_screening`, `usage_monitoring`, `overlay_pause` | Không có dữ liệu riêng: là quyền hệ điều hành cấp cho app. Ghi vào sổ để chứng minh đã giải thích | — | **Không** (Android thực thi quyền; máy chủ không kiểm) |
| `guardian_alerts` | Nội dung tin gửi người giám hộ qua Zalo (tóm tắt sự cố, 3 số cuối), trạng thái quyền mỗi 15 phút; người giám hộ xem lại sự cố và truy vết trên web | tin: `jobs.payload` 30 ngày; sự cố 12 tháng | **Một phần**: thiếu ⇒ không xếp tin Zalo (034). **Không kiểm** ở các route đọc của web (câu hỏi mở (i) của spec 027) |
| `lookups` | Kết quả tra cứu số/link: `HMAC` chủ thể, 3 số cuối (số điện thoại), kết luận, nguồn; không lưu số thô, h1, URL | `verifications` 90 ngày | **Có**: chưa đồng ý ⇒ 403; hạn mức giờ/ngày/30 ngày; rút đồng ý ⇒ xóa phần nhận diện, giữ dòng đếm hạn mức |
| `drills` | Lịch diễn tập, mã lựa chọn của từng bước (không lưu chữ tự do), điểm, thời điểm | `drills` 12 tháng | **Một phần**: lời mời chỉ khi có bài hợp lệ trong khung giờ; cờ `is_drill` tự khai bị hạ (028). Chưa có bước người cao tuổi đồng ý từng khung giờ |
| `llm_processing` | Bản tóm tắt đã che PII gửi nhà cung cấp LLM ở nước ngoài | `agent_steps` nội dung 30 ngày | **Chưa**: mã không kiểm đồng ý này ở đâu |
| `voice_input` | Giọng nói trả lời "có/không/không biết" qua nhận dạng của Android | — | **Chưa**: chưa có tính năng; chưa có mã ghi/kiểm |
| `pilot_research` | Heartbeat 15 phút (trạng thái quyền, phiên bản), số liệu thí điểm tổng hợp | `device_heartbeats` 90 ngày | **Chưa**: heartbeat chỉ kiểm `core_protection` |

## 2. Luồng dữ liệu
Máy (Android) → máy chủ HỏiCon (VPS, Việt Nam hoặc nơi đội chọn; Caddy HTTPS) → nhà cung cấp LLM (nước ngoài: **chỉ dữ liệu đã che PII**,
gói trả phí không dùng để huấn luyện — cần xác nhận điều khoản thật khi có khóa API) → Zalo (người giám hộ). Mọi lời gọi LLM đi qua `llm_router`
(che PII, ngân sách, timeout, rơi về mẫu soạn sẵn). Số điện thoại: máy băm `h1`, máy chủ chỉ giữ `HMAC(pepper, h1)` + 3 số cuối (ADR-006).
Nhật ký proxy che token một lần và tiêu đề bí mật (`docs/setup/VPS-DEPLOYMENT.md` §6). Nhật ký này vẫn có địa chỉ IP khách (mục đích: vận hành và điều tra sự cố); giữ tối đa 5 × 10 MB mỗi dịch vụ rồi tự xóa (hạn theo dung lượng, `docs/DATA-MODEL.md` §6).

## 3. Dữ liệu nhạy cảm
- Không thu nội dung cuộc gọi/SMS/danh bạ; không ghi âm; số điện thoại chỉ ở dạng băm (ADR-006).
  - `CallScreeningService` được gọi cho cả cuộc gọi **đến và đi** tới số không có trong danh bạ ⇒ DPIA ghi cả hai chiều (review bảo mật 09/10).
  - `h1` là SHA-256 không muối trên không gian ~10⁹ số ⇒ coi là **dữ liệu cá nhân đã bí danh hóa**, không phải ẩn danh; lưu trên máy phải mã hóa
    (Room + Tink AEAD, P2-05), không để trong SharedPreferences dạng rõ như bản spike.
  - Log chẩn đoán (tên gói ngân hàng + 3 số cuối + mức rủi ro) chỉ có ở bản debug.
- Danh sách đe dọa phát xuống máy chỉ là **bucket k-ẩn danh** (ADR-011, đang chờ Tiến chấp nhận), không phải tập h1.
- Dữ liệu về người ≥ 60 tuổi và quan hệ gia đình có thể được coi là nhạy cảm theo ngữ cảnh: nên được luật sư xác nhận phân loại.

## 4. Quyền chủ thể
| Quyền | Cách thực hiện hiện nay | Còn thiếu |
|---|---|---|
| Biết mình đồng ý gì | Văn bản đồng ý theo mục đích (`docs/legal/consent/`), sổ `consents` có phiên bản + sha256 | Bản nháp, chờ Minh duyệt |
| Rút đồng ý | Tắt quyền trong Cài đặt điện thoại; ghi dòng `granted=false` qua `POST /v1/consents`. `core_protection` ⇒ máy chủ thôi nhận sự kiện; `lookups` ⇒ xóa phần nhận diện | Màn E12 trên app; thực thi `llm_processing`, `voice_input`, `pilot_research` |
| Xóa dữ liệu | Qua đội thí điểm: `ops.data request-delete`; mục tiêu ≤ 72 giờ; sổ đồng ý giữ nhưng ẩn danh (mục "Xóa dữ liệu theo yêu cầu" bên dưới) | Màn trên app/web; thời hạn luật định chưa xác nhận |
| Xem/xuất dữ liệu | Chưa có công cụ tự phục vụ | `data_requests.kind = export` (để dành) |
| Phản đối/khiếu nại | Kênh hỗ trợ của thí điểm (`docs/PILOT-PROTOCOL.md` §5) | Số liên hệ chờ Minh điền |

## 5. Rủi ro & biện pháp
| Rủi ro | Biện pháp đã có | Còn lại |
|---|---|---|
| Rò rỉ DB | Không lưu số thô/h1/URL; khóa pepper + khóa dữ liệu ngoài DB; sao lưu mã hóa; Postgres không có cổng ra ngoài | Role `hoicon_app` chưa áp ở prod (012); sao lưu chưa chép ngoài máy |
| Prompt injection | Văn bản kẻ gian bọc `<untrusted>`, LLM chỉ nâng mức, công cụ có tác dụng phụ chỉ ở node cho phép | Eval ≥ 100 ca |
| Báo nhầm gây hoảng | Giọng ấm áp, không cụm hoảng sợ (kiểm bằng test), nút "tiếp tục" giữ 3 giây | Đo tỷ lệ báo nhầm khi thí điểm |
| Lạm dụng diễn tập | Cờ `is_drill` chỉ tin khi khớp bài đang chạy; hư cấu 100%; ≤ 2 lần/tháng; luôn debrief | Bước đồng ý từng khung giờ |
| Người giám hộ lạm quyền | Chỉ người đã ghép; token một lần; phiên 7 ngày | Thu hồi phiên thật (027); đồng ý xem lại trên web |
| Dò danh sách đe dọa qua tra cứu | Hạn mức giờ/ngày/30 ngày, k-ẩn danh, không bao giờ trả "an toàn" | Giới hạn theo IP ở proxy (Caddy mặc định không có) |
| Khôi phục bản sao lưu cũ làm sống lại dữ liệu đã xóa | Ghi trong tài liệu; chạy lại `purge_family` | Sổ xóa lưu ngoài DB (012) |
| Chuyển dữ liệu ra nước ngoài (LLM) | Chỉ dữ liệu đã che PII | Thực thi `llm_processing`; xác nhận điều khoản nhà cung cấp |
| Người dưới 18 tuổi tham gia | Quy trình tuyển hỏi tuổi; thí điểm chỉ ≥ 18 | Không có kiểm tra kỹ thuật |

## 6. Công khai AI
"Đây là trợ lý AI HỏiCon" mở đầu tin đầu tiên tới người cao tuổi, mọi tin Zalo trong một sự cố và các văn bản đồng ý về AI/tác tử
(test `AiDisclosureCopyTest` phía Android, test backend, `tests/contract/test_consent_texts.py`). Trang `/ai` giải thích: chưa có.

## 7. Thí điểm
Chỉ người ≥ 18 tuổi. Văn bản đồng ý có phiên bản trong `docs/legal/consent/`; quy trình, rút lui, xóa dữ liệu và kênh hỗ trợ ở
`docs/PILOT-PROTOCOL.md`. Mục đích thí điểm: `pilot_research`, `drills`.

## 8. Cần Minh quyết trước khi đưa cho người thật
1. Duyệt (hoặc sửa) 10 văn bản nháp; chuyển `status` sang `approved` và ghi `released` khi phát hành (`docs/legal/consent/README.md`).
2. `guardian_alerts` có bao gồm việc người giám hộ **xem lại** sự cố/truy vết trên web không (nếu không ⇒ tách mục đích mới + kiểm đồng ý ở route đọc).
3. `llm_processing`, `voice_input`, `pilot_research`: thực thi ở mã hoặc bỏ lời hứa trong văn bản (đang là điều kiện chặn).
4. Chấp nhận ADR-011 (bucket k-ẩn danh), kèm điều kiện của review bảo mật 026.
5. Số liên hệ và người phụ trách trong `PILOT-PROTOCOL.md`; nhờ rà soát pháp lý.

## Quy trình vận hành đã cài đặt (spec 034 — gia cố lõi)
Phần này ghi cái ĐÃ chạy được và kiểm bằng test; những gì phụ thuộc VPS/lịch chạy (spec 012) ghi rõ là chưa.

### Hạn lưu tự động
Job `retention` chạy mỗi ngày (khóa `retention:<ngày giờ VN>`), theo lô ≤ 1.000 dòng, lũy đẳng; `python -m hoicon.ops.data
retention --dry-run` in số dòng sẽ bị đụng. Bảng hạn lưu là DATA-MODEL §6 (test so khớp hằng số `RETENTION` với bảng đó).
`consents` không bao giờ bị đụng. Toàn văn tin gửi người giám hộ nằm trong `jobs.payload` nên bị xóa sau 30 ngày kể từ
khi job xong; `messages_out` không có cột văn bản và được giữ để đếm hạn mức Zalo.

### Xóa dữ liệu theo yêu cầu (US-09 / US-20.2)
1. Người dùng yêu cầu qua đội thí điểm (chưa có màn trên app: spec riêng sau; `requested_via` đã dự phòng `app`, `web`).
2. Đội chạy `python -m hoicon.ops.data request-delete --family <id>` (ngoài dev cần `--confirm`): ghi `data_requests`
   (`pending`) và xếp job `purge_family`. Mục tiêu hoàn tất ≤ 72 giờ; `status --request <id>` xem trạng thái.
3. Job: thu hồi thiết bị trước; xóa checkpoint đồ thị; xóa sự cố, sự kiện rủi ro, bước tác tử, job, tin gửi đi, token
   hành động, liên hệ tin cậy, mã ghép, xác minh, diễn tập, thiết bị; ẩn danh `members` (bí danh `[đã xóa]`, HMAC Zalo và
   bản mã định danh = NULL) và `families`. **Giữ nguyên `consents`** (Nghị định 356/2025): chỉ còn mục đích, đồng ý hay
   không, băm văn bản đồng ý và thời điểm; không còn định danh. `data_requests` giữ làm vết (không có văn bản tự do).
4. Token thiết bị/người giám hộ cũ bị từ chối ngay (401). Lỗi giữa chừng ⇒ yêu cầu `failed` kèm mã lỗi ngắn, job thử lại.
5. Chưa làm: xuất dữ liệu (`kind=export`), màn E12 trên app.

### Sao lưu
`docs/setup/BACKUP.md`. Bản sao lưu chứa dữ liệu cá nhân nên luôn mã hóa AES-256-GCM (khóa `HOICON_BACKUP_KEY_<kid>` riêng,
khác khóa dữ liệu) trước khi rời container; bản rõ không chạm đĩa. **Sau khi một gia đình bị xóa, bản sao lưu cũ vẫn chứa dữ
liệu của họ cho tới khi xoay vòng đẩy nó đi (tối đa ~4 tuần: 7 bản ngày + 4 bản tuần)** — phải nêu rõ điều này trong văn
bản đồng ý/chính sách khi thí điểm; không khôi phục bản cũ vào hệ thống đang chạy mà không chạy lại các yêu cầu xóa.

### Đồng ý được thực thi ở máy chủ
Rút `core_protection` ⇒ `POST /v1/events` trả 403 `consent_withdrawn` và không ghi gì. Thiếu `guardian_alerts` ⇒ vẫn nhận
sự kiện (an toàn người cao tuổi) nhưng không có tin Zalo nào tới người giám hộ. Trễ tối đa 60 giây (đệm) nếu đồng ý đổi từ
kênh khác ngoài `/v1/consents`.

### Đồng ý lúc gửi, độ trễ đệm và liên kết cũ (spec 037)
- **Điều kiện lúc GỬI** (FR-002): `send_to_guardian` (và trả lời "3" chi tiết trên Zalo, bản tin tuần, tổng kết diễn tập, hồ sơ
  vụ việc) kiểm `guardian_alerts` của người cao tuổi ngay lúc gửi, không dựa vào cờ lúc xếp job; không xác định được người cao
  tuổi ⇒ KHÔNG gửi. Tin demo/mô phỏng (hư cấu) được miễn.
- **Độ trễ đệm ≤ 60 giây**: trạng thái đồng ý được đệm 60 giây trong bộ nhớ máy chủ. Đổi qua `/v1/consents` thì đệm bị xóa ngay;
  đổi bằng kênh khác (ghi thẳng sổ, thao tác vận hành) có hiệu lực trong tối đa 60 giây. Chấp nhận được vì rút đồng ý không
  thu hồi tin đã gửi.
- **Liên kết cũ sau khi rút `guardian_alerts`** (chính sách D2, mặc định; Minh có thể đổi — MASTER-PLAN §8 mục 14): `GET
  /v1/action/{token}` và trang web đọc dữ liệu sự cố trả cùng 404 như liên kết không tồn tại (không lộ nhãn/mức/tóm tắt); quyết
  định (`POST …/decision`) VẪN được ghi và đóng sự cố vì đó là đường an toàn (dừng nhắc nhở) — hiện thân phản hồi vẫn có
  `state`/`outcome`. Rút đồng ý không chặn người giám hộ dừng một sự cố đang mở.
- **Đăng xuất phía máy chủ**: `DELETE /v1/guardian/session` ghi mã phiên (`jti`, không PII) vào `revoked_sessions` tới khi token hết
  hạn (≤ 7 ngày), nên bản sao cookie bị lấy cắp không còn dùng được; job `retention` xóa dòng quá hạn.

### Bảng dữ liệu ↔ mục đích ↔ hạn lưu (sinh từ model)
Nguồn duy nhất: `uv run --directory backend python -m hoicon.ops.privacy_report` (in từ `Base.metadata` + ánh xạ ở
`ops/privacy_report.py`; bảng mới mà chưa ánh xạ ⇒ thoát khác 0; có kiểm số điện thoại thô trong mã/fixture, văn bản đồng ý ↔ mã,
và đếm dòng nghi PII — chỉ đếm). Bản chụp 24/10/2026 (21 bảng, 0 bảng chưa ánh xạ, 0 dòng nghi PII):

| Bảng | Mục đích | Hạn lưu | Dữ liệu cá nhân |
|---|---|---|---|
| `action_tokens` | liên kết hành động dùng một lần | 30 ngày sau hết hạn | chỉ SHA-256 của token |
| `agent_runs`, `agent_steps` | trace tác tử (đã che) | nội dung 30 ngày; số đo giữ | đã che PII |
| `case_files` | hồ sơ vụ việc cho người giám hộ | theo sự cố | tóm tắt đã che, 3 số cuối, bí danh |
| `consents` | sổ đồng ý chỉ ghi thêm | không xóa (bằng chứng, NĐ 356/2025) | không |
| `data_requests` | vết yêu cầu xóa | giữ (vết pháp lý) | không |
| `device_heartbeats` | đo độ phủ bảo vệ | 90 ngày | không |
| `devices`, `members`, `families`, `trusted_contacts` | tài khoản gia đình | đến khi xóa gia đình (ẩn danh) | bí danh, HMAC Zalo, chat id mã hóa, HMAC + 3 số cuối |
| `drills` | diễn tập | 365 ngày | không (hư cấu) |
| `incidents`, `incident_transitions` | sự cố, nhật ký chuyển | 365 ngày sau đóng | không |
| `jobs` | hàng đợi (có toàn văn tin gửi) | 30 ngày | văn bản đã che |
| `messages_out` | đếm hạn mức Zalo | giữ dòng, không cột văn bản | id kênh |
| `pairing_codes` | mã ghép đôi | 15 phút / một lần | HMAC của mã |
| `revoked_sessions` | thu hồi phiên đăng xuất | tới khi token hết hạn (≤ 7 ngày) | mã phiên ngẫu nhiên |
| `risk_events` | sự kiện từ thiết bị | 90 ngày | HMAC + 3 số cuối |
| `threat_indicators` | danh sách lừa đảo | theo phiên bản | HMAC + 3 số cuối |
| `verifications` | kết quả tra cứu | 90 ngày | HMAC + 3 số cuối |
Thiết bị demo `sim:` của `/sim` bị dọn sau 24 giờ (không thuộc dữ liệu thật).

### Gỡ cờ một số điện thoại bị gắn nhầm
1. Người bị gắn nhầm (hoặc người giám hộ) báo cho đội; đội xác minh bằng chứng ngoài hệ thống.
2. Lấy `h1` của số đó (SHA-256 của `"hoicon:v1:" + E.164`) ở máy đội, ghi vào tệp tạm, mỗi dòng một h1 (không bao giờ ghi
   số thô vào tệp hay ticket).
3. `python -m hoicon.ops.threat_list unflag --h1-file <tệp> [--confirm]` — gỡ theo HMAC với mọi kid pepper, in số đã gỡ/không
   thấy, không in h1; một dòng sai định dạng ⇒ từ chối cả tệp. Xóa tệp tạm.
4. Máy giữ ảnh chụp danh sách cũ tới lần đồng bộ kế tiếp (bucket chỉ để lọc sơ bộ, kết luận cuối vẫn do máy chủ tra).

### Thu hồi thiết bị bị mất
`python -m hoicon.ops.devices revoke --device <id>`: token cũ bị từ chối ngay ở yêu cầu kế tiếp, không chờ hết hạn.

### Tách role CSDL
`infra/postgres/roles.sql`: role `hoicon_app` không sở hữu bảng, chỉ `SELECT`/`INSERT` trên `consents` và
`incident_transitions`, không tắt được trigger bất biến (kiểm bằng quyền, không chỉ bằng trigger). Áp dụng ở prod thuộc 012.

## Hồ sơ vụ việc (spec 031)
Khi người giám hộ chọn "nghi lừa đảo", HỏiCon soạn bản nháp hồ sơ để họ mang đi trình báo nếu muốn. Dữ liệu trong `case_files.content`
chỉ là dữ kiện máy chủ đã có: dòng thời gian, mức rủi ro, loại ứng dụng, **3 số cuối** của số gọi tới, câu trả lời E8, kết quả
tra cứu, bí danh gia đình (không tên thật). Không số điện thoại đầy đủ, h1, HMAC, tên gói hay lời kể tự do (có test quét). Các ô
**tự điền** (số điện thoại đã gọi tới, số tài khoản, số tiền, giờ chuyển, ngân hàng) nằm trên trình duyệt của người giám hộ,
không gửi về máy chủ, không lưu `localStorage` (ADR-006). Đoạn tóm tắt do LLM (nếu có khóa) đi qua `llm_router` (che PII) và bộ lọc
số/link/lời khuyên nguy hiểm. HỏiCon **không tự gửi** hồ sơ cho cơ quan nào. Giữ theo sự cố (12 tháng sau khi đóng), xóa khi xóa dữ liệu gia đình;
hồ sơ nháp bị bỏ sau 30 ngày không ai duyệt. Mục đích dữ liệu: `guardian_alerts` (văn bản đồng ý đã thêm câu về hồ sơ, bản `2026.10-v4`, chưa phát hành).

## Coach hằng tuần và báo "mất bảo vệ" (spec 032)
HỏiCon dùng **heartbeat** (độ phủ, cờ quyền) để (a) nhắn người giám hộ khi điện thoại của người cao tuổi im lặng hơn 24 giờ hoặc
quyền nhắc dừng lại bị tắt, và (b) gửi bản tin tuần (số lần nhắc dừng lại, độ phủ làm tròn 5%, số bài luyện tập). Mục đích dữ liệu:
`guardian_alerts` (văn bản đồng ý bản `2026.10-v4`, chưa phát hành, nói rõ "họ được báo nếu HỏiCon bị tắt" và "tóm tắt mỗi tuần").
Không số điện thoại, không tên thật trong tin; không LLM. Tin gửi tối đa một lần mỗi đợt/tuần, không gửi 21:00–07:00. Chỉ gia đình
thật, người cao tuổi còn đồng ý `guardian_alerts`; người giám hộ tắt được bản tin tuần bằng "TẮT TIN TUẦN" (tin cảnh báo mất bảo vệ
không tắt được vì là an toàn). Tin không bao giờ khẳng định "an toàn" (máy không được bảo vệ thì "không thấy gì" không có nghĩa
là không có gì).
