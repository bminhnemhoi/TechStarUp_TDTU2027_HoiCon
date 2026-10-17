# Implementation Plan: Design system v1 (`tokens.json` → Compose + CSS)

**Branch**: `feat/010-design-system` (tách từ `origin/tien-collab-dev` @ `9ae5532`) | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-design-system/spec.md`

## Summary

Thêm `design-system/hoicon/tokens.json` làm nguồn duy nhất. Generator Python chỉ dùng thư viện chuẩn
`scripts/gen-design-tokens.py` (cùng kiểu `gen-bank-apps.py`) sinh `Tokens.kt`, khối màu trong `colors.xml` và
`apps/web/src/app/tokens.css`, có `--check` cho CI. Unittest đo tương phản WCAG cho mọi cặp khai báo (chữ ≥ 7:1, không phải
chữ ≥ 3:1) và kiểm luật 15. App đóng gói Be Vietnam Pro trong `res/font`. Màn hiện có giữ tên biến màu (bí danh) nên gần như
không phải sửa.

**Quyết định kỹ thuật (Opus đề xuất theo ủy quyền của Tiến 15/10/2026, áp dụng mặc định; chạy một mạch, §2.6):**
- **DS1 — Generator Python thuần + tệp sinh ra được commit** (như `gen-bank-apps.py`). Loại: Style Dictionary (thêm thư viện
  npm và Node vào build Android); task Gradle sinh mã (khó chạy cho web, CI phức tạp hơn).
- **DS2 — Font đóng gói trong APK** (`res/font/*.ttf`, ~3 tệp). Loại: downloadable fonts (cần mạng + Play services ⇒ trái
  luật 4 khi offline).
- **DS3 — Mọi chữ ≥ 7:1, kể cả chữ lớn.** CLAUDE.md luật 15 viết phẳng "≥ 7:1", chặt hơn WCAG AAA (chữ lớn chỉ cần 4,5:1). Hệ
  quả: không có chữ trắng trên nền cam; `brand.orange.text` và `brand.green.text` đổi sang biến thể tối đạt 7:1.
- **DS4 — Bảng risk/drill** (đã đo 15/10, công thức WCAG 2.x; giá trị cuối do test quyết, được chỉnh nhẹ nếu cần):

  | Token | `fg` | `bg` | fg/trắng | fg/bg | Hue | Biểu tượng gợi ý (Material Symbols) |
  |---|---|---|---|---|---|---|
  | `risk.low` | `#13603F` | `#F0F9F4` | 7,57 | 7,06 | 154° | `verified_user` + "An toàn" |
  | `risk.medium` | `#7A4A00` | `#FFF8E6` | 7,48 | 7,06 | 36° | `info` + "Cần để ý" |
  | `risk.high` | `#8C2F10` | `#FFF7F2` | 8,30 | 7,84 | 15° | `warning` + "Nguy cơ cao" |
  | `risk.critical` | `#991B1B` | `#FEF2F2` | 8,31 | 7,60 | 0° | `dangerous` + "Rất nguy hiểm" |
  | `drill` | `#4C2A85` | `#F5F0FC` | 10,62 | 9,48 | 262° | `school` + "[DIỄN TẬP]" |
  | `brand.orange.text` | `#8F3A0F` | trắng | 7,55 | — | — | — |
  | `brand.green.text` | `#13603F` | trắng | 7,57 | — | — | — |

  Câu chữ hiển thị ("An toàn"…) chỉ là gợi ý cho spec màn hình; chữ thật nằm trong `strings.xml`/web, **không** trong tokens.json.
  `accent` (viền/mảng) của mỗi mức chỉ cần ≥ 3:1 trên trắng.
- **DS5 — Chỉ nền sáng**, Material 3 `lightColorScheme` làm cầu nối; vai trò M3 không có token thì giữ navy/trắng như `Theme.kt`
  hiện tại (UX-9).
- **DS6 — Không thêm JSON Schema vào `docs/schemas/`**: tokens.json là tệp build nội bộ, không phải hợp đồng API/sự kiện;
  generator tự kiểm cấu trúc bằng thư viện chuẩn (CI harness không có `jsonschema`).

## Technical Context

**Language/Version**: Python 3.12 (script, chỉ thư viện chuẩn) · Kotlin 2.4 (Compose) · CSS (Tailwind v4 `@theme`)

**Primary Dependencies**: không thêm thư viện. Font Be Vietnam Pro (OFL 1.1) là tài nguyên, không phải thư viện

**Storage**: không

**Testing**: `python3 -m unittest discover -s scripts/tests` · `python3 scripts/gen-design-tokens.py --check` ·
`apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug` ·
`pnpm --dir apps/web typecheck` + `lint` + `build` · `scripts/emu-scenario.py --scenario fake_police --runs 10` (AVD 36)

**Target Platform**: Android 10–16 (AVD `hc-api36`, `hc-api34`) · web Next.js

**Project Type**: monorepo — làn A (+ ngoại lệ `apps/web/src/app/{globals,tokens}.css`)

**Performance Goals**: E7 p95 ≤ 3 s trên máy ảo (không đổi); APK +≤ 1 MB

**Constraints**: offline cho E7; không thêm thư viện; không đổi câu chữ; tệp sinh ra tất định

**Scale/Scope**: ~40 token màu, ~8 cỡ chữ, ~10 kích thước; ≥ 20 cặp tương phản

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Nguồn: `.specify/memory/constitution.md`.

| # | Nguyên tắc | Đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn offline ≤ 3 s | **Có** (font E7) | Font trong APK; FR-014 đo lại trên AVD 36 |
| II | Riêng tư, quyền cấm | Không | Không dữ liệu, không quyền mới (không INTERNET cho font) |
| III | LLM chỉ nâng | Không | — |
| IV | Công khai AI, `is_drill` | Gián tiếp | Màu `drill` khác hue ≥ 30° với mọi mức rủi ro (test) ⇒ diễn tập không giống sự cố thật |
| V | Hợp đồng trước | Không (DS6) | tokens.json là nguồn duy nhất; generator kiểm cấu trúc |
| VI | UX người cao tuổi | **Có** | Luật 15 thành kiểm tự động (cỡ chữ, vùng chạm, 7:1); ảnh 200% + `ux-elder-reviewer` |
| VII | Bằng chứng trung thực | **Có** | Tỷ lệ tương phản do test in ra; số máy ảo ghi rõ là máy ảo |
| VIII | Ít code nhất | **Có** | Theo mẫu `gen-bank-apps.py`; giữ tên biến màu cũ ⇒ màn không phải sửa; không thư viện |
| IX | Chặn phát hành | Không | — |

Kết quả: **ĐẠT**.

## Tái sử dụng *(mandatory)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới |
|---|---|---|
| Mẫu generator JSON → Kotlin/XML + CI kiểm lệch | `scripts/gen-bank-apps.py`; bước `gen-bank-apps.py && git diff --exit-code` trong `.github/workflows/android.yml` | **theo mẫu** (thêm `--check` để chạy cả ở máy dev không cần git) |
| Màu thương hiệu đã chốt | `docs/DESIGN-SYSTEM.md`, `ui/theme/Color.kt`, `res/values/colors.xml`, `apps/web/src/app/globals.css` | **chuyển** vào tokens.json; ba tệp sau thành tệp sinh ra / bí danh |
| Thang chữ người cao tuổi | `ui/theme/Type.kt` (`HoiConTypography`: 20–36sp) | **chuyển** cỡ chữ vào token, giữ cấu trúc `Typography` |
| Color scheme M3 | `ui/theme/Theme.kt` (`lightColorScheme`, UX-9) | **giữ**, chỉ đổi nguồn giá trị |
| Font web | `apps/web/src/app/layout.tsx` (`next/font/google` Be Vietnam Pro 400/600/700) | **dùng lại** nguyên |
| Test script Python | `scripts/tests/` (unittest, CI harness) | **thêm** `test_design_tokens.py` |
| Đo E7 trên máy ảo | `scripts/emu-scenario.py`, `scripts/emu-start.sh` | **dùng lại** |
| Gợi ý thiết kế | skill `ui-ux-pro-max` (`scripts/search.py --design-system --persist`) | **tham khảo**, DESIGN-SYSTEM.md thắng |

## Project Structure

### Documentation (this feature)

```text
specs/010-design-system/
├── spec.md · plan.md · research.md · quickstart.md (tasks phase tạo)
├── tasks.md             # /speckit-tasks
└── evidence.md          # phase cuối (mẫu .specify/templates/overrides/evidence-template.md)
```

### Source Code (repository root)

```text
design-system/hoicon/tokens.json                    # MỚI — nguồn duy nhất (FR-001)
design-system/hoicon/MASTER.md (+ pages/ nếu có)    # MỚI — đầu ra ui-ux-pro-max, chỉ tham khảo (FR-011)
design-system/hoicon/fonts/OFL.txt                  # MỚI — giấy phép Be Vietnam Pro (FR-007)
scripts/gen-design-tokens.py                        # MỚI — generator + --check (FR-003, FR-004)
scripts/tests/test_design_tokens.py                 # MỚI — tương phản, luật 15, tất định, hue drill (FR-002, FR-006)
apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/Tokens.kt   # SINH RA
apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/{Color,Type,Theme}.kt  # đọc từ Tokens.kt (FR-008)
apps/android/app/src/main/res/values/colors.xml     # khối BEGIN/END sinh ra
apps/android/app/src/main/res/font/be_vietnam_pro_{regular,semibold,bold}.ttf   # MỚI (FR-007)
apps/web/src/app/tokens.css                         # SINH RA (FR-009)
apps/web/src/app/globals.css                        # @import "./tokens.css"; bỏ giá trị chép tay
.github/workflows/android.yml · harness.yml · web.yml   # --check + paths (FR-010)
docs/DESIGN-SYSTEM.md · docs/ROADMAP.md (dòng P1-05)   # FR-012, FR-015
```

**Structure Decision**: token ở `design-system/hoicon/` đúng đường dẫn DESIGN-SYSTEM.md đã hứa; generator ở `scripts/` cạnh
`gen-bank-apps.py`.

## Thiết kế & trade-off

- **Hình dạng tokens.json** (rút gọn; implement chốt chi tiết, giữ tên khóa ổn định vì Kotlin/CSS phụ thuộc):

  ```json
  {
    "version": "1.0.0",
    "color": {
      "brand":   {"navy": "#1F3A5F", "orange": "#C4561D", "orange_text": "#8F3A0F", "green": "#1E7B53", "green_text": "#13603F"},
      "surface": {"base": "#FFFFFF", "muted": "#F4F6F9"},
      "text":    {"primary": "#1F3A5F", "on_primary": "#FFFFFF"},
      "risk":    {"low": {"fg": "…", "bg": "…", "accent": "…"}, "medium": {…}, "high": {…}, "critical": {…}},
      "drill":   {"fg": "#4C2A85", "bg": "#F5F0FC", "accent": "…"},
      "focus":   {"ring": "…"}
    },
    "font": {"family": "Be Vietnam Pro", "weights": [400, 600, 700]},
    "type": {"display": {"size_sp": 36, "line_sp": 44, "weight": 700}, "body": {"size_sp": 22, "line_sp": 32, "weight": 400},
             "body_small": {"size_sp": 20, …}, "button": {"size_sp": 24, "line_sp": 30, "weight": 700}, …},
    "size":   {"touch_min_dp": 64, "space_dp": [4, 8, 12, 16, 24, 32], "radius_dp": {"button": 16, "card": 20}},
    "motion": {"short_ms": 150, "medium_ms": 250, "reduced_ms": 0},
    "contrast_pairs": [{"fg": "text.primary", "bg": "surface.base", "kind": "text", "use": "chữ thân"}, …]
  }
  ```

  Tên khóa dùng `snake_case` (an toàn cho cả Kotlin lẫn CSS). Cặp tham chiếu token bằng đường dẫn, không lặp hex.
- **Đầu ra Kotlin** (`Tokens.kt`, đầu tệp ghi "sinh bởi scripts/gen-design-tokens.py, không sửa tay"):
  `object HoiConTokens { object Color { val BrandNavy = Color(0xFF1F3A5F) … } object Type { val BodySp = 22 … } object Size { val TouchMinDp = 64 … } }`.
  `Color.kt` giữ `val BrandNavy = HoiConTokens.Color.BrandNavy` … (bí danh) ⇒ `SafePauseScreen.kt`, `PermissionsScreen.kt`,
  `MainActivity.kt` không phải sửa. `Type.kt` dùng `FontFamily(Font(R.font.be_vietnam_pro_regular, W400), …)` + cỡ từ token.
- **Đầu ra CSS** (`tokens.css`): `@theme inline { --color-brand-navy: #1f3a5f; --color-risk-high-fg: …; --text-body: 1.375rem; … }`.
  Giữ tên biến đang dùng ở `globals.css` (`--color-background`, `--color-foreground`, `--color-brand-*`, `--font-sans`). Cỡ chữ
  web đổi sp → rem theo 1sp = 1px/16 ⇒ 22sp = 1.375rem (web không có luật sp; ghi chú trong DESIGN-SYSTEM.md).
- **Kiểm trong generator (FR-004)**: hex `^#[0-9A-Fa-f]{6}$`; khóa `^[a-z][a-z0-9_]*$`; `type.body*.size_sp ≥ 20`,
  `type.button.size_sp ≥ 24` và `weight ≥ 600`; `size.touch_min_dp ≥ 64`; mọi cặp tham chiếu token có thật. Sai ⇒ exit 2,
  thông điệp tiếng Việt, không ghi tệp.
- **Unittest (`test_design_tokens.py`)**: (1) tương phản từng cặp + in bảng; (2) có đủ cặp bắt buộc: `text.primary`/`surface.*`,
  `text.on_primary`/`brand.navy`, `risk.*.fg` trên trắng và trên `bg` của chính nó, `drill.fg` tương tự, `brand.*_text`/trắng,
  `brand.orange`/`brand.green` dạng `non_text`; (3) hue `drill.fg` cách mọi `risk.*.fg` ≥ 30°; (4) chạy generator vào thư mục
  tạm hai lần ⇒ cùng sha256; (5) tokens.json hỏng (hex sai, chữ 18sp, chạm 48dp) ⇒ exit 2; (6) `--check` phát hiện lệch.
  Generator nhận `--out-root` để test ghi vào thư mục tạm (không đụng cây làm việc).
- **Font**: tải 3 tệp TTF từ `github.com/google/fonts` (thư mục `ofl/bevietnampro`) ở một commit cố định; tên tài nguyên Android
  phải là chữ thường + gạch dưới. Ghi URL commit + sha256 vào evidence. Kiểm APK trước/sau (SC-005).
- **CI**: `android.yml` thêm bước `python3 ../../scripts/gen-design-tokens.py --check` cạnh bước bank apps; bộ lọc `paths` thêm
  `design-system/**` + `scripts/gen-design-tokens.py`. `harness.yml` đã chạy `scripts/tests` (thêm `design-system/**` vào
  `paths`). `web.yml` thêm `design-system/**` vào `paths` (tokens.css đổi theo).
- **Ảnh chụp (FR-013)**: chụp TRƯỚC khi đổi font (nhánh hiện tại) và SAU; dùng `scripts/emu-start.sh` + `adb shell settings
  put system font_scale 2.0`; ảnh lưu ngoài repo (`~/hoicon-evidence/010-design-system/`), evidence ghi đường dẫn + mô tả.
- **Rủi ro**: (a) Be Vietnam Pro ở 200% rộng hơn Roboto ⇒ dễ tràn chữ trên E7: kiểm ảnh, sửa bằng `softWrap`/cuộn sẵn có, không
  giảm cỡ chữ; (b) `colors.xml` còn được `themes.xml`/manifest dùng ⇒ giữ tên `brand_navy`, `brand_orange`, `surface_white`,
  `navy_40`; (c) máy ảo không đủ RAM khi chạy Gradle + emulator cùng lúc ⇒ build trước, rồi mới bật máy ảo (MASTER-PLAN §5 luật 3).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
