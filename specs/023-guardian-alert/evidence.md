# Bằng chứng nghiệm thu: Spec 023 — Cảnh báo người giám hộ & Trang hành động khẩn cấp

**Spec**: `specs/023-guardian-alert/spec.md` · **Mã ROADMAP**: P2-07 · **Làn B (Server + Web)** · **Nhánh**: `feat/023-guardian-alert` · **Ngày**: 16/10/2026
**Cột mốc**: **Gate M1** (06/12)

---

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Đạt? | Bằng chứng |
|---|---|---|---|---|
| SC-001 | Cảnh báo giai đoạn 1 (Fast Alert mẫu) qua Zalo Bot $p95 \le 10\text{ s}$ khi sự cố rủi ro cao mở | Đang đo kiểm... | ... | `test_guardian_alert.py` |
| SC-002 | Công khai AI Luật 6 (`Đây là trợ lý AI HỏiCon.`), nhãn `[DIỄN TẬP]` Luật 8, kèm magic link `/a/{token}` và cú pháp trả lời 1/2/3 | Đang đo kiểm... | ... | `test_guardian_alert.py`, Zalo message delivery |
| SC-003 | ActionToken sinh ngẫu nhiên 32-bytes URL-safe, chỉ lưu SHA-256 hash, hạn 24h, chỉ dùng đúng 1 lần (`used_at`) | Đang đo kiểm... | ... | `test_action_token_service.py` |
| SC-004 | Trang web `/a/[token]` (Next.js) mobile-first, Design System `tokens.css` (WCAG AAA $\ge 7:1$, nút $\ge 4\text{rem}$), 4 nút hành động | Đang đo kiểm... | ... | Next.js build & check, test specs |
| SC-005 | Quyết định của người giám hộ (web hoặc tin nhắn Zalo 1/2/3) đóng sự cố thành công qua `IncidentService.transition()` | Đang đo kiểm... | ... | `test_guardian_decision.py` |
| SC-006 | Kịch bản tích hợp E2E Gate M1 (`scripts/e2e-m1.sh`): Cuộc gọi lạ $\to$ demobank $\to$ SafePause $\le 3\text{ s}$ $\to$ Zalo alert $\le 10\text{ s}$ $\to$ đóng sự cố $\to$ 0 PII thô | Đang đo kiểm... | ... | `scripts/e2e-m1.sh` |

---

## FR ↔ kiểm chứng

| FR | Kết quả |
|---|---|
| FR-001 Schemas `incident_decision` & `action_view` | Đang thực hiện |
| FR-002 Dịch vụ `ActionTokenService` | Đang thực hiện |
| FR-003 Kích hoạt Fast Alert trong `IncidentService` | Đang thực hiện |
| FR-004 `GET /v1/action/{token}` | Đang thực hiện |
| FR-005 `POST /v1/action/{token}/decision` | Đang thực hiện |
| FR-006 `POST /v1/incidents/{id}/decision` | Đang thực hiện |
| FR-007 Zalo webhook 1/2/3 mapping | Đang thực hiện |
| FR-008 Next.js `/a/[token]/page.tsx` | Đang thực hiện |
| FR-009 E2E Gate M1 & test tích hợp | Đang thực hiện |
| FR-010 Quét bảo mật PII (`privacy-audit`) | Đang thực hiện |
