# Spec 029: Bộ thí điểm & Play internal v0.3 (Gate M2)

**Mã ROADMAP**: `P2-14` · **Làn**: A + B + H · **Cột mốc**: **Gate M2 (20/12)**: ≥ 5 gia đình, ≥ 1 máy thật,
heartbeat ≥ 90%, crash-free ≥ 99% · **Phụ thuộc (MASTER-PLAN)**: `012`, `020`, `022`, `034`
· **Nhánh**: `feat/029-pilot-kit-server`, `feat/029-pilot-kit-android` · **ADR**: ADR-005 (phát hành qua Play testing)
· **Hiến chương**: IX (chặn phát hành) + checklist `release-block`

---

## 1. Bối cảnh & điều kiện tiên quyết

029 là spec **cuối** của Đợt 4 và là spec đầu tiên đưa app tới người thật. Hiện trạng đã đọc ngày 16/10/2026:

| Điều kiện | Trạng thái | Hệ quả |
|---|---|---|
| `012-release-and-hosting` (P1-08, P1-09, P2-04): buildType release/demo + R8 + tắt log chẩn đoán, Play internal, VPS + Caddy | **Chưa có spec** (P1-08, P1-09, P2-04 đều ☐); `app/build.gradle.kts` bản release **chưa bật** `isMinifyEnabled` | Không phát hành được. Hiến chương IX chặn |
| W0-3 / P0-08: Play Console + Firebase | ⏸ (Minh đang đăng ký; Play Console cá nhân cần máy thật để xác minh) | Không có kênh internal testing, không có Crashlytics, không có FTL |
| `034-hardening-core` | Đã có spec (16/10), chưa thi công | `release-block` đòi `privacy-audit` sạch + 0 High |
| `011-consent-legal` (P1-06: văn bản đồng ý v1, DPIA, PILOT-PROTOCOL) | **Chưa có spec** (☐); `PILOT-PROTOCOL.md` vẫn là "khung" | Thí điểm cần quy trình đã chốt và Minh duyệt |
| Heartbeat | Android gửi `POST /v1/heartbeat` mỗi 15 phút (022), **máy chủ không có route này**; `devices.last_heartbeat_at` chỉ được ghi lúc ghép đôi | Chỉ số "heartbeat ≥ 90%" của Gate M2 **hiện không đo được** |
| Crash-free | Chưa có Crashlytics (037, cần Firebase) | Nguồn duy nhất trước 037 là Android vitals trong Play Console. Với 5 gia đình, con số chỉ mang tính chỉ báo |
| Máy thật | Chưa có (mua/mượn máy là quyết định của Minh) | "≥ 1 máy thật" là điều kiện ngoài code |

**Kết luận phạm vi.** 029 tách thành hai phần:
- **Giai đoạn 1 (làm được ngay):** heartbeat ở máy chủ, báo cáo sức khỏe thí điểm, kịch bản kiểm `release-block` tự động
  và bộ tài liệu thí điểm. Không cần 012 hay tài khoản.
- **Giai đoạn 2 (chỉ bắt đầu khi 012 + 034 merge và W0-3 xong):** bản v0.3 lên internal testing, cài cho gia đình thật,
  đo Gate M2.

Bản giao việc nêu "baseline profile, khởi động nguội ≤ 1,5 s" và "R8 bảo vệ API keys": cả hai không thuộc 029. Baseline
profile và đo khởi động nguội (hạn 5 s của Telecom) là AC của **012**. App không chứa khóa API nào cần bảo vệ (khóa LLM
và Zalo chỉ nằm ở máy chủ).

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-14.1 | **P1** | Là đội thí điểm, tôi biết máy nào của gia đình nào đang được bảo vệ (heartbeat gần đây, quyền còn bật) mà không cần hỏi từng nhà |
| US-14.2 | **P1** | Là đội thí điểm, trước mỗi lần phát hành tôi chạy một lệnh và biết chắc bản build đạt `release-block` |
| US-14.3 | **P1** | Là con, tôi được hướng dẫn cài cho bố mẹ qua cuộc gọi video trong khoảng 5 phút, có hướng dẫn riêng cho Samsung/Xiaomi/Oppo |
| US-14.4 | **P2** | Là đội thí điểm, tôi có báo cáo Gate M2 (≥ 5 gia đình, ≥ 1 máy thật, heartbeat, crash-free) sinh từ dữ liệu, không điền tay |

## 3. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Heartbeat ở máy chủ | `POST /v1/heartbeat` khớp hợp đồng Android đang gửi (022); cập nhật `last_heartbeat_at` + `permission_state`; trước đồng ý / thiết bị bị thu hồi / sai gia đình ⇒ từ chối; hạn mức 8 lần/giờ/thiết bị; 0 dữ liệu ngoài hợp đồng được lưu | pytest + chạy trên AVD API 36 (log 200 thay vì 404) |
| **(SC-002)** | Báo cáo sức khỏe | `ops pilot report --days N` tính đúng độ phủ heartbeat (số khung 15 phút có heartbeat ÷ số khung kỳ vọng) theo từng thiết bị, quyền bị tắt, số sự cố/báo nhầm; không chứa PII (chỉ id rút gọn + bí danh gia đình); khớp `pilot_report.v1` | pytest với dữ liệu dựng sẵn (độ phủ 100%, 50%, 0%) |
| **(SC-003)** | `release-block` tự động | `scripts/release-gate.sh <aab|apk>` kiểm và in ĐẠT/TRƯỢT cho từng mục. TRƯỢT nếu: có quyền cấm trong manifest đã gộp; R8 tắt; chuỗi log chẩn đoán (`HC_TIMING`, `HC_SPIKE`) còn trong dex; còn `usesCleartextTraffic`/`networkSecurityConfig` cho phép cleartext; thiếu câu công khai AI trong tài nguyên; `ConsentLedger.VERSION` không khớp hash đã ghim. Thử trên bản debug ⇒ TRƯỢT đúng mục | chạy script trên APK debug hiện có (phải TRƯỢT) và trên bản release của 012 (phải ĐẠT) |
| **(SC-004)** | Bộ tài liệu thí điểm | `PILOT-ONBOARDING.md` (≤ 5 phút qua video call, có ảnh E1–E4 và bước theo hãng), `PILOT-SUPPORT.md` (sổ tay xử lý: mất bảo vệ, báo nhầm, gỡ app, yêu cầu xóa dữ liệu qua 034), kiểm tuổi ≥ 18 trong quy trình ghi danh; `ux-elder-reviewer` và Minh duyệt câu chữ | review |
| **(SC-005)** | Gate M2 trên người thật | ≥ 5 gia đình ghi danh `plan=pilot`, ≥ 1 máy thật, độ phủ heartbeat ≥ 90% trong 7 ngày, crash-free ≥ 99% (Play vitals; ghi rõ nguồn và cỡ mẫu), không còn finding High (034) | `ops pilot gate-m2` + ảnh Play Console. **BLOCKED** tới khi 012, 034, W0-3 xong |
| **(SC-006)** | Hồi quy | Không đổi hành vi đường dừng an toàn; pytest, Gradle, eval smoke xanh | CI |

## 4. Yêu cầu chức năng

**Giai đoạn 1: làm được ngay**

- **(FR-001)** Hợp đồng `docs/schemas/heartbeat.v1.json`, viết **từ những gì Android đang gửi**
  (`PairingApiClient.sendHeartbeat`: `app_version`, `rules_version`, `permission_state` là map tên quyền → bool, và
  tùy chọn `threat_list_version`). Fixture valid lấy từ chính thân Android dựng (test Android ghim cùng fixture). Không
  thêm trường mới (mọi trường mới là dữ liệu mới và phải sửa văn bản đồng ý).
  - Android hiện ánh xạ **mọi** 403 thành `Unauthorized` (hiện "Kết nối lại"). Làn A phải phân biệt 403 có mã
    `consent_withdrawn` (của 034) thành trạng thái "cần đồng ý lại", cho cả `sendHeartbeat` lẫn `sendEvents`.
- **(FR-002)** `POST /v1/heartbeat` (JWT thiết bị):
  - cập nhật `devices.last_heartbeat_at`, `permission_state`, `app_version`, `rules_version`;
  - ghi một dòng `device_heartbeats(device_id, at, protected)` (tối đa 1 dòng mỗi khung 15 phút, `ON CONFLICT DO NOTHING`
    theo `(device_id, khung)`) để tính độ phủ;
  - `protected` = các quyền lõi đều bật;
  - kiểm đồng ý `core_protection` (dùng hàm của 034 nếu đã merge, không thì kiểm trực tiếp);
  - hạn mức 8 lần/giờ/thiết bị;
  - `device_heartbeats` giữ 90 ngày (đăng ký với job hạn lưu của 034).
- **(FR-003)** Migration (số kế tiếp sau head): bảng `device_heartbeats` (`device_id` FK `CASCADE`, `slot` timestamptz đã
  làm tròn 15 phút, `protected` bool, PK `(device_id, slot)`). `families.plan` dùng giá trị `pilot` (cột đã có, không cần
  CHECK mới); test bảo đảm không có giá trị lạ.
- **(FR-004)** `ops pilot`:
  - `enroll --family <id> --confirm-adult` (đặt `plan=pilot`; bắt buộc cờ xác nhận người cao tuổi ≥ 18 tuổi theo luật 8;
    không lưu ngày sinh);
  - `report --days N [--json]` theo `docs/schemas/pilot_report.v1.json`;
  - `gate-m2 --days 7 --crash-free <số từ Play vitals> --real-devices <số>` in ĐẠT/TRƯỢT từng chỉ tiêu, ghi rõ chỉ tiêu
    nào do người nhập tay.

  Không in PII: thiết bị hiện 8 ký tự đầu của id, gia đình hiện bí danh.
- **(FR-005)** `scripts/release-gate.sh <tệp>`:
  - giải nén AAB/APK, đọc manifest đã gộp bằng `aapt2 dump xmltree` từ SDK;
  - kiểm danh sách quyền cấm của CLAUDE.md luật 3 + ADR-007;
  - phát hiện R8 tắt (thiếu `mapping`/tên lớp chưa rút gọn);
  - grep dex tìm `HC_TIMING`/`HC_SPIKE`;
  - kiểm cleartext;
  - kiểm `strings.xml` có "Đây là trợ lý AI HỏiCon";
  - chạy test ghim hash `ConsentTextsPinTest`.

  Mỗi mục ra ĐẠT/TRƯỢT; script thoát ≠ 0 nếu có TRƯỢT. Mục không tự động được (≥ 18 tuổi, `privacy-audit`) in "KIỂM TAY".
- **(FR-006)** Tài liệu thí điểm (làn H, Tiến soạn, Minh duyệt):
  - `docs/setup/PILOT-ONBOARDING.md`: kịch bản video call 5 phút; ảnh E1–E4 lấy từ `~/hoicon-evidence/020…`; bước bật
    quyền và "không giới hạn pin" theo Samsung One UI / Xiaomi HyperOS / Oppo ColorOS; cách kiểm "Đang bảo vệ" trên E6;
    cách tham gia Google Group tester.
  - `docs/setup/PILOT-SUPPORT.md`: mất bảo vệ (heartbeat dừng, quyền tắt), báo nhầm, gỡ cài đặt, yêu cầu xóa dữ liệu
    (`ops data request-delete` của 034), liên hệ khẩn.
  - Hoàn thiện phần thí điểm của `docs/PILOT-PROTOCOL.md` nếu 011 chưa làm (ghi rõ phần nào chờ 011).

**Giai đoạn 2: chỉ khi 012 + 034 merge và W0-3 xong**

- **(FR-007)** Bản v0.3:
  - `versionName 0.3.0`, `versionCode` tăng;
  - build bằng buildType release/demo của 012;
  - chạy `release-gate.sh` ĐẠT;
  - tải lên kênh internal testing (thao tác trên Play Console do Tiến/Minh làm; Claude chỉ chuẩn bị AAB và ghi chú phát
    hành tiếng Việt).

  Không bao giờ gửi APK cho người dùng (hiến chương IX).
- **(FR-008)** Kiểm trên máy thật:
  - ≥ 1 máy thật (mượn/mua, hoặc FTL nếu có Firebase): chạy kịch bản `fake_police` hoặc tương đương, đo SafePause, ghép
    đôi thật, heartbeat lên VPS;
  - ghi model + phiên bản Android vào `evidence.md` (thông tin máy của đội, không phải của gia đình thí điểm).
- **(FR-009)** Vận hành Gate M2:
  - ghi danh ≥ 5 gia đình theo `PILOT-ONBOARDING`;
  - sau 7 ngày chạy `ops pilot gate-m2`, đính kèm ảnh Android vitals (crash-free, cỡ mẫu), kết quả 034 (0 High);
  - đánh ROADMAP `P2-14` ☑ chỉ khi đủ mọi chỉ tiêu; thiếu thì ghi rõ chỉ tiêu nào không đạt và phương án.
- **(FR-010)** Kiểm chứng & tài liệu: pytest, test hợp đồng dùng chung fixture với Android, Gradle; cập nhật
  `docs/API.md`, `docs/DATA-MODEL.md`, `docs/PLAY-POLICY.md` (Data safety theo dữ liệu heartbeat thật); `evidence.md` có
  số và nguồn.

## 5. Bất biến & ranh giới

1. **Hiến chương IX:** không bản build nào tới người thật khi `release-block` chưa ĐẠT. `release-gate.sh` là bằng chứng.
2. **Luật 8:** thí điểm chỉ người ≥ 18 tuổi; dữ liệu demo `is_demo` không trộn với gia đình thí điểm.
3. **ADR-006 / tối thiểu hóa:** heartbeat chỉ chứa trường Android đang gửi theo văn bản đồng ý hiện hành; báo cáo không
   có PII.
4. Thao tác trên Play Console và với gia đình thật do người làm (Tiến/Minh); Claude chuẩn bị bản build, tài liệu, lệnh và
   số liệu.
5. Không đổi đường dừng an toàn hay luật trên máy.

## 6. Ngoài phạm vi

Crashlytics (037) · baseline profile, R8, VPS, Caddy (012) · dashboard web cho thí điểm (danh sách cắt; báo cáo dòng
lệnh là đủ) · báo "mất bảo vệ" tới người giám hộ (I4, 032).
