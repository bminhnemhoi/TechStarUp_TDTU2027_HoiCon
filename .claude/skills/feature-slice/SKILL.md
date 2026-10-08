---
name: feature-slice
description: Xây một tính năng HỏiCon trọn vẹn theo lát dọc (hợp đồng JSON Schema → migration → domain → API → tác tử/MCP → Android/web → test → docs) cho một task trong docs/ROADMAP.md hoặc user story trong docs/PRD.md. Dùng khi bắt đầu mọi task tính năng.
---

# feature-slice — dựng tính năng theo lát dọc

## 0. Phạm vi
- Lấy mã task trong `docs/ROADMAP.md` (ví dụ `P2-05`) và user story `US-xx` trong `docs/PRD.md`. Chép tiêu chí chấp nhận thành checklist.
- **Không làm ngoài phạm vi** — ý tưởng thêm ghi vào mục "Ghi chú" của ROADMAP.
- Tinh thần ponytail: tái dùng cái có sẵn, ưu tiên tính năng native của nền tảng, không trừu tượng hóa sớm. Không bao giờ cắt kiểm tra hợp lệ, xử lý lỗi, a11y, quyền riêng tư.
- Task lớn hoặc đụng nhiều tầng: vào Plan mode và hỏi chuyên gia (`android-engineer`, `agent-architect`, `backend-db`, `web-ux`).

## 1. Hợp đồng trước
- Sự kiện/payload mới hoặc đổi: sửa `docs/schemas/*.json` + fixture dùng chung trong `docs/schemas/fixtures/` (số điện thoại hư cấu).
- API: cập nhật `docs/API.md`; sau khi code xong sinh lại client TS (`bash scripts/gen-api-client.sh`).
- Mục đích dữ liệu mới ⇒ giá trị enum đồng ý mới + skill `consent-copy`.

## 2. Dữ liệu
- Migration Alembic mới (skill `new-migration`), có `downgrade`. Chuyển trạng thái sự cố ⇒ skill `state-transition`.

## 3. Domain → API → tác tử
- Logic thuần trong `backend/src/hoicon/domain/` (unit test không cần DB).
- Route FastAPI mỏng; lỗi trả thông điệp tiếng Việt an toàn.
- Đụng LLM/đồ thị/MCP: theo `agent-architect` (router, che PII, fallback, bất biến mức sàn) và chạy `run-eval` smoke.

## 4. Giao diện
- Android: luật mới vào `:rules` (unit test trước), UI Compose theo skill `ui-screen` (nhánh elder), kiểm thử trên máy ảo bằng skill `android-emulator-test`.
- Web: skill `ui-screen` (nhánh web).

## 5. Kiểm thử & review
- Test xanh ở mọi tầng bị đụng: `uv run --directory backend pytest`, `pnpm --dir apps/web test`, `apps/android/gradlew -p apps/android :rules:test`.
- Gọi `security-privacy-reviewer` nếu đụng dữ liệu cá nhân/LLM/manifest/Zalo; `ux-elder-reviewer` nếu có màn/tin mới; chạy `/ponytail-review`.

## 6. Kết thúc
- Cập nhật docs liên quan + trạng thái task trong ROADMAP (`[x]`, ngày, ghi chú số đo).
- Báo cáo Minh (tiếng Việt): đã làm gì, lệnh test + kết quả, ảnh chụp/số đo, rủi ro còn lại, đề xuất task kế tiếp. **Không commit nếu Minh chưa yêu cầu.**
