# AGENTS.md

Hướng dẫn cho mọi tác tử lập trình (Claude Code, Codex, Gemini CLI, Android CLI…) làm việc trong repo HỏiCon.

- **Nguồn quy tắc chính là `CLAUDE.md`** — đọc và tuân theo toàn bộ (quyền riêng tư, Android cấm quyền, LLM chỉ nâng rủi ro, công khai AI, Definition of Done).
- Tài liệu nguồn sự thật nằm trong `docs/` (ROADMAP, PRD, ARCHITECTURE, DATA-MODEL, API, AGENTS, DESIGN-SYSTEM, PRIVACY-DPIA, PLAY-POLICY, EMULATOR).
- Chỉ làm task có mã trong `docs/ROADMAP.md`. Báo cáo bằng tiếng Việt. Không commit/push khi chưa được yêu cầu.
- Không đọc `.env*`, keystore, `D:/secrets`. Không hardcode số điện thoại thật; fixture hư cấu đặt trong `tests/` hoặc `data/`.
- Next.js: API thay đổi giữa các phiên bản — đọc tài liệu trong `apps/web/node_modules/next/dist/docs/` trước khi dùng API lạ.
- Android: dùng Android CLI (`D:/Android/Sdk/cmdline-tools/latest/bin/android.exe`) cho `emulator`, `run`, `layout`, `screen`, `docs`; xem `docs/EMULATOR.md`.
