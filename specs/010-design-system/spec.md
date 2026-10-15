# Feature Specification: Design system v1 — một `tokens.json` sinh theme Compose + CSS, tương phản ≥ 7:1 có test

**Feature Branch**: `feat/010-design-system`

**Created**: 2026-10-15

**Status**: Ready — quyết định kỹ thuật DS1–DS6 (plan.md) do Opus soạn theo ủy quyền của Tiến (kỹ sư chủ trì, 15/10/2026);
áp dụng mặc định khi giao implement, chạy tự hành một mạch (MASTER-PLAN §2.6)

**Input**: Tiến giao 15/10/2026: "soạn Spec + Plan cho Đợt 3 (Làn A: P1-05 Design System …) theo chế độ tự hành một mạch".

## Truy vết *(mandatory)*

- **Mã ROADMAP**: P1-05 (design system: `docs/DESIGN-SYSTEM.md` + `design-system/hoicon/tokens.json`, Be Vietnam Pro)
- **User story PRD**: nền cho mọi màn E1–E12 (US-01…US-08) và trang web người giám hộ (US-03, US-10) — spec này không
  thêm màn hình mới
- **ADR liên quan**: không đổi quyết định nào ⇒ không cần ADR. Ràng buộc: CLAUDE.md luật 15 (UX người cao tuổi), luật 4
  (đường dừng an toàn offline ⇒ font phải nằm trong APK)
- **Gate nghiệm thu**: chuẩn bị MVP (MASTER-PLAN §3 Đợt 2); điều kiện trước 020/022 (màn E1–E4, E6–E7 dùng token)
- **Phụ thuộc spec**: không. 001/004 (đã tích hợp) là nguồn ảnh "trước"
- **Làn**: A — `apps/android/**`, `design-system/**`, `scripts/gen-design-tokens.py`, `scripts/tests/test_design_tokens.py`,
  `docs/DESIGN-SYSTEM.md`. **Ngoại lệ sở hữu (Tiến chốt khi giao):** spec này được sửa `apps/web/src/app/globals.css`,
  `apps/web/src/app/tokens.css` (mới) và `.github/workflows/{android,harness,web}.yml`; làn B (spec 003) không đụng
  `apps/web/**` trong đợt này

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đổi một màu ở một chỗ, hai nền tảng cùng đổi, test chặn màu không đủ tương phản (Priority: P1)

Kỹ sư sửa `design-system/hoicon/tokens.json`, chạy `python3 scripts/gen-design-tokens.py`. Theme Compose và CSS của web
cùng cập nhật. Nếu cặp chữ/nền nào dưới 7:1 thì test đỏ, chỉ rõ cặp nào và tỷ lệ bao nhiêu. Quên chạy generator thì CI đỏ.

**Why this priority**: ROADMAP P1-05 và DESIGN-SYSTEM.md đều cam kết "một tokens.json dùng chung". Hiện màu được chép tay ở
3 nơi (`Color.kt`, `colors.xml`, `globals.css`), và 2 token chữ đang dưới 7:1 (`brand.orange.text` 5,47:1, `brand.green`
5,23:1 trên nền trắng — đo bằng công thức WCAG 2.x, 15/10/2026).

**Independent Test**: `python3 -m unittest discover -s scripts/tests` + `python3 scripts/gen-design-tokens.py --check`.

**Acceptance Scenarios**:

1. **Given** tokens.json hợp lệ, **When** chạy generator, **Then** `Tokens.kt`, khối màu trong `colors.xml` và `tokens.css`
   được ghi lại; chạy lần hai không đổi byte nào (tất định).
2. **Given** một cặp chữ/nền khai báo trong tokens.json có tỷ lệ < 7,0, **When** chạy unittest, **Then** test đỏ và in tên
   cặp + tỷ lệ.
3. **Given** tokens.json đã sửa nhưng chưa chạy generator, **When** CI chạy `--check`, **Then** exit 1 và in tệp lệch.
4. **Given** token cỡ chữ thân < 20sp, nhãn nút chính < 24sp hoặc vùng chạm < 64dp, **When** chạy generator, **Then** từ
   chối (exit 2) và nói rõ luật 15 bị vi phạm.

---

### User Story 2 - Màn hình app dùng font Be Vietnam Pro và token, kể cả khi offline (Priority: P1)

Người cao tuổi mở app hoặc gặp màn dừng an toàn (E7): chữ dùng Be Vietnam Pro (dấu tiếng Việt rõ), màu lấy từ token. Font
nằm sẵn trong APK nên không cần mạng; cỡ chữ hệ thống 200% không cắt chữ.

**Why this priority**: font là cam kết thương hiệu của DESIGN-SYSTEM.md; tải font qua mạng sẽ phá luật 4 (đường dừng an toàn
offline).

**Independent Test**: `:app:assembleDebug` + ảnh chụp E7 và màn quyền ở cỡ chữ 100% và 200% trên AVD `hc-api36` và `hc-api34`.

**Acceptance Scenarios**:

1. **Given** máy ảo ở chế độ máy bay, **When** kích hoạt dừng an toàn, **Then** E7 hiện với Be Vietnam Pro (không rơi về
   Roboto), ≤ 3 s như trước.
2. **Given** cỡ chữ hệ thống 200%, **When** mở E7 và màn quyền, **Then** không chữ nào bị cắt hay chồng; nút vẫn ≥ 64dp.

---

### User Story 3 - Màu rủi ro và màu diễn tập dùng chung, luôn đi kèm biểu tượng + chữ (Priority: P2)

Màn sau này (E6, E8, E10, E11, trang `/a/[token]`) cần 4 mức rủi ro (thấp, trung bình, cao, rất cao) và màu diễn tập riêng.
Spec này chốt bảng màu, tên biểu tượng gợi ý và luật dùng; chưa dựng màn.

**Why this priority**: 020/022/023/028 cần token sẵn; chốt một lần tránh mỗi màn tự chọn màu.

**Independent Test**: unittest tương phản cho mọi cặp `risk.*`/`drill.*`; kiểm khác biệt màu diễn tập với 4 mức rủi ro.

**Acceptance Scenarios**:

1. **Given** token `risk.<mức>.fg` trên nền trắng và trên `risk.<mức>.bg`, **When** test, **Then** cả hai ≥ 7:1.
2. **Given** token `drill.*`, **When** so với 4 mức rủi ro, **Then** khác sắc độ (hue) ≥ 30° với mọi mức, để diễn tập không
   bao giờ trông như sự cố thật (luật 8).

### Edge Cases

- **Offline / khởi động nguội**: font đóng gói trong `res/font` (không dùng downloadable fonts của Google Play services).
- **Cỡ chữ 200% / TalkBack**: token cỡ chữ là `sp` (theo cỡ chữ hệ thống); không token nào dùng `dp` cho chữ.
- **Android 10 (API 29)**: font XML family + `FontFamily(Font(R.font…))` chạy từ API 26 ⇒ đủ cho minSdk 29.
- **Generator nhận dữ liệu xấu**: hex sai, thiếu khóa, tên token không hợp lệ cho Kotlin/CSS ⇒ từ chối trước khi ghi tệp
  (giá trị được chèn thẳng vào mã như `gen-bank-apps.py`).
- **Màu thương hiệu không đạt 7:1 cho chữ** (`brand.orange` 4,47:1, `brand.green` 5,23:1): vẫn giữ làm màu không phải chữ
  (biểu tượng, viền, mảng lớn, ≥ 3:1 theo WCAG 1.4.11). Chữ dùng biến thể `.text` đạt 7:1.
- **Chữ trắng trên nền cam**: cấm (4,47:1). Nút chính dùng nền navy (11,48:1) như hiện tại.
- **`:demobank`**: app ngân hàng giả, cố ý KHÔNG mang thương hiệu HỏiCon ⇒ không áp token.
- **Chế độ tối**: không làm (app người cao tuổi chỉ dùng nền sáng ở v1); ghi vào "Ngoài phạm vi".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Repo MUST có một nguồn token duy nhất `design-system/hoicon/tokens.json` (phiên bản `1.0.0`) gồm: màu
  (`brand`, `text`, `surface`, `risk.{low,medium,high,critical}`, `drill`, `focus`), cỡ chữ (sp, chiều cao dòng, độ đậm),
  họ font + độ đậm có đóng gói, kích thước (vùng chạm tối thiểu, khoảng cách, bo góc), chuyển động (thời lượng; giảm
  chuyển động ⇒ 0) và danh sách `contrast_pairs` (chữ/nền hoặc không-phải-chữ/nền + ngưỡng).
- **FR-002**: Mọi cặp `contrast_pairs` loại `text` MUST ≥ 7,0:1; loại `non_text` MUST ≥ 3,0:1 (WCAG 2.x, công thức độ sáng
  tương đối). Test in tỷ lệ của từng cặp; cặp dưới ngưỡng làm test đỏ.
- **FR-003**: `scripts/gen-design-tokens.py` (chỉ thư viện chuẩn) MUST sinh tất định: `apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/Tokens.kt`,
  khối giữa dấu BEGIN/END trong `apps/android/app/src/main/res/values/colors.xml`, và `apps/web/src/app/tokens.css`
  (`@theme inline`). Có cờ `--check`: không ghi, exit 1 nếu tệp sinh ra lệch.
- **FR-004**: Generator MUST kiểm luật 15 trước khi ghi: cỡ chữ thân ≥ 20sp, nhãn nút chính ≥ 24sp và đậm (≥ 600), vùng chạm
  ≥ 64dp; kiểm định dạng hex và tên token. Sai ⇒ exit 2, không ghi tệp nào.
- **FR-005**: Token chữ MUST đạt 7:1 trên nền khai báo: thêm/đổi `brand.orange.text` và `brand.green.text` thành giá trị
  đạt (gợi ý đã đo: `#8F3A0F` 7,55:1; `#13603F` 7,57:1). `brand.orange`/`brand.green` giữ giá trị đã chốt nhưng chỉ khai báo
  trong cặp `non_text`.
- **FR-006**: Bảng `risk.{low,medium,high,critical}` và `drill` MUST có `fg` (chữ/biểu tượng), `bg` (nền nhạt), `accent`
  (viền/mảng); `fg` ≥ 7:1 trên trắng và trên `bg` của chính nó; `drill` khác hue ≥ 30° với cả 4 mức (test). DESIGN-SYSTEM.md
  ghi luật "màu rủi ro luôn kèm biểu tượng + chữ" và tên biểu tượng gợi ý cho từng mức.
- **FR-007**: App Android MUST đóng gói Be Vietnam Pro 400/600/700 (OFL 1.1) trong `res/font/`, kèm tệp giấy phép OFL trong
  repo; `HoiConTypography` dùng họ font này. Không dùng downloadable fonts, không thêm thư viện.
- **FR-008**: `Color.kt`/`Type.kt`/`Theme.kt` MUST lấy giá trị từ `Tokens.kt` sinh ra; tên đang dùng ở màn hình
  (`BrandNavy`, `BrandOrange`, `SurfaceWhite`…) giữ nguyên (bí danh) để màn hiện có không phải sửa. Không còn mã màu hex chép
  tay trong `:app` ngoài tệp sinh ra.
- **FR-009**: Web MUST import `tokens.css` từ `globals.css`; biến CSS cũ (`--color-brand-*`, `--color-foreground`…) giữ tên;
  `pnpm --dir apps/web typecheck`, `lint`, `build` xanh. Font web vẫn qua `next/font/google` (đã có).
- **FR-010**: CI MUST chạy `gen-design-tokens.py --check` và unittest token khi đổi `design-system/**`, `scripts/gen-design-tokens.py`,
  `apps/android/**` hoặc `apps/web/**` (thêm đường dẫn vào bộ lọc `paths` của workflow tương ứng).
- **FR-011**: Chạy skill `ui-ux-pro-max` (truy vấn "elderly-friendly fintech safety family protection", `--design-system
  --persist -p "HoiCon"`) làm đầu vào tham khảo; kết quả lưu ở `design-system/hoicon/`; khác biệt với DESIGN-SYSTEM.md được
  giải quyết theo DESIGN-SYSTEM.md (file này thắng) và ghi vào `research.md`.
- **FR-012**: `docs/DESIGN-SYSTEM.md` MUST lên trạng thái v1: bảng token đầy đủ (kể cả risk/drill), tỷ lệ tương phản đã đo,
  quy trình đổi token (sửa JSON → chạy generator → unittest → ảnh chụp), luật chữ trên nền cam.
- **FR-013**: Ảnh chụp E7 (dừng an toàn) và màn quyền ở cỡ chữ 100% và 200% trên AVD `hc-api36` và `hc-api34`, trước và sau
  đổi font; báo cáo `ux-elder-reviewer` không còn mục mức cao.
- **FR-014**: Đổi font không phá hạn E7: `emu-scenario.py --scenario fake_police --runs 10` trên `hc-api36` đạt 10/10 và p95
  SafePause ≤ 3 000 ms; ghi cạnh số spec 001 (p95 1 724 ms, cùng AVD) để tham khảo. Máy ảo dao động lớn (001: p95 1 387–1 724 ms
  giữa hai lô) ⇒ không kết luận nhanh/chậm hơn từ máy ảo (ADR-008).
- **FR-015**: `docs/ROADMAP.md` dòng P1-05 cập nhật trạng thái + link `specs/010-design-system/`.

### Key Entities

- **Design token**: cặp tên ↔ giá trị (màu hex, sp, dp, ms, độ đậm). Không phải dữ liệu người dùng; không vào DB.
- **Contrast pair**: (`fg`, `bg`, `kind` ∈ {`text`, `non_text`}, ghi chú dùng ở đâu) ⇒ tỷ lệ đo được.

## Bất biến an toàn *(mandatory)*

- **Dừng an toàn** (I): E7 chỉ đổi font + nguồn màu. Font trong APK ⇒ vẫn offline; FR-014 đo lại thời gian hiện.
  Không đổi luồng, nút giữ 3 giây, hay giọng nói.
- **LLM chỉ nâng** (III): không đụng tới.
- **Công khai AI** (IV): không đổi câu chữ nào.

## Quyền riêng tư & đồng ý *(mandatory)*

| Dữ liệu mới / thay đổi | Dạng lưu | Mục đích đồng ý | Hạn lưu | Gửi LLM? |
|---|---|---|---|---|
| Không có dữ liệu người dùng mới | — | — | — | Không |

Quyền Android mới: **không có** (font trong APK không cần INTERNET).

## UX người cao tuổi *(mandatory)*

- Màn hình: không có màn mới; E7 (dừng an toàn) và màn quyền đổi font + nguồn màu. Theo `docs/DESIGN-SYSTEM.md`.
- Giữ ≤ 2 hành động chính · cỡ chữ 200% · tương phản ≥ 7:1 cho mọi chữ · TalkBack không đổi.
- Câu chữ: không đổi.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% cặp `text` ≥ 7,0:1 và 100% cặp `non_text` ≥ 3,0:1 — đo bằng unittest trên tokens.json (n = mọi cặp khai báo,
  ≥ 20 cặp).
- **SC-002**: 0 mã màu hex chép tay trong `apps/android/app/src/main/java/**` ngoài `Tokens.kt` sinh ra — đo bằng grep trong
  evidence.
- **SC-003**: `gen-design-tokens.py --check` exit 0 sau khi sinh; chạy 2 lần liên tiếp cho cùng byte (sha256 giống nhau).
- **SC-004**: E7 và màn quyền ở 200%: 0 chữ bị cắt — đo trên: AVD `hc-api36` + `hc-api34` (ảnh chụp), không phải máy thật.
- **SC-005**: APK debug `:app` tăng ≤ 1 MB do font — đo trên: kích thước tệp trước/sau.
- **SC-006**: E7 hiện 10/10, p95 ≤ 3 000 ms — đo trên: AVD `hc-api36`, n = 10 (máy ảo, chỉ để phát hiện hỏng, không so tốc độ).

## Kế hoạch bằng chứng *(mandatory)*

- Output unittest token (bảng tỷ lệ tương phản từng cặp) + `--check` + sha256 hai lần chạy.
- Gradle `:rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug` xanh; kích thước APK trước/sau.
- `pnpm --dir apps/web typecheck lint build` xanh.
- Ảnh E7 + màn quyền 100%/200% × AVD 36/34 (trước/sau) + báo cáo `ux-elder-reviewer`.
- `emu-scenario.py --scenario fake_police` p50/p95 + so với spec 001.
- grep mã hex trong `:app`; diff `ui-ux-pro-max` ↔ DESIGN-SYSTEM.md trong `research.md`.

## Ngoài phạm vi & mốc cắt

- Ngoài phạm vi: màn hình mới (E1–E6, E8–E12 thuộc 020/022/024/026/028), chế độ tối, component library dùng chung, Storybook,
  trang xem token trên web, áp token cho `:demobank`/`:voicelab`/`:latency`, thư viện icon mới.
- Nếu trễ, cắt trước: FR-011 (`ui-ux-pro-max` chỉ là tham khảo) → FR-014 (đo lại E7, ghi BLOCKED nếu máy ảo không chạy được).
  Không cắt: FR-002 (tương phản), FR-007 (font offline).

## Assumptions

- Be Vietnam Pro tải từ kho `google/fonts` (thư mục `ofl/bevietnampro`, giấy phép OFL 1.1) bằng mạng của máy dev lúc
  implement; ghi commit/URL nguồn và sha256 từng tệp trong evidence.
- Material 3 `lightColorScheme` giữ là cầu nối; token không ánh xạ hết mọi vai trò của M3 — vai trò còn lại đặt về navy/trắng
  như `Theme.kt` hiện tại (UX-9).
- Máy ảo đủ cho ảnh chụp và đo tương đối; số máy thật là việc của 001 (FTL, BLOCKED chờ Firebase).
