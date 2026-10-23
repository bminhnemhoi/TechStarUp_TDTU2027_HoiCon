# Kế hoạch Spec 050: Chế độ gian trưng bày

> **BẢN NHÁP — Opus /speckit-analyze lại khi có quota.** Soạn 23/10/2026 bởi làn B (Sonnet).

**Mã**: `050-booth-mode` · **ROADMAP**: `P4-02` · **Làn**: A+B · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Chỉ gia đình `is_demo`, sự cố cờ `sim`, kịch bản và bản ghi hư cấu; không phân tích/cookie theo dõi khách; mã tham gia ngắn hạn, hết hạn khi đặt lại |
| III. LLM chỉ nâng | Gian chạy **đồ thị thật** qua `/v1/sim/*` (`llm: "replay"`); bản ghi chỉ là phát lại hình ảnh, không có đường tắt quyết định |
| IV. Công khai AI | Tin Zalo mô phỏng giữ nguyên câu "Đây là trợ lý AI HỏiCon" (hợp đồng `sim_run.v1` bắt); băng rôn "MÔ PHỎNG" |
| V. Hợp đồng trước | Dùng `sim_*` có sẵn cho `/booth` + `/demo/console`; phần cần hợp đồng mới (`sim_reset`, `booth_join`) **BLOCKED chờ Opus** — không tự viết `docs/schemas` |
| VI. UX | Chữ ≥ 28 px ở khối chính, tương phản ≥ 7:1, biểu tượng + chữ cho mọi trạng thái, chữ tiếng Việt ấm, không hoảng sợ; `ux-elder-reviewer` đọc ảnh |
| VII. Bằng chứng | Băng rôn "BẢN GHI" không giấu; số đo ghi nguồn ("máy dev, replay, mạng cục bộ"), không tuyên bố số ở hội trường |
| VIII. Ít code | Tái dùng `api()`, `useRunStream`, `describeStep`, `TraceView`, `guardian-ui`, `/v1/sim/*`, `ops guardian_link --seed` |

## 2. Quyết định

| # | Quyết định | Lý do | Phương án bỏ |
|---|---|---|---|
| D1 | **Hai giai đoạn theo hợp đồng**: giai đoạn 1 chỉ dùng `/v1/sim/*` có sẵn (`/booth`, `/demo/console`, phát lại, đặt lại bằng CLI); giai đoạn 2 (`/join`, nút Đặt lại gọi API) chờ hợp đồng của Opus | Không đổi `docs/schemas`; giai đoạn 1 đã đủ cho Gate G4 trừ khách dùng điện thoại riêng | Tự viết schema (vi phạm quy trình); làm API không hợp đồng |
| D2 | Danh sách phát + câu trả lời kịch bản là hằng số có kiểu trong `apps/web/src/lib/booth.ts` | Đổi kịch bản gian = sửa một tệp, có kiểu; không cần bảng DB | Lưu trong DB (cần migration/hợp đồng) |
| D3 | **Bản ghi** = tệp JSON `{scenario_id, recorded_at, frames[{t_ms, run}], steps[{t_ms, ...}]}` trong `public/booth/replay/`, ghi bằng nút "Ghi bản ghi" ở console (trình duyệt tải về) hoặc `e2e/booth-record.spec.ts` (bật bằng `BOOTH_RECORD=1`); mỗi khung kiểm theo `sim_run.v1` | Không cần quyền DB/Python; bản ghi là dữ liệu thật của đồ thị replay nên khớp màn trực tiếp | Dựng tay (lệch với trực tiếp); video (không tương tác) |
| D4 | Phát hiện mất mạng: `navigator.onLine === false` **hoặc** 2 lần liên tiếp gọi API hỏng/quá 3 giây (`AbortSignal.timeout(3000)`) **hoặc** người điều khiển chọn; băng rôn cố định, không giấu | Wi-Fi hội trường thường "còn sóng nhưng không đi được"; `onLine` đơn thuần không đủ | Chỉ `onLine` |
| D5 | `/booth` đo `t_alert_ms` bằng `performance.now()` quanh `POST /v1/sim/runs` → khung có tin `fast_alert` đầu tiên | Không cần trường mới ở hợp đồng; ghi rõ là đo ở trình duyệt | Đo ở máy chủ (cần trường mới) |
| D6 | Đặt lại dữ liệu = `ops/booth.py reset` (CLI, chỉ `HOICON_ENV=dev`/gia đình `is_demo`); nút trong console chỉ đặt lại **màn hình** và hiện lệnh cần chạy cho tới khi có `POST /v1/sim/reset` | Hợp đồng chưa có; CLI đã đủ cho Gate G4 (người điều khiển có máy) | API không hợp đồng |
| D7 | Bộ đếm "đạt liên tiếp" và bảng lượt gần đây chỉ nằm trong bộ nhớ trang console (BroadcastChannel), **không** dùng localStorage/sessionStorage | Bất biến 5 của 027 (web không lưu gì ở trình duyệt); chỉ là tiện ích của người điều khiển, không là bằng chứng — bằng chứng chính thức ghi vào `evidence.md` | Lưu trình duyệt hoặc DB |

## 3. Luồng

```
/demo/console ─ Bắt đầu (kịch bản, chế độ) ─▶ /booth (cùng trình duyệt hoặc tab thứ hai, qua BroadcastChannel)
/booth ─ POST /v1/sim/runs ─▶ GET /v1/sim/runs/{id} (2 s) + EventSource /v1/runs/{id}/stream ─▶ 3 cột
        ─ POST …/answer (theo kịch bản) ─▶ POST /v1/incidents/{id}/decision (con quyết định theo kịch bản)
mất mạng (D4) ─▶ ReplayPlayer(bản ghi) ─▶ cùng 3 cột + băng rôn "BẢN GHI"; có mạng ⇒ chạy trực tiếp ở lượt kế
đặt lại ─▶ màn hình: dừng phát/xóa trạng thái · dữ liệu: `python -m hoicon.ops.booth reset`
```

## 4. Bản đồ file

| Nhóm | File | Thay đổi |
|---|---|---|
| B-web | `apps/web/src/lib/booth.ts` (danh sách phát, kiểu bản ghi, kiểm khung) | mới |
| B-web | `apps/web/src/lib/use-booth-runner.ts` (live + replay + phát hiện mất mạng + đo `t_alert_ms`) | mới |
| B-web | `apps/web/src/components/booth-columns.tsx` (3 cột chia sẻ giữa `/booth` và `/demo/console`) | mới |
| B-web | `apps/web/src/app/booth/page.tsx`, `apps/web/src/app/demo/console/page.tsx` | mới |
| B-web | `apps/web/public/booth/replay/*.json` (3 bản ghi), `apps/web/e2e/{booth,booth-offline,booth-record}.spec.ts` | mới |
| B-api | `backend/src/hoicon/ops/booth.py`, `backend/tests/integration/test_ops_booth.py` | mới |
| B-api | `routers/sim.py` (`/reset`), `services/sim_service.py`, join (mã ngắn hạn), `/join/[code]` | **BLOCKED** (hợp đồng) |
| A | `apps/android/**`, `docs/EMULATOR.md` (bấm máy tại gian) | làn A |

## 5. Phân tích chéo (analyze, 23/10/2026)

`spec.md` ↔ `plan.md` ↔ `tasks.md`: FR-001…FR-010 đều có task; SC-001…SC-006 đều có lệnh đo. **0 CRITICAL, 2 HIGH đã xử lý, 3 MEDIUM, 1 LOW.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| A1 | HIGH | `/join` và nút Đặt lại gọi API cần hợp đồng mới mà làn B không được thêm | D1: tách giai đoạn; FR-001 là task [Opus]; task phụ thuộc đánh BLOCKED |
| A2 | HIGH | Cần xác định "cảnh báo < 5 s" đo ở đâu, kẻo tuyên bố vượt chứng cứ | D5 + SC-002 ghi "đo ở trình duyệt, máy dev, replay"; không dùng cho số ở hội trường |
| A3 | MEDIUM | Phát lại có thể bị hiểu là trực tiếp ⇒ sai sự thật khi thuyết trình | FR-006 băng rôn cố định + test Playwright kiểm băng rôn |
| A4 | MEDIUM | Bản ghi có thể chứa dữ liệu thật nếu ghi từ gia đình thật | Chỉ ghi qua `/v1/sim/*` (gia đình demo, cổng bật); test quét số điện thoại thô + kiểm `sim_run.v1` trên tệp |
| A5 | MEDIUM | Cổng `HOICON_SIM_ENABLED` phải tắt ở prod, gian cần bật | Bật bằng biến môi trường ở máy gian; test hạ tầng 033 đã chặn `compose.prod.yml` |
| A6 | LOW | FR-009 (Android) thuộc làn A | Task [A] ghi rõ, không làm ở đây |
