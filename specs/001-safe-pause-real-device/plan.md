# Implementation Plan: Dừng an toàn — số đo máy thật và hoàn tất spike S1/S2

**Branch**: `feat/001-safe-pause-real-device` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-safe-pause-real-device/spec.md`

## Summary

Hoàn tất spike S1/S2 bằng **đo đạc và sửa nhỏ**, không đổi cơ chế cảm biến:

1. Thêm tham số `variant=view|compose` cho bộ đo `:latency`, chạy thử trên AVD 36/34.
2. Chạy trên ≥ 2 máy thật FTL cho cả hai biến thể E7, ghi số vào `device-matrix.md` + spike S2 §7, đề xuất đóng phần
   "Chưa chốt" của ADR-007 qua PR.
3. Kiểm đường dự phòng khi thu hồi SAW (FSI, AVD 34/36).
4. Sửa tiêu đề demobank chồng dòng.
5. Bộ ảnh 100/200% → `ux-elder-reviewer`.
6. Khắc phục `tts_unavailable` trên AVD Linux bằng cách chuẩn bị môi trường (không đổi luật chọn giọng offline của app).

## Technical Context

**Language/Version**: Kotlin 2.4 (Android, minSdk 29, target/compileSdk 36) · Bash/Python cho script đo

**Primary Dependencies**: Compose + Material 3 (demobank, E7 biến thể Compose) · AndroidX Test instrumentation (`:latency`) ·
gcloud CLI (Firebase Test Lab) — không thêm thư viện

**Storage**: N/A (kết quả đo là tệp FTL + bảng trong docs)

**Testing**: `apps/android/gradlew -p apps/android :rules:test :app:lintDebug :demobank:lintDebug` ·
`:latency:connectedDebugAndroidTest` trên AVD · `python scripts/emu-scenario.py` · `bash scripts/ftl-latency.sh`

**Target Platform**: AVD hc-api36 (Android 16), hc-api34 (Android 14) trên máy Linux của Tiến · FTL máy thật: Samsung
dòng A Android 14 + Pixel Android 15/16

**Project Type**: monorepo mobile + API + web (spec này chỉ làn A)

**Performance Goals**: `app_foreground → pause_shown` p95 ≤ 3 s (máy thật); dự phòng không SAW ≤ 3 s tới câu nói đầu

**Constraints**: đường găng offline, không mạng/LLM · FTL Spark 5 lượt máy thật/ngày · RAM 14 GB: một emulator mỗi lúc,
không chạy Gradle song song với làn B

**Scale/Scope**: 2 máy thật × 2 biến thể × (10 nguội + 10 ấm); 2 AVD

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Nguồn: `.specify/memory/constitution.md`.

| # | Nguyên tắc | Feature này đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn offline ≤ 3 s, không chặn vĩnh viễn | Có (đo) | Không đổi cơ chế; FR-010 + `emu-scenario.py` hồi quy AVD 36/34 |
| II | Riêng tư: không PII thô, quyền Android cấm | Có (bộ đo, debug) | Cuộc gọi mô phỏng, số hư cấu; không quyền mới; receiver mô phỏng + FSI chỉ ở `src/debug` (FR-011, CI kiểm manifest release) |
| III | LLM chỉ nâng, qua `llm_router` | Không | — |
| IV | Công khai AI, đồng ý chỉ ghi thêm | Có (thông báo dự phòng) | Giữ phụ đề; `AiDisclosureCopyTest` xanh |
| V | Hợp đồng trước, migration bất biến | Không | Không đổi schema |
| VI | UX người cao tuổi | Có | Ảnh 100/200% + `ux-elder-reviewer` (US3) |
| VII | Bằng chứng trung thực | Có (trọng tâm) | Mỗi số ghi loại máy/model/ngày/n/nguồn; trượt ghi đúng số; thiếu Firebase ⇒ BLOCKED |
| VIII | Ít code nhất, tái sử dụng trước | Có | Chỉ thêm 1 tham số cho bộ đo + 1 sửa bố cục; còn lại là đo và tài liệu |
| IX | Chặn phát hành | Có | Không đưa bản build cho người thật; FTL là máy thử của Google, không phải người dùng |

Kết quả: **ĐẠT**, không có vi phạm (Complexity Tracking để trống).

## Tái sử dụng *(mandatory — điền TRƯỚC khi thiết kế mới)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới (lý do) |
|---|---|---|
| Đo độ trễ máy thật | `apps/android/latency/.../SafePauseLatencyTest.kt` (args `runs`, `compile`; nguội/ấm; `latency.json`) | **mở rộng**: thêm arg `variant` |
| Chạy trên FTL | `scripts/ftl-latency.sh` (`--environment-variables runs=10,compile=speed`) | **mở rộng**: truyền `variant` |
| Chuyển E7 sang Compose | `SafePauseActivity` đọc `files/spike_compose_pause` (chỉ debug) | dùng lại qua `run-as … touch/rm` từ bộ đo |
| Kịch bản máy ảo + hồi quy | `scripts/emu-scenario.py` (`fake_police`, `--prep`, mốc `HC_TIMING`) | dùng lại |
| Mô phỏng cuộc gọi | `ScenarioReceiver` (src/debug, quyền `DUMP`) | dùng lại |
| Thông báo dự phòng + FSI log `fsi=` | `sensing/Notifications.kt` (FSI chỉ debug) | dùng lại để đo |
| Chọn giọng offline | `pause/Speaker.kt` (engine Google, `isNetworkConnectionRequired == false`) | **không đổi** — chỉ chuẩn bị AVD |
| Môi trường Linux | `scripts/android-env.sh`, `docs/EMULATOR.md` §1.2 | mở rộng tài liệu (TTS) |

## Project Structure

### Documentation (this feature)

```text
specs/001-safe-pause-real-device/
├── spec.md · plan.md · research.md · quickstart.md
├── contracts/README.md  # không có hợp đồng mới
├── tasks.md
├── checklists/requirements.md
└── evidence.md          # tạo ở phase cuối
```

### Source Code (repository root)

```text
apps/android/latency/src/main/java/vn/hoicon/latency/SafePauseLatencyTest.kt   # [A] arg variant
apps/android/demobank/src/main/java/vn/hoicon/demobank/MainActivity.kt         # [A] tiêu đề chuyển tiền
scripts/ftl-latency.sh                                                          # [A] truyền variant
docs/spikes/device-matrix.md · docs/spikes/P1-S2-dung-an-toan.md · docs/spikes/P1-S1-cam-bien.md
docs/EMULATOR.md (§1.2 TTS Linux) · (không sửa docs/adr/**: đề xuất đóng "Chưa chốt" của ADR-007 nằm trong P1-S1-cam-bien.md + evidence.md, Minh duyệt rồi sửa ADR qua PR riêng)
docs/ROADMAP.md (chỉ dòng P1-S1/P1-S2)
```

**Structure Decision**: chỉ làn A + tài liệu; không đụng `backend/**`, `apps/web/**`, `docs/schemas/**`.

## Thiết kế & trade-off

- **Biến thể E7 trong bộ đo** — chọn tham số `variant` + `run-as` bật/tắt tệp cờ có sẵn, thay vì build hai APK: không
  đổi code sản phẩm, cùng một bản cài, đo xen kẽ được. Rủi ro: `run-as` hỏng trên máy FTL nào đó ⇒ bộ đo ghi
  `variant_unavailable` và dừng biến thể đó (không đo nhầm).
- **Ngân sách FTL** (5 lượt/ngày): mỗi lượt = 1 máy × 1 biến thể (10 nguội + 10 ấm) ⇒ 4 lượt cho 2 máy × 2 biến thể;
  lượt thứ 5 dành chạy lại nếu lỗi.
- **TTS trên AVD Linux** — sửa môi trường, không sửa app: luật "chỉ giọng offline" (SEC-8) là bất biến bảo mật/UX.
- **ADR-007** — không sửa file ADR; chỉ viết đề xuất điền số vào mục "Chưa chốt" và đổi trạng thái theo số đo; quyết định cơ chế giữ nguyên. Nếu số máy
  thật trượt và cần đổi quyết định (ví dụ bắt buộc View thuần) ⇒ ghi đề xuất, quyết định ở P2-05/Minh.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
