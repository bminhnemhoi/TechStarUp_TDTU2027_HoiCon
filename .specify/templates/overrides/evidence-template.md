# Bằng chứng nghiệm thu: [FEATURE NAME]

**Spec**: `specs/[###-feature-name]/spec.md` · **Mã ROADMAP**: [P2-xx] · **Nhánh/PR**: [feat/… · #PR] · **Ngày**: [DATE]

<!-- Điền SAU khi implement + converge. Mỗi dòng phải có thứ kiểm lại được (lệnh, đường dẫn ảnh, link CI).
     Bước không chạy được: ghi SKIPPED/UNAVAILABLE + lý do — không bỏ trống, không ghi "đạt" khi chưa chạy. -->

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Môi trường (máy ảo / FTL / máy thật, n) | Đạt? | Bằng chứng |
|---|---|---|---|---|---|
| SC-001 | | | | | |

## Yêu cầu chức năng (FR) ↔ test

| FR | Test / cách kiểm | Kết quả |
|---|---|---|
| FR-001 | | |

## Cổng các tầng (lệnh đã chạy)

| Tầng | Lệnh | Kết quả |
|---|---|---|
| Backend | `uv run --directory backend ruff check . && uv run --directory backend pytest` | |
| Android | `apps/android/gradlew -p apps/android :rules:test :app:lintDebug` | |
| Web | `pnpm --dir apps/web typecheck && pnpm --dir apps/web lint` | |
| Hook | `node --test ".claude/hooks/test/*.test.mjs"` | |
| Máy ảo | `python scripts/emu-scenario.py --avd hc-api36 --scenario …` | |
| Eval | `run-eval smoke` | |
| Truy vết | `python3 scripts/check-spec-trace.py` | |

## Review

| Reviewer | Kết quả | Đã xử lý |
|---|---|---|
| `security-privacy-reviewer` | | |
| `ux-elder-reviewer` | | |
| `/ponytail-review` | | |

## `/speckit-converge`

[Số lượt chạy, finding cuối = 0]

## Còn tồn / hoãn có chủ đích

- [việc còn lại → ROADMAP task nào]
