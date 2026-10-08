// Regression tests for the project hooks: `node --test ".claude/hooks/test/*.test.mjs"` (or `pnpm test:hooks`)
// Each hook runs as a subprocess with the JSON Claude Code would send on stdin; exit 2 = blocked.
// Fictional phone numbers are assembled at runtime so no raw number literal lives in the repo.
import { spawnSync } from "node:child_process";
import path from "node:path";
import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const HOOKS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ROOT = path.resolve(HOOKS, "..", "..");

function runHook(name, payload, env = {}) {
  const r = spawnSync("node", [path.join(HOOKS, name)], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    cwd: ROOT,
    env: { ...process.env, CLAUDE_PROJECT_DIR: ROOT, HOICON_DISABLE_RTK: "1", ...env },
    timeout: 20_000,
  });
  return { code: r.status, out: r.stdout, err: r.stderr };
}
const shell = (command, tool = "Bash") => runHook("guard-shell.mjs", { tool_name: tool, tool_input: { command } });
const write = (file, content) =>
  runHook("guard-privacy.mjs", { tool_name: "Write", tool_input: { file_path: path.join(ROOT, file), content } });

const ENV = ".e" + "nv";
const FAKE_PHONE = "09" + "1".repeat(8); // fictional, built at runtime
const FAKE_PHONE_INTL = "+84 9" + "2".repeat(8);

// ---------------------------------------------------------------- guard-shell
const BLOCKED = [
  ["git", "push", "--force", "origin", "feat/x"].join(" "),
  ["git", "push", "-f"].join(" "),
  "git push origin main",
  "git push origin HEAD:main",
  ["git", "reset", "--hard", "HEAD~1"].join(" "),
  "git clean -fd",
  "pip install requests",
  "python -m pip install requests",
  ["docker", "compose", "down", "-v"].join(" "),
  "docker volume rm foodsave_db",
  "docker stop foodsave-db-1",
  "uv run alembic -x url=postgresql://u:p@vps.example.com:5432/db upgrade head",
  "rm backend/migrations/versions/0001_init.py",
  ["rm", "-rf", "src"].join(" "),
  ["rm", "-rf", "/"].join(" "),
  `cat backend/${ENV}`,
  `head -5 apps/web/${ENV}.local`,
  "cat D:/secrets/release.jks",
  // review bảo mật 08/10: đọc bí mật qua script nội tuyến / ghi .env / ép add file bị ignore
  `uv run --directory backend python -c "from hoicon.config import get_settings; print(get_settings().zalo_bot_token.get_secret_value())"`,
  `python -c "print(open('backend/${ENV}').read())"`,
  `uv run python -c "from dotenv import dotenv_values; print(dotenv_values())"`,
  `node -e "console.log(require('fs').readFileSync('backend/${ENV}','utf8'))"`,
  `python - <<'PY'\nimport os; print(os.environ['HOICON_ANTHROPIC_API_KEY'])\nPY`,
  "uv run --directory backend python -m hoicon.ops.init_env",
  `git add -f backend/${ENV}`,
  `git add --force backend/${ENV}`,
];
const ALLOWED = [
  "git status",
  "git push -u origin feat/p0-06-scaffold",
  "uv pip install -e .",
  "uv add fastapi",
  ["rm", "-rf", "node_modules"].join(" "),
  ["rm", "-rf", "apps/android/app/build"].join(" "),
  ["rm", "-rf", "backend/.venv"].join(" "),
  "docker compose -f infra/compose.dev.yml stop",
  "docker ps --format '{{.Names}}'",
  `cat backend/${ENV}.example`,
  "uv run alembic upgrade head",
  "uv run alembic -x url=postgresql+psycopg://hoicon:hoicon@localhost:15432/hoicon upgrade head",
  "uv run --directory backend python -m hoicon.ops.check_keys",
  `uv run python -c "print(1 + 1)"`,
  `node -e "console.log(require('./package.json').name)"`,
  `python -c "print(open('backend/${ENV}.example').read())"`,
  "git add -A",
  "git add x && ls -lf",
  "git add docs/setup/ACCOUNTS.md",
];
for (const cmd of BLOCKED) test(`guard-shell blocks: ${cmd}`, () => assert.equal(shell(cmd).code, 2));
for (const cmd of ALLOWED) test(`guard-shell allows: ${cmd}`, () => assert.equal(shell(cmd).code, 0));
test("guard-shell blocks Remove-Item -Recurse outside build dirs (PowerShell)", () =>
  assert.equal(shell("Remove-Item -Recurse -Force apps", "PowerShell").code, 2));
test("guard-shell allows Remove-Item -Recurse node_modules (PowerShell)", () =>
  assert.equal(shell("Remove-Item -Recurse -Force node_modules", "PowerShell").code, 0));

// -------------------------------------------------------------- guard-privacy
const manifest = (perm) =>
  `<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n  <uses-permission android:name="${perm}" />\n</manifest>`;
for (const p of ["READ_SMS", "READ_CALL_LOG", "READ_CONTACTS", "QUERY_ALL_PACKAGES", "BIND_ACCESSIBILITY_SERVICE"]) {
  test(`guard-privacy blocks manifest permission ${p}`, () =>
    assert.equal(write("apps/android/app/src/main/AndroidManifest.xml", manifest(`android.permission.${p}`)).code, 2));
}
test("guard-privacy allows manifest with allowed permissions", () => {
  const ok = ["INTERNET", "FOREGROUND_SERVICE_SPECIAL_USE", "PACKAGE_USAGE_STATS", "SYSTEM_ALERT_WINDOW"]
    .map((p) => `  <uses-permission android:name="android.permission.${p}" />`)
    .join("\n");
  assert.equal(write("apps/android/app/src/main/AndroidManifest.xml", `<manifest>\n${ok}\n</manifest>`).code, 0);
});
test("guard-privacy blocks raw phone in Kotlin source", () =>
  assert.equal(write("apps/android/app/src/main/java/vn/hoicon/X.kt", `val n = "${FAKE_PHONE}"`).code, 2));
test("guard-privacy blocks +84 phone in Python source", () =>
  assert.equal(write("backend/src/hoicon/x.py", `N = "${FAKE_PHONE_INTL}"`).code, 2));
test("guard-privacy allows fictional phone in tests/ and data/", () => {
  assert.equal(write("backend/tests/unit/test_pii.py", `N = "${FAKE_PHONE}"`).code, 0);
  assert.equal(write("data/fixtures/phones.py", `N = "${FAKE_PHONE}"`).code, 0);
});
test("guard-privacy blocks logging a raw phone variable", () =>
  assert.equal(write("backend/src/hoicon/x.py", 'logger.info("caller %s", phone_number)').code, 2));
test("guard-privacy blocks Log.d with callerNumber (Kotlin)", () =>
  assert.equal(write("apps/android/app/src/main/java/vn/hoicon/X.kt", 'Log.d("HC", "from $callerNumber")').code, 2));
test("guard-privacy allows logging a masked value", () =>
  assert.equal(write("backend/src/hoicon/x.py", 'logger.info("caller %s", mask(phone_number))').code, 0));
test("guard-privacy ignores non-source files", () =>
  assert.equal(write("docs/PRD.md", `Ví dụ ${FAKE_PHONE}`).code, 0));

// ------------------------------------------------------------ other hooks
test("guard-migrations allows a brand-new migration file", () =>
  assert.equal(
    runHook("guard-migrations.mjs", {
      tool_name: "Write",
      tool_input: { file_path: path.join(ROOT, "backend/migrations/versions/9999_new.py"), content: "x = 1\n" },
    }).code,
    0,
  ));
test("rtk-rewrite never blocks, even on garbage input", () => {
  const r = spawnSync("node", [path.join(HOOKS, "rtk-rewrite.mjs")], { input: "not json", encoding: "utf8" });
  assert.equal(r.status, 0);
});
test("session-start exits 0 and prints the HoiCon banner", () => {
  const r = runHook("session-start.mjs", { hook_event_name: "SessionStart", source: "startup" });
  assert.equal(r.code, 0);
  assert.match(r.out, /HỏiCon/);
});
test("format-on-edit skips docs/proposal without failing", () =>
  assert.equal(
    runHook("format-on-edit.mjs", {
      tool_name: "Write",
      tool_input: { file_path: path.join(ROOT, "docs/proposal/src/build.js") },
    }).code,
    0,
  ));
