// PostToolUse (Edit|Write|MultiEdit): format the edited file with the project's formatter. Silent, non-blocking.
//  .py            -> ruff format + ruff check --select I --fix (import order)
//  .kt/.kts       -> ktlint -F (only if installed)
//  ts/js/json/... -> prettier from the root node_modules (only if installed)
import { existsSync } from "node:fs";
import path from "node:path";
import { isWin, projectDir, readInput, relPath, run, which } from "./lib.mjs";

const input = readInput();
const file = relPath(input?.tool_input?.file_path ?? "");
if (!file || file.startsWith("..")) process.exit(0);
if (/(^|\/)(node_modules|\.next|build|\.gradle|\.venv|migrations\/versions)\//.test(file)) process.exit(0);
if (/^apps\/web\/src\/lib\/api\/schema\.d\.ts$/.test(file)) process.exit(0); // generated client

if (/\.py$/.test(file)) {
  const ruff = which("ruff");
  if (ruff) {
    run(ruff, ["format", "--quiet", file], { timeoutMs: 15_000 });
    run(ruff, ["check", "--quiet", "--select", "I", "--fix", file], { timeoutMs: 15_000 });
  }
  process.exit(0);
}

if (/\.(kt|kts)$/.test(file)) {
  const ktlint = which("ktlint");
  if (ktlint) run(ktlint, ["-F", file], { timeoutMs: 20_000 });
  process.exit(0);
}

if (/\.(ts|tsx|js|jsx|mjs|cjs|json|css|md|mdx|yml|yaml|html)$/.test(file)) {
  if (/^docs\/(research|proposal)\//.test(file)) process.exit(0); // keep research/proposal text untouched
  const bin = path.join(projectDir, "node_modules", ".bin", isWin ? "prettier.cmd" : "prettier");
  if (!existsSync(bin)) process.exit(0); // before root `pnpm install`
  run(bin, ["--write", "--log-level", "warn", file], { timeoutMs: 15_000 });
}
process.exit(0);
