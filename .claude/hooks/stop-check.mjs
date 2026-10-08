// Stop: quick, scoped quality gate before Claude finishes a turn (budget ~90 s).
//  backend/**.py changed  -> ruff check (changed files) + pytest tests/unit -x
//  apps/web/**.ts(x)      -> tsc --noEmit --incremental
//  apps/android/rules/**  -> gradlew :rules:test (pure JVM, warm daemon)
// Skips when re-entered, when nothing relevant changed, or when the tree is unchanged since last pass.
// On failure: exit 2 (Claude continues and fixes). On timeout: warn and exit 0. Full suites run in CI / phase-gate.
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { block, isWin, projectDir, readInput, run, tail, which } from "./lib.mjs";

const BUDGET_MS = 90_000;
const started = Date.now();
const input = readInput();
if (input?.stop_hook_active) process.exit(0);
if (process.env.HOICON_SKIP_STOP_HOOK === "1") process.exit(0);

const status = run("git", ["status", "--porcelain", "--untracked-files=all"], { timeoutMs: 10_000 });
if (status.code !== 0) process.exit(0);
const changed = status.out
  .split(/\r?\n/)
  .map((l) => l.slice(3).trim().replace(/^"|"$/g, ""))
  .map((l) => (l.includes(" -> ") ? l.split(" -> ").pop() : l))
  .filter(Boolean);

const py = changed.filter((f) => /^backend\/.*\.py$/.test(f) && !/^backend\/migrations\//.test(f));
const ts = changed.filter((f) => /^apps\/web\/.*\.(ts|tsx)$/.test(f));
const rules = changed.filter((f) => /^apps\/android\/rules\/.*\.(kt|kts)$/.test(f));
if (!py.length && !ts.length && !rules.length) process.exit(0);

// Fingerprint = porcelain status + diff, so unchanged trees are skipped.
const diff = run("git", ["diff", "--no-ext-diff"], { timeoutMs: 10_000 });
const fingerprint = createHash("sha256").update(status.out).update(diff.out).digest("hex");
const cacheDir = path.join(projectDir, ".claude", ".cache");
const stateFile = path.join(cacheDir, "stop-check.json");
try {
  if (JSON.parse(readFileSync(stateFile, "utf8")).fingerprint === fingerprint) process.exit(0);
} catch {
  /* no previous state */
}

const remaining = () => BUDGET_MS - (Date.now() - started);
const timeout = (what) => {
  process.stdout.write(`[stop-check] ${what} quá thời gian — bỏ qua, phase-gate/CI sẽ kiểm tra.\n`);
  process.exit(0);
};

// --- Backend --------------------------------------------------------------
if (py.length && existsSync(path.join(projectDir, "backend", "pyproject.toml"))) {
  const uv = which("uv");
  if (uv) {
    const rel = py.filter((f) => existsSync(path.join(projectDir, f))).map((f) => f.replace(/^backend\//, ""));
    if (rel.length) {
      const lint = run(uv, ["run", "--directory", "backend", "ruff", "check", ...rel], { timeoutMs: remaining() });
      if (lint.timedOut) timeout("ruff");
      if (lint.code !== 0 && !lint.missing) block(`[stop-check] ruff báo lỗi:\n${tail(lint.out)}`);
    }
    if (existsSync(path.join(projectDir, "backend", "tests", "unit")) && remaining() > 15_000) {
      const t = run(uv, ["run", "--directory", "backend", "pytest", "tests/unit", "-x", "-q", "--no-header"], {
        timeoutMs: remaining(),
      });
      if (t.timedOut) timeout("pytest");
      if (t.code !== 0 && t.code !== 5) block(`[stop-check] Unit test backend lỗi:\n${tail(t.out)}`);
    }
  }
}

// --- Web ------------------------------------------------------------------
if (ts.length && existsSync(path.join(projectDir, "apps", "web", "node_modules")) && remaining() > 15_000) {
  const pnpm = isWin ? "pnpm.cmd" : "pnpm";
  const tsc = run(pnpm, ["--dir", "apps/web", "exec", "tsc", "--noEmit", "--incremental", "--pretty", "false"], {
    timeoutMs: remaining(),
  });
  if (tsc.timedOut) timeout("tsc");
  if (tsc.code !== 0) block(`[stop-check] TypeScript (apps/web) lỗi:\n${tail(tsc.out)}`);
}

// --- Android rules (pure JVM) --------------------------------------------
const gradlew = path.join(projectDir, "apps", "android", isWin ? "gradlew.bat" : "gradlew");
if (rules.length && existsSync(gradlew) && remaining() > 30_000) {
  const g = run(gradlew, ["-p", "apps/android", ":rules:test", "-q", "--console=plain"], { timeoutMs: remaining() });
  if (g.timedOut) timeout("gradle :rules:test");
  if (g.code !== 0) block(`[stop-check] Test :rules lỗi:\n${tail(g.out)}`);
}

mkdirSync(cacheDir, { recursive: true });
writeFileSync(stateFile, JSON.stringify({ fingerprint, at: new Date().toISOString() }));
process.exit(0);
