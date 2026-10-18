# Kế hoạch Spec 031: Hồ sơ vụ việc

**Mã**: `031-case-file` · **ROADMAP**: `P2-16` · **Làn**: B (nhóm **[B-api]** rồi **[B-web]**) · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | `content` chỉ dữ kiện đã che; lược đồ cấm dãy ≥ 4 chữ số, link, trường lạ; ô tự điền chỉ ở trình duyệt |
| III. LLM | Một lời gọi tùy chọn qua `llm_router` (`strong`), lọc, rơi về mẫu; không ảnh hưởng mức rủi ro |
| IV. Công khai AI | `ai_label` bắt buộc mở đầu "Đây là trợ lý AI HỏiCon"; tin Zalo cũng vậy (test luật 6) |
| IV. Đồng ý | Không enum mới; câu về hồ sơ thêm vào `guardian_alerts` cùng PR với mã — ★ Minh xác nhận phạm vi |
| V. Hợp đồng trước | `case_file.v1`, `case_file_action.v1` + fixture (giai đoạn 0, đã làm); migration chỉ làn B |
| Luật 11 | Mọi chuyển trạng thái sự cố (`case_open → closed`) qua `IncidentService.transition()` |
| VII. Bằng chứng | Người giám hộ thật dùng thử = BLOCKED (thí điểm) |
| VIII. Ít code | In bằng trình duyệt (không DOCX), tái dùng phiên/CSRF của 027, `retention` của 034, bộ lọc `_UNSAFE_SUMMARY` |

## 2. Quyết định

| # | Quyết định | Lý do | Phương án bỏ |
|---|---|---|---|
| D1 | Phần dữ kiện **tất định** (khóa enum ⇒ câu cố định trong `agents/texts.py`); LLM chỉ viết đoạn tóm tắt ≤ 600 ký tự | Văn bản mang tới cơ quan phải đúng; giữ vai trò tác tử "Hồ sơ" trong thuyết minh | LLM viết cả hồ sơ; bỏ hẳn LLM (lệch thuyết minh) |
| D2 | Ô tự điền (số điện thoại, tài khoản, số tiền, giờ, ngân hàng) là `input` không thuộc form gửi, không lưu trình duyệt | ADR-006: máy chủ không được có số thô; người giám hộ vẫn có bản in đủ | Gửi số lên rồi mã hóa (vẫn là lưu PII thô có thể giải) |
| D3 | Nhánh sau `resolve`: `case_open` ⇒ `case_file` ⇒ interrupt `await_case_approval` (resume `{"case_action": "approve"|"discard", "actor": "guardian"|"system"}`) ⇒ `END` | Đồ thị hiển thị được trong `/trace` (033) như các tác tử khác; resume chống trùng như `await_guardian` | Job riêng ngoài đồ thị (không có trace, không nhất quán với AGENTS.md) |
| D4 | Job `case_autoclose` hằng ngày: `case_open` không hoạt động 30 ngày ⇒ resume `discard`/`system` (nếu còn bản nháp) và `closed` qua `IncidentService` | Thread không treo `waiting` mãi; hạn lưu 12 tháng chạy được | Không đóng (lỗi hiện có); đóng ngay khi duyệt (người giám hộ còn cần in lại) |
| D5 | `mark_sent` không resume đồ thị (thread đã `END` sau `approve`), chỉ ghi hồ sơ + đóng sự cố | Ít trạng thái trong đồ thị | Giữ thread chờ tới `sent` (treo lâu, tốn checkpoint) |
| D6 | Diễn tập, eval, sim ⇒ không có hồ sơ | Luật 8 (diễn tập không như sự cố thật); eval/sim không có sự cố thật hoặc là trình diễn | Hồ sơ "diễn tập" |
| D7 | Tin Zalo báo "đã có bản nháp — nhắn 4 để mở trang web", không gửi liên kết có token | Giảm token trong tin; tái dùng đăng nhập 027; 1 tin, `urgent=True` | Liên kết `/a/<token>` mới cho hồ sơ |
| D8 | Hướng dẫn trình báo là dữ liệu có cờ `approved` (mẫu `data/drills`) | Không bịa số đường dây nóng; Minh duyệt nội dung | Viết cứng trong mã |

## 3. Đồ thị

```
… → await_guardian → resolve ─┬─ outcome ≠ case_open, hoặc is_drill, hoặc sim, hoặc eval ─▶ END
                              └─ case_open ─▶ case_file ─▶ [INTERRUPT await_case_approval] ─▶ END
case_file: dựng content (D1) → (tùy chọn) llm_router strong → lọc → ghi case_files (draft) → tin Zalo (D7) → agent_steps "case_file"
```

## 4. Bản đồ file

| Nhóm | File | Thay đổi |
|---|---|---|
| chung | `docs/schemas/case_file.v1.json`, `case_file_action.v1.json` + fixtures | mới (giai đoạn 0, đã làm) |
| B-api | `backend/tests/contract/test_case_file_schemas.py` | mới |
| B-api | migration `<số>_case_files`, `db/models.py` (`CaseFile`), `tests/integration/test_schema_<số>.py` | mới |
| B-api | `agents/incident_graph.py` (nút `case_file`, interrupt, cạnh), `agents/texts.py` (câu cố định, tin Zalo), `agents/prompts/case_file.md` (front-matter `case_file@1`) | sửa / mới |
| B-api | `services/case_file_service.py` (dựng content, máy trạng thái hồ sơ, auto-close), `jobs` (handler `case_autoclose`), `services/retention_service.py`, `services/purge_service.py` | mới / sửa |
| B-api | `api/routers/guardian.py` (GET/POST case-file) | sửa |
| B-api | `data/case_file/report_guidance.vi.yaml` (`approved: false`) + test | mới |
| B-api | `tests/integration/test_case_file_graph.py`, `test_api_case_file.py`, `test_case_autoclose.py`; eval (FR-013) | mới / sửa |
| B-web | `apps/web/src/app/incidents/[id]/case-file/page.tsx`, CSS in, link từ trang chi tiết; `e2e/case-file.spec.ts` | mới / sửa |
| docs | `docs/legal/consent/guardian_alerts.vi.md` + `manifest.json` (FR-012), `docs/AGENTS.md`, `DATA-MODEL.md` (bảng + §6), `API.md`, `PRIVACY-DPIA.md` | sửa |

## 5. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| `guardian_alerts` đã 159/160 từ ⇒ thêm câu vượt trần SC-004 của 011 | TB | Rút gọn câu khác trong cùng văn bản; `ux-elder-reviewer`; nếu không được thì tách văn bản (★ Minh) |
| Người giám hộ hiểu "HỏiCon đã báo công an" | TB | Câu "HỏiCon không tự gửi cho cơ quan nào" ở tin Zalo, trang, bản in |
| LLM bịa dữ kiện trong tóm tắt | TB | Nhãn "do trợ lý AI soạn", duyệt bắt buộc, lọc số/link, mẫu khi lỗi; eval FR-013 |
| Thread `await_case_approval` treo khi app khởi động lại | Thấp | `recover()` sẵn có + D4 |

## 6. Rà soát `/speckit-analyze` (18/10/2026, vòng 1)

Phủ FR: 14/14 có task. **0 CRITICAL, 1 HIGH (đã sửa), 3 MEDIUM, 0 LOW.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| C1 | HIGH | FR-013 đòi eval kiểm hồ sơ trong khi FR-003 cho eval đi thẳng `END` (không có sự cố thật) ⇒ yêu cầu không làm được | FR-013 + T010 chuyển sang pytest trên sự cố seed với ≥ 5 kịch bản; eval chỉ còn hồi quy |
| C2 | MEDIUM | `backend/Dockerfile` chỉ chép `data/` được liệt kê ⇒ `data/case_file` không có trong ảnh | T004 thêm `COPY` + test hạ tầng |
| C3 | MEDIUM | `guardian_alerts` 159/160 từ, 031 và 032 cùng thêm câu | Rủi ro §5; T011 rút gọn; gộp với 032 T008 |
| C4 | MEDIUM | Sự cố `case_open` hiện không bao giờ đóng (lỗi có sẵn, ngoài 031) ⇒ hạn lưu 12 tháng không chạy | FR-008 + T008 tự đóng sau 30 ngày |
