---

description: "Task list — Spec 010 Design system v1 (HỏiCon)"
---

# Tasks: Design system v1 — `tokens.json` sinh theme Compose + CSS

**Input**: `/specs/010-design-system/` (spec.md, plan.md, research.md)

**Prerequisites**: plan.md, spec.md (DS1–DS6 đã duyệt trước — không hỏi lại)

**Tests**: bắt buộc, viết trước, thấy đỏ rồi mới code (T006 đỏ trước T007). Đổi UI ⇒ có task chụp ảnh 100% + 200% và gọi
`ux-elder-reviewer`; đổi font E7 ⇒ có task `emu-scenario.py` AVD 36.

**Làn**: A. Ngoại lệ sở hữu đã ghi ở spec: `apps/web/src/app/{globals,tokens}.css`, `.github/workflows/{android,harness,web}.yml`.
Cấm sửa `backend/**`.

**Thiếu tài nguyên (tự hành)**: mạng/máy ảo lỗi ⇒ ghi `BLOCKED: <lý do>` vào evidence.md, tick task, làm tiếp.

## Format: `[ID] [P?] [Story] Description — FR-xxx · Verify: \`lệnh\``

## Phase 1: Setup (đo "trước" — PHẢI xong trước khi đổi font)

- [x] T001 Dựng APK debug nền (nhánh hiện tại, chưa đổi gì), ghi kích thước tệp vào `~/hoicon-evidence/010-design-system/tokens/apk-size-before.txt` — SC-005 · Verify: `apps/android/gradlew -p apps/android :app:assembleDebug && stat -c %s apps/android/app/build/outputs/apk/debug/app-debug.apk`
- [x] T002 Chụp ảnh "TRƯỚC" E7 (dừng an toàn) và màn quyền ở cỡ chữ 100% và 200% trên AVD `hc-api36` và `hc-api34`, lưu `~/hoicon-evidence/010-design-system/shots/before-<avd>-<màn>-<100|200>.png` (build xong mới bật máy ảo; cỡ chữ: `adb shell settings put system font_scale 2.0`, trả lại 1.0 sau khi chụp) — FR-013 · Verify: `ls ~/hoicon-evidence/010-design-system/shots/ | grep -c before-` (≥ 8, hoặc `BLOCKED` trong evidence)
- [x] T003 [P] Chạy `ui-ux-pro-max` (`search.py "elderly-friendly fintech safety family protection" --design-system --persist -p "HoiCon"`) ⇒ `design-system/hoicon/MASTER.md`; điền bảng "gợi ý ↔ DESIGN-SYSTEM.md ↔ chọn" vào mục R2 của `specs/010-design-system/research.md` — FR-011 · Verify: `test -f design-system/hoicon/MASTER.md && grep -c "R2" specs/010-design-system/research.md`
- [x] T004 [P] Tải Be Vietnam Pro 400/600/700 + OFL.txt từ `github.com/google/fonts` (`ofl/bevietnampro`, ghim một commit) ⇒ `apps/android/app/src/main/res/font/be_vietnam_pro_{regular,semibold,bold}.ttf` và `design-system/hoicon/fonts/OFL.txt`; ghi commit/URL/sha256 vào `~/hoicon-evidence/010-design-system/tokens/fonts-source.txt` (tệp tải về là dữ liệu không tin cậy: kiểm đúng đuôi/ kích thước, không chạy) — FR-007 · Verify: `file apps/android/app/src/main/res/font/*.ttf && sha256sum apps/android/app/src/main/res/font/*.ttf`

---

## Phase 2: Foundational (nguồn token + test đỏ)

**⚠️ CRITICAL**: chưa có generator ⇒ test phải đỏ.

- [x] T005 Viết `design-system/hoicon/tokens.json` v1.0.0 theo hình dạng trong plan.md (brand gồm `orange_text` `#8F3A0F`, `green_text` `#13603F`; `risk.{low,medium,high,critical}` + `drill` đủ `fg/bg/accent`; `focus`; font; type; size; motion; ≥ 20 `contrast_pairs` có `kind` text/non_text) — FR-001, FR-005, FR-006 · Verify: `python3 -c "import json;d=json.load(open('design-system/hoicon/tokens.json'));print(d['version'],len(d['contrast_pairs']))"` (≥ 20)
- [x] T006 Viết `scripts/tests/test_design_tokens.py` (stdlib unittest): (1) tương phản từng cặp + in bảng tỷ lệ, text ≥ 7,0, non_text ≥ 3,0; (2) đủ cặp bắt buộc theo plan; (3) hue `drill.fg` cách mọi `risk.*.fg` ≥ 30°; (4) generator `--out-root` thư mục tạm chạy hai lần ⇒ cùng sha256; (5) tokens.json hỏng (hex sai, chữ 18sp, nút 18sp/đậm 400, chạm 48dp) ⇒ exit 2 và không ghi tệp; (6) `--check` exit 1 khi lệch — FR-002, FR-003, FR-004, FR-006 · Verify: `python3 -m unittest scripts.tests.test_design_tokens` ĐỎ (generator chưa có) trước T007

**Checkpoint**: token + test đỏ có chủ đích.

---

## Phase 3: User Story 1 - Đổi một màu ở một chỗ, hai nền tảng cùng đổi (Priority: P1) 🎯 MVP

**Goal**: sửa JSON → chạy generator → Compose + CSS cập nhật; cặp dưới 7:1 thì test đỏ; quên generator thì CI đỏ.

**Independent Test**: `python3 -m unittest discover -s scripts/tests` + `python3 scripts/gen-design-tokens.py --check`.

- [x] T007 [US1] Viết `scripts/gen-design-tokens.py` (stdlib, theo mẫu `gen-bank-apps.py`; `--check`, `--out-root`): kiểm cấu trúc/hex/tên khóa/luật 15 TRƯỚC khi ghi (sai ⇒ exit 2, thông điệp tiếng Việt, không ghi tệp); sinh `Tokens.kt` (`object HoiConTokens`), khối BEGIN/END trong `colors.xml` (giữ `brand_navy`, `brand_orange`, `surface_white`, `navy_40`), `apps/web/src/app/tokens.css` (`@theme inline`, sp→rem) — FR-003, FR-004 · Verify: `python3 -m unittest scripts.tests.test_design_tokens` xanh và `ruff check scripts/gen-design-tokens.py scripts/tests/test_design_tokens.py` (type hints, Hiến chương VIII)
- [x] T008 [US1] Thêm dấu BEGIN/END vào `apps/android/app/src/main/res/values/colors.xml`, chạy generator, chạy 2 lần lấy sha256 từng tệp sinh ra ⇒ `~/hoicon-evidence/010-design-system/tokens/sha256.txt` — FR-003, SC-003 · Verify: `python3 scripts/gen-design-tokens.py && python3 scripts/gen-design-tokens.py --check && sha256sum apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/Tokens.kt apps/web/src/app/tokens.css`
- [x] T009 [US1] Web: `apps/web/src/app/globals.css` `@import "./tokens.css"`, bỏ giá trị chép tay, giữ tên biến cũ (`--color-background`, `--color-foreground`, `--color-brand-*`, `--font-sans`) — FR-009 · Verify: `pnpm --dir apps/web typecheck && pnpm --dir apps/web lint && pnpm --dir apps/web build`
- [x] T010 [P] [US1] CI: `android.yml` thêm bước `python3 ../../scripts/gen-design-tokens.py --check` + `paths` (`design-system/**`, `scripts/gen-design-tokens.py`); `harness.yml` thêm `design-system/**`, `scripts/gen-design-tokens.py` vào `paths`; `web.yml` thêm `design-system/**` — FR-010 · Verify: `grep -c "gen-design-tokens" .github/workflows/android.yml .github/workflows/harness.yml && git diff --stat -- .github/workflows` (đọc lại ba tệp YAML: thụt lề đúng)

**Checkpoint**: US1 chạy độc lập (unittest xanh, `--check` exit 0, web build xanh).

---

## Phase 4: User Story 2 - Màn hình app dùng Be Vietnam Pro + token, kể cả offline (Priority: P1)

**Goal**: E7 và màn quyền dùng font đóng gói và màu từ `Tokens.kt`; 200% không cắt chữ; E7 vẫn ≤ 3 s.

**Independent Test**: `:app:assembleDebug` + ảnh 100%/200% trên AVD 36/34.

- [x] T011 [US2] `ui/theme/Color.kt` thành bí danh `HoiConTokens.Color.*` (giữ tên `BrandNavy`, `BrandOrange`, `BrandOrangeText`, `BrandGreen`, `SurfaceWhite`; thêm bí danh risk/drill/`BrandGreenText`); `Theme.kt` đổi nguồn giá trị, giữ UX-9; không sửa `SafePauseScreen.kt`/`PermissionsScreen.kt`/`MainActivity.kt` trừ khi build bắt buộc — FR-008 · Verify: `apps/android/gradlew -p apps/android :app:compileDebugKotlin`
- [x] T012 [US2] `ui/theme/Type.kt`: `FontFamily(Font(R.font.be_vietnam_pro_regular, W400), …semibold W600, …bold W700)` + cỡ/dòng/độ đậm từ `HoiConTokens.Type`; không downloadable fonts, không thư viện, không quyền INTERNET — FR-007, FR-008 · Verify: `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`
- [x] T013 [US2] Đo APK sau, SC-005 (≤ +1 MB so với T001) và SC-002 (0 mã hex chép tay trong `apps/android/app/src/main/java/**` ngoài `Tokens.kt`) — SC-002, SC-005 · Verify: `grep -rEn "0x[0-9A-Fa-f]{8}|#[0-9A-Fa-f]{6}" apps/android/app/src/main/java --include=*.kt | grep -v Tokens.kt` (rỗng) và `stat -c %s apps/android/app/build/outputs/apk/debug/app-debug.apk`
- [x] T014 [US2] Chụp ảnh "SAU" E7 + màn quyền 100%/200% × `hc-api36`/`hc-api34` ⇒ `~/hoicon-evidence/010-design-system/shots/after-*.png`; xem từng ảnh: không chữ cắt/chồng, nút ≥ 64dp, đúng Be Vietnam Pro — FR-013, SC-004 · Verify: `ls ~/hoicon-evidence/010-design-system/shots/ | grep -c after-` (≥ 8, hoặc `BLOCKED`)
- [x] T015 [US2] Đo lại hạn E7: `python3 scripts/emu-scenario.py --avd hc-api36 --scenario fake_police --runs 10` ⇒ 10/10, p95 ≤ 3 000 ms; ghi cạnh spec 001 (p95 1 724 ms) chỉ để tham khảo (ADR-008) — FR-014, SC-006 · Verify: output của lệnh, lưu `~/hoicon-evidence/010-design-system/tokens/emu-fake-police.txt`
- [x] T016 [US2] Gọi `ux-elder-reviewer` trên ảnh T014 — FR-013 · Verify: báo cáo không còn mục mức cao — **ĐẠT cho biến thể ngân hàng (18/10/2026)**: 0 High trên ảnh E7 Compose mới (hc-api34/36); biến thể điều khiển từ xa chưa có ảnh; xem evidence.md "E7 sửa 18/10/2026"

**Checkpoint**: US2 xong; US1 không vỡ (`--check` vẫn 0).

---

## Phase 5: User Story 3 - Màu rủi ro và diễn tập dùng chung, luôn kèm biểu tượng + chữ (Priority: P2)

**Goal**: bảng risk/drill đã chốt, có tài liệu, tương phản và hue có test.

**Independent Test**: unittest cặp `risk.*`/`drill.*` và hue.

- [x] T017 [US3] Rà test hue + tương phản risk/drill đã xanh sau T007; nếu giá trị plan DS4 sai vài điểm, chỉnh trong `tokens.json` (nhẹ, ghi lại tỷ lệ cuối) rồi sinh lại — FR-006 · Verify: `python3 -m unittest scripts.tests.test_design_tokens -v` + `python3 scripts/gen-design-tokens.py --check`
- [x] T018 [US3] `docs/DESIGN-SYSTEM.md` lên v1: bảng token đầy đủ (kể cả risk/drill, tỷ lệ đo), luật "màu rủi ro luôn kèm biểu tượng + chữ" + tên biểu tượng gợi ý, cấm chữ trắng trên nền cam, quy trình đổi token (sửa JSON → generator → unittest → ảnh chụp), ghi chú sp→rem, chế độ tối ngoài phạm vi, bỏ dòng "Trạng thái: khung" — FR-006, FR-012 · Verify: review + `grep -c "7:1" docs/DESIGN-SYSTEM.md`

---

## Phase 6: Polish & Cross-Cutting

- [x] T019 [P] Gọi `/ponytail-review` trên diff (tối giản, không over-engineer) và `security-privacy-reviewer` (manifest: 0 quyền mới) — Verify: không còn finding High
- [x] T020 Chạy `privacy-audit`-mức nhẹ: `git diff` không chứa số điện thoại/secret; manifest không thêm quyền — Verify: `git diff --stat && git diff -- apps/android/app/src/main/AndroidManifest.xml`

---

## Phase 7: Acceptance evidence *(bắt buộc)*

- [x] T021 Chạy `/speckit-converge` tới 0 finding hoặc điều kiện dừng (MASTER-PLAN §2.5; chặn ⇒ BLOCKED trong evidence.md) — Verify: báo cáo converge
- [x] T022 Chạy cổng các tầng: `python3 scripts/check-spec-trace.py` · `python3 -m unittest discover -s scripts/tests` · `python3 scripts/gen-design-tokens.py --check` · `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug` · `pnpm --dir apps/web typecheck && pnpm --dir apps/web lint && pnpm --dir apps/web build` — Verify: output dán vào evidence.md
- [x] T023 Viết `specs/010-design-system/evidence.md` từ `.specify/templates/overrides/evidence-template.md` (mỗi SC-001…SC-006 có số đo + nguồn; ảnh ở `~/hoicon-evidence/010-design-system/`; điền R2 trong research.md) — Verify: `python3 scripts/check-spec-trace.py`
- [x] T024 Cập nhật dòng P1-05 trong `docs/ROADMAP.md` (◐ → ☑ nếu đủ ảnh + test, còn BLOCKED thì giữ ◐ và nói rõ) — FR-015 · Verify: `python3 scripts/check-spec-trace.py`

---

## Dependencies & Execution Order

- Phase 1 trước hết (T001 → T002 trước mọi sửa Android; T004 sau T001 vì thêm tệp vào `res/` đổi kích thước APK).
- T005 → T006 (đỏ) → T007 → T008 → T009/T010; T011 → T012 → T013 → T014 → T015 → T016; T017 → T018.
- Phase 6–7 cuối cùng.
- [P]: T003 song song T004 (sau T001); T010 song song T009.

## Notes

- Không đánh `[x]` khi Verify chưa xanh; bước không chạy được ghi BLOCKED/SKIPPED + lý do trong evidence.md.
- Không commit/push (Tiến merge vào `tien-collab-dev` sau).

---

## Phase 8: Convergence

*(`/speckit-converge` lượt 1, 15/10/2026 — còn 2 finding, đều về FR-013; các FR/SC khác thấy đã đáp ứng trong mã.)*

- [x] T025 HIGH — Ghi vào `docs/ROADMAP.md` mục "Ghi chú" (không làm trong spec này) 2 mục High của `ux-elder-reviewer` về E7 ở 200% trên màn nhỏ: (a) hàng "Đây là trợ lý AI HỏiCon + Nghe lại" ép chữ công khai AI thành 3 dòng hẹp, (b) vùng cuộn chỉ còn ~1–2 dòng thân khi đang giữ nút; chuyển sang P2-05 (E7 thuộc P2-05), và ghi `BLOCKED: FR-013 chưa đạt "không còn mục High"` vào evidence.md per FR-013 (partial)
- [x] T026 MEDIUM — Ghi vào mục "Ghi chú" của ROADMAP các mục Medium/Low do đổi font cần quyết định thiết kế (khoảng cách từ hẹp ở "như một", cân nhắc đóng gói thêm Medium 500, tên mục quyền dài thành 2 dòng, nhắc "vuốt lên để đọc tiếp", chụp trạng thái "✗ Chưa bật" của màn quyền) per FR-013 (partial)

---

## Phase 9: Wave 2 (18/10/2026 — tồn đọng Wave 1)

- [x] T027 [A] Chụp E7 biến thể **điều khiển từ xa** (`PauseKind.REMOTE_CONTROL`, luật R5) ở cỡ chữ 100% và 200% trên `hc-api36` và
  `hc-api34`, rồi gọi `ux-elder-reviewer` — đóng phần "chưa có ảnh" của FR-013 (evidence: "biến thể điều khiển từ xa CHƯA có ảnh, không
  dựng được trên máy ảo"). Cách dựng trên máy ảo, theo tiền lệ `vn.hoicon.demobank` trong `BankAppCatalog`:
  - thêm gói hư cấu `vn.hoicon.demoremote` vào `RemoteControlCatalog` (tăng `VERSION`) và `<queries>` của manifest (giữ
    `RemoteControlCatalogTest` xanh);
  - `:demobank` thêm một product flavor `remote` với `applicationId "vn.hoicon.demoremote"`, nhãn "Điều khiển từ xa (mẫu)", màn
    hình đơn giản (không có chức năng điều khiển thật);
  - `scripts/emu-scenario.py --scenario remote_control`: cài flavor đó, giả lập cuộc gọi lạ, mở app ⇒ SafePause REMOTE_CONTROL; chụp
    ở `font_scale` 1.0 và 2.0 (`adb shell settings put system font_scale 2.0`, đặt lại 1.0 sau khi chụp).

  Tiêu đề dài có thể 5–6 dòng ở 200%: nếu reviewer báo High thì sửa bố cục như biến thể ngân hàng (vùng đọc rộng hơn ở ≥ 150%,
  commit `ad2f2b7`). FR-013 · Verify: `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug`;
  `python3 scripts/emu-scenario.py --avd hc-api36 --scenario remote_control` và `--avd hc-api34` ĐẠT; 8 ảnh (2 AVD × 2 cỡ × trước/sau
  nếu sửa) ở `~/hoicon-evidence/010-design-system/`; báo cáo reviewer 0 High trong `evidence.md`

---

## Phase 10: Wave 3 (22/10/2026) — chốt câu chữ E7 biến thể "điều khiển từ xa"

Câu chữ chốt bởi kiến trúc sư Spec Kit theo `docs/DESIGN-SYSTEM.md` (giọng ấm áp, không gây hoảng sợ, có hành động cụ thể; nói đúng
điều máy biết) và 3 đề xuất của `ux-elder-reviewer` lượt 3 (evidence.md, mục "E7 biến thể điều khiển từ xa"). Tiêu đề cùng khuôn với
biến thể ngân hàng ("Bác ơi, khoan chuyển tiền đã") và trùng câu thứ hai của lời đọc `pause_speech_remote` (màn và giọng nói một ý).
Bỏ "Kẻ gian" khỏi màn người cao tuổi; không đổi `pause_reason_remote_*` (đã nói đúng điều máy biết) và `pause_speech_remote`.

| Khóa `strings.xml` | Hiện tại | Chốt |
|---|---|---|
| `pause_title_remote` | Bác ơi, có người lạ đang muốn điều khiển điện thoại của bác? | **Bác ơi, khoan cho người lạ điều khiển điện thoại** |
| `pause_body_remote` | Kẻ gian hay bảo bác cài ứng dụng để họ nhìn và điều khiển điện thoại của bác, rồi lấy tiền trong ngân hàng. Công an, ngân hàng không bao giờ bảo làm vậy. Bác cúp máy, đóng ứng dụng đó (như AnyDesk, TeamViewer), rồi bấm Hỏi con. | **Ứng dụng này cho người khác nhìn thấy và điều khiển điện thoại của bác, kể cả ứng dụng ngân hàng. Công an, ngân hàng không bao giờ bảo bác cài ứng dụng này. Bác cúp máy, đóng ứng dụng đó (như AnyDesk, TeamViewer), rồi bấm Hỏi con.** |

- [x] T028 [A] [FR-013] Thay đúng hai chuỗi trên trong `apps/android/app/src/main/res/values/strings.xml` (không đổi khóa, không đổi
  bố cục `SafePauseScreen.kt`; nếu có test/screenshot test nhắc chuỗi cũ thì sửa theo). Dựng lại E7 biến thể điều khiển từ xa trên
  máy ảo theo cách của Wave 2 (evidence.md): `apps/android/gradlew -p apps/android :demobank:installDebug
  -PdemobankApplicationId=com.anydesk.anydeskandroid` (bản giả, chỉ máy ảo) rồi
  `HC_DEMOBANK_PACKAGE=com.anydesk.anydeskandroid python3 scripts/emu-scenario.py --avd <avd> --scenario fake_police`; chụp ở
  `adb shell settings put system font_scale 1.0` và `2.0` (đặt lại 1.0 sau khi chụp) trên `hc-api36` và `hc-api34` ⇒ 4 ảnh
  `~/hoicon-evidence/010-design-system/w3/e7-remote-{36,34}-{100,200}.png`. Gọi `ux-elder-reviewer` đọc 4 ảnh + hai chuỗi mới;
  còn High ⇒ sửa bố cục (chỉ nhánh `fontScale ≥ 1,5`, như `ad2f2b7`) và chụp lại, tối đa 2 vòng, quá 2 vòng ⇒ dừng, ghi BLOCKED.
  Đạt 0 High ⇒ tick cả T027 (phần "reviewer đọc lại ảnh sau mục 4" được đóng bằng ảnh mới).
  · Verify: `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug` xanh; `emu-scenario.py` ĐẠT trên
  cả hai AVD (10/10 không bắt buộc, 1 lượt đủ cho ảnh; giữ `--runs 10` trên hc-api36 để xác nhận E7 vẫn ≤ 3 s); báo cáo reviewer
  "0 High" + đường dẫn 4 ảnh ghi vào `specs/010-design-system/evidence.md` mục mới "E7 điều khiển từ xa — Wave 3".
