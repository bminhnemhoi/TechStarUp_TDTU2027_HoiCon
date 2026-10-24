import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { RUN_ID, STEPS, doneFrame, mockApi, sse, step, stepFrame } from "./fixtures";

// Sơ đồ xyflow nạp động: lần đầu có thể chậm khi nhiều worker tranh CPU (vượt hạn 7,5 s mặc định). Cùng điều kiện, chỉ chờ lâu hơn.
const XYFLOW_LOAD_MS = 20_000;

// Spec 033, FR-011: `/trace/[runId]` — sơ đồ + bản chữ + chi tiết bước, bằng fixture hợp đồng.
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "033-sim-trace");

test("bản chữ có đủ các bước của lượt chạy và sơ đồ vẽ đủ khối", async ({ page }) => {
  await mockApi(page);
  await page.goto(`/trace/${RUN_ID}`);
  await expect(page.getByTestId("stream-status")).toContainText("Trợ lý AI đã làm xong các bước");
  await expect(page.getByTestId("steps").getByRole("listitem")).toHaveCount(STEPS.length);
  await expect(page.getByTestId("trace-canvas")).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(10, { timeout: XYFLOW_LOAD_MS }); // 8 nút + bắt đầu + kết thúc
});

test("chọn một khối ở danh sách hiện chi tiết bước", async ({ page }) => {
  await mockApi(page);
  await page.goto(`/trace/${RUN_ID}`);
  await expect(page.getByTestId("steps").getByRole("listitem").first()).toBeVisible();
  await page.getByTestId("steps").getByRole("button").first().click();
  await expect(page.getByTestId("node-detail")).toContainText("Nhận sự kiện");
});

test("bước mới qua SSE hiện trong 1 giây", async ({ page }) => {
  const first = step("01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e91", "ingest", { level: "high" }, "2026-12-01T02:15:31.000Z");
  const next = step("01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e92", "fast_alert", { template: "fast_alert" }, "2026-12-01T02:15:32.000Z");
  await mockApi(page, {
    steps: () => ({ status: 200, json: { run_id: RUN_ID, status: "running", is_drill: false, is_demo: true, steps: [first] } }),
    stream: () => ({ body: sse([stepFrame(next), doneFrame(2)]), delayMs: 200 }),
  });
  await page.goto(`/trace/${RUN_ID}`);
  await expect(page.getByTestId("steps").getByRole("listitem")).toHaveCount(1);
  const started = Date.now();
  await expect(page.getByTestId("steps").getByRole("listitem")).toHaveCount(2, { timeout: 1000 });
  expect(Date.now() - started).toBeLessThan(1000);
});

test("lượt của gia đình khác: 'Không tìm thấy'", async ({ page }) => {
  await mockApi(page, { steps: () => ({ status: 404, json: { detail: "x" } }) });
  await page.goto(`/trace/${RUN_ID}`);
  await expect(page.getByRole("heading", { name: "Không tìm thấy" })).toBeVisible();
  await expect(page.getByTestId("steps")).toHaveCount(0);
});

test("sơ đồ không tải được thì bản chữ vẫn dùng được", async ({ page }) => {
  await mockApi(page, { topology: () => ({ status: 503, json: { detail: "x" } }) });
  await page.goto(`/trace/${RUN_ID}`);
  await expect(page.getByText("Chưa tải được sơ đồ")).toBeVisible();
  await expect(page.getByTestId("steps").getByRole("listitem")).toHaveCount(STEPS.length);
});

for (const view of [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]) {
  test(`axe 0 lỗi nghiêm trọng, không tràn ngang, ảnh · ${view.width}px`, async ({ page }) => {
    await page.setViewportSize(view);
    await mockApi(page);
    await page.goto(`/trace/${RUN_ID}`);
    await expect(page.getByTestId("stream-status")).toContainText("Trợ lý AI đã làm xong các bước");
    await expect(page.locator(".react-flow__node:visible").first()).toBeVisible({ timeout: XYFLOW_LOAD_MS });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
      .options({ rules: { "color-contrast-enhanced": { enabled: true } } })
      .analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
    mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `trace-${view.width}.png`), fullPage: true });
  });
}
