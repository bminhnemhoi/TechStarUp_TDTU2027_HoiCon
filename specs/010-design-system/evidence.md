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

## E7 biến thể "điều khiển từ xa" (R5) — Làn A Wave 2, 21/10/2026 (T016 vẫn ☑; MỘT PHẦN, xem "Chưa kiểm")

**Cách dựng.** Máy ảo không có app điều khiển từ xa, nên `:demobank` có thể dựng với `-PdemobankApplicationId=com.anydesk.anydeskandroid` (bản giả, chỉ cài lên máy ảo, không phát hành); cuộc gọi số lạ giả
(`adb emu gsm call`) rồi mở gói đó ⇒ luật R5 ⇒ E7 biến thể `REMOTE_CONTROL`. `emu-scenario.py` nhận `HC_DEMOBANK_PACKAGE` để đổi gói.
Ảnh: `~/hoicon-evidence/010-design-system/w2/` (hc-api36, 1080×2400) và `w2-api34/` (hc-api34, 1080×2340), 100% và 200%.

**Thấy trên ảnh và đã sửa (`SafePauseScreen.kt`, chỉ từ chữ ≥ 150%):**
1. Câu "Đây là trợ lý AI HỏiCon" trải cả chiều ngang, "Nghe lại" xuống ngay dưới (viền xanh đậm cùng kiểu các nút khác).
2. Nhãn mức rủi ro dùng cỡ nhỏ hơn; tiêu đề câu hỏi điều khiển từ xa 24sp (≥ 20sp).
3. Dòng "Kéo xuống đọc tiếp ↓" trên nền đặc khi còn chữ phía dưới (lớp mờ một mình dễ bị đọc là "chữ bị tắt").
4. Sau `ux-elder-reviewer` lượt 3 (xem dưới): ở ≥ 150% thứ tự là **câu AI → tiêu đề → nhãn mức rủi ro → "Nghe lại" → thân chữ**, để thông điệp chính nằm ngay đầu vùng đọc.
Giữ nguyên: 3 nút ghim (≥ 64dp, ≤ 2 hành động chính), "Vẫn tiếp tục" giữ 3 giây, lời của mọi nút và đoạn chữ.

**`ux-elder-reviewer`.** Lượt 1 (hc-api36): 0 Chặn, 0 Cao; 4 Trung bình/Thấp (chỉ thấy ≈ 1 dòng thân ở 200%; ảnh 100% chụp nhầm cuối trang ⇒ đã chụp lại đầu và cuối).
Lượt 3 (thêm hc-api34): 0 Chặn; **1 Cao chỉ ở hc-api34, 200%**: tiêu đề bị cắt ở dòng 3 vì phần đầu (câu AI + "Nghe lại" + nhãn) chiếm hơn 1/3 vùng đọc.
Đã sửa bằng mục 4. Ảnh sau sửa (hc-api34, 200%, `w2-api34/e7-remote-200-a.png`): tiêu đề hiện đủ 4 dòng "…của bác?", rồi nhãn mức rủi ro, rồi dòng "Kéo xuống đọc tiếp ↓".
**Chưa có reviewer đọc lại ảnh sau mục 4** ⇒ chưa thể ghi "0 High" cho cả hai máy.
Chưa đổi (đề xuất của reviewer, cần Tiến/Minh vì đụng lời): rút tiêu đề còn ≈ 8 từ ("Đừng để người lạ điều khiển điện thoại của bác"); đổi "Kẻ gian" thành "Người xấu"; nói đúng điều máy biết ("Bác vừa mở ứng dụng điều khiển từ xa khi đang nghe số lạ").

**Hạn E7 (máy ảo, `emu-scenario.py --scenario fake_police --runs 10`, chữ 100%):**
- hc-api36 (21/10, bản có gợi ý cuộn): lần 1 có một lần cây UI không thấy màn E7 nên script báo TRƯỢT dù 10/10 có mốc hiện SafePause; lần 2: **10/10 ĐẠT**, phát hiện p50/p95 418/945 ms, SafePause **p50 875 / p95 1 440 ms** (≤ 3 000).
- hc-api34 sau khởi động nguội (bản trước khi đổi thứ tự phần đầu ở mục 4): **10/10 ĐẠT**, SafePause **p50 670 / p95 1 957 ms**.
- hc-api34 với bản **cuối cùng** (có mục 4): 10/10 lần không có mốc nào (`Telecom không thấy cuộc gọi đến`): máy ảo, không phải ứng dụng; trước đó chính AVD này cũng trượt 10/10 theo cách y hệt cho tới khi khởi động nguội, và chạy tay `gsm call` vẫn
  đổ chuông. Đã khởi động lại máy ảo 2 lần ⇒ dừng theo luật, **chưa có số đo cho bản cuối trên hc-api34**. Mục 4 chỉ đổi thứ tự hiển thị, không đụng cảm biến.
- Số p95 dao động nhiều giữa các lượt; không kết luận về máy thật.

## Còn tồn / hoãn có chủ đích

- **BLOCKED — FR-013 "không còn mục High"**: E7 ở 200% trên AVD API 34 (1080×2340): hàng "Đây là trợ lý AI HỏiCon + Nghe lại" ép chữ công khai AI thành 3 dòng; thanh nút ghim chiếm ~37% màn (trước đổi font ~31%); vùng cuộn còn ~2 dòng thân, ~1 dòng khi giữ nút (`after-hc-api34-e7-200-giu-1s.png`). Đây là bố cục E7 có sẵn, nặng thêm do font rộng hơn; sửa cần thiết kế riêng cho `fontScale ≥ 1,5` ⇒ P2-05 (E7), không mở rộng spec này. Cũng ghi ở ROADMAP "Ghi chú".
- Chưa kiểm: hc-api29 (font XML chạy từ API 26, minSdk 29 đủ theo tài liệu, **chưa đo**); máy thật (không có; số máy thật là việc của spec 001/FTL); GitHub Actions (chưa push).
- Ảnh "trước" hc-api36 E7 có banner cuộc gọi của hệ thống ở đầu (dựng bằng modem), ảnh "sau" dựng bằng broadcast debug ⇒ vùng cuộn không so sánh được trực tiếp ở API 36; phần so sánh vùng cuộn dựa trên API 34 (cả hai cùng broadcast).
- `Color.kt` đã có bí danh `Risk*`/`Drill*`/`FocusRing`/`SurfaceMuted` chưa màn nào dùng (plan: thêm sẵn cho 020/022/023/028).

## Wave 3 (22/10/2026) — T028: câu chữ E7 "điều khiển từ xa" + ảnh + reviewer (đóng cả T027)

**Chuỗi đã đổi** (`strings.xml`, giữ khóa, không đổi bố cục ngoài gợi ý cuộn dưới): `pause_title_remote` = "Bác ơi, khoan cho người lạ điều khiển điện thoại";
`pause_body_remote` = "Ứng dụng này cho người khác nhìn thấy và điều khiển điện thoại của bác, kể cả ứng dụng ngân hàng. Công an, ngân hàng không bao giờ bảo bác
cài ứng dụng này. Bác cúp máy, đóng ứng dụng đó (như AnyDesk, TeamViewer), rồi bấm Hỏi con." Đã bỏ "Kẻ gian". Không test/ảnh nào nhắc chuỗi cũ.

**Sửa bố cục (1 vòng).** Vòng 1 của `ux-elder-reviewer` (8/10 ảnh): 0 Chặn, **1 Cao** — ở 100% câu hành động cuối ("đóng ứng dụng đó… rồi bấm Hỏi con") bị mờ và cắt, không có
gợi ý cuộn (dải "Kéo xuống đọc tiếp ↓" chỉ hiện từ chữ ≥ 150%). Thân bài mới dài hơn nên tràn cả ở 100%. Sửa: `SafePauseScreen.kt` hiện dải gợi ý khi
`large || kind == PauseKind.REMOTE_CONTROL` (biến thể ngân hàng ở 100% không đổi). Vòng 2: **mục Cao đã hết, 0 Chặn, 0 Cao mới.** Còn Trung bình: (1) 200% trên hc-api34 vùng
đọc đầu trang chưa hiện dòng thân nào (ba nút ghim chiếm ≈ 40% màn); (2) lớp mờ cắt đáy nút "Nghe lại" ở 200% hc-api34. Thấp: "AnyDesk, TeamViewer" là tên tiếng Anh (giữ, vì có "như").
Vòng 1 còn đề xuất tách thân bài thành 2 việc có đánh số và đổi nút "Vẫn tiếp tục" thành nút chữ: đụng chữ/bố cục ngoài task ⇒ **cần Opus** quyết.

**Ảnh** `~/hoicon-evidence/010-design-system/w3/e7-remote-{36,34}-{100,200}-*.png` (a = đầu màn; b–d = cuộn dần ở 200%). Dựng bằng `:demobank` mang gói giả
`com.anydesk.anydeskandroid` (chỉ máy ảo) và cuộc gọi giả.

**`fake_police` trên bản cuối** (số máy ảo, không kết luận về máy thật; mỗi dòng n = 10, 10/10 hiện SafePause, ngưỡng ≤ 3000 ms ĐẠT):
| AVD | Biến thể | Phát hiện p50 / p95 (ms) | SafePause p50 / p95 (ms) |
|---|---|---|---|
| hc-api36 | điều khiển từ xa | 304 / 989 | 615 / 1091 |
| hc-api36 | ngân hàng | 282 / 762 | 784 / 1270 |
| hc-api34 (khởi động nguội) | điều khiển từ xa | 465 / 846 | 914 / 1264 |
| hc-api34 (khởi động nguội) | ngân hàng | 424 / 626 | 816 / 1082 |
Đường dừng an toàn không đổi (chỉ chữ và một dòng gợi ý). Lần trượt "Telecom không thấy cuộc gọi" của hc-api34 ở Wave 2 **không** tái hiện sau `emu-start.sh --cold`.

**Kết luận T028/T027: ĐẠT, "0 High" cho ảnh E7 điều khiển từ xa** (reviewer vòng 2 đọc lại). Tick T027 và T028.

## Wave 5 (23/10/2026) — debug: hc-api34 "Telecom không thấy cuộc gọi" (CHƯA tái hiện, CHƯA xác định nguyên nhân)

**Hiện tượng (Wave 2, 21/10):** `emu-scenario.py --scenario fake_police` trên hc-api34 báo `Telecom không thấy cuộc gọi đến (lỗi modem giả lập)` 10/10 cho tới khi khởi động lại máy ảo (`emu-start.sh --cold`).

**Đã làm trong Wave 5 (đọc mã, không chạy máy ảo):** tìm nguyên nhân khả dĩ trong chính `emu-scenario.py` (`ring`, `flush_modem`, `screening_diagnosis`). `ring()` coi cuộc gọi là "đổ chuông" khi
`dumpsys telephony.registry` có `mCallState=1`; nhưng thông báo trên chỉ in khi log Telecom **không** có `IncomingCallFilterGraph`, tức là lớp Telecom chưa nhận cuộc gọi dù registry đã thấy đổ chuông.
Giả thuyết còn lại, theo thứ tự dễ kiểm: (H1) ngay sau khởi động nguội modem giả chưa đăng ký mạng (`gsm.sim.state`/`mVoiceRegState` chưa `IN_SERVICE`) trong khi `sys.boot_completed` đã = 1;
(H2) vai trò `CALL_SCREENING` không còn do Lính gác giữ (sau `pm clear`/cài lại); (H3) trạng thái modem giả treo sau nhiều cuộc gọi tay (`flush_modem` đã có để xử lý trường hợp này).
Wave 3 và Wave 4 khởi động nguội hc-api34 thêm ba lần: cả ba lần `fake_police` 10/10 (không tái hiện), nên H1/H3 không bị loại và cũng chưa được xác nhận.

**Sửa cho dễ chẩn đoán và phòng ngừa (`scripts/emu-scenario.py`, chưa chạy được 10/10 sau cold boot — xem dưới):**
- `radio_ready()` (SIM `LOADED`/`READY` và `mVoiceRegState=0(IN_SERVICE)`), `role_held()`, `ensure_ready()` chờ modem tối đa 120 s và cấp lại vai trò nếu mất; gọi ở đầu `main()` cho mọi kịch bản.
- Thông báo `Telecom không thấy cuộc gọi đến` giờ kèm `modem IN_SERVICE=… · vai trò do Lính gác giữ=…`, để lần tới biết ngay H1 hay H2.
- Kiểm tay chỉ-đọc trên hc-api36 đang chạy: `radio_ready()` = True, `role_held()` = True (đúng với máy khỏe).

**Chưa làm được (chặn):** đo lại "10/10 sau cold boot" trên hc-api36 và hc-api34. hc-api36 đang chạy bộ đo heartbeat 032 T011 (Wave 4, 23/10 00:42 → ≈ 10:45 +07; khởi động lại máy ảo sẽ làm hỏng phép đo), và máy chỉ đủ RAM cho một AVD.
Việc kế tiếp (sau ≈ 10:45): `bash scripts/emu-start.sh hc-api34 --headless --cold` rồi chạy ngay `fake_police --runs 10` (chưa chờ gì) để thử H1; nếu trượt, dùng thông báo mới để phân biệt H1/H2; lặp lại trên hc-api36. Kết luận "hạn chế AVD" hay "lỗi app" **chưa có**.

## Wave 6 (làn A, 24/10/2026) — T029 và chẩn đoán hc-api34

**Nguồn: máy ảo (hc-api36 = API 36, hc-api34 = API 34), bản debug, máy ảo ≠ máy thật.**

### T029 — E7 điều khiển từ xa (đã tick)
- Mã: `SafePauseScreen.kt` + `strings.xml` (chuỗi chốt Wave 4: `pause_body_remote` một đoạn + mảng `pause_steps_remote` hiện "1. …/2. …"; "Vẫn tiếp tục" viền 1 dp, vùng chạm ≥ 64 dp, vẫn giữ 3 s). `PauseRemoteStringsTest` đỏ → xanh. `:rules:test :app:testDebugUnitTest :app:lintDebug` xanh (gồm `ConsentManifestPinTest`).
- `fake_police --runs 10` hc-api36: lần 1 (ngay sau cài lại APK, tiến trình nguội) 10/10 hiện E7 nhưng SafePause p95 3414 ms ⇒ TRƯỢT ngưỡng 3000 ms vì 1 lượt đầu (3414 ms); lần 2 ngay sau đó: **10/10, SafePause p50 1160 / p95 1467 ms ⇒ ĐẠT**. Biến thể điều khiển từ xa (`HC_DEMOBANK_PACKAGE=com.anydesk.anydeskandroid`, n = 3): 3/3, p95 1888 ms.
- Ảnh: `~/hoicon-evidence/010-design-system/w4r/` — `api36-` và `api34-{remote,bank}-{100,200}-{top,scroll1,scroll2,scroll3}.png` (32 ảnh, có cuộn thật). Thư mục `w4/` là lượt đầu vuốt hỏng (không cuộn), bỏ.
- `ux-elder-reviewer` vòng 1 (ảnh w4/): 1 Chặn = thiếu bằng chứng (ảnh không cuộn) ⇒ chụp lại. **Vòng 2 (w4r/, 12 ảnh api36 đã xem): nhóm lỗi bản dựng 0 Chặn / 0 Cao / 1 Trung bình / 3 Thấp.** Trung bình: thứ tự nhãn/tiêu đề/"Nghe lại" đổi giữa 100% và 200% (bố cục thích ứng có từ trước, không do T029). Thấp: danh sách không thụt lề treo; mép trên vùng cuộn cắt chữ không mờ dần; nhãn phụ "Giữ ngón tay 3 giây" ↔ "Giữ 3 giây" theo cỡ chữ. Ảnh api34: chỉ tôi xem (cùng bố cục), reviewer chưa đọc riêng.
- **Cần Opus/Minh (đề xuất ngoài quyết định đã chốt, không làm):** (1) đặt hành động trước lý do hoặc rút thân bài để bước 1–2 lên trên mép gập (200%: phải vuốt ~2 lần mới thấy bước 1–2; nút Hỏi con ghim + tự đọc to giảm nhẹ); (2) "Hủy giao dịch" ở biến thể ngân hàng chỉ đưa về màn hình chính — cân nhắc "Về màn hình chính" cả hai biến thể; (3) "Kéo xuống đọc tiếp ↓" dễ hiểu nhầm hướng (đề xuất "Vuốt lên…", là chữ nên cần duyệt).

### Chẩn đoán hc-api34 "Telecom không thấy cuộc gọi" (CHƯA kết luận)
- Khởi động nguội hc-api34 hai lần liên tiếp (`emu-start.sh hc-api34 --headless --cold`), chạy `fake_police --runs 10` ngay sau khi sẵn sàng:
  - **Lần 1:** chỉ 4/10 hiện SafePause. 5 lượt "cuộc gọi giả KHÔNG đổ chuông (lỗi môi trường)" + 1 lượt kẹt "máy ảo vẫn còn cuộc gọi treo"; lượt qua đầu tiên SafePause 7998 ms (watchdog dự phòng bật), lượt kế 3410 ms, rồi 1306/881 ms. (Lỗi nằm ở bước đổ chuông của modem giả, TRƯỚC khi tới Telecom; chưa có chẩn đoán kèm vì thông báo mới thêm sau lần này.)
  - **Lần chạy lại ngay (không khởi động lại): 10/10 ĐẠT**, SafePause p50 554 / p95 660 ms.
  - **Lần 2 (cold boot thứ hai, đã có chẩn đoán mới):** 10/10 hiện E7, không có lượt không-đổ-chuông; lượt đầu 3907 ms (p95 3907 ⇒ TRƯỢT ngưỡng 3000 ms vì lượt đầu), 9 lượt sau 315–1194 ms.
- **Kết luận có thể nói:** (a) triệu chứng "modem giả không đổ chuông / Telecom không thấy cuộc gọi" tái hiện **1/2** lần cold boot, xảy ra ở vài lượt đầu rồi tự hết ⇒ phù hợp H1 (modem chưa sẵn sàng sau cold boot) nhưng **không xác nhận** (lần 2 không tái hiện; chưa có `gsm list`/trạng thái modem của lần 1); (b) lượt đầu sau cold boot/cài lại luôn chậm: 7998 ms (hc-api34 lần 1), 3907 ms (hc-api34 lần 2), 3414 ms (hc-api36 sau cài lại) — tiến trình nguội + bản debug không có baseline profile; từ lượt thứ hai ≤ 1.5 s. Kết luận "hạn chế AVD" hay "lỗi app" **vẫn chưa có**; số máy thật mới quyết định (gate 012/T018: onScreenCall p95 ≤ 214 ms trên bản `demo`).
- `scripts/emu-scenario.py` `ring()` nay in kèm chẩn đoán khi cuộc gọi không đổ chuông: trả lời console modem, `gsm list` (số đã che), `call_state`, modem IN_SERVICE, vai trò — để lần tới phân biệt được.
- **Đề xuất Opus:** khi đo ngưỡng "E7 ≤ 3 s" tại gian/gate, bỏ lượt khởi động nguội đầu hoặc ghi riêng "lượt đầu sau cold boot"; không tuyên bố p95 ≤ 3 s gộp cả lượt đầu cho debug AVD.
