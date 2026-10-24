import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { mockApi } from "./fixtures";

// Spec 033 FR-012 (P3): `/eval` đọc baseline đã commit qua `/v1/eval/summary`, bằng fixture hợp đồng.
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "033-sim-trace");

test("bảng chỉ số theo bộ kiểm; bộ chưa chứng minh bằng model thật có dòng cảnh báo rõ", async ({ page }) => {
  await mockApi(page);
  await page.goto("/eval");
  await expect(page.getByRole("heading", { name: "Kết quả đánh giá trợ lý AI" })).toBeVisible();
  const full = page.getByTestId("suite-full");
  await expect(full.getByRole("row", { name: /Số ca cần cảnh báo được cảnh báo/ })).toContainText("100%");
  await expect(full.getByRole("row", { name: /Báo nhầm/ })).toContainText("0%");
  await expect(full.getByRole("row", { name: /Vi phạm an toàn/ })).toContainText("0");
  await expect(full.getByTestId("gate")).toContainText("Số rào tất định — CHƯA PHẢI SỐ M3");
  const smoke = page.getByTestId("suite-smoke");
  await expect(smoke.getByTestId("gate")).toHaveCount(0); // đã ghi bằng model thật: không cảnh báo
  await expect(page.getByTestId("sim-banner")).toContainText("MÔ PHỎNG");
});

test("cổng mô phỏng tắt (API 404): 'Trang này chưa mở'", async ({ page }) => {
  await mockApi(page, { evalSummary: () => ({ status: 404, json: { detail: "Không tìm thấy" } }) });
  await page.goto("/eval");
  await expect(page.getByRole("heading", { name: "Trang này chưa mở" })).toBeVisible();
});

test("chưa có baseline nào: nói thẳng, không hiện bảng rỗng", async ({ page }) => {
  await mockApi(page, { evalSummary: () => ({ status: 200, json: { suites: [] } }) });
  await page.goto("/eval");
  await expect(page.getByText("Chưa có kết quả đánh giá nào được lưu")).toBeVisible();
});

for (const view of [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]) {
  test(`axe 0 lỗi nghiêm trọng, không tràn ngang, ảnh · ${view.width}px`, async ({ page }) => {
    await page.setViewportSize(view);
    await mockApi(page);
    await page.goto("/eval");
    await expect(page.getByTestId("suite-full")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
      .options({ rules: { "color-contrast-enhanced": { enabled: true } } })
      .analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
    mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `eval-${view.width}.png`), fullPage: true });
  });
}
