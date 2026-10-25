# Hướng dẫn cho Tiến — phần việc con người để hoàn thiện HỏiCon

Soạn 25/10/2026. Từ nay **Tiến làm một mình**: Minh chỉ là người nêu ý tưởng ban đầu. Mọi chỗ trong repo ghi "★ chờ Minh", "Minh duyệt",
"Minh quyết" nay là **Tiến quyết**. Phần máy làm được đã xong hết (`tien-collab-dev`, xem `.handover/LATEST.md`); tài liệu này chỉ còn
việc **cần người**: tài khoản, tiền, máy thật, người dùng thật, quyết định, quay phim, nộp bài.

Mốc cứng: **nộp Vòng 1 13/11/2026** (hạn 15/11) · Vòng 2 23/11–10/01/2027 (nộp 09/01, đóng băng code 06/01) · chung kết 18/01–21/02/2027.

---

## 0. Cách đọc và cách nhờ Claude

- Làm theo thứ tự §1 → §8. Mỗi bước có: **làm gì · ở đâu · xong thì gỡ chặn task nào · kiểm bằng gì**.
- Khóa/bí mật: **không bao giờ dán vào chat với Claude**, issue, PR. Mở `backend/.env` (dev) hoặc `infra/.env.prod` (VPS) bằng editor và dán
  trực tiếp. Claude bị chặn đọc các tệp này. Repo là **public**.
- Sau mỗi bước xong, mở Claude Code ở checkout chính và gõ một câu, ví dụ:
  - `Đã có token bot Zalo trong backend/.env — chạy 002 T024 và ghi evidence.`
  - `Đã có khóa Anthropic — ghi cassette recorded cho eval (036) và đo số M3.`
  - `Đã có VPS + tên miền <tên> — làm 012 T010–T014 theo docs/setup/VPS-DEPLOYMENT.md.`
  Claude sẽ tự làm phần máy và chỉ hỏi lại khi cần bạn bấm/ký/trả tiền.
- Ghi quyết định: sửa đúng mục trong `docs/MASTER-PLAN.md` §8, thêm dòng "**Tiến chốt dd/mm: …**" (hoặc nhờ Claude ghi).

---

## 1. Việc gấp nhất tuần này (25/10–01/11)

### 1.1 Hỏi BTC về đội 1 người (5 phút, làm ngay)
Thể lệ (`docs/competition/The_le_Tech_Startup_Challenger_2027.pdf` tr.1): "nhóm **không quá 05** sinh viên, **trên 20%** là sinh viên Khoa CNTT"
— không ghi số tối thiểu. Gửi email BTC xác nhận **đội 1 người được không**. Nếu cần ≥ 2 người: rủ thêm 1 bạn (marketing/tài chính) trước 08/11
và ghi tên vào thuyết minh. Thuyết minh hiện ghi **5 người** — phải sửa (§2).

### 1.2 Tài khoản — theo đúng thứ tự (chi tiết từng bước: `docs/setup/ACCOUNTS.md`)

| # | Việc | Chi phí / chờ | Đặt khóa ở đâu | Gỡ chặn |
|---|---|---|---|---|
| 1 | ~~Google Play Console~~ — **hoãn** (Tiến chốt 25/10: giai đoạn thử chỉ phát **APK tải trực tiếp**, §6). Chỉ đăng ký khi cần link cửa hàng | 25 USD | — | (sau thí điểm) |
| 2 | **Firebase** (Spark, miễn phí) + `gcloud` | 0 | `google-services.json` ngoài git (`apps/android/app/`, đã gitignore) | 001 T007–T010 (đo máy thật FTL), FCM cho E8 |
| 3 | **Anthropic API** — đặt **trần chi tiêu** 10–20 USD | trả trước | `backend/.env` → `HOICON_ANTHROPIC_API_KEY` | 036 cassette `recorded` (số M3 thật), P1-S4 so mô hình, 011 T020 |
| 4 | **Zalo Bot Platform** — bot `hoicon-dev` | 0 (3 bot × 50 người × 3.000 tin/tháng) | `backend/.env` → `HOICON_ZALO_BOT_TOKEN` (xóa tin chứa token trong Zalo sau khi chép) | 002 T024/T025 (đo giao tin thật), 012 T011 |
| 5 | **GitHub Student Pack** → tên miền + VPS | 0–vài trăm nghìn/tháng | `infra/.env.prod` trên VPS | 012 T010–T014, P1-09 |
| 6 | Gemini API (tùy chọn) | free tier, chỉ dữ liệu giả | `backend/.env` | P1-S4/S5 so sánh |

Kiểm sau mỗi khóa: `uv run --directory backend uvicorn hoicon.api.main:app --port 18000 --loop asyncio:SelectorEventLoop` rồi mở
`http://localhost:18000/readyz` — thiếu khóa thì trả 503 và nêu **tên** biến (không in giá trị).

**VPS:** chọn máy chủ **đặt tại Việt Nam** (thuyết minh đã cam kết lưu dữ liệu định danh trong nước). Tối thiểu 2 vCPU / 4 GB RAM.

### 1.3 Máy Android thật (ngân sách nhỏ)
Mua máy cũ 1–2 triệu (Samsung dòng A hoặc Xiaomi, Android 13–15) **trước 06/12**, hoặc dùng Firebase Test Lab (sau bước 2). Máy ảo ≠ máy thật:
mọi số hiện có là số máy ảo. Gỡ chặn: 001 T007–T010, 029 T012, 032 T014 (heartbeat theo hãng).

---

## 2. Hồ sơ Vòng 1 (hạn nộp 13/11)

Đọc trước: `docs/proposal/PITCH-SYNC-2026-10-25.md` (15 cam kết, đề xuất sửa **A–J**), `docs/proposal/JUDGE-PRECHECK-2026-10-25.md`
(≈ 74/110, 5 điểm yếu, 10 câu phản biện), `docs/proposal/VIDEO-V1-SCRIPT.md`.

### 2.1 Chốt quyết định cho thuyết minh (30 phút)
- **B4 thí điểm**: đề xuất **20–30 gia đình** (khớp gate M3 ≥ 20, G3 ≥ 30), không phải 50–100.
- **B5 đội ngũ**: đội thật (1 người hoặc 2 nếu rủ thêm) + đội tác tử AI lập trình; "sinh viên" là mở rộng sau MVP.
- Duyệt đề xuất **G** (viết lại Bảng 9 "agentic" cho đúng), **H** (bỏ tính năng không có: "Hỏi con" gửi Zalo, hỏi bằng giọng nói, Langfuse,
  gọi lại người thân, MCP `zalo`), **I** (thống nhất 6.000/6.900 đồng; "mục tiêu ≥ 90%"), **J** (số khảo sát thật).

### 2.2 Sửa Word + xuất PDF (cần **Windows + Microsoft Word**)
Bản `docs/proposal/HoiCon_Ban_mo_ta_y_tuong_TSC2027.docx` đã được sửa tay ⇒ **sửa thẳng trong Word**, đừng chạy lại pipeline `src/` (sẽ mất
sửa tay — `docs/proposal/src/README.md`). Điền `[Điền tên đội]`, `[Họ và tên]`, bỏ cố vấn chưa nhận lời. Xuất PDF; kiểm Times New Roman 14, A4,
mục lục, không trang trắng. Chép bản mới đè vào `docs/proposal/` rồi nhờ Claude chạy lại `pitch-sync` để kiểm "sạch".

### 2.3 Khảo sát (P1-02) — chạy song song từ hôm nay
Bảng hỏi có sẵn: `docs/research/survey/P1-02-bang-hoi.md`. Dựng Google Form, phát qua nhóm lớp/Facebook/Zalo. Mục tiêu ≥ 300 phản hồi,
**chốt số 06/11**; chưa đủ thì ghi đúng n vào thuyết minh (đề xuất J). Xuất CSV (bỏ tên/số điện thoại) ⇒ nhờ Claude lập báo cáo số liệu.

### 2.4 Video 3 phút (P1-03) — quay 05–08/11
Theo `docs/proposal/VIDEO-V1-SCRIPT.md` (đã đối chiếu sản phẩm thật, có mục "không được nói"). Chuẩn bị máy ảo + web như mục "Chuẩn bị".
Xem máy ảo trong Orca: `~/.config/environment.d/android-sdk.conf` đã tạo ⇒ **cài `scrcpy`** (`sudo pacman -S scrcpy`), **đăng xuất/đăng nhập**,
mở bảng Mobile Emulator ⇒ chọn hc-api36 ⇒ Connect. Thu giọng đọc ~125 từ/phút; dựng bằng skill `video-use` nếu muốn; kiểm ≤ 3:00.

### 2.5 Chấm thử và nộp
10/11: nhờ Claude "chạy judge chấm Vòng 1 với bản PDF mới" ⇒ sửa theo góp ý ⇒ **nộp 13/11** theo email hướng dẫn của BTC
(thuyết minh + video ≤ 3 phút + hình ảnh nếu có). Lưu biên nhận nộp, cập nhật ROADMAP P1-04 ☑.

---

## 3. Quyết định treo — Tiến chốt (đề xuất có sẵn trong `docs/MASTER-PLAN.md` §8)

| Mục §8 | Nội dung | Đề xuất của kiến trúc sư | Chốt xong thì |
|---|---|---|---|
| 1, 5 | I1–I5; I4 "mất bảo vệ" trong 032 | Giữ I4 (đã code, cờ `HOICON_PROTECTION_WATCH`) | Không cần làm gì thêm; bác thì 032 T010 |
| 2 | B1, B2, B8 | Bỏ T2 khỏi danh sách cắt; **cắt P1-S6** | Sửa ROADMAP |
| 3 | B4 (thí điểm), B6 (chấm eval) | 20–30 gia đình; eval chấm tất định là chính | Sửa thuyết minh §2.1 |
| 4 | Phạm vi `guardian_alerts` | Giữ một mục đích gồm cảnh báo + tin Coach | Không đổi mã |
| 6, 11 | Duyệt 110 kịch bản eval + kiểm URL nguồn | Mở từng `source_ref`, đổi `draft` ⇒ `approved` (có thể nhờ Claude soạn danh sách URL để bạn bấm kiểm) | Số eval được dùng trong hồ sơ |
| 7 | Trần tra cứu 30 ngày | Giữ 600 / 600 / 3.000 | Ghi "Tiến chốt" |
| 8 | **F-1** báo nhầm chuyển tiền chính đáng | **Chọn A** (hỏi thêm một câu "bác có biết rõ người gọi không") — nếu không, Gate M3 trượt khi có mô hình thật | Claude làm 024 T016–T017 |
| 9 | ADR-012 | Chấp nhận (đã thi công) | Sửa trạng thái ADR thành "Chấp nhận" |
| 12, 16 | Chữ màn đồng ý E3/E4/E10 | Theo đề xuất reviewer | Văn bản lên phiên bản mới; Claude làm 011 T012 |
| 13 | Crashlytics | **Chưa dùng**; đo bằng Android vitals | Không làm gì |
| 14 | Link Zalo cũ sau khi rút đồng ý | Giữ D2 (vẫn ghi quyết định, trả thân tối thiểu) | Không làm gì |
| 15 | Đồng ý của người giám hộ | **Có** — một câu đồng ý trong tin chào của bot | Claude viết spec nhỏ + làm (trước thí điểm) |
| 17 | Xóa khi nhà ≥ 2 người được bảo vệ | Hoãn (thí điểm 1 người/nhà) | Không làm gì |
| — | Văn bản đồng ý 011 T010, `report_guidance` 031 T018, `tips` Coach 032 T015, tài liệu thí điểm 029 T009 | Đọc, sửa chữ, đổi `approved: true`/`released` | Gỡ chặn thí điểm |

Mẹo: gõ cho Claude "Tiến chốt §8 theo đề xuất, trừ mục X" — Claude sẽ ghi và chạy các task phát sinh.

---

## 4. Git: đưa code lên `main`

Từ nay không có người duyệt thứ hai ⇒ **tự duyệt**:
1. `git push origin tien-collab-dev`.
2. `gh pr create --base main --head tien-collab-dev` (nhờ Claude soạn mô tả PR từ `.handover/LATEST.md`).
3. Chờ CI xanh (CI chỉ chạy trên PR/push `main`), đọc lướt diff các phần nhạy cảm (đồng ý, PII, manifest Android), rồi **squash merge**.
4. Sau squash: đặt lại `tien-collab-dev` theo `main` (MASTER-PLAN §5 luật 9 — nhờ Claude làm).
5. Nên sửa `CLAUDE.md` mục "Quy trình làm việc" (đang ghi "người còn lại duyệt", "Minh quyết phạm vi") cho đúng thực tế một người — tự sửa hoặc
   bảo Claude: "cho phép sửa CLAUDE.md: Tiến làm một mình, Tiến quyết phạm vi".

---

## 5. Hạ tầng thật (sau khi có VPS + tên miền — trước 22/11)

Làm theo `docs/setup/VPS-DEPLOYMENT.md` từ §1 tới §8 (hoặc nhờ Claude dẫn từng lệnh qua SSH — bạn tự gõ phần nhập mật khẩu):
1. Chuẩn bị VPS (§1), tạo `infra/.env.prod` trên VPS (§2) — **không commit**; thêm `HOICON_BOOTH_CODE_KEY` (≥ 32 ký tự, khác khóa JWT).
2. Triển khai `compose.prod.yml` + Caddy (§3); áp migration **tới 0015**; chạy `infra/postgres/roles.sql` (role `hoicon_app` không sở hữu bảng).
3. Kiểm `https://<tên-miền>/healthz` 200, `/readyz` 200 (§4).
4. Đặt webhook Zalo (§5) ⇒ gửi một tin thử đầu–cuối (012 T011).
5. Bật `hoicon-backup.timer` + chép bản sao lưu ra ngoài máy (§8, `docs/setup/BACKUP.md`); thử khôi phục một lần.
6. Giám sát ngoài: một dịch vụ ping `/readyz` mỗi phút báo về điện thoại (012 T014; UptimeRobot miễn phí là đủ).
Xong ⇒ báo Claude để tick 012 T010–T014 và ghi evidence.

---

## 6. Phát APK cho người thử (Tiến chốt 25/10 — chưa dùng Play)

Giai đoạn thử, chưa công khai ⇒ **APK tải trực tiếp** (0 đồng). Firebase App Distribution là phương án nâng cấp khi đông người thử (email mời,
báo bản mới) — vẫn là APK, chỉ tiện quản lý.
1. Tạo keystore phát hành **ngoài repo** (ví dụ `~/secrets/hoicon-release.jks`), sao lưu 2 nơi. **Mọi bản cập nhật phải ký cùng khóa** — mất khóa
   ⇒ người dùng phải gỡ app và ghép đôi lại. Không phát bản debug. Biến môi trường ký: `specs/012-release-and-hosting`.
2. `apps/android/gradlew -p apps/android :app:assembleRelease` (R8 + baseline profile); `scripts/release-gate.sh` phải ĐẠT.
3. Tải APK lên **GitHub Releases** (bản pre-release) hoặc Google Drive; ghi số phiên bản + ngày.
4. **Cài thử trên một máy Android thật** (13 trở lên): kiểm cảnh báo Play Protect, "cài đặt bị hạn chế" khi cấp quyền sàng lọc cuộc gọi / dữ liệu
   sử dụng / hiển thị trên ứng dụng khác; ghi kết quả vào evidence 029 (nhờ Claude).
5. **Độ ổn định**: không có Play ⇒ không có Android vitals ⇒ tiêu chí "crash-free ≥ 99%" của M2 cần nguồn khác — chốt ở MASTER-PLAN §8 mục 18.

---

## 7. Thí điểm với gia đình thật (M2 20/12 → M3 09/01 → G3 14/02)

Quy định cứng: chỉ người **≥ 18 tuổi**, có đồng ý bằng văn bản trong app; dữ liệu thật không bao giờ đưa vào demo/eval.
1. Hoàn thiện `docs/setup/PILOT-ONBOARDING.md`, `PILOT-SUPPORT.md` (điền ô `[CHỜ MINH ĐIỀN]`: số hỗ trợ, người phụ trách = Tiến, Google Group).
2. Tuyển từ danh sách người khảo sát đồng ý tham gia; mục tiêu **≥ 5 gia đình trước M2**, ≥ 20 trước M3, ≥ 30 trước G3.
3. **Cài APK tại chỗ** (bật "cài ứng dụng không rõ nguồn gốc" giúp bác, bỏ qua cảnh báo Play Protect, tắt lại sau khi cài), ghép đôi, bật người giám hộ trên Zalo.
4. Ghi danh: `uv run --directory backend python -m hoicon.ops.pilot enroll --family <id> --confirm-adult` (029 T013). Sau 7 ngày: `ops pilot report`.
5. Mỗi tuần: hỏi người giám hộ về tin "mất bảo vệ" có phải báo nhầm không (032 T014); một người giám hộ duyệt + in thử hồ sơ của một sự cố
   **demo** (031 T017); người cao tuổi đọc thử màn đồng ý và ghi chỗ khó hiểu (011 T011).
6. Báo Claude để chạy `phase-gate` M2/M3 và lập báo cáo thí điểm.

---

## 8. Vòng 2 và chung kết (sản phẩm đã gần đủ — việc người là chính)

| Hạn | Việc của Tiến | Claude làm được khi bạn yêu cầu |
|---|---|---|
| 22/11 | VPS + bot Zalo thật chạy | Triển khai, đo giao tin p95 (002 T024) |
| 06/12 (M1) | Một sự cố đầu–cuối trên máy thật: cuộc gọi lạ → app ngân hàng → dừng an toàn → Zalo tới điện thoại bạn | Kịch bản, đo, báo cáo gate |
| 20/12 (M2) | ≥ 5 gia đình cài APK | `phase-gate M2`, báo cáo độ ổn định (Android vitals, `docs/setup/STABILITY.md`) |
| 06/01 | Đóng băng code | Rà soát cuối, `pitch-sync` |
| 09/01 (M3) | Nộp: tài liệu Vòng 1 hoàn thiện + **poster** (mẫu BTC) + MVP + **video 5 phút** | Số eval với mô hình thật (cần khóa API), kịch bản video 5' (`demo-video-director`), nội dung poster |
| 18/01–21/02 | Slide pitching 10 phút; tập trả lời 10 câu phản biện (`JUDGE-PRECHECK`) | Slide, `judge` chấm thử, chế độ gian `/booth` cho buổi trưng bày |

---

## 9. Bảng đánh dấu nhanh (in ra dán bàn)

- [ ] Email BTC hỏi đội 1 người
- [ ] Tạo keystore release, cất 2 nơi
- [ ] Firebase + `gcloud`
- [ ] Khóa Anthropic có trần chi tiêu
- [ ] Bot Zalo `hoicon-dev`
- [ ] GitHub Student Pack → tên miền + VPS tại VN
- [ ] Chốt §8 (gõ "Tiến chốt §8 theo đề xuất…")
- [ ] Sửa thuyết minh trong Word (A–J), điền tên, xuất PDF
- [ ] Khảo sát ≥ 300 (chốt số 06/11)
- [ ] Cài `scrcpy`, đăng xuất/đăng nhập để Orca thấy máy ảo
- [ ] Quay video 3' (05–08/11)
- [ ] `judge` chấm 10/11 → **nộp 13/11**
- [ ] Push + PR + squash merge vào `main`
- [ ] Triển khai VPS, webhook Zalo, sao lưu, giám sát
- [ ] Máy Android thật / FTL
- [ ] APK release ký đúng khóa lên GitHub Releases/Drive; cài thử trên máy thật (kiểm "cài đặt bị hạn chế")
- [ ] Tuyển ≥ 5 → 20 → 30 gia đình thí điểm
- [ ] Poster + video 5' + nộp Vòng 2 (09/01)
- [ ] Slide chung kết
