---
name: phase-gate
description: Kiểm tra cổng cuối mỗi phase HỏiCon (G0, G1, M1, M2, M3, G3, G4) theo docs/ROADMAP.md — chạy toàn bộ test các tầng, eval, kịch bản máy ảo, kiểm quyền riêng tư, đối chiếu tiêu chí đo được, xuất báo cáo docs/phase-reports/<gate>.md, cập nhật STATUS và áp dụng danh sách cắt khi trễ. Dùng cuối mỗi tuần, cuối phase, hoặc khi Minh hỏi "đã qua gate chưa".
---

# phase-gate — kiểm soát chất lượng từng phase

## 1. Xác định gate
- Đọc khối `<!-- STATUS -->` và mục gate của phase hiện tại trong `docs/ROADMAP.md`. Liệt kê task: xong / chưa xong / bị cắt.

## 2. Chạy kiểm tra (ghi output tóm tắt, không dán toàn bộ log)
```bash
docker compose -f infra/compose.dev.yml up -d
uv run --directory backend ruff check . && uv run --directory backend pytest
pnpm --dir apps/web typecheck && pnpm --dir apps/web test
apps/android/gradlew -p apps/android :rules:test :app:assembleDebug
python scripts/emu-scenario.py --avd hc-api36 --scenario all --runs 10     # từ M1
uv run --directory backend hoicon-eval --suite full                        # từ W5
```
Bước nào chưa tồn tại ở phase hiện tại thì ghi "chưa áp dụng" — không bịa kết quả.

## 3. Kiểm bổ sung
- Skill `privacy-audit` (bắt buộc từ M1).
- Gọi song song `security-privacy-reviewer` và `ux-elder-reviewer` trên diff kể từ gate trước (`git diff <tag-gate-trước>..HEAD`).
- Từ M1: gọi `judge` đối chiếu cam kết thuyết minh (skill `pitch-sync`).

## 4. Đối chiếu tiêu chí
- Bảng: `| Tiêu chí gate | Ngưỡng | Đo được | Đạt? | Bằng chứng (lệnh/ảnh/file) |`. Số đo từ máy ảo ghi rõ "máy ảo"; từ thiết bị thật ghi model + Android.

## 5. Kết luận
- **Đạt**: cập nhật STATUS (phase kế, "Việc kế tiếp"), đề xuất tag `gate/<tên>` (chỉ tạo khi Minh đồng ý).
- **Chưa đạt**: liệt kê việc thiếu + ước lượng. Nếu trễ > 2 ngày so với ROADMAP ⇒ đề xuất cắt mục kế tiếp trong danh sách cắt (không tự cắt mục "không bao giờ cắt").
- Ghi báo cáo vào `docs/phase-reports/<gate>.md` và tóm tắt cho Minh bằng tiếng Việt.
