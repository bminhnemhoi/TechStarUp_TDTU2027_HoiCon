# Bằng chứng nghiệm thu: Design system v1 — `tokens.json` sinh theme Compose + CSS

**Spec**: `specs/010-design-system/spec.md` · **Mã ROADMAP**: P1-05 · **Nhánh/PR**: feat/010-design-system · chưa commit/PR (Tiến merge vào `tien-collab-dev` sau) · **Ngày**: 15/10/2026

> **Cập nhật 18/10/2026 (Làn A Android):** 2 mục **High** của E7 ở 200% trên màn nhỏ (xem "Còn tồn") đã được xử lý trên bản **Compose đang phát hành**
> (ảnh 15/10 là bản View đời đầu): `ux-elder-reviewer` đọc ảnh mới trên hc-api34 (1080×2340) và hc-api36 ⇒ **không còn High cho biến thể ngân hàng**;
> biến thể "điều khiển từ xa" CHƯA có ảnh (không dựng được trên máy ảo) nên chưa kết luận được cho toàn bộ E7. Còn 3 Medium + 3 Low (mục
> "E7 sửa 18/10"). Mọi số đo bên dưới là số **máy ảo** (Linux headless, bản debug), trừ khi ghi khác. Ảnh, APK, log nằm ngoài repo:
> `~/hoicon-evidence/010-design-system/{shots,apk,tokens,e7-w1}` (viết tắt `$EV`).

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Môi trường (máy ảo / FTL / máy thật, n) | Đạt? | Bằng chứng |
|---|---|---|---|---|---|
| SC-001 | 100% cặp `text` ≥ 7,0:1, 100% cặp `non_text` ≥ 3,0:1, ≥ 20 cặp | 26 cặp (17 text, 9 non_text), tất cả đạt. Thấp nhất: text 7,06 (`risk.low.fg`/`risk.low.bg`, `risk.medium.fg`/`risk.medium.bg`); non_text 4,47 (`brand.orange`, `risk.high.accent`) | unittest trên `tokens.json` (công thức WCAG 2.x), không phụ thuộc máy | ✓ | `python3 -m unittest scripts.tests.test_design_tokens.ContrastTest -v` in bảng từng cặp |
| SC-002 | 0 mã hex chép tay trong `apps/android/app/src/main/java/**` ngoài `Tokens.kt` | 0 kết quả; cả `ic_launcher_*` trong `res/` cũng đã trỏ `@color/brand_navy`/`surface_white` | grep trong worktree | ✓ | `grep -rEn "0x[0-9A-Fa-f]{8}\|#[0-9A-Fa-f]{6}" apps/android/app/src/main/java --include='*.kt' \| grep -v ui/theme/Tokens.kt` rỗng |
| SC-003 | `--check` exit 0 sau khi sinh; hai lần chạy cùng sha256 | exit 0; sha256 lần 2 = lần 1 (3 tệp) | máy dev Linux | ✓ | `$EV/tokens/sha256.txt` (`sha256sum -c` OK); test `test_deterministic_and_idempotent` |
| SC-004 | E7 và màn quyền ở 200%: 0 chữ bị cắt | Không chữ nào bị cắt/chồng, không dấu nào mất (reviewer đọc 16 ảnh + 2 ảnh trạng thái đang giữ/xác nhận). Chữ rộng hơn nên vùng cuộn thu hẹp (xem "Còn tồn") | AVD hc-api36 + hc-api34 (ảnh chụp), **không phải máy thật** | ✓ cho "0 chữ bị cắt"; ⚠ vùng cuộn hẹp | `$EV/shots/{before,after}-hc-api{36,34}-{e7,quyen}-{100,200}.png`, `after-hc-api34-e7-200-giu-1s.png` |
| SC-005 | APK debug tăng ≤ 1 MB do font | 29 701 580 → 30 200 262 byte = +498 682 B (**+487 KB**) | tệp `app-debug.apk` trước/sau | ✓ | `$EV/tokens/apk-size-{before,after}.txt` |
| SC-006 | E7 hiện 10/10, p95 ≤ 3 000 ms | **A/B cold (`--prep force-stop`), xen kẽ trước/sau font, 3 vòng × 5 lượt = n 15 mỗi bên, hc-api36:** trước p50 837/872/886 ms, sau p50 864/909/882 ms (chênh khoảng +25–35 ms ở p50, trong dải nhiễu vì p95 mỗi lô dao động 956–1 628 ms); 30/30 lượt hiện, mọi lượt ≤ 3 000 ms (`$EV/tokens/ab-latency.txt`). Lô 10 lượt đầu (không cold): 10/10, SafePause p50 794 / p95 2 521 ms. Lô trước đó (cùng mã trừ 1 ký tự nbsp): 10/10, p50 362 / p95 1 752 ms. Cold (`--prep force-stop`): 10/10, p50 824 / p95 1 135 ms. Tham khảo spec 001 cùng AVD: p95 1 387–1 724 ms. Máy ảo dao động lớn giữa các lô (ADR-008) ⇒ **không kết luận nhanh/chậm hơn**, chỉ xác nhận không hỏng | AVD hc-api36, n = 10 mỗi lô, máy ảo | ✓ (chỉ để phát hiện hỏng) | `$EV/tokens/emu-fake-police.txt`, `emu-fake-police-forcestop.txt` |

## Yêu cầu chức năng (FR) ↔ test

| FR | Test / cách kiểm | Kết quả |
|---|---|---|
| FR-001 | `design-system/hoicon/tokens.json` v1.0.0: màu (brand, surface, text, risk×4, drill, focus), font, cỡ chữ, kích thước, chuyển động, 26 `contrast_pairs`; `test_required_pairs_present` | ✓ |
| FR-002 | `ContrastTest.test_every_declared_pair_meets_threshold` (in tỷ lệ từng cặp) | ✓ — test bắt được lỗi thật trong lúc làm: `brand.orange_text`/`brand.green_text` gợi ý `#8F3A0F`/`#13603F` chỉ 6,98/7,00 trên `surface.muted` ⇒ đổi thành `#843410` (8,47 trắng, 7,82 muted) và `#115A3B` (8,24; 7,61) |
| FR-003 | `scripts/gen-design-tokens.py` (chỉ stdlib) sinh `Tokens.kt`, khối BEGIN/END `colors.xml`, `tokens.css`; `--check`; `GeneratorTest` ×5 | ✓ |
| FR-004 | `GeneratorRejectsBadInputTest` ×15: hex sai, body 18sp, nút 18sp, nút không đậm, chạm 48dp, tên khóa sai, cặp trỏ token không có, thiếu mục, `contrast_pairs` rỗng/không phải đối tượng, chèn chuỗi vào `version`/`font.family`/`motion`, số không nguyên — đều exit 2 và không ghi tệp | ✓ |
| FR-005 | `brand.*_text` đạt ≥ 7:1 (xem FR-002); `brand.orange`/`brand.green` chỉ khai báo `non_text` (`test_orange_and_green_never_used_as_text`) | ✓ |
| FR-006 | bảng `risk.*`/`drill` có `fg/bg/accent`; `DrillHueTest` (hue 262° cách mọi mức ≥ 30°; gần nhất 98°); `docs/DESIGN-SYSTEM.md` ghi luật biểu tượng + chữ | ✓ |
| FR-007 | `res/font/be_vietnam_pro_{regular,semibold,bold}.ttf` + `be_vietnam_pro.xml`; OFL ở `design-system/hoicon/fonts/OFL.txt`; nguồn `github.com/google/fonts@d47d546884f75bbf718d3ddbb8d4627c68b9c782/ofl/bevietnampro`, sha256 ở `$EV/tokens/fonts-source.txt` (reviewer tải lại, khớp cả 4 tệp). Không thư viện, không quyền mới. **Phát hiện khi chụp:** E7 mặc định là layout **View**, không phải Compose ⇒ chỉ Type.kt không đủ, đã đặt `android:fontFamily` ở `Theme.HoiCon` (`themes.xml`); ảnh sau đổi cho thấy font mới ở cả E7 và màn quyền | ✓ |
| FR-008 | `Color.kt`/`Type.kt`/`Theme.kt` lấy từ `HoiConTokens`; tên cũ giữ; màn hình (`SafePauseScreen.kt`, `PermissionsScreen.kt`, `MainActivity.kt`) không sửa. Theme đổi `secondary`/`tertiary` sang biến thể `*_text` (7:1) | ✓ |
| FR-009 | `globals.css` `@import "./tokens.css"`; build ra `.text-brand-navy{color:#1f3a5f}`, `.text-brand-orange-text{color:#843410}`; `typecheck`, `lint`, `build` xanh | ✓ |
| FR-010 | `android.yml` (bước `--check` + paths), `harness.yml` (paths; đã chạy `scripts/tests`), `web.yml` (paths); YAML hợp lệ (đọc bằng PyYAML) — **chưa chạy trên GitHub Actions** (chưa push) | ✓ cục bộ · CI UNAVAILABLE |
| FR-011 | `design-system/hoicon/MASTER.md` (đã gắn nhãn CHỈ THAM KHẢO); bảng đối chiếu ở `research.md` R2 — không nhận gợi ý nào ngoài các mục trùng | ✓ |
| FR-012 | `docs/DESIGN-SYSTEM.md` v1: bảng token + tỷ lệ, quy trình đổi token, luật chữ trên nền cam, bảng risk/drill, chế độ tối ngoài phạm vi | ✓ |
| FR-013 | Ảnh E7 + màn quyền 100%/200% × AVD 36/34, trước/sau, + ảnh trạng thái đang giữ/xác nhận (API 34, 200%); `ux-elder-reviewer` đã chạy | ⚠ **một phần**: còn 2 High (xem "Còn tồn") |
| FR-014 | `emu-scenario.py --scenario fake_police --runs 10` trên hc-api36: 10/10, p95 ≤ 3 000 ms (xem SC-006) | ✓ |
| FR-015 | Dòng P1-05 trong `docs/ROADMAP.md` (giữ ◐, link spec, lý do) | ✓ |

## Cổng các tầng (lệnh đã chạy)

| Tầng | Lệnh | Kết quả |
|---|---|---|
| Python / script | `python3 -m unittest discover -s scripts/tests` | 67 test OK (35 trong `test_design_tokens.py`; còn lại là test có sẵn) |
| Lint Python | `uv run --directory backend ruff check ../scripts/gen-design-tokens.py ../scripts/tests/test_design_tokens.py` | All checks passed |
| Generator | `python3 scripts/gen-design-tokens.py --check` | exit 0 |
| Android | `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:processReleaseMainManifest` | BUILD SUCCESSFUL (lần cuối sau mọi sửa mã Android, gồm `Type.kt` đủ 15 vai trò) |
| Manifest release | liệt kê `uses-permission` trong manifest đã merge | 6 quyền có sẵn (FOREGROUND_SERVICE, …SPECIAL_USE, POST_NOTIFICATIONS, SYSTEM_ALERT_WINDOW, HIDE_OVERLAY_WINDOWS, PACKAGE_USAGE_STATS); **0 INTERNET, 0 RECORD_AUDIO**; `AndroidManifest.xml` nguồn không đổi |
| Web | `pnpm --dir apps/web typecheck && lint && build` | xanh (cài deps bằng `pnpm install --frozen-lockfile`) |
| Máy ảo | `python3 scripts/emu-scenario.py --avd hc-api36 --scenario fake_police --runs 10` | 10/10 ĐẠT (xem SC-006). hc-api34: modem giả lập không báo cuộc gọi cho Telecom ở phiên này (cả sau 2 lần boot `--cold`; lỗi đã gặp ở spec 001) ⇒ **E7 trên hc-api34 dựng bằng broadcast debug `ScenarioReceiver`** (docs/EMULATOR.md) cho ảnh chụp; không chạy `fake_police` trên API 34 |
| Truy vết | `python3 scripts/check-spec-trace.py` | 0 lỗi |
| Eval | `run-eval smoke` | N/A — không đổi agent/prompt |
| Hook | — | N/A — không đổi hook |

## Review

| Reviewer | Kết quả | Đã xử lý |
|---|---|---|
| `security-privacy-reviewer` | 0 Critical/High/Medium; 3 Low: (1) `version`/`font.family` chèn thẳng vào Kotlin không kiểm, (2) `motion`/`space`/`radius` không ép số nguyên, `contrast_pairs` phần tử không phải dict ⇒ traceback, (3) `MASTER.md` ghi `@import` Google Fonts trái quyết định offline | (1)(2) sửa trong `gen-design-tokens.py` + 7 test mới (fuzz trước khi sửa xác nhận cả `contrast_pairs: {}` bị chấp nhận exit 0); (3) gắn nhãn "CHỈ THAM KHẢO — không nhập font từ Google Fonts" ở đầu `MASTER.md` |
| `ux-elder-reviewer` | 2 High (E7 200% màn nhỏ: hàng công khai AI/"Nghe lại"; vùng cuộn hẹp khi giữ nút), 3 Medium (ngắt "3 / giây"; khoảng từ hẹp; Regular 400 mảnh), 6 Low | "3 giây" ⇒ thêm U+00A0 trước "giây" (ảnh sau: "3 giây" cùng dòng); các mục còn lại ⇒ ROADMAP "Ghi chú" → P2-05. Đã thử tính xếp dọc hàng "Nghe lại": không tiết kiệm chỗ (nút ≥ 64dp) nên không làm |
| `code-reviewer` (ponytail) | 0 High; 4 Medium, 7 Low. M1 generator traceback (thiếu `motion.reduced_ms`, `fg` là list); M2 `tokens.css` sửa tay không bị CI bắt; M3 `Typography` chỉ 6 kiểu, kiểu M3 còn lại rơi về Roboto/cỡ < 20sp; M4 chưa đo A/B chi phí nạp font ở E7; L1 kiểm luật 15 chỉ áp cho khóa `body*`, bool lọt vào số nguyên, khóa `motion` không bắt `_ms`; L2 dấu BEGIN/END chưa chặt; L3 test so generator với chính nó | **Đã xử lý:** M1 (+ test); M2 (`web.yml` thêm `--check`); M3 (`Type.kt` ánh xạ đủ 15 vai trò M3 từ token, không còn kiểu < 20sp); M4 (A/B xen kẽ, xem SC-006); L1 (mọi cỡ chữ ≥ 20sp, bool bị loại, khóa `motion` phải `_ms`); L2 (đúng một cặp BEGIN…END, BEGIN trước END; 3 test); L3 (`GeneratedValuesTest` đối chiếu giá trị độc lập với JSON, hue `drill.accent`). **Không làm, có chủ đích:** L4 bí danh/biến chưa dùng (plan thêm sẵn cho 020/022/023/028); L5 cỡ chữ viết cứng trong `activity_safe_pause.xml` (generator chỉ sinh màu cho XML; E7 thuộc P2-05); L6 NBSP ở hai chuỗi "3 giây" còn lại (không hiện trên nút; để P2-05); L7 đổi tên tham số (đã đổi `sp`→`size`, `T`→`tokens`) |

## `/speckit-converge`

Lượt 1: 2 finding (cả hai FR-013 partial) ⇒ T025–T026 (ghi vào ROADMAP, đã làm). Ngoài ra một finding LOW xử lý ngay: `ic_launcher_*` còn hex chép tay ⇒ trỏ token. Lượt 2: 0 finding mới ngoài FR-013 đã ghi BLOCKED.

## E7 sửa 18/10/2026 (T016)

**Vấn đề (thấy trên ảnh `before-api34-e7-200*.png`, bản Compose, hc-api34):** ở chữ 200% thanh nút ghim chiếm gần nửa màn, thân chữ còn chưa tới 1
dòng (0 dòng khi giữ nút "Vẫn tiếp tục"); hàng "Đây là trợ lý AI HỏiCon + Nghe lại" 3 dòng.
**Sửa (`SafePauseScreen.kt`, chỉ từ cỡ chữ ≥ 150%):** bớt khoảng cách dọc, tiêu đề 28sp thay 32sp, gợi ý nút giữ rút còn "Giữ 3 giây".
Giữ nguyên: nút ≥ 64dp, ≤ 2 hành động chính, "Vẫn tiếp tục" giữ 3 giây (`HOLD_MS` 3 000 ms), nhãn "Hủy giao dịch" + "Về màn hình chính" ở mọi cỡ chữ.
(Thử đổi nhãn nút hủy thành "Về màn hình chính" ở chữ lớn: reviewer thấy không tiết kiệm chỗ và lệch DESIGN-SYSTEM ⇒ đã hoàn lại.)

| Đo trên ảnh (hc-api34, 200%) | Trước | Sau |
|---|---|---|
| Thân chữ nhìn thấy, không giữ nút | ≈ 0,5 dòng | ≈ 1,5–2 dòng |
| Thân chữ nhìn thấy, đang giữ nút | 0 dòng | ≈ 1 dòng |

`ux-elder-reviewer` (lượt cuối): **0 High** cho biến thể ngân hàng đã chụp. Còn lại, để theo dõi: **Medium** — phần đầu (AI 3 dòng + "Rất cần cẩn thận" 2 dòng + tiêu đề)
vẫn ăn phần lớn vùng đọc ở 200%; dòng "Giữ yên nhé…" chiếm 1 dòng khi giữ (gợi ý: đưa vào chính nút); phần "mật khẩu gia đình"/"nghỉ một phút" luôn dưới nếp
gập. **Low** — "Vẫn tiếp tục" trông giống "Hủy giao dịch" (chưa "lặng" hơn); viền "Nghe lại" nhạt; khoảng cách nút ≈ 8dp.
**Chưa kiểm:** biến thể điều khiển từ xa (tiêu đề dài, có thể 5–6 dòng ở 200%; cần chụp bằng Preview Compose `kind = REMOTE_CONTROL`, `fontScale = 2f` hoặc cài
app điều khiển từ xa); TalkBack; máy thật. Việc đổi chữ nút chỉ làm theo một cỡ, không đổi hành vi.

**Hạn E7 sau sửa (máy ảo, `emu-scenario.py --scenario fake_police --runs 10`, mã cuối cùng):**
- hc-api36: 10/10 hiện SafePause; phát hiện p50/p95 310/805 ms; SafePause p50/p95 852/1 603 ms ⇒ ĐẠT (≤ 3 000 ms).
- hc-api34: 10/10 hiện SafePause; lần chạy đầu ngay sau khi khởi động máy ảo: SafePause p95 2 777 ms nhưng script báo TRƯỢT vì một lần cây UI không thấy màn E7 lúc
  đo; chạy lại: phát hiện p50/p95 578/627 ms, SafePause p50/p95 674/725 ms ⇒ ĐẠT. (Số p95 dao động nhiều giữa các lượt; không kết luận về máy thật.)
- Script `emu-scenario.py` cũng được sửa để nhận ra E7 bản Compose (trước đó tìm chữ "gọi cho con" của bản View nên báo TRƯỢT dù 10/10 hiện SafePause).
Ảnh: `$EV/e7-w1/{before,final}-api{34,36}-e7-{100,200}[-giu].png`.

## Còn tồn / hoãn có chủ đích

- **BLOCKED — FR-013 "không còn mục High"**: E7 ở 200% trên AVD API 34 (1080×2340): hàng "Đây là trợ lý AI HỏiCon + Nghe lại" ép chữ công khai AI thành 3 dòng; thanh nút ghim chiếm ~37% màn (trước đổi font ~31%); vùng cuộn còn ~2 dòng thân, ~1 dòng khi giữ nút (`after-hc-api34-e7-200-giu-1s.png`). Đây là bố cục E7 có sẵn, nặng thêm do font rộng hơn; sửa cần thiết kế riêng cho `fontScale ≥ 1,5` ⇒ P2-05 (E7), không mở rộng spec này. Cũng ghi ở ROADMAP "Ghi chú".
- Chưa kiểm: hc-api29 (font XML chạy từ API 26, minSdk 29 đủ theo tài liệu, **chưa đo**); máy thật (không có; số máy thật là việc của spec 001/FTL); GitHub Actions (chưa push).
- Ảnh "trước" hc-api36 E7 có banner cuộc gọi của hệ thống ở đầu (dựng bằng modem), ảnh "sau" dựng bằng broadcast debug ⇒ vùng cuộn không so sánh được trực tiếp ở API 36; phần so sánh vùng cuộn dựa trên API 34 (cả hai cùng broadcast).
- `Color.kt` đã có bí danh `Risk*`/`Drill*`/`FocusRing`/`SurfaceMuted` chưa màn nào dùng (plan: thêm sẵn cho 020/022/023/028).
