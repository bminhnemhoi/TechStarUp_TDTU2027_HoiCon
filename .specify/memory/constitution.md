# Hiến chương HỏiCon (Spec Kit constitution)

> Nguyên tắc **không thương lượng** mà mọi spec/plan/tasks phải qua (`/speckit-plan` → mục *Constitution Check*,
> `/speckit-analyze` coi vi phạm là CRITICAL). File này **tóm tắt và trỏ về** nguồn gốc; chi tiết nằm ở `CLAUDE.md`
> (mục "Luật bắt buộc", đánh số 1–16) và `docs/adr/`. **Khi mâu thuẫn: `CLAUDE.md` + ADR thắng** — sửa file này
> cho khớp, không làm ngược lại.

## Nguyên tắc

### I. Đường dừng an toàn tất định, offline, ≤ 3 giây, không bao giờ chặn vĩnh viễn
Phát hiện → SafePause chạy hoàn toàn trên máy bằng luật tất định (`:rules`), không mạng, không LLM; hiện ≤ 3 s (p95);
"tiếp tục" cần giữ 3 s và được ghi lại. Manifest đường găng không cần `INTERNET`.
*Nguồn:* CLAUDE.md luật 3–4 · ADR-001, ADR-007, ADR-008.
*Cách kiểm:* `:rules:test`; `emu-scenario.py` API 36 + 34 (có `--prep force-stop`, tắt mạng); số máy thật qua `:latency`.

### II. Riêng tư theo thiết kế
Không bao giờ log/lưu/in/gửi LLM số điện thoại, số tài khoản, tên thật, Zalo ID, OTP, CCCD dạng thô. Máy gửi
`h1 = SHA-256("hoicon:v1:"+E164)`, máy chủ lưu `HMAC(pepper[kid], h1)` + 3 số cuối. Android cấm SMS, nhật ký cuộc gọi,
danh bạ, `QUERY_ALL_PACKAGES`, `REQUEST_INSTALL_PACKAGES`, Accessibility, Notification Listener, ghi âm cuộc gọi.
Lời kể tự do của người cao tuổi không lưu. Fixture chỉ dùng số hư cấu.
*Nguồn:* CLAUDE.md luật 1–3, 9 · ADR-006, ADR-009 · `docs/DATA-MODEL.md` §3, §6.
*Cách kiểm:* hook `guard-privacy`; `hoicon.domain.pii`; skill `privacy-audit` (bắt buộc từ M1); `security-privacy-reviewer`.

### III. LLM chỉ được nâng rủi ro, mọi lời gọi qua một cổng
Mức rủi ro cuối ≥ `rule_floor` (`raise_only`). Mọi lời gọi LLM đi qua `backend/src/hoicon/agents/llm_router.py`
(che PII, ngân sách, timeout ≤ 4 s, trace, output có cấu trúc, rơi về mẫu). Nội dung kẻ gian bọc `<untrusted>`, không vào
system prompt. Công cụ có tác dụng phụ chỉ gọi từ node trong danh sách cho phép; đường cảnh báo (`fast_alert`) không cần LLM.
*Nguồn:* CLAUDE.md luật 5 · ADR-009 · `docs/AGENTS.md`.
*Cách kiểm:* test `llm_router`; `run-eval smoke` (0 vi phạm an toàn) khi đổi prompt/đồ thị/model.

### IV. Công khai AI và đồng ý chỉ ghi thêm
Tin đầu tiên tới người cao tuổi và mọi tin Zalo trong sự cố mở đầu "Đây là trợ lý AI HỏiCon". Mục đích dữ liệu mới ⇒
giá trị enum đồng ý + phiên bản văn bản; bảng `consents` chỉ ghi thêm. Diễn tập luôn `is_drill`, demo luôn `is_demo`,
thí điểm chỉ người ≥ 18 tuổi.
*Nguồn:* CLAUDE.md luật 6–8.
*Cách kiểm:* `AiDisclosureCopyTest` (Android), test công khai AI phía backend; trigger chặn UPDATE/DELETE `consents`.

### V. Hợp đồng trước, dữ liệu bất biến
JSON Schema + fixture dùng chung trong `docs/schemas/` là nguồn sự thật; đổi API ⇒ sinh lại client TS
(`scripts/gen-api-client.sh`). Mọi chuyển trạng thái sự cố qua `IncidentService.transition()`. Migration Alembic đã lên
`main` là bất biến. Gửi Zalo chỉ qua bộ kiểm hạn mức `messages_out`.
*Nguồn:* CLAUDE.md luật 9–11 · ADR-002, ADR-003, ADR-004.
*Cách kiểm:* `backend/tests/contract/*`, `SchemaContractTest` (`:rules`).

### VI. UX cho người cao tuổi
Chữ ≥ 20sp, nút chính ≥ 24sp đậm, vùng chạm ≥ 64dp, ≤ 2 hành động chính/màn, tương phản ≥ 7:1, dùng được ở cỡ chữ 200%,
màn quan trọng tự đọc to; màu rủi ro luôn kèm biểu tượng + chữ; chữ người dùng thấy bằng tiếng Việt, giọng ấm, xưng "bác".
*Nguồn:* CLAUDE.md luật 13, 15–16 · `docs/DESIGN-SYSTEM.md` (thắng mọi plugin thiết kế).
*Cách kiểm:* skill `ui-screen`; ảnh chụp 100% + 200%; `ux-elder-reviewer` (app) hoặc Playwright screenshot (web).

### VII. Bằng chứng trung thực
Không tuyên bố số liệu hay tương thích chưa đo. Mỗi con số ghi nguồn (máy ảo / Firebase Test Lab / máy thật, ngày, n).
Không đánh `☑` khi chưa có `evidence.md` của spec. Bước bị bỏ qua ghi rõ SKIPPED/UNAVAILABLE.
*Nguồn:* CLAUDE.md "Kiểm soát phạm vi" · `docs/EMULATOR.md` §6.
*Cách kiểm:* `python3 scripts/check-spec-trace.py`; reviewer đọc `evidence.md`.

### VIII. Ít code nhất đủ dùng, tái sử dụng trước
Liệt kê module/hàm sẵn có trước khi viết mới; không thêm thư viện khi chưa nêu lý do; không over-engineer — nhưng không
bao giờ cắt kiểm tra hợp lệ, xử lý lỗi, khả năng tiếp cận, quyền riêng tư, trạng thái loading/empty/error.
Python: type hints + `ruff`; Kotlin: không `!!` ở code sản phẩm; TS: `strict`.
*Nguồn:* CLAUDE.md luật 12, 14.
*Cách kiểm:* mục "Tái sử dụng" của `plan.md`; `/ponytail-review`.

### IX. Chặn phát hành
Không đưa bản build cho người thật (closed testing, thí điểm, gian trưng bày) trước khi có: E3 công bố nổi bật + bản ghi
đồng ý có phiên bản (P2-02), Room + Tink thay SharedPreferences (P2-05), buildType release/demo với R8 + log chẩn đoán tắt
(P1-08). Chỉ phát hành qua Google Play, không gửi APK.
*Nguồn:* ROADMAP "Ghi chú" (review 09/10) · ADR-005, ADR-008.
*Cách kiểm:* checklist `release-block` trong `.specify/memory/checklists.md`.

## Ràng buộc dự án
- Mốc cứng: nộp Vòng 1 13/11/2026 (hạn 15/11) · MVP Vòng 2 09/01/2027 (đóng băng 06/01) · chung kết 27/02/2027.
- Chỉ làm task có mã trong `docs/ROADMAP.md`; ý tưởng ngoài phạm vi ghi vào "Ghi chú". Gate trễ > 2 ngày ⇒ cắt theo
  danh sách cắt. **Không bao giờ cắt:** sổ đồng ý, công khai AI, che PII, dừng an toàn, đường cảnh báo, trace, eval ≥ 100 ca.
- Cổng: Postgres 15432, API 18000, web 3100. Không đọc `.env`, keystore, thư mục bí mật.

## Quy trình phát triển
- Spec Kit theo `docs/MASTER-PLAN.md` §2 và §6: làn **full** (specify → clarify → plan → tasks → analyze → checklist →
  implement → converge → evidence → review → PR) cho tính năng/đổi hành vi; làn **lite** (≤ 1 ngày, không đổi hành vi hay
  hợp đồng) chỉ cần task ROADMAP + PR.
- Số spec được cấp trước trong `docs/MASTER-PLAN.md` §3; không tự đặt số mới.
- Definition of Done = mục DoD trong `CLAUDE.md` + `evidence.md` đầy đủ + `check-spec-trace.py` sạch.
- Commit chỉ khi Minh hoặc Tiến yêu cầu; nhánh `feat/<mã>-<slug>`; PR được người còn lại duyệt rồi squash merge.

## Quản trị
- Sửa hiến chương = PR riêng, cả Minh và Tiến duyệt; tăng phiên bản theo semver (MAJOR: bỏ/đổi nghĩa nguyên tắc;
  MINOR: thêm nguyên tắc; PATCH: câu chữ).
- Mỗi spec/plan phải ghi rõ đã qua Constitution Check; vi phạm có chủ đích ghi ở "Complexity Tracking" kèm lý do và cần duyệt.

**Version**: 1.0.0 | **Ratified**: 2026-10-15 | **Last Amended**: 2026-10-15
