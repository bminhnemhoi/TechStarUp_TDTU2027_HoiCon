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
- **(SC-004)**: Trang web hành động `/a/[token]` (Next.js `apps/web`) tối ưu mobile-first, áp dụng Design System `tokens.css` (độ tương phản WCAG AAA $\ge 7:1$, nút bấm $\ge 4\text{rem}$), hiển thị tóm tắt biến cố không lộ số điện thoại thô, cung cấp 4 nút hành động: Gọi người thân (`tel:`), An toàn (`safe`), Nghi lừa đảo (`emergency_pause` ⇒ `case_open`, sự cố còn mở), Báo nhầm (`false_alarm`); mỗi quyết định phải xác nhận lần hai.
- **(SC-005)**: Thao tác của người giám hộ (qua trang web `/a/[token]` hoặc trả lời Zalo 1/2/3) gọi `IncidentService.transition(actor="guardian")` đóng thành công sự cố sang các trạng thái kết thúc (`resolved_safe`, `resolved_prevented`, `resolved_false_alarm`) hoặc mở hồ sơ vụ việc (`case_open`).
- **(SC-006)**: Kịch bản kiểm chứng tích hợp E2E Gate M1 (`scripts/e2e-m1.sh`): Cuộc gọi lạ $\rightarrow$ Mở app ngân hàng $\rightarrow$ SafePause Android $\le 3\text{ s}$ $\rightarrow$ Đồng bộ sự kiện $\rightarrow$ Cảnh báo Zalo $\le 10\text{ s}$ $\rightarrow$ Người giám hộ đóng sự cố $\rightarrow$ 0 số điện thoại thô trong DB và log (`privacy-audit`). Toàn bộ testsuite pass 100%.

---

## 3. Yêu cầu chức năng (Functional Requirements)

- **(FR-001)**: Hiện thực schemas hợp đồng `docs/schemas/incident_decision.v1.json` và `docs/schemas/action_view.v1.json` kèm fixtures valid/invalid.
- **(FR-002)**: Dịch vụ `ActionTokenService`: sinh token URL-safe 32-bytes, lưu băm SHA-256 vào `action_tokens`, kiểm tra tính hợp lệ (`verify`), đánh dấu đã dùng (`consume`).
- **(FR-003)**: Cơ chế tự động kích hoạt cảnh báo giai đoạn 1 trong `IncidentService`: khi lô sự kiện mở/nâng sự cố lên `level` $\ge$ `high`, xếp job `notify_guardian` (một lần mỗi sự cố); `ActionToken` sinh lúc gửi tin, token thô không nằm trong DB/job/log. (Kích hoạt khi chuyển `awaiting_guardian` để cho đồ thị P2-09: hiện chưa có tác nhân nào chuyển sang trạng thái này ngoài chính quyết định của người giám hộ.)
- **(FR-004)**: Endpoint `GET /v1/action/{token}`: xác thực băm token, trả về dữ liệu tóm tắt sự cố (mức độ, nhãn diễn tập, tóm tắt sự kiện, tên thành viên/thiết bị được bảo vệ), trạng thái đã xử lý (nếu token đã dùng).
- **(FR-005)**: Endpoint `POST /v1/action/{token}/decision`: nhận quyết định `safe` / `prevented` / `false_alarm` / `emergency_pause`, chuyển đổi trạng thái sự cố qua `IncidentService.transition(actor="guardian")`, vô hiệu hóa token (ghi `used_at`).
- **(FR-006)**: Endpoint `POST /v1/incidents/{id}/decision`: cho phép người giám hộ đã đăng nhập JWT thực hiện quyết định đóng sự cố có kiểm tra quyền gia đình.
- **(FR-007)**: Xử lý phản hồi tin nhắn Zalo 1/2/3 trong `hoicon.channels.updates`: chuyển thành quyết định người giám hộ tương ứng gọi `IncidentService.transition()`, phản hồi xác nhận qua Zalo Bot.
- **(FR-008)**: Xây dựng trang Next.js `apps/web/src/app/a/[token]/page.tsx`: giao diện mobile khẩn cấp, tuân thủ token màu và typography từ `tokens.css`, hiển thị công bố AI, xử lý tương tác gửi quyết định lên backend.
- **(FR-009)**: Triển khai kịch bản kiểm chứng E2E Gate M1 `scripts/e2e-m1.sh` và bộ test tích hợp `backend/tests/integration/test_guardian_alert.py`.
- **(FR-010)**: Kiểm tra bảo mật PII (`privacy-audit`): đảm bảo không có số điện thoại thô trong nội dung tin nhắn Zalo, URL `/a/[token]`, log hệ thống hay DB.

---

## 4. Điều chỉnh khi rà soát độc lập (16/10/2026)

- Token thô từng nằm trong `jobs.payload` (`text`, `action_url`) ⇒ đổi sang sinh token lúc gửi (`channels.guardian._fill_action_link`); log truy cập uvicorn che `/v1/action/***`.
- "Nghi lừa đảo" (web nút 2, Zalo "2 - vẫn thấy đáng ngờ") từng đóng sự cố thành `resolved_prevented` ⇒ đổi sang `case_open` để còn theo dõi.
- `IncidentService.transition()` không còn tác dụng phụ (gửi cảnh báo); `apply_guardian_decision` chuyển từ router API vào `services.incident_service`; ghi chú tự do của người giám hộ không còn được chép vào `incident_transitions.reason`.
- Trang `/a/[token]`: màu theo token (chữ ≥ 7:1), nhãn `[DIỄN TẬP]` + màu diễn tập riêng, xác nhận 2 bước, `no-referrer` + `noindex`, gọi API cùng nguồn qua rewrite của Next (trước đó không có CORS nên trang không gọi được API).
- `scripts/e2e-m1.sh` từng in sẵn kết quả ở bước 6 ⇒ mọi bước giờ chạy kiểm thật; chặng Android ↔ máy chủ ghi rõ CHƯA TỰ ĐỘNG.
