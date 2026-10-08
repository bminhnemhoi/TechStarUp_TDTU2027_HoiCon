// PreToolUse (Bash|PowerShell): block destructive or policy-breaking commands that permission rules cannot express.
import { block, readInput } from "./lib.mjs";

const input = readInput();
const cmd = String(input?.tool_input?.command ?? "");
if (!cmd) process.exit(0);

// Normalise whitespace for matching; keep original for messages.
const c = cmd.replace(/\s+/g, " ");

const SAFE_DELETE_TARGETS =
  /^(\.\/)?((apps\/(android|web)\/)?(node_modules|\.next|\.turbo|dist|out|coverage|test-results|playwright-report|build|\.gradle)|(apps\/android\/[\w-]+\/)build|backend\/(\.venv|\.pytest_cache|\.ruff_cache|htmlcov)|\.claude\/\.cache|eval\/reports\/tmp|docs\/proposal\/src\/(out|node_modules))(\/.*)?$/;

const rules = [
  {
    test: () => /\bgit\b.*\bpush\b.*(\s--force(-with-lease)?\b|\s-f\b|\s\+\S+)/.test(c),
    msg: "Force push bị cấm trong HỏiCon. Tạo commit mới hoặc hỏi Minh.",
  },
  {
    test: () => /\bgit\b.*\bpush\b(\s+\S+)?\s+(HEAD:)?(refs\/heads\/)?main\b/.test(c),
    msg: "Không push thẳng vào main. Push nhánh feat/* rồi mở Pull Request.",
  },
  {
    test: () => /\bgit\b.*\breset\b.*--hard\b/.test(c) || /\bgit\b.*\bclean\b.*-[a-z]*f/.test(c),
    msg: "git reset --hard / git clean -f có thể làm mất việc chưa commit. Hỏi Minh trước.",
  },
  {
    test: () => /(^|[;&|]\s*|\s)(python(3)?\s+-m\s+)?pip3?\s+install\b/.test(c) && !/\buv\s+pip\b/.test(c),
    msg: "Không cài gói Python vào môi trường global. Dùng `uv add <gói>` trong backend/ (hoặc `uv tool install` cho công cụ CLI).",
  },
  {
    test: () => /\bdocker\b.*\bcompose\b.*\bdown\b.*\s-v\b/.test(c) || /\bdocker\b.*\bvolume\b.*\b(rm|prune)\b/.test(c),
    msg: "Lệnh này xóa volume dữ liệu Postgres. Muốn reset DB local thì dùng `pnpm db:reset` (có xác nhận).",
  },
  {
    test: () =>
      /\bdocker\b.*\b(stop|rm|kill)\b/.test(c) && !/hoicon|infra\/compose\.\w+\.yml|stop-other-stacks/i.test(c),
    msg: "Không dừng/xóa container không thuộc HỏiCon bằng tay. Dùng `bash scripts/stop-other-stacks.sh` (có liệt kê trước).",
  },
  {
    test: () => /\balembic\b/.test(c) && /postgres(ql)?(\+\w+)?:\/\/(?!\S*(localhost|127\.0\.0\.1|:15432))/.test(c),
    msg: "Không chạy Alembic vào DB ngoài máy (staging/VPS) từ phiên Claude. Deploy qua script triển khai có xác nhận.",
  },
  {
    test: () => /(\brm\b|Remove-Item|\bdel\b)[^|;&]*backend[\\/]+migrations[\\/]+versions/i.test(c),
    msg: "Không xóa file migration. Muốn hoàn tác thì viết migration mới.",
  },
  {
    test: () => {
      const m = c.match(/\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\s+(.+)/);
      if (!m) return false;
      const targets = m[2].split(" ").filter((t) => t && !t.startsWith("-") && !/^[;&|]/.test(t));
      return targets.some((t) => !SAFE_DELETE_TARGETS.test(t.replace(/^["']|["']$/g, "")));
    },
    msg: "rm -rf chỉ được dùng cho thư mục build/cache (node_modules, .next, build, .gradle, .venv, coverage…).",
  },
  {
    test: () =>
      /Remove-Item\b.*-Recurse\b/i.test(c) &&
      !/Remove-Item\s+(-\S+\s+)*["']?(\.\\|\.\/)?[\w\\/.-]*\b(node_modules|\.next|build|\.gradle|\.venv|coverage|test-results|playwright-report)\b/i.test(c),
    msg: "Remove-Item -Recurse chỉ được dùng cho thư mục build/cache.",
  },
  {
    test: () =>
      /(\bcat\b|\btype\b|Get-Content|\bless\b|\bhead\b|\btail\b|\bmore\b)\s+[^|;&]*\.env(?!\.example)(\.[\w.-]+)?\b/i.test(c),
    msg: "Không đọc file .env (chứa secret). Dùng .env.example để biết tên biến.",
  },
  {
    test: () => /(\bcat\b|\btype\b|Get-Content|\bhead\b|\btail\b|\bkeytool\b)[^|;&]*(\.jks\b|\.keystore\b|keystore\.properties|[\\/]secrets[\\/])/i.test(c),
    msg: "Không đọc keystore/bí mật ký app. Ký bản phát hành qua script release có xác nhận.",
  },
];

for (const rule of rules) {
  if (rule.test()) block(`[guard-shell] Đã chặn: ${cmd}\n${rule.msg}`);
}
process.exit(0);
