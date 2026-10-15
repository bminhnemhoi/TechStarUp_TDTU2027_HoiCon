# Design system HỏiCon

> Trạng thái: **v1** (P1-05, spec [`specs/010-design-system/`](../specs/010-design-system/), 15/10/2026).
> **File này thắng mọi gợi ý của plugin thiết kế** (đầu ra `ui-ux-pro-max` chỉ để tham khảo: `design-system/hoicon/MASTER.md`,
> đối chiếu trong `specs/010-design-system/research.md` R2).

**Nguồn sự thật duy nhất: [`design-system/hoicon/tokens.json`](../design-system/hoicon/tokens.json)** (phiên bản `1.0.0`).
Generator `scripts/gen-design-tokens.py` sinh ra ba tệp — **không sửa tay**:

| Tệp sinh ra | Dùng cho |
|---|---|
| `apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/Tokens.kt` | `object HoiConTokens` (màu, cỡ chữ, kích thước, chuyển động); `Color.kt`/`Type.kt` là bí danh |
| khối `BEGIN/END design_tokens` trong `apps/android/app/src/main/res/values/colors.xml` | màu cho layout XML của màn dừng an toàn (E7) |
| `apps/web/src/app/tokens.css` | Tailwind v4 `@theme inline` + biến chuyển động |

## Đổi một token (quy trình)

1. Sửa `design-system/hoicon/tokens.json` (cặp chữ/nền mới ⇒ thêm vào `contrast_pairs`).
2. `python3 scripts/gen-design-tokens.py` — từ chối (exit 2) nếu vi phạm luật 15 (chữ thân < 20sp, nhãn nút chính < 24sp hoặc
   không đậm, vùng chạm < 64dp, hex sai, tên khóa sai).
3. `python3 -m unittest discover -s scripts/tests` — in tỷ lệ tương phản từng cặp; chữ < 7:1 hoặc không-phải-chữ < 3:1 ⇒ đỏ.
4. Build (`:app:assembleDebug`, `pnpm --dir apps/web build`) và **chụp ảnh E7 + màn quyền ở 100% và 200%** (AVD `hc-api36`,
   `hc-api34`).
CI chạy `gen-design-tokens.py --check` (quên bước 2 ⇒ đỏ) và unittest.

## Màu thương hiệu (đã chốt)
| Token | Giá trị | Tương phản trên trắng | Dùng |
|---|---|---|---|
| `brand.navy` | `#1F3A5F` | 11,48 | chữ chính, header, nền nút chính |
| `brand.orange` | `#C4561D` | 4,47 | **không phải chữ**: biểu tượng, viền, mảng (≥ 3:1) |
| `brand.orange_text` | `#843410` | 8,47 (trên `surface.muted`: 7,82) | chữ cam |
| `brand.green` | `#1E7B53` | 5,23 | **không phải chữ**: biểu tượng, viền, mảng |
| `brand.green_text` | `#115A3B` | 8,24 (trên `surface.muted`: 7,61) | chữ xanh lá |
| `surface.base` / `surface.muted` | `#FFFFFF` / `#F4F6F9` | — | nền |
| `text.primary` / `text.on_primary` | `#1F3A5F` / `#FFFFFF` | 11,48 | chữ thân / chữ trên nền navy |
| `focus.ring` | `#005FCC` | 5,98 | vòng focus bàn phím/TalkBack |

**Luật chữ trên nền cam/xanh lá:** CLAUDE.md luật 15 viết phẳng "tương phản ≥ 7:1" (chặt hơn WCAG AAA, vốn cho chữ lớn 4,5:1)
⇒ **không có chữ trắng trên nền cam hoặc xanh lá** (4,47:1 và 5,23:1). Nút chính dùng nền navy. Chữ cam/xanh lá dùng biến thể
`*_text`. `brand.orange_text` cũ `#B04A17` (5,47:1) bị thay vì không đạt 7:1.

## Màu rủi ro và diễn tập — luôn kèm biểu tượng + chữ
Màu không bao giờ là cách duy nhất báo mức rủi ro (người mù màu, màn nắng): mỗi mức đi với **biểu tượng + từ**. Câu chữ thật
nằm ở `strings.xml`/web, không nằm trong tokens.json; cột cuối chỉ là gợi ý cho spec màn hình.

| Token | `fg` (chữ/biểu tượng) | `bg` (nền nhạt) | `accent` (viền/mảng) | fg/trắng | fg/bg | Biểu tượng gợi ý (Material Symbols) |
|---|---|---|---|---|---|---|
| `risk.low` | `#13603F` | `#F0F9F4` | `#1E7B53` | 7,57 | 7,06 | `verified_user` + "An toàn" |
| `risk.medium` | `#7A4A00` | `#FFF8E6` | `#A66300` | 7,48 | 7,06 | `info` + "Cần để ý" |
| `risk.high` | `#8C2F10` | `#FFF7F2` | `#C4561D` | 8,30 | 7,84 | `warning` + "Nguy cơ cao" |
| `risk.critical` | `#991B1B` | `#FEF2F2` | `#DC2626` | 8,31 | 7,60 | `dangerous` + "Rất nguy hiểm" |
| `drill` | `#4C2A85` | `#F5F0FC` | `#7C4DBA` | 10,62 | 9,48 | `school` + "[DIỄN TẬP]" |

`accent` chỉ dùng cho viền/mảng (≥ 3:1 trên trắng), không dùng cho chữ. **Màu diễn tập (tím, hue 262°) cách xa mọi mức rủi ro
(≥ 30°; test kiểm)** để diễn tập không bao giờ trông như sự cố thật (CLAUDE.md luật 8); diễn tập vẫn phải mang nhãn "[DIỄN TẬP]".

Mọi tỷ lệ trên do `scripts/tests/test_design_tokens.py` đo bằng công thức độ sáng tương đối WCAG 2.x (26 cặp khai báo).

## Font, cỡ chữ, kích thước
- **Font: Be Vietnam Pro** 400/600/700 (SIL OFL 1.1; giấy phép ở `design-system/hoicon/fonts/OFL.txt`).
  Android: **đóng gói trong APK** (`res/font/`) — không dùng downloadable fonts vì màn dừng an toàn phải hiện đủ chữ khi offline
  (CLAUDE.md luật 4). Màn E7 dùng layout View nên font được đặt ở theme (`Theme.HoiCon` → `@font/be_vietnam_pro`); Compose dùng cùng ba
  tệp qua `Type.kt`. Web: `next/font/google` (đã có ở `layout.tsx`).
- Cỡ chữ (sp; web quy đổi 1sp = 1/16 rem, web không có luật sp): `display` 36/44 · `headline` 28/36 · `title` 24/32 ·
  `body_large` 22/32 · `body` 20/28 · `button` 24/30 đậm 700. Chữ luôn dùng `sp` để theo cỡ chữ hệ thống (dùng được ở 200%).
- Kích thước: vùng chạm tối thiểu **64dp**; khoảng cách 4/8/12/16/24/32dp; bo góc nút 16dp, thẻ 20dp.
- Chuyển động: 150/250 ms; khi bật "giảm chuyển động" của hệ thống ⇒ 0 ms (web: `prefers-reduced-motion`).
- **Chế độ tối: không làm ở v1** (app người cao tuổi chỉ nền sáng). Ngoài phạm vi: component library dùng chung, trang xem token,
  token cho `:demobank` (app ngân hàng giả cố ý không mang thương hiệu HỏiCon).

## Chuẩn cho người cao tuổi (bắt buộc)
Chữ ≥ 20sp · nút chính ≥ 24sp đậm · vùng chạm ≥ 64dp · ≤ 2 hành động chính/màn · tương phản ≥ 7:1 · dùng được ở cỡ chữ
200% · màn quan trọng tự đọc to · nhãn TalkBack tiếng Việt · không đếm ngược gây hoảng.

**Nút bấm là chính, giọng nói chỉ bổ trợ.** Mọi hành động trả lời (có / không / không biết, gọi cho con, tiếp tục) phải làm
được bằng nút bấm; giọng nói (đọc to, và nếu sau này có: trả lời bằng giọng) chỉ là lớp thêm, không bao giờ là cách duy nhất —
bảo vệ người nói giọng địa phương, khó phát âm, nơi ồn, máy không có bộ nhận dạng vi-VN. Số đo và quy tắc quyết định:
`docs/spikes/P1-S5-giong-noi.md` (spec 004; trên ảnh máy ảo `google_apis_playstore`: nhận dạng vi-VN trên máy có ở API 36, không có ở API 34 — chưa đo máy thật).

## Màn hình app (E1–E12)
E1 Chào mừng (công khai AI) · E2 Ghép đôi · E3 Xin quyền (mỗi quyền một màn) · E4 Liên hệ tin cậy · E5 Thử giọng ·
E6 "Đang bảo vệ" · **E7 Dừng an toàn** · E8 Câu hỏi nhanh · E9 Chờ con · E10 Kết quả tra cứu · E11 Diễn tập ·
E12 Cài đặt & quyền riêng tư. Chi tiết luồng: kế hoạch đã duyệt §5; mỗi màn làm bằng skill `ui-screen`.

## Zalo (Z1–Z8) & Web
Xem kế hoạch §5; mẫu tin Zalo đặt ở `backend/src/hoicon/integrations/zalo/templates/` (mở đầu "Đây là trợ lý AI HỏiCon").
