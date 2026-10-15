# Spec 023: Cảnh báo người giám hộ & Trang hành động khẩn cấp (Guardian Alert & Action Token)

**Mã ROADMAP**: `P2-07` · **Làn sở hữu**: Làn B (Server + Web) · **Phụ thuộc**: `002-zalo-guardian-channel`, `021-events-incident-service` · **Cột mốc**: **Gate M1** · **Nhánh tính năng**: `feat/023-guardian-alert`

---

## 1. Mục tiêu & Bối cảnh

Spec 023 hoàn thiện "đường cảnh báo khẩn cấp" — huyết mạch cốt lõi của HỏiCon đưa thông tin từ máy chủ tới tay người thân (người giám hộ) ngay khi phát hiện rủi ro cao hoặc lừa đảo. Cảnh báo giai đoạn 1 (Fast Alert) sử dụng mẫu tin tất định (không phụ thuộc LLM) đảm bảo độ trễ gửi tin p95 $\le 10\text{ s}$ qua kênh Zalo Bot (Spec 002), đính kèm liên kết hành động dùng 1 lần (Magic link `/a/[token]`, ADR-003/010) mở trang web Next.js hỗ trợ người giám hộ đưa ra quyết định can thiệp đóng sự cố tức thời.

Đây là điều kiện tiên quyết để nghiệm thu **Gate M1** (06/12) theo `docs/MASTER-PLAN.md` và `docs/ROADMAP.md`.

---

## 2. Tiêu chí thành công (Success Criteria)

- **(SC-001)**: Khi sự cố đạt mức rủi ro `high` hoặc `critical`, tin cảnh báo giai đoạn 1 (Fast Alert) được xếp hàng đợi `notify_guardian` và chuyển phát qua Zalo Bot với thời gian $p95 \le 10\text{ s}$ (ở chế độ mock trong CI / dev token thật).
- **(SC-002)**: Mọi tin cảnh báo bắt buộc tuân thủ Hiến pháp HỏiCon (Luật 6 & 8): mở đầu bằng câu công khai AI (`Đây là trợ lý AI HỏiCon.`), có nhãn `[DIỄN TẬP]` nếu là diễn tập, đính kèm magic link `/a/{token}` và cú pháp trả lời nhanh 1/2/3.
- **(SC-003)**: Token hành động `/a/[token]` (bảng `action_tokens`) sinh ngẫu nhiên an toàn (entropy $\ge 256$ bits, URL-safe), chỉ lưu băm SHA-256 trong CSDL, có thời hạn (mặc định 24h), sử dụng đúng 1 lần (`used_at`).
- **(SC-004)**: Trang web hành động `/a/[token]` (Next.js `apps/web`) tối ưu mobile-first, áp dụng Design System `tokens.css` (độ tương phản WCAG AAA $\ge 7:1$, nút bấm $\ge 4\text{rem}$), hiển thị tóm tắt biến cố không lộ số điện thoại thô, cung cấp 4 nút hành động: An toàn (`safe`), Lừa đảo/Dừng khẩn (`prevented`), Báo nhầm (`false_alarm`), Gọi người thân (`tel:`).
- **(SC-005)**: Thao tác của người giám hộ (qua trang web `/a/[token]` hoặc trả lời Zalo 1/2/3) gọi `IncidentService.transition(actor="guardian")` đóng thành công sự cố sang các trạng thái kết thúc (`resolved_safe`, `resolved_prevented`, `resolved_false_alarm`) hoặc mở hồ sơ vụ việc (`case_open`).
- **(SC-006)**: Kịch bản kiểm chứng tích hợp E2E Gate M1 (`scripts/e2e-m1.sh`): Cuộc gọi lạ $\rightarrow$ Mở app ngân hàng $\rightarrow$ SafePause Android $\le 3\text{ s}$ $\rightarrow$ Đồng bộ sự kiện $\rightarrow$ Cảnh báo Zalo $\le 10\text{ s}$ $\rightarrow$ Người giám hộ đóng sự cố $\rightarrow$ 0 số điện thoại thô trong DB và log (`privacy-audit`). Toàn bộ testsuite pass 100%.

---

## 3. Yêu cầu chức năng (Functional Requirements)

- **(FR-001)**: Hiện thực schemas hợp đồng `docs/schemas/incident_decision.v1.json` và `docs/schemas/action_view.v1.json` kèm fixtures valid/invalid.
- **(FR-002)**: Dịch vụ `ActionTokenService`: sinh token URL-safe 32-bytes, lưu băm SHA-256 vào `action_tokens`, kiểm tra tính hợp lệ (`verify`), đánh dấu đã dùng (`consume`).
- **(FR-003)**: Cơ chế tự động kích hoạt cảnh báo giai đoạn 1 trong `IncidentService`: khi sự cố mới được tạo có `level` $\ge$ `high` hoặc chuyển trạng thái sang `awaiting_guardian`, tự động tạo `ActionToken` và xếp job `notify_guardian`.
- **(FR-004)**: Endpoint `GET /v1/action/{token}`: xác thực băm token, trả về dữ liệu tóm tắt sự cố (mức độ, nhãn diễn tập, tóm tắt sự kiện, tên thành viên/thiết bị được bảo vệ), trạng thái đã xử lý (nếu token đã dùng).
- **(FR-005)**: Endpoint `POST /v1/action/{token}/decision`: nhận quyết định `safe` / `prevented` / `false_alarm` / `emergency_pause`, chuyển đổi trạng thái sự cố qua `IncidentService.transition(actor="guardian")`, vô hiệu hóa token (ghi `used_at`).
- **(FR-006)**: Endpoint `POST /v1/incidents/{id}/decision`: cho phép người giám hộ đã đăng nhập JWT thực hiện quyết định đóng sự cố có kiểm tra quyền gia đình.
- **(FR-007)**: Xử lý phản hồi tin nhắn Zalo 1/2/3 trong `hoicon.channels.updates`: chuyển thành quyết định người giám hộ tương ứng gọi `IncidentService.transition()`, phản hồi xác nhận qua Zalo Bot.
- **(FR-008)**: Xây dựng trang Next.js `apps/web/src/app/a/[token]/page.tsx`: giao diện mobile khẩn cấp, tuân thủ token màu và typography từ `tokens.css`, hiển thị công bố AI, xử lý tương tác gửi quyết định lên backend.
- **(FR-009)**: Triển khai kịch bản kiểm chứng E2E Gate M1 `scripts/e2e-m1.sh` và bộ test tích hợp `backend/tests/integration/test_guardian_alert.py`.
- **(FR-010)**: Kiểm tra bảo mật PII (`privacy-audit`): đảm bảo không có số điện thoại thô trong nội dung tin nhắn Zalo, URL `/a/[token]`, log hệ thống hay DB.
