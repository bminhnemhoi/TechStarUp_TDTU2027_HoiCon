import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";

// Kịch bản đầu–cuối với API + DB dev THẬT (spec 027, T019, SC-004). Chỉ chạy khi HOICON_E2E_LIVE=1:
//   1. API: HOICON_DEVICE_JWT_SECRET=<chuỗi ngẫu nhiên ≥ 32 ký tự> uv run --directory backend uvicorn hoicon.api.main:app --port 18010 --loop asyncio:SelectorEventLoop
//   2. Web build trỏ vào API đó: HOICON_API_URL=http://127.0.0.1:18010 pnpm --dir apps/web build
//   3. HOICON_E2E_LIVE=1 pnpm --dir apps/web e2e live
// Dữ liệu là gia đình demo "E2E 027" do `hoicon.ops.guardian_link` dựng và dọn (chặn chạy khi HOICON_ENV ≠ dev).
const REPO = path.resolve(__dirname, "../../..");

function ops(...args: string[]): string {
  return execFileSync("uv", ["run", "--directory", "backend", "python", "-m", "hoicon.ops.guardian_link", ...args], {
    cwd: REPO,
    encoding: "utf-8",
  }).trim();
}

test.describe("live: API + DB dev thật", () => {
  test.skip(process.env.HOICON_E2E_LIVE !== "1", "đặt HOICON_E2E_LIVE=1 và chạy API + DB dev (xem đầu tệp)");
  test.setTimeout(120_000);

  test("đăng nhập → danh sách → chi tiết → bước mới hiện ≤ 1 s → quyết định", async ({ page, context }, testInfo) => {
    const seeded = JSON.parse(ops("--seed")) as { family_id: string; incident_id: string; run_id: string; login_url: string };
    try {
      // Đăng nhập bằng liên kết một lần: URL mất token, cookie đúng cờ.
      await page.goto(seeded.login_url);
      await page.waitForURL("**/incidents");
      expect(page.url()).not.toContain(seeded.login_url.split("/login/")[1]);
      const cookie = (await context.cookies()).find((c) => c.name === "hc_guardian");
      expect(cookie, "cookie hc_guardian").toBeTruthy();
      expect(cookie?.httpOnly).toBe(true);
      expect(cookie?.sameSite).toBe("Strict");
      expect(cookie?.path).toBe("/v1");

      // Liên kết đã dùng thì không dùng lại được.
      const again = await page.context().newPage();
      await again.goto(seeded.login_url);
      await expect(again.locator('main [role="alert"]')).toContainText("Liên kết đăng nhập không dùng được");
      await again.close();

      // Danh sách → chi tiết.
      await expect(page.getByText("E2E 027")).toBeVisible();
      await page.getByRole("region", { name: "Đang cần chú ý" }).getByRole("link").first().click();
      await page.waitForURL(`**/incidents/${seeded.incident_id}`);
      await expect(page.getByTestId("stream-status")).toHaveText("Đang theo dõi trực tiếp");
      await expect(page.getByText("Nhận tín hiệu từ điện thoại của Mẹ")).toBeVisible();

      // SC-004: bước mới commit trong DB hiện trên trang ≤ 1 s (localhost, cùng đồng hồ máy). Đo 3 bước liên tiếp; `at`
      // do DB đặt bằng clock_timestamp() ngay lúc chèn nên gần với lúc commit.
      const probes: [node: string, text: string][] = [
        ["intervention", "Gửi tóm tắt cho người nhà"],
        ["fast_alert", "Đã gửi cảnh báo nhanh cho người nhà"],
        ["verify", "Đã tra số điện thoại và đường dẫn trong danh sách cảnh báo của HỏiCon"],
      ];
      await page.evaluate((texts) => {
        const w = window as unknown as { __seen: Record<string, number> };
        w.__seen = {};
        new MutationObserver(() => {
          for (const text of texts) if (!w.__seen[text] && document.body.innerText.includes(text)) w.__seen[text] = Date.now();
        }).observe(document.body, { childList: true, subtree: true, characterData: true });
      }, probes.map(([, text]) => text));
      const latencies: number[] = [];
      for (const [node, text] of probes) {
        const added = JSON.parse(ops("--add-step", seeded.run_id, "--node", node)) as { at: string };
        await expect(page.getByText(text).first()).toBeVisible();
        const seen = await page.evaluate((t) => (window as unknown as { __seen: Record<string, number> }).__seen[t] ?? 0, text);
        latencies.push(seen - new Date(added.at).getTime());
      }
      testInfo.annotations.push({ type: "SC-004 độ trễ (ms)", description: latencies.join(", ") });
      console.log(`SC-004: ${latencies.length} bước mới hiện sau (ms kể từ lúc chèn vào DB): ${latencies.join(", ")}`);
      for (const latency of latencies) expect(latency).toBeLessThanOrEqual(1000);

      // Quyết định có xác nhận: POST qua cookie + Origin thật của trình duyệt (kiểm CSRF thật), sự cố chuyển trạng thái.
      await page.getByRole("button", { name: /đang bị lừa/ }).click();
      await page.getByRole("button", { name: "Đúng, gửi xác nhận" }).click();
      await expect(page.getByText("✓ Đã ghi nhận")).toBeVisible();
      await expect(page.getByText("Đang theo dõi (nghi lừa đảo)").first()).toBeVisible();
    } finally {
      ops("--cleanup", seeded.family_id);
    }
  });
});
