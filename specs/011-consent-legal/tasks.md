# Công việc Spec 011: Văn bản đồng ý, DPIA rút gọn, quy trình thí điểm

`PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`. Tick một task chỉ khi `Verify` đã chạy xanh.
`GRADLE = ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/opt/android-studio/jbr PATH="/opt/android-studio/jbr/bin:$PATH" ./apps/android/gradlew -p apps/android`.
**Thẻ làn** (thêm 18/10 cho task chưa xong): `[A]` Android (`../hoicon-wt/android`), `[B]` server (`../hoicon-wt/server`). Task
T001–T009, T016–T017 làm trước khi có thẻ: đều là làn B.

## Giai đoạn 1: Lõi kiểm tra (đỏ trước)
- [x] T001 [FR-009, FR-010] Viết `backend/tests/contract/test_consent_texts.py` (đỏ vì chưa có văn bản/mô-đun) và
  `backend/src/hoicon/ops/consent_texts.py` (trích chữ, chuẩn hóa, sha256, manifest, `problems()`, CLI `check|write`);
  gồm cả test "DPIA nhắc đủ mọi mục đích" và "PILOT-PROTOCOL có đủ mục" (dùng ở T004/T005).
  · Verify: `$PYTEST tests/contract/test_consent_texts.py` đỏ đúng lý do (thiếu văn bản) trước khi có văn bản
- [x] T002 [FR-002, FR-003] Test bất biến phiên bản trên dữ liệu giả (`released`), test chuẩn hóa/sha256.
  · Verify: `$PYTEST tests/contract/test_consent_texts.py -k "released or normal or sha"`

## Giai đoạn 2: Văn bản
- [x] T003 [FR-001, FR-004, FR-005, FR-006] Soạn 10 tệp `docs/legal/consent/<purpose>.vi.md` + `README.md`, rồi
  `python -m hoicon.ops.consent_texts write` sinh `manifest.json`.
  · Verify: `$PYTEST tests/contract/test_consent_texts.py` xanh; `python -m hoicon.ops.consent_texts check` thoát 0
- [x] T004 [FR-007] Hoàn thiện `docs/PRIVACY-DPIA.md` (giữ phần quy trình đã cài đặt của 034).
  · Verify: test "DPIA nhắc đủ mọi mục đích" xanh
- [x] T005 [FR-008] Hoàn thiện `docs/PILOT-PROTOCOL.md`.
  · Verify: test "PILOT-PROTOCOL có đủ mục" xanh

## Giai đoạn 3: Rà soát và nghiệm thu
- [x] T006 [FR-005, FR-006] Chạy skill `privacy-audit` (mã ↔ chữ ↔ DPIA) và `ux-elder-reviewer` cho văn bản; sửa mục chặn/High.
  **Giới hạn:** chữ đã sửa; 3 văn bản (`llm_processing`, `voice_input`, `pilot_research`) vẫn CHẶN phát hành vì mã chưa thực thi lời hứa (xem `evidence.md`).
  · Verify: báo cáo ghi vào `evidence.md`; test xanh sau sửa
- [x] T007 [FR-011] Liệt kê (không sửa) chỗ Android hard-code chuỗi đồng ý cần đồng bộ cho làn A vào `evidence.md`.
  · Verify: `grep` các tệp Android liệt kê; không có thay đổi dưới `apps/android/`
- [x] T008 [FR-009] Kiểm độ nhạy bằng đột biến (đổi 1 ký tự, xóa 1 tệp, đổi enum, bỏ banner, thêm số điều luật).
  · Verify: mọi đột biến làm test đỏ
- [x] T009 [FR-001..FR-011] Bộ kiểm cuối: ruff, pytest toàn bộ, `hoicon-eval --suite smoke --compare baseline --shared-db-ok`,
  `check-spec-trace`, gitleaks `backend infra specs docs`; điền `evidence.md`; ROADMAP `P1-06` ở ◐.
  **Ghi chú:** `gitleaks dir backend` báo 4 phát hiện CHỈ ở tệp cấu hình cục bộ của máy dev (bị `.gitignore`, không nằm trong git;
  `backend/src`, `tests`, `migrations`, `eval` sạch); eval chạy trên DB `hoicon_eval` riêng (không cần `--shared-db-ok`).
  · Verify: mọi lệnh xanh

## BLOCKED
- [ ] T010 [FR-004, SC-007] Minh duyệt văn bản (`draft` → `approved`, ghi `released` khi đưa cho người thật). **BLOCKED**: Minh.
- [ ] T011 [SC-008] Người cao tuổi thật đọc thử, ghi chỗ khó hiểu. **BLOCKED**: cần thí điểm (029 giai đoạn 2).
- [ ] T012 [A] [FR-011] Đồng bộ **lại** chuỗi Android khi Minh sửa chữ lúc duyệt (T010): lặp T018 với phiên bản mới. **BLOCKED**: sau T010.
  (Đồng bộ lần đầu theo bản nháp `2026.10-v3` **không** chờ Minh: T018.)

## Phase 4: Convergence
- [ ] T013 [B] [FR-006, SC-006] Thực thi đồng ý `llm_processing` ở `llm_router`: người cao tuổi chưa đồng ý (hoặc đã rút) ⇒ không
  gọi nhà cung cấp LLM, rơi về mẫu soạn sẵn, ghi `agent_steps.fallback_used` + lý do `consent`. **BLOCKED** tới khi có khóa LLM thật
  (P0-08): trước đó máy chủ không gửi gì cho dịch vụ AI nên lời hứa giữ được; T019 chặn phát hành nếu mục đích này được "phát hành"
  trước khi task này xong. Quyết định (thực thi, không bỏ lời hứa): plan D8.
  · Verify: test "thiếu `llm_processing` ⇒ 0 lời gọi client, fallback" xanh; `hoicon-eval --suite smoke --compare baseline` không lệch
- [ ] T014 [B] [FR-006, SC-006] Thực thi đồng ý `pilot_research`: heartbeat của người chưa đồng ý vẫn nhận (bảo vệ cần nó) nhưng
  **không** vào báo cáo thí điểm (`ops pilot report`/`gate-m2`); báo cáo gộp theo nhóm khi < 3 gia đình thì ẩn. **BLOCKED** tới
  029 giai đoạn 2 (chưa có người tham gia thật). Quyết định: plan D8.
  · Verify: test "thiếu `pilot_research` ⇒ không có trong báo cáo" xanh; `consent_texts check` đạt
- [ ] T015 [B] Giữ `voice_input.vi.md` ở trạng thái chặn phát hành cho tới khi tính năng trả lời bằng giọng nói tồn tại (spec 004) và sửa chữ theo thực tế per FR-006 (partial). **BLOCKED**: 004.
- [x] T016 Sửa `lookups.vi.md` để nói cách từ chối/rút, và thêm luật máy kiểm "mỗi văn bản có cụm thoát" vào `style_problems` per FR-006 (partial).
  · Verify: `$PYTEST tests/contract/test_consent_texts.py` xanh; đột biến bỏ cụm thoát ⇒ đỏ; `consent_texts check` rc = 0
- [x] T017 Chạy lại `ux-elder-reviewer` trên các văn bản đã sửa per SC-006 (partial).
  · Verify: báo cáo ghi vào `evidence.md`, 0 mục Chặn mới

## Wave 2 (18/10/2026 — từ `/speckit-analyze` và tồn đọng Wave 1)

Thứ tự: T018 → T019 → T020; T021 độc lập. T018 làm trước 028 T023 (màn đồng ý `drills` dùng chuỗi của T018).

- [x] T018 [A] [FR-002, FR-011] Đồng bộ chuỗi đồng ý Android theo `docs/legal/consent/manifest.json` (bản nháp `2026.10-v3`, không chờ
  Minh — các văn bản chưa `released`, chưa có người dùng thật): mỗi dòng giữa `BEGIN-TEXT`/`END-TEXT` của
  `<purpose>.vi.md` là **một** chuỗi tài nguyên, đúng thứ tự, cho 7 mục đích app đang hiện (`core_protection`, `guardian_alerts`,
  `lookups`, 3 trang quyền, `drills` — chuẩn bị cho 028 T023); `ConsentLedger.VERSION = "2026.10-v3"`; E3/E4/E10 hiện lại chữ mới
  (đổi phiên bản ⇒ hỏi lại đồng ý, đúng luật 7); mảng đọc to (`*_speech`) theo chữ mới. Sửa `ConsentTextsPinTest` để ghim **sha
  của `manifest.json`** (đọc tệp qua system property như `hoicon.appStrings`) thay vì sha chép tay ⇒ đổi văn bản trong `docs/`
  mà quên Android thì test đỏ. Chụp E3/E4/E10 ở 100% + 200% (`hc-api36`), gọi `ux-elder-reviewer` (bố cục thẻ, 158 từ ở 200%).
  Danh sách chỗ cần sửa: mục "Android đang hard-code chuỗi đồng ý" trong `evidence.md`.
  · Verify: `$GRADLE :app:testDebugUnitTest --tests '*ConsentTextsPinTest*' :app:testDebugUnitTest :app:lintDebug`; ảnh + báo cáo
  reviewer trong `evidence.md`; `python3 scripts/emu-scenario.py --avd hc-api36 --scenario fake_police` vẫn ĐẠT (đường dừng an toàn
  không đổi)
- [x] T019 [B] [FR-003, SC-006] Chốt chặn phát hành cho 3 mục đích hứa điều mã chưa làm (`llm_processing`, `voice_input`,
  `pilot_research`): test `backend/tests/contract/test_consent_release_block.py` — mục đích nào trong 3 mục đích này có mặt trong
  `released` hoặc `status: approved` của `manifest.json` thì **phải** có tệp test thực thi tương ứng
  (`tests/integration/test_consent_enforcement_<purpose>.py`), nếu không thì đỏ. Test chạy trong CI mọi PR (job `backend/test`), nên
  không ai đánh dấu "phát hành" được khi lời hứa chưa có mã. Không cần khóa, chạy được ngay. Không sửa `scripts/release-gate.sh`
  (tệp của làn A, kiểm AAB).
  · Verify: `$PYTEST tests/contract/test_consent_release_block.py`; đột biến: thêm `llm_processing` vào `released` trên bản sao tạm
  (`monkeypatch` đường dẫn manifest) ⇒ đỏ
- [ ] T020 [B] [FR-006, SC-006] Thực thi 3 lời hứa khi tính năng có thật: `llm_processing` (T013, khi P0-08), `pilot_research` (T014,
  khi 029 giai đoạn 2), `voice_input` (T015, khi spec 004 có trả lời bằng giọng nói). Mỗi lời hứa xong ⇒ thêm tệp
  `test_consent_enforcement_<purpose>.py` và T019 cho phép phát hành mục đích đó. **BLOCKED** tới khi tính năng có thật.
  · Verify: T019 xanh với mục đích đã chuyển `approved`
- [ ] T021 [B] [FR-006] Kiểm đồng ý ở route đọc web của người giám hộ (027: `/v1/guardian/incidents*`, `/v1/runs/*` qua phiên web):
  người cao tuổi đã rút `guardian_alerts` ⇒ danh sách chỉ còn sự cố **trước** lúc rút (hoặc rỗng — chọn theo quyết định ★ của Minh ở
  MASTER-PLAN §8, mặc định: rỗng), chi tiết ⇒ 404. Tên mục đích lấy từ một hằng số (đổi sang mục đích mới nếu Minh tách) — plan D9.
  · Verify: `$PYTEST tests/integration/test_guardian_incidents.py tests/integration/test_guardian_consent_gate.py`


## Wave 4 (23/10/2026) — bố cục màn đồng ý theo `ux-elder-reviewer` (evidence "đọc 15 ảnh", 22/10)

Tách hai loại: **bố cục** (làn A làm ngay, không đổi chữ trong `docs/legal/consent/`) và **chữ** (chờ Minh duyệt cùng T010 —
MASTER-PLAN §8 mục 12; không tăng phiên bản văn bản trước khi Minh quyết).

- [ ] T022 [A] [FR-011] Bố cục, không đổi chữ đồng ý: (a) màn "Xong rồi" (cuối E4) có dải "Kéo xuống đọc tiếp ↓" khi còn chữ phía
  dưới — dùng lại thành phần gợi ý cuộn của E7 (`SafePauseScreen.kt`), không chép mã; (b) trang quyền E4: nút "Mở cài đặt" đứng ngay
  sau đoạn đầu (trước 3 đoạn giải thích còn lại), vẫn ≤ 2 hành động chính; (c) nhãn "✗ Chưa bật"/"✓ Đã bật" ≥ 20sp đậm, kèm biểu
  tượng + chữ (luật 15); (d) dòng "Đã kết nối với …" giữ tên gia đình do người giám hộ đặt (mục Cao của reviewer là dữ liệu thử, không
  phải lỗi sản phẩm) — không sửa. Chụp E3, E4 (cả 3 trang quyền), "Xong rồi", E10 ở 100% + 200% `hc-api36`; `ux-elder-reviewer` ⇒
  0 Chặn/0 Cao.
  · Verify: `apps/android/gradlew -p apps/android :app:testDebugUnitTest --tests '*ConsentManifestPinTest*' :app:testDebugUnitTest :app:lintDebug`
  (chuỗi đồng ý không đổi ⇒ sha vẫn khớp); ảnh + báo cáo reviewer trong `evidence.md` mục "Wave 4"
