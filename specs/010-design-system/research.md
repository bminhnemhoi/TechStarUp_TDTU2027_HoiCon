# Research: Design system v1

## R1 — Kiểm tương phản token hiện có (15/10/2026, công thức WCAG 2.x, nền trắng `#FFFFFF`)

| Token (DESIGN-SYSTEM.md / `Color.kt`) | Giá trị | Tỷ lệ | Luật 15 (chữ ≥ 7:1) | Xử lý trong 010 |
|---|---|---|---|---|
| `brand.navy` | `#1F3A5F` | 11,48 | đạt | giữ |
| `brand.orange` | `#C4561D` | 4,47 | **không đạt** cho chữ | chỉ dùng không-phải-chữ (biểu tượng E7 đang tint cam: ≥ 3:1, đạt) |
| `brand.orange.text` | `#B04A17` | 5,47 | **không đạt** | đổi sang `#8F3A0F` (7,55) |
| `brand.green` | `#1E7B53` | 5,23 | **không đạt** cho chữ | chỉ dùng không-phải-chữ; chữ dùng `brand.green_text` `#13603F` (7,57) |

Script đo: hàm độ sáng tương đối sRGB → `(L1 + 0,05) / (L2 + 0,05)`. Unittest của spec này dùng đúng công thức đó.

Kết luận: DESIGN-SYSTEM.md ghi `brand.orange.text` cho "chữ cam cỡ nhỏ" nhưng giá trị chỉ đạt AA, mâu thuẫn CLAUDE.md luật 15
(CLAUDE.md thắng) ⇒ DS3 trong plan.md.

## R2 — Đầu ra `ui-ux-pro-max` so với DESIGN-SYSTEM.md (15/10/2026)

Lệnh: `python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "elderly-friendly fintech safety family protection" --design-system --persist -p "HoiCon"`
⇒ `design-system/hoicon/MASTER.md` (chỉ tham khảo; DESIGN-SYSTEM.md thắng).

| Hạng mục | Gợi ý plugin | DESIGN-SYSTEM.md / spec | Chọn |
|---|---|---|---|
| Phong cách | "Accessible & Ethical" (WCAG AAA, chữ lớn, focus rõ) | chuẩn người cao tuổi luật 15 | giữ DESIGN-SYSTEM.md; trùng tinh thần |
| Màu chính | `#2563EB` xanh dương, phụ `#059669`, CTA `#D97706` | navy `#1F3A5F`, cam `#C4561D`, xanh lá `#1E7B53` | DESIGN-SYSTEM.md (màu đã chốt; gợi ý không đạt 7:1 cho chữ, CTA `#D97706` trên trắng ≈ 3,2:1) |
| Phông | Baloo 2 / Comic Neue ("kids, playful") | Be Vietnam Pro (dấu tiếng Việt rõ) | DESIGN-SYSTEM.md (gợi ý nhắm trẻ em, không hợp) |
| Cỡ chữ / vùng chạm | chữ ≥ 16px, chạm 44×44 | chữ ≥ 20sp, nút ≥ 24sp, chạm ≥ 64dp | DESIGN-SYSTEM.md (chặt hơn) |
| Chế độ tối | hỗ trợ Light + Dark | chỉ nền sáng v1 (DS5) | DESIGN-SYSTEM.md |
| Mẫu trang | "Marketplace / Directory" | không áp dụng (app bảo vệ, không phải sàn) | bỏ |
| Chuyển động | 150–300 ms, tôn trọng giảm chuyển động | `motion.short/medium`, `reduced_ms = 0` | trùng ⇒ giữ; thêm vào tokens.json |
| Focus | vòng 3–4 px | token `focus.ring` | trùng ⇒ giữ |
| Biểu tượng | SVG (Heroicons/Lucide), không emoji | Material Symbols (Android) | giữ Material Symbols; cùng nguyên tắc không emoji |
| Tránh | chữ nhỏ, điều hướng phức tạp, gradient tím/hồng AI | tương tự (≤ 2 hành động chính/màn) | trùng |

Kết luận: plugin cho đầu vào chung chung (không biết người cao tuổi Việt Nam); không có gợi ý nào được nhận ngoài các mục
"trùng" ở trên. Không cần đổi DESIGN-SYSTEM.md theo plugin.
