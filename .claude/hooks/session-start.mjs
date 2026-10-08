// SessionStart (startup|resume|compact): phase STATUS, next task, git state, local services, countdown (<= 25 lines).
import { existsSync, readFileSync } from "node:fs";
import net from "node:net";
import path from "node:path";
import { androidSdk, isWin, projectDir, run } from "./lib.mjs";

const lines = ["[HỏiCon] Bối cảnh phiên làm việc"];

// Countdown to competition milestones (Asia/Ho_Chi_Minh dates).
const today = new Date();
const days = (iso) => Math.ceil((new Date(`${iso}T23:59:59+07:00`) - today) / 86_400_000);
lines.push(
  `Còn ${days("2026-11-15")} ngày tới hạn Vòng 1 (15/11) · ${days("2027-01-10")} ngày tới hạn Vòng 2 (10/01) · ${days("2027-02-27")} ngày tới chung kết (27/02)`,
);

const roadmap = path.join(projectDir, "docs", "ROADMAP.md");
if (existsSync(roadmap)) {
  const text = readFileSync(roadmap, "utf8");
  const status = text.match(/<!--\s*STATUS\s*-->([\s\S]*?)<!--\s*\/STATUS\s*-->/);
  if (status) {
    lines.push(
      ...status[1]
        .trim()
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean)
        .slice(0, 6),
    );
    const next = status[1].match(/Việc kế tiếp:\s*([A-Z0-9-]+)/);
    if (next) {
      const row = text.split(/\r?\n/).find((l) => l.includes(`| ${next[1]} `) || l.includes(`|${next[1]}|`));
      if (row) lines.push(`Task: ${row.replace(/\s+/g, " ").slice(0, 220)}`);
    }
  } else lines.push("docs/ROADMAP.md chưa có khối <!-- STATUS -->.");
} else lines.push("Chưa có docs/ROADMAP.md.");

const branch = run("git", ["branch", "--show-current"], { timeoutMs: 5_000 });
const status = run("git", ["status", "--short"], { timeoutMs: 5_000 });
if (branch.code === 0) lines.push(`Nhánh: ${branch.out.trim() || "(chưa có commit)"}`);
if (status.code === 0) {
  const changed = status.out.trim().split(/\r?\n/).filter(Boolean);
  lines.push(`Thay đổi chưa commit: ${changed.length} file`);
  lines.push(...changed.slice(0, 6).map((l) => `  ${l}`));
  if (changed.length > 6) lines.push(`  … và ${changed.length - 6} file khác`);
}

// Local services: Postgres on 15432, API on 18000, adb devices.
const probe = (port) =>
  new Promise((resolve) => {
    const s = net.connect({ host: "127.0.0.1", port, timeout: 400 });
    s.on("connect", () => (s.destroy(), resolve(true)));
    s.on("error", () => resolve(false));
    s.on("timeout", () => (s.destroy(), resolve(false)));
  });
const [pg, api] = await Promise.all([probe(15432), probe(18000)]);
let adbInfo = "chưa cài adb";
const adb = path.join(androidSdk(), "platform-tools", isWin ? "adb.exe" : "adb");
if (existsSync(adb)) {
  const d = run(adb, ["devices"], { timeoutMs: 5_000 });
  const n = d.out.split(/\r?\n/).filter((l) => /\tdevice$/.test(l)).length;
  adbInfo = `${n} thiết bị/máy ảo`;
}
lines.push(`Dịch vụ: Postgres:15432 ${pg ? "đang chạy" : "tắt"} · API:18000 ${api ? "đang chạy" : "tắt"} · adb: ${adbInfo}`);

lines.push("Nhắc: làm 1 task/lần theo docs/ROADMAP.md và CLAUDE.md; chạy CLI bằng tool Bash (rtk); báo cáo bằng tiếng Việt.");
process.stdout.write(lines.slice(0, 25).join("\n") + "\n");
