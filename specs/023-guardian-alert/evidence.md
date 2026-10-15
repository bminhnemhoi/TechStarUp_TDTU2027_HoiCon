# Bằng chứng nghiệm thu: Spec 023 — Cảnh báo người giám hộ & Trang hành động khẩn cấp

**Spec**: `specs/023-guardian-alert/spec.md` · **Mã ROADMAP**: P2-07 · **Làn B (Server + Web)** · **Nhánh**: `feat/023-guardian-alert` · **Ngày**: 16/10/2026
**Cột mốc**: Gate M1 (06/12) — tệp này chỉ chứng minh **phần máy chủ + web**; chặng Android ↔ máy chủ còn mở (SC-006).

Nguồn số liệu: máy Tiến (Linux, Postgres dev cổng 15432), Zalo **MOCK** trong tiến trình, trình duyệt Playwright (Chromium) 390×844. Không có số nào từ máy thật hay Zalo thật.

---

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Đạt? | Bằng chứng |
|---|---|---|---|---|
| SC-001 | Fast Alert p95 ≤ 10 s | 31–36 ms từ `POST /v1/events` tới tin nằm trong Zalo MOCK (n = 1/lần chạy, trong tiến trình) | ĐẠT phần máy chủ · **BLOCKED** p95 Zalo thật (chưa có token bot, như spec 002 T024/T025) | `test_m1_server_flow_event_to_closed_incident_without_pii` |
| SC-002 | Công khai AI, `[DIỄN TẬP]`, liên kết `/a/{token}`, cú pháp 1/2/3 | Tin bắt đầu bằng `AI_DISCLOSURE`, có liên kết thật sinh lúc gửi; cổng `deliver` chặn tin thiếu công khai AI/nhãn diễn tập | ĐẠT | `test_fast_alert_job_never_carries_a_raw_token`, `channels/guardian.py` |
| SC-003 | Token 256 bit, chỉ SHA-256, 24 h, 1 lần | `secrets.token_urlsafe(32)`; DB chỉ có hash; token thô không có trong `jobs.payload` (truy vấn `payload::text LIKE`) và log truy cập (`/v1/action/***`); bấm lại ⇒ 409; hết hạn ⇒ 410 | ĐẠT | `test_action_token_service.py` (5), `test_guardian_alert.py`, `test_action_token_log.py`, log uvicorn thật |
| SC-004 | Trang mobile, token màu, chữ ≥ 7:1, nút ≥ 4 rem, 4 hành động | Ảnh 100%/200%: không tràn ngang ở 390 px, nút thấp nhất 128 px ở 200%; màu chỉ từ `tokens.css` (cặp chữ/nền đã đo ≥ 7:1 ở spec 010) | ĐẠT (máy tính, Chromium) | `~/hoicon-evidence/023-guardian-alert/023-a-{real,drill,done,200pct}.png` |
| SC-005 | Quyết định đóng sự cố qua `IncidentService.transition()` | web/JWT: `safe`/`prevented`/`false_alarm` ⇒ `resolved_*`; `emergency_pause` ⇒ `case_open`; Zalo "1" ⇒ `resolved_safe`, "2" ⇒ `case_open` | ĐẠT | 6 test trong `test_guardian_alert.py` |
| SC-006 | E2E M1: cuộc gọi lạ → SafePause ≤ 3 s → Zalo ≤ 10 s → đóng → 0 PII | Phần máy chủ: sự kiện → cảnh báo → `/a/[token]` → đóng, 0 số điện thoại thô/0 token thô trong job | ◐ phần máy chủ ĐẠT · chặng Android ↔ máy chủ **CHƯA TỰ ĐỘNG** | `bash scripts/e2e-m1.sh` (5/5 bước tự động) |

## FR ↔ kiểm chứng

| FR | Kết quả | Bằng chứng |
|---|---|---|
| FR-001 | ĐẠT | `test_action_schemas.py` 13/13; phản hồi GET được kiểm với `action_view.v1.json` |
| FR-002 | ĐẠT | `test_action_token_service.py` |
| FR-003 | ĐẠT (kích hoạt từ lô sự kiện) | `test_fast_alert_job_never_carries_a_raw_token`, `test_family_without_guardian_queues_nothing`, luồng M1 |
| FR-004 | ĐẠT | `test_action_view_matches_the_contract_and_hides_pii` |
| FR-005 | ĐẠT | `test_decision_closes_the_incident_and_burns_the_token`, `test_suspected_scam_opens_a_case_instead_of_closing`, `test_unknown_decision_or_expired_link` |
| FR-006 | ĐẠT (route) · chưa có nơi cấp JWT người giám hộ (spec 027) | `test_guardian_jwt_decides_only_inside_the_family` |
| FR-007 | ĐẠT | `test_zalo_reply_1_closes_as_safe`, `test_zalo_reply_2_keeps_the_incident_open_as_a_case` |
| FR-008 | ĐẠT | lint + typecheck + build; Playwright: tải, bấm "nghi lừa đảo" → xác nhận → `case_open`; tải lại ⇒ "đã được xử lý" |
| FR-009 | ĐẠT phần máy chủ | `scripts/e2e-m1.sh` |
| FR-010 | ĐẠT | quét regex số điện thoại (mã nguồn, phản hồi API, payload job) + `gitleaks dir --config .gitleaks.toml` sạch |

## Lệnh đã chạy (16/10/2026)

| Lệnh | Kết quả |
|---|---|
| `uv run --directory backend pytest -q` | 995 passed (trước rà soát: 983 passed + **5 error** — cả 5 test của spec 023 lỗi fixture, thiếu khóa dữ liệu giả) |
| `uv run --directory backend ruff check . && ruff format --check .` | sạch |
| `bash scripts/e2e-m1.sh` | 5/5 bước tự động đạt; bước 6 in CHƯA TỰ ĐỘNG |
| `python3 scripts/check-spec-trace.py` | 10 spec, 0 lỗi |
| `pnpm --dir apps/web lint && typecheck && build` | sạch; route `ƒ /a/[token]` |
| Đột biến: `emergency_pause → resolved_prevented` | 2 test đỏ (đã khôi phục) |
| uvicorn + `next start` thật, gọi `/v1/action/<token>` | log truy cập ghi `/v1/action/***`, 0 lần xuất hiện token |

## Còn mở / BLOCKED

- p95 Zalo thật ≤ 10 s: cần token bot (P0-08) — cùng chặn với spec 002.
- Chặng Android ↔ máy chủ trong `e2e-m1.sh` (máy ảo gửi sự kiện tới API dev, đo SafePause + cảnh báo trên cùng một lần chạy).
- Cấp JWT người giám hộ (đăng nhập web) thuộc spec 027; `fallback_required` (hết hạn mức Zalo) chưa có kênh dự phòng gửi liên kết.
