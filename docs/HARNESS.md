# Harness Claude Code của HỏiCon

Cách "đội chuyên gia tác tử" được cấu hình: hook, quyền, plugin, subagent, skill, RTK. Mọi thứ ở **phạm vi project**
(`.claude/`, commit vào git) trừ khi ghi rõ khác.

## 1. Thành phần

| Thành phần | Vị trí | Vai trò |
|---|---|---|
| Hướng dẫn chung | `CLAUDE.md` (`AGENTS.md` trỏ về đây) | Luật bắt buộc, lệnh, Definition of Done |
| Quyền + hook + plugin | `.claude/settings.json` | allow/ask/deny, 7 hook, `enabledPlugins`, `extraKnownMarketplaces` |
| Ghi đè cá nhân | `.claude/settings.local.json` | gitignore — không commit |
| Hook | `.claude/hooks/*.mjs` (+ `lib.mjs`) | Chặn lệnh nguy hiểm, bảo vệ quyền riêng tư, format, kiểm tra khi dừng |
| Test hook | `.claude/hooks/test/hooks.test.mjs` | `node --test ".claude/hooks/test/*.test.mjs"` (64 ca) — chạy trong CI |
| Subagent | `.claude/agents/*.md` | 8 chuyên gia (bảng §4) |
| Skill dự án | `.claude/skills/*/SKILL.md` | Quy trình lặp lại (bảng §5) |
| Cài plugin + RTK | `scripts/setup-claude-tools.sh` | Bước 1 thêm marketplace (đọc mã nguồn), bước 2 `--install` |

## 2. Hook

| Sự kiện | Matcher | Hook | Hành vi |
|---|---|---|---|
| SessionStart | `startup\|resume\|compact` | `session-start.mjs` | Đếm ngược 15/11 · 10/01 · 27/02, khối STATUS của `docs/ROADMAP.md` + task kế tiếp, git, Postgres 15432 / API 18000, số máy adb |
| PreToolUse | `Bash\|PowerShell` | `guard-shell.mjs` | Chặn (exit 2): force push, push vào main, `reset --hard`, `clean -f`, `pip install` (trừ `uv pip`), `compose down -v`, `docker volume rm`, dừng container không thuộc HỏiCon, Alembic vào DB ngoài máy, xóa migration, `rm -rf` ngoài thư mục build/cache, `Remove-Item -Recurse`, đọc `.env`/keystore/`secrets` |
| PreToolUse | `Bash` | `rtk-rewrite.mjs` | Chuyển lệnh qua `rtk hook claude` để nén output (§6). Không bao giờ chặn |
| PreToolUse | `Edit\|Write\|MultiEdit` | `guard-migrations.mjs` | Không sửa migration đã có trên `origin/main` |
| PreToolUse | `Edit\|Write\|MultiEdit` | `guard-privacy.mjs` | Chặn quyền Android bị cấm trong `AndroidManifest.xml`; số điện thoại VN thô trong mã nguồn (trừ tests/fixtures/eval/data/docs); log/print biến PII chưa `mask()` |
| PostToolUse | `Edit\|Write\|MultiEdit` | `format-on-edit.mjs` | ruff (`.py`), ktlint (`.kt`), prettier (web/docs); bỏ qua `docs/research`, `docs/proposal` |
| Stop | — | `stop-check.mjs` | Chỉ kiểm tra phần đã đổi trong ≤ 90 s: ruff + `pytest tests/unit`, `tsc` web, `gradlew :rules:test`; cache theo dấu vân tay. Tắt tạm: `HOICON_SKIP_STOP_HOOK=1` |

**Quy ước lệnh hook:** một chuỗi duy nhất `node "$CLAUDE_PROJECT_DIR/.claude/hooks/<tên>.mjs"`.
> ⚠️ **Đã gặp (08/10/2026):** `claude plugin install --scope project` ghi lại `settings.json` và **xóa trường `args`**
> của hook dạng `{"command":"node","args":[…]}` ⇒ mọi hook thành `node` trơn. Vì vậy chỉ dùng dạng một chuỗi.
> `scripts/setup-claude-tools.sh` kiểm tra lại số hook (7/7) sau khi cài plugin. Sau mỗi lần cài/gỡ plugin: `git diff .claude/settings.json`.

**Sửa hook:** sửa file `.mjs` → thêm ca vào `hooks.test.mjs` → chạy test. Hook mới cần `/hooks` hoặc khởi động lại Claude Code mới nạp.

## 3. Quyền

- **allow:** `uv run` **chỉ** cho `pytest`, `ruff`, `alembic`, `uvicorn hoicon.api.main:app`, `python -m hoicon.ops.check_keys`
  (siết 08/10 theo review bảo mật — `uv run *` cũ cho phép `uv run python -c …` đọc `.env` không hỏi); `uv sync|lock|add|tree`,
  script `pnpm`, `gradlew`, adb/emulator/Android CLI, `docker compose -f infra/compose.dev.yml`, `docker ps`,
  `scripts/emu-scenario.py`, git chỉ-đọc + `switch`/`add`, `gh pr|run view|list`, `rtk`. Lệnh `uv run` khác ⇒ hỏi Minh.
- **ask:** `git commit|push`, worktree add/remove, `gh pr create|merge`, `gh repo`, script cài đặt/dừng stack khác/deploy, `compose.prod`, `db:reset`, gỡ app trên máy ảo.
- **deny:** đọc/sửa `.env*` (kể cả `.env.tmp`), `*.jks`, `*.keystore`, `keystore.properties`, `google-services.json`,
  `D:/secrets/**`; `git add -f/--force`; mọi lệnh chạy `hoicon.ops.init_env` (chỉ Minh chạy); force push; push vào main.
- **guard-shell (lớp 2, không phụ thuộc permission):** chặn thêm script nội tuyến (`python -c`, `node -e`, here-doc)
  chạm tới `get_secret_value`/`dotenv`/`.env`/biến `HOICON_*KEY|TOKEN|SECRET|PEPPER`, chạy `init_env`, `git add -f`.
  Luật này thiên về an toàn nên có thể chặn nhầm commit message/here-doc chỉ *nhắc tới* các chuỗi đó ⇒ ghi message
  ra file trong scratchpad rồi `git commit -F <file>`.
- `ask`/`deny` ở project thắng `allow` cấp người dùng (settings cấp người dùng của Minh có `Bash(git push *)` — trong repo này vẫn bị hỏi).

## 4. Subagent ("đội chuyên gia")

| Tác tử | Vai trò | Gọi khi |
|---|---|---|
| `android-engineer` | Kotlin/Compose, chính sách Play, giới hạn nền Android 12–16, máy ảo | Mọi task Android |
| `agent-architect` | LangGraph, interrupt, prompt có phiên bản, MCP, `llm_router` (đọc skill `claude-api` trước) | `backend/src/hoicon/agents`, `mcp_servers` |
| `backend-db` | FastAPI, SQLAlchemy, Alembic, state machine, sinh client TS | API, DB |
| `web-ux` | Next.js, trace/eval/booth, Playwright screenshot | Web |
| `security-privacy-reviewer` (chỉ đọc) | PII, đồng ý, công khai AI, injection, manifest vs Play, webhook | Diff đụng dữ liệu cá nhân/LLM/manifest/Zalo; mỗi gate |
| `ux-elder-reviewer` (chỉ đọc) | Tiếp cận người cao tuổi, giọng văn tiếng Việt | Mỗi màn hình, mẫu tin Zalo |
| `qa-eval` (sonnet) | Kịch bản eval/test, chạy suite, phân loại hồi quy | Sau đổi prompt/đồ thị; trước gate |
| `judge` | Chấm theo thể lệ TSC 2027 §5, câu hỏi phản biện | Trước nộp/quay video; sau mỗi gate |

## 5. Skill dự án

`feature-slice` · `phase-gate` · `ui-screen` · `android-emulator-test` · `privacy-audit` · `add-scam-scenario` ·
`run-eval` · `pitch-sync`. Sẽ thêm khi cần lần đầu: `state-transition`, `new-migration`, `seed-demo`, `demo-reset`,
`consent-copy`, `zalo-flow`.

## 6. Plugin & RTK

| Plugin | Nguồn | Trạng thái | Ghi chú review mã nguồn |
|---|---|---|---|
| ponytail | DietrichGebert/ponytail | bật | Hook SessionStart/SubagentStart/UserPromptSubmit ghi file nhỏ trong `~/.claude`; không gọi mạng |
| ui-ux-pro-max | nextlevelbuilder/ui-ux-pro-max-skill | bật | Chỉ skill + dữ liệu |
| frontend-design, security-guidance, pr-review-toolkit, commit-commands | claude-plugins-official | bật | |
| typescript-lsp, pyright-lsp | claude-plugins-official | bật | Binary: `npm i -g pyright typescript-language-server typescript` (đã cài 08/10) |
| kotlin-lsp | claude-plugins-official | **tắt** | Server nền IntelliJ ~1–2 GB RAM — máy dev chỉ còn ~1–3 GB khi chạy máy ảo + Gradle. Kotlin kiểm tra qua Gradle. Bật lại khi có RAM: tải bản standalone Windows ở github.com/Kotlin/kotlin-lsp/releases về `D:\tools\kotlin-lsp`, đưa `kotlin-lsp` lên PATH, đổi `enabledPlugins` thành `true` |
| example-skills | anthropics/skills | bật | webapp-testing, skill-creator… |
| caveman | JuliusBrussee/caveman | **tắt** | Bật tay khi cần: `/caveman lite` |

**RTK** (Rust Token Killer, v0.50) nén output CLI để tiết kiệm ngữ cảnh.
- Cài: `winget install rtk-ai.rtk`. Gói portable của winget **không tạo shim** trong `WinGet\Links` ⇒ chép `rtk.exe` vào
  `%USERPROFILE%\.local\bin` (đã có trên PATH, cạnh `uv.exe`). Script cài làm việc này. Nâng cấp RTK ⇒ chép lại.
- **Không chạy `rtk init -g`** (ghi hook vào settings toàn cục). Hook dự án `rtk-rewrite.mjs` gọi `rtk hook claude`.
- Hook chỉ chạy khi `rtk` có trên PATH: lệnh được viết lại thành `rtk …`; nếu rtk không có trên PATH mà vẫn viết lại,
  mọi lệnh Bash sẽ lỗi `rtk: command not found` (đã gặp 08/10).
- RTK "biết quyền": chỉ trả `allow` cho lệnh nó coi là an toàn; lệnh nguy hiểm không bị viết lại ⇒ `guard-shell`
  vẫn phán xử. `guard-shell` trả exit 2 thì lệnh bị chặn dù RTK trả `allow` (deny thắng).
- Cần output đầy đủ khi debug: `rtk run <lệnh>`; tắt hẳn: `HOICON_DISABLE_RTK=1`.

## 7. MCP (`.mcp.json`)

context7 (tài liệu thư viện, `@upstash/context7-mcp@4.2.0`), playwright (screenshot web, `@playwright/mcp@0.0.83`) —
ghim phiên bản, trên Windows bọc `cmd /c npx …`. Lần chạy đầu `npx` phải tải gói nên health check có thể báo "Failed
to connect"; chạy `claude mcp list` lần nữa (08/10: cả hai ✓ Connected). Tùy chọn sau: mobile-mcp để tác tử
nhìn/chạm màn hình máy ảo (đánh giá mã nguồn trước khi bật).

**GitHub CLI:** `gh` 2.102 đăng nhập 08/10 bằng thông tin GitHub đã lưu trong Git Credential Manager
(`git credential fill | gh auth login --with-token`, token không in ra; scope `repo, workflow, read:org`).

## 8. Việc Minh làm tay

- Hook, plugin, 8 subagent, MCP đã nạp (kiểm 08/10: `claude plugin list`, `claude mcp list`). `/hooks` để xem hook.
- Ủy quyền connector claude.ai (Gmail, Calendar, Drive) nếu muốn dùng — hiện chưa ủy quyền.
- Settings cấp người dùng đã dọn 08/10 (bỏ `Bash(pip install *)`, sửa `additionalDirectories`); bản sao lưu
  `%USERPROFILE%\.claude\settings.json.bak-2026-10-08`.
