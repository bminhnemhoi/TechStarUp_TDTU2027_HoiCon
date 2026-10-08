// Shared helpers for HoiCon Claude Code hooks (Node >= 20, cross-platform). Ported from FoodSave.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
export const isWin = process.platform === "win32";

/** Read and parse the hook JSON payload from stdin (returns {} on empty/invalid input). */
export function readInput() {
  try {
    const raw = readFileSync(0, "utf8");
    return raw.trim() ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** Run a command synchronously; never throws. */
export function run(cmd, args, { timeoutMs = 30_000, cwd = projectDir, env } = {}) {
  const res = spawnSync(cmd, args, {
    cwd,
    encoding: "utf8",
    timeout: Math.max(1_000, timeoutMs),
    shell: /\.(cmd|bat)$/i.test(cmd), // Windows .cmd/.bat shims need a shell
    windowsHide: true,
    env: env ? { ...process.env, ...env } : process.env,
  });
  return {
    code: res.status,
    timedOut: res.error?.code === "ETIMEDOUT" || res.signal === "SIGTERM",
    missing: res.error?.code === "ENOENT",
    out: `${res.stdout ?? ""}${res.stderr ?? ""}`,
  };
}

/** Find an executable on PATH (returns null when absent). */
export function which(name) {
  const r = run(isWin ? "where" : "which", [name], { timeoutMs: 5_000 });
  if (r.code !== 0) return null;
  return r.out.split(/\r?\n/).map((s) => s.trim()).find(Boolean) ?? null;
}

/** Block the tool call / stop: message goes to Claude via stderr, exit code 2. */
export function block(message) {
  process.stderr.write(`${message}\n`);
  process.exit(2);
}

/** Path relative to the project root using forward slashes. */
export function relPath(p) {
  if (!p) return "";
  const abs = path.isAbsolute(p) ? p : path.join(projectDir, p);
  return path.relative(projectDir, abs).split(path.sep).join("/");
}

export function tail(text, lines = 40) {
  return text.trim().split(/\r?\n/).slice(-lines).join("\n");
}

export const exists = (...p) => existsSync(path.join(projectDir, ...p));

/** Android SDK location (project settings env, then default on D:). */
export function androidSdk() {
  return process.env.ANDROID_HOME || process.env.ANDROID_SDK_ROOT || "D:/Android/Sdk";
}
