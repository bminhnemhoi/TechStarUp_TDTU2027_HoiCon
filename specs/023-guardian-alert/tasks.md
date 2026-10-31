# Danh sách Công việc Hiện thực: Spec 023 — Cảnh báo người giám hộ & Trang hành động

**Mã ROADMAP**: `P2-07` · **Làn sở hữu**: Làn B (Server + Web) · **Cột mốc**: **Gate M1**

---

## Danh sách Tác vụ Kỹ thuật

- [x] T001: Hiện thực schemas `docs/schemas/incident_decision.v1.json` và `docs/schemas/action_view.v1.json` kèm fixtures valid/invalid [FR-001]
- [x] T002: Hiện thực dịch vụ `ActionTokenService` sinh token ngẫu nhiên, băm SHA-256, kiểm tra thời hạn và đánh dấu đã dùng [FR-002]
- [x] T003: Hiện thực logic tự động tạo `ActionToken` và kích hoạt Fast Alert Zalo khi sự cố mở mức `high`/`critical` hoặc chuyển `awaiting_guardian` [FR-003]
- [x] T004: Xây dựng endpoint `GET /v1/action/{token}` xác thực băm token và trả thông tin tóm tắt sự cố không lộ PII [FR-004]
- [x] T005: Xây dựng endpoint `POST /v1/action/{token}/decision` xử lý quyết định an toàn / lừa đảo / báo nhầm và gọi `IncidentService.transition()` [FR-005]
- [x] T006: Xây dựng endpoint `POST /v1/incidents/{id}/decision` cho người giám hộ đăng nhập JWT với kiểm tra quyền thành viên gia đình [FR-006]
- [x] T007: Mở rộng `hoicon.channels.updates` xử lý tin nhắn Zalo 1/2/3 gọi `IncidentService.transition(actor="guardian")` đóng sự cố [FR-007]
- [x] T008: Phát triển trang giao diện Next.js `apps/web/src/app/a/[token]/page.tsx` mobile-first với Design System `tokens.css` và công bố AI [FR-008]
- [x] T009: Viết kịch bản kiểm thử tích hợp backend `backend/tests/integration/test_guardian_alert.py` bao phủ luồng từ cảnh báo đến quyết định [FR-009]
- [x] T010: Xây dựng kịch bản kiểm chứng E2E Gate M1 `scripts/e2e-m1.sh` khép kín luồng cuộc gọi lạ $\to$ SafePause $\to$ Zalo alert $\to$ đóng sự cố [FR-009]
- [x] T011: Quét bảo mật PII (`privacy-audit`) và kiểm tra gitleaks: xác nhận 0 số điện thoại thô trong DB, tin nhắn Zalo, URL và log [FR-010]
- [x] T012: Cập nhật tài liệu kỹ thuật trong `docs/API.md`, `docs/DATA-MODEL.md`, `docs/ROADMAP.md` và hoàn thiện `evidence.md` [FR-001] [FR-009]
