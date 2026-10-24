# Công việc Spec 032: Coach hằng tuần + báo "mất bảo vệ"

## Cách chạy

- **Chạy một mạch** ở worktree làn B (`../hoicon-wt/server`, nhánh `feat/032-coach-weekly`); task `[A]` T011 chạy ở
  `../hoicon-wt/android` (chỉ đo và ghim sha, không đổi hành vi Android).
- **Thẻ làn:** `[B]` server, `[A]` Android/máy ảo, `[AB]` chung.
- **Biến:** `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache` ·
  `GRADLE = ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/opt/android-studio/jbr PATH="/opt/android-studio/jbr/bin:$PATH" ./apps/android/gradlew -p apps/android`
- **Số migration:** số kế tiếp sau head; nếu 031 merge trước thì đổi `down_revision` và ghi vào evidence.
- **Không có hợp đồng mới trong `docs/schemas/`:** tin Zalo là văn bản mẫu; lệnh "tắt/bật tin tuần" là giá trị nội bộ của job
  `zalo_update` (không có lược đồ công khai). Test luật 6 thay cho lược đồ.
- **Dừng:** `Verify` đỏ 2 lần ⇒ dừng task, chẩn đoán, không sửa test cho xanh. Không gọi Zalo thật (`HOICON_ZALO_MODE=mock`).

## Làn B

- [x] T001 [B] [FR-001] Migration cột `members.weekly_digest_enabled` + model + `tests/integration/test_schema_<số>.py`.
  · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head && $PYTEST tests/integration/test_schema_<số>.py`
- [x] T002 [B] [FR-005] Tách hàm độ phủ của `ops/pilot.py` thành hàm dùng chung (plan D3) nếu chưa là service; `ops pilot` gọi lại,
  hành vi không đổi.
  · Verify: `$PYTEST tests/integration/test_ops_pilot.py`
- [x] T003 [B] [FR-003, FR-005, FR-007] Mẫu tin trong `agents/texts.py`: `protection_silent`, `protection_permission_off`,
  `weekly_digest` (biến thể: có sự cố / không sự cố / chưa đủ dữ liệu), `digest_off_ack`, `digest_on_ack`. Test TDD (viết trước): mở
  đầu công khai AI; không chứa chữ "an toàn" dạng khẳng định ("an toàn", "đã an toàn" — mẫu phủ định "chưa chắc an toàn" được phép
  nếu cần); độ phủ làm tròn 5%; không dãy ≥ 4 chữ số ngoài giờ; câu xác nhận tắt nói "vẫn nhận cảnh báo khi có chuyện".
  · Verify: `$PYTEST tests/unit/test_coach_texts.py tests/unit/test_texts_zalo.py tests/unit/test_texts_and_threat.py`
- [x] T004 [B] [FR-002, FR-003] `services/coach_service.py::find_protection_lapses(now)` + job `protection_watch` mỗi giờ (khóa giờ VN,
  lũy đẳng), giờ im lặng 21:00–07:00 (hoãn tới 07:00), chọn người giám hộ hạng 1 rồi hạng 2, cờ `HOICON_PROTECTION_WATCH`. Test
  `tests/integration/test_protection_watch.py` với đồng hồ giả: 23 giờ ⇒ 0; 25 giờ ⇒ 1 tin; 48 lần chạy cùng đợt ⇒ 1 tin; heartbeat trở
  lại rồi mất ⇒ tin thứ hai; 2 khung `protected=false` ⇒ 1 tin; 1 khung ⇒ 0; thiết bị thu hồi / gia đình demo / chưa đồng ý
  `guardian_alerts` / cờ tắt ⇒ 0; 22:30 ⇒ hoãn tới 07:00; quét tin + job + `agent_steps` không có số điện thoại/h1.
  · Verify: `$PYTEST tests/integration/test_protection_watch.py`
- [x] T005 [B] [FR-004, FR-005, FR-008] Job `coach_weekly` (Chủ nhật 19:00 VN, khóa tuần ISO, tự xếp lần kế tiếp) + `agent_runs(graph
  ='coach')` + `agent_steps` (`collect`, `compose`, `send`, chỉ số đếm). Mẹo từ `data/coach/tips.vi.yaml` (`approved: false` ⇒ bản
  prod bỏ dòng mẹo; test cho cả hai chế độ). Test `tests/integration/test_coach_weekly.py`: số lần nhắc (loại diễn tập/demo), độ phủ,
  số bài luyện tập khớp seed; người giám hộ tắt bản tin ⇒ 0 tin cho người đó, người kia vẫn nhận; chạy hai lần cùng tuần ⇒ 1 tin;
  gia đình chưa có thiết bị ⇒ 0.
  Thêm `COPY data/coach /app/data/coach` vào `backend/Dockerfile` (ảnh 012 chỉ chép các thư mục `data/` được liệt kê) và kiểm trong
  `scripts/tests/test_deploy_vps.py`.
  · Verify: `$PYTEST tests/integration/test_coach_weekly.py && python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py`
- [x] T006 [B] [FR-006] Hạn mức: bản tin dừng ở `warn_pct`, tin mất bảo vệ đi tới `hold_pct`, cả hai `urgent=False`; tin sự cố không bị
  ảnh hưởng. Test đếm bằng `messages_out` giả lập 79% / 81% / 96% hạn mức.
  · Verify: `$PYTEST tests/integration/test_coach_weekly.py -k quota tests/integration/test_protection_watch.py -k quota tests/integration/test_notify_guardian.py`
- [x] T007 [B] [FR-007] `classify`: "tắt tin tuần"/"bật tin tuần" (bỏ dấu, hoa thường, khoảng trắng thừa) ⇒ `digest_off`/`digest_on`;
  handler `zalo_update` cập nhật `weekly_digest_enabled` + trả lời xác nhận qua `deliver`. Test: phân loại (gồm chữ gần giống không
  khớp); webhook không lưu chữ thô (`test_zalo_no_leak.py` vẫn xanh); người lạ (không phải người giám hộ) ⇒ không đổi gì.
  · Verify: `$PYTEST tests/unit/test_zalo_inbound.py tests/integration/test_zalo_webhook.py tests/integration/test_zalo_no_leak.py tests/integration/test_guardian_reply.py`
- [x] T008 [B] [FR-009] Văn bản đồng ý: câu của 032 **đã vào ở 031 T011** (bản gộp, chốt 22/10 — MASTER-PLAN §5 "Wave 3"). Ở đây
  chỉ: kiểm chữ khớp mã thật (job `coach_weekly` + `protection_watch` chạy), `PILOT-PROTOCOL.md` §4 thêm lại dòng đã bỏ. Minh bác
  I4 (MASTER-PLAN §8 mục 5) ⇒ bỏ câu "Họ được báo nếu HỏiCon bị tắt." của bản `2026.10-v4` (còn 153 từ), tăng `2026.10-v5`, `consent_texts write`,
  `ux-elder-reviewer`, và báo làn A chạy 032 T010.
  · Verify: `$PYTEST tests/contract/test_consent_texts.py && uv run --directory backend python -m hoicon.ops.consent_texts check`
- [x] T009 [B] [FR-011] `docs/AGENTS.md` (Coach: hai job, không LangGraph, plan D1), `docs/DATA-MODEL.md` (cột mới, khóa chống trùng),
  `docs/PRIVACY-DPIA.md` (dùng heartbeat để báo người giám hộ), ROADMAP "Ghi chú" (trace của lượt `coach` chưa hiện cho người giám
  hộ).
  · Verify: `grep -n "coach_weekly\|protection_watch" docs/AGENTS.md docs/DATA-MODEL.md` có kết quả

## Làn A

- [ ] T010 [A] [FR-009] Đồng bộ chuỗi `guardian_alerts` trên Android đã làm chung ở 031 T014 (bản gộp). Task này chỉ chạy khi T008 đổi chữ (Minh bác I4); không đổi ⇒ chạy Verify của 031 T014 một lần nữa rồi tick.
  · Verify: `$GRADLE :app:testDebugUnitTest --tests '*ConsentManifestPinTest*'`
- [x] T011 [A] [FR-010] Đo khoảng trống heartbeat trên `hc-api36` (và `hc-api34` nếu kịp) với backend dev: (a) bình thường 2 giờ, (b)
  `adb shell dumpsys deviceidle force-idle` 2 giờ, (c) `adb shell am set-standby-bucket vn.hoicon.sentinel rare` 4 giờ, (d) khởi động
  lại máy, (e) `adb shell am kill vn.hoicon.sentinel`. Đọc `device_heartbeats` bằng truy vấn đếm (không in định danh). Ghi khoảng
  trống dài nhất mỗi điều kiện vào evidence, ghi "máy ảo ≠ máy thật".
  · Verify: bảng 5 điều kiện có số trong `evidence.md`; khoảng trống dài nhất < 24 giờ, nếu không thì đề xuất ngưỡng mới trong spec

## Rà soát & nghiệm thu

- [x] T012 [AB] [FR-011] `ux-elder-reviewer` (5 mẫu tin) và `security-privacy-reviewer` (job, `agent_steps`, lệnh Zalo, đồng ý, hạn
  mức). Sửa mọi Chặn/Critical/High.
  · Verify: báo cáo trong `evidence.md`, không còn mục chặn chưa xử lý
- [x] T013 [AB] [FR-001..FR-011] Bộ kiểm cuối: `$PYTEST`; `ruff`; `hoicon-eval --suite smoke --compare baseline`; `$GRADLE
  :app:testDebugUnitTest`; gitleaks **từng thư mục** `backend/src`, `backend/tests`, `data/coach`, `docs/legal`,
  `specs/032-coach-weekly`; `check-spec-trace`. Điền `evidence.md`; ROADMAP `P2-17` ◐ (☑ khi SC-007 có số thí điểm hoặc Minh chấp nhận
  số máy ảo).
  · Verify: mọi lệnh xanh; check-spec-trace 0 lỗi

## BLOCKED (bên ngoài)

- [ ] T014 [AB] [SC-007] Đếm tin "mất bảo vệ" và số lần là báo nhầm (hỏi người giám hộ) trong 7 ngày thí điểm, theo hãng máy.
  **BLOCKED**: thí điểm (029 giai đoạn 2).
  · Verify: bảng theo hãng trong `evidence.md`
- [ ] T015 [B] [FR-005] Minh duyệt `data/coach/tips.vi.yaml` (`approved: true`). **BLOCKED**: Minh.
  · Verify: test "bản prod có dòng mẹo khi đã duyệt" xanh
