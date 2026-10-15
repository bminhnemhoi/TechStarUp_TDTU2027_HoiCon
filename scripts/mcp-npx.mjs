// Chạy `npx <tham số>` cho máy chủ MCP (stdio) trên cả Windows và Linux/macOS — dùng trong .mcp.json.
// Windows cần `cmd /c npx`; Linux không có `cmd` ⇒ một launcher Node chung thay cho hai cấu hình riêng.
import { spawn } from "node:child_process";

const isWin = process.platform === "win32";
const child = spawn(isWin ? "npx.cmd" : "npx", process.argv.slice(2), {
  stdio: "inherit",
  shell: isWin, // Node ≥ 20 không cho spawn .cmd nếu không có shell
});
child.on("error", (err) => {
  console.error(`[mcp-npx] không chạy được npx: ${err.message}`);
  process.exit(1);
});
child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
