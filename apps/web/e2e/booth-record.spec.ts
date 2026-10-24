import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { PLAYLIST, recordingProblems } from "../src/lib/booth";

// Spec 050, FR-006/T003: ghi 3 bản ghi từ đồ thị THẬT (`/v1/sim/*`, llm: "replay", gia đình demo) rồi kiểm tệp.
//   Ghi:  API dev cổng 18010 có HOICON_SIM_ENABLED=true + web build trỏ vào đó (xem đầu live.spec.ts), rồi
//         BOOTH_RECORD=1 pnpm --dir apps/web e2e booth-record
//   Kiểm: luôn chạy (không cần API): mỗi bản ghi hợp `sim_run.v1`, tin mở đầu bằng câu công khai AI, không có số điện thoại thô.
const REPO = path.resolve(__dirname, "../../..");
const DIR = path.join(__dirname, "../public/booth/replay");

function ops(...args: string[]): string {
  return execFileSync("uv", ["run", "--directory", "backend", "python", "-m", "hoicon.ops.guardian_link", ...args], {
    cwd: REPO,
    encoding: "utf-8",
  }).trim();
}

test.describe("ghi bản ghi từ API thật", () => {
  test.skip(process.env.BOOTH_RECORD !== "1", "đặt BOOTH_RECORD=1 và chạy API + web (xem đầu tệp)");
  test.setTimeout(300_000);

  test("chạy từng kịch bản qua console và lưu bản ghi", async ({ page, context }) => {
    const seeded = JSON.parse(ops("--seed")) as { family_id: string; login_url: string };
    try {
      await page.goto(seeded.login_url);
      await page.waitForURL("**/incidents");
      await page.goto("/booth?autoplay=0");
      const console_ = await context.newPage();
      await console_.goto("/demo/console");
      await expect(console_.getByTestId("booth-link")).toContainText("đã kết nối");
      mkdirSync(DIR, { recursive: true });
      for (const item of PLAYLIST) {
        await console_.getByRole("button", { name: `Chạy: ${item.title}` }).click();
        await expect(console_.getByRole("button", { name: `Tải bản ghi: ${item.scenarioId}` })).toBeVisible({ timeout: 120_000 });
        const [download] = await Promise.all([
          console_.waitForEvent("download"),
          console_.getByRole("button", { name: `Tải bản ghi: ${item.scenarioId}` }).click(),
        ]);
        await download.saveAs(path.join(DIR, `${item.scenarioId}.json`));
      }
    } finally {
      ops("--cleanup", seeded.family_id);
    }
  });
});

test.describe("kiểm tệp bản ghi", () => {
  for (const item of PLAYLIST) {
    test(`bản ghi ${item.scenarioId} hợp lệ, hư cấu, có câu công khai AI`, () => {
      const file = path.join(DIR, `${item.scenarioId}.json`);
      expect(existsSync(file), `thiếu ${file}: chạy BOOTH_RECORD=1`).toBe(true);
      const recording = JSON.parse(readFileSync(file, "utf-8")) as unknown;
      expect(recordingProblems(recording)).toEqual([]);
      const rec = recording as { frames: { t_ms: number; run: { guardian_messages: unknown[]; scenario_id: string } }[]; duration_ms: number };
      expect(rec.frames.every((f) => f.run.scenario_id === item.scenarioId)).toBe(true);
      expect(rec.frames.at(-1)?.run.guardian_messages.length ?? 0).toBeGreaterThan(0); // có tin cho con (kể cả ca hợp lệ)
      expect(rec.duration_ms).toBeGreaterThan(0);
    });
  }
});
