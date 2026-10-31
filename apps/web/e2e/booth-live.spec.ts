import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";

// Spec 050 (SC-001, SC-002): chạy gian với API + DB dev THẬT, nhịp thật (không `fast`). Chỉ chạy khi HOICON_E2E_LIVE=1:
//   API dev cổng 18010 với HOICON_SIM_ENABLED=true + web build trỏ vào đó (xem đầu live.spec.ts), rồi
//   HOICON_E2E_LIVE=1 pnpm --dir apps/web e2e booth-live
// Số đo: trình duyệt này, máy dev, `llm: "replay"`, mạng cục bộ — KHÔNG phải số ở hội trường.
const REPO = path.resolve(__dirname, "../../..");

function ops(...args: string[]): string {
  return execFileSync("uv", ["run", "--directory", "backend", "python", "-m", "hoicon.ops.guardian_link", ...args], {
    cwd: REPO,
    encoding: "utf-8",
  }).trim();
}

test.describe("live: gian trưng bày với API thật", () => {
  test.skip(process.env.HOICON_E2E_LIVE !== "1", "đặt HOICON_E2E_LIVE=1 và chạy API + web (xem đầu tệp)");
  test.setTimeout(240_000);

  test("3 lượt trực tiếp liên tiếp: cảnh báo < 5 giây, mỗi lượt ≤ 90 giây", async ({ page, context }) => {
    const seeded = JSON.parse(ops("--seed")) as { family_id: string; login_url: string };
    try {
      await page.goto(seeded.login_url);
      await page.waitForURL("**/incidents");
      await page.goto("/booth?autoplay=0");
      const panel = await context.newPage();
      await panel.goto("/demo/console");
      await expect(panel.getByTestId("booth-link")).toContainText("đã kết nối");
      const started = Date.now();
      await panel.getByRole("button", { name: "Chạy cả danh sách (lặp lại)" }).click();
      await expect(panel.getByTestId("results").getByRole("row")).toHaveCount(4, { timeout: 200_000 }); // tiêu đề + 3 lượt
      await panel.getByRole("button", { name: "Dừng" }).click();
      const seconds = Math.round((Date.now() - started) / 1000);
      const rows = await panel.getByTestId("results").getByRole("row").allInnerTexts();
      console.log(`BOOTH-LIVE 3 lượt trong ${seconds} s:\n${rows.join("\n")}`);
      await expect(panel.getByTestId("streak")).toContainText("Đạt liên tiếp: 3/3");
      for (const row of rows.slice(1)) {
        expect(row).toContain("Trực tiếp");
        const ms = Number(row.split("\t")[2]);
        expect(ms).toBeLessThan(5000);
      }
      expect(seconds).toBeLessThanOrEqual(270); // 3 lượt × (≤ 90 s) — thực tế ≈ 1 phút
    } finally {
      ops("--cleanup", seeded.family_id);
    }
  });
});
