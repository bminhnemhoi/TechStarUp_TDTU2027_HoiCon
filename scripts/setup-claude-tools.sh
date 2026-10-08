#!/usr/bin/env bash
# Cài bộ skill/plugin cộng đồng cho Claude Code ở PHẠM VI PROJECT (ghi vào .claude/settings.json) và RTK.
# Chạy một lần trên máy (Git Bash) từ thư mục gốc repo:  bash scripts/setup-claude-tools.sh
# Bước 1 chỉ THÊM marketplace (clone về ~/.claude/plugins/marketplaces) để đọc mã nguồn trước;
# bước 2 cài plugin sau khi đã review (chạy lại với --install). Xem docs/HARNESS.md.
set -euo pipefail

if ! command -v claude >/dev/null 2>&1; then
  echo "Không tìm thấy lệnh 'claude'. Cài Claude Code trước." >&2
  exit 1
fi

MODE="${1:-}"

echo "== Marketplaces =="
claude plugin marketplace add anthropics/claude-plugins-official || true
claude plugin marketplace add anthropics/skills || true
claude plugin marketplace add DietrichGebert/ponytail || true
claude plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill || true
claude plugin marketplace add JuliusBrussee/caveman || true

if [ "$MODE" != "--install" ]; then
  echo
  echo "Đã thêm marketplace. ĐỌC MÃ NGUỒN trong ~/.claude/plugins/marketplaces/ (hooks, scripts, MCP) rồi chạy:"
  echo "  bash scripts/setup-claude-tools.sh --install"
  exit 0
fi

echo "== Plugins (scope project) =="
install() { claude plugin install "$1" --scope project || echo "!! Không cài được $1 — kiểm tra tên trong /plugin" >&2; }
install ponytail@ponytail
install ui-ux-pro-max@ui-ux-pro-max-skill
install frontend-design@claude-plugins-official
install security-guidance@claude-plugins-official
install pr-review-toolkit@claude-plugins-official
install commit-commands@claude-plugins-official
install typescript-lsp@claude-plugins-official
install pyright-lsp@claude-plugins-official
install kotlin-lsp@claude-plugins-official
install example-skills@anthropic-agent-skills          # webapp-testing, skill-creator…
install caveman@caveman
claude plugin disable caveman@caveman --scope project || true   # mặc định TẮT; bật tay khi cần: /caveman lite

echo "== RTK (Rust Token Killer) =="
# KHÔNG chạy 'rtk init -g' (ghi hook vào settings toàn cục). Hook dự án .claude/hooks/rtk-rewrite.mjs
# gọi 'rtk hook claude' và chỉ chạy khi rtk có trên PATH — lệnh được viết lại thành 'rtk …'.
if ! command -v rtk >/dev/null 2>&1; then
  if command -v winget >/dev/null 2>&1; then
    winget install --id rtk-ai.rtk -e --accept-source-agreements --accept-package-agreements || true
    # winget gói portable không luôn tạo shim trong WinGet\Links ⇒ chép exe vào ~/.local/bin (đã có trên PATH)
    exe=$(ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/rtk-ai.rtk_*/rtk.exe 2>/dev/null | head -1)
    [ -n "$exe" ] && mkdir -p "$HOME/.local/bin" && cp "$exe" "$HOME/.local/bin/rtk.exe"
  else
    echo "Cài RTK theo https://github.com/rtk-ai/rtk rồi chạy lại." >&2
  fi
fi
command -v rtk >/dev/null 2>&1 && rtk --version || echo "!! rtk chưa có trên PATH — hook RTK sẽ tự bỏ qua." >&2

# 'claude plugin install --scope project' ghi lại .claude/settings.json: kiểm tra hook còn nguyên.
node -e "const s=require('./.claude/settings.json');const n=Object.values(s.hooks||{}).flat().flatMap(m=>m.hooks).filter(h=>/\.claude\/hooks\/.+\.mjs/.test(h.command)).length;if(n<7){console.error('!! settings.json mất hook ('+n+'/7) — khôi phục từ git');process.exit(1)}console.log('hooks OK ('+n+'/7)')"

echo "Xong. Mở lại Claude Code trong thư mục repo và chạy /plugin để kiểm tra."
