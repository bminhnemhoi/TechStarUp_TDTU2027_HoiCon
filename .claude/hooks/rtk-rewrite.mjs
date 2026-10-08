// PreToolUse (Bash): forward to `rtk hook claude` so CLI output is compressed (token saving).
// Project-scoped replacement for `rtk init -g` (which would patch the user's global settings).
// rtk is permission-aware: it only adds permissionDecision "allow" for commands already allowed;
// destructive commands are left untouched for guard-shell to judge. Silent no-op when rtk is absent.
// rtk must be on PATH: the rewritten command calls bare `rtk …`, so an exe found elsewhere would
// turn every Bash call into "rtk: command not found". See docs/HARNESS.md (RTK) for the PATH setup.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { which } from "./lib.mjs";

if (process.env.HOICON_DISABLE_RTK === "1") process.exit(0);
const rtk = which("rtk");
if (!rtk) process.exit(0);

let raw = "";
try {
  raw = readFileSync(0, "utf8");
} catch {
  process.exit(0);
}
const res = spawnSync(rtk, ["hook", "claude"], { input: raw, encoding: "utf8", timeout: 8_000, windowsHide: true });
if (res.status === 0 && res.stdout && res.stdout.trim().startsWith("{")) process.stdout.write(res.stdout);
process.exit(0); // never block: rtk failures must not stop the tool call
