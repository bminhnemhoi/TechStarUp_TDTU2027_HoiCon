import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { SimMock, mockApi } from "./fixtures";

// Spec 050 (FR-010, SC-001/003/006): `/booth` + `/demo/console` bằng fixture hợp đồng (mạng bị chặn, tất định). `?fast=1` rút nhịp dừng.
// Số đo trực tiếp (t_alert_ms với API thật) nằm ở booth-live.spec.ts.
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "050-booth-mode");
const PHONE = /(?:\+?84|0)[\s.-]?[35789](?:[\s.-]?\d){8}/;
const VIEWPORTS = [
  { name: "390", width: 390, height: 844 },
  { name: "768", width: 768, height: 1024 },
  { name: "1440", width: 1440, height: 900 },
];

async function firstQuestion(page: Page) {
  await expect(page.getByTestId("question")).toContainText("Đây là trợ lý AI HỏiCon");
}

test("một lượt hoàn chỉnh: câu hỏi của bác → tin cho con → quyết định, nhãn MÔ PHỎNG luôn hiện", async ({ page }) => {
  const sim = new SimMock();
  const calls = await mockApi(page, { sim });
  await page.goto("/booth?fast=1");
  await expect(page.getByTestId("sim-banner")).toContainText("MÔ PHỎNG — dữ liệu hư cấu, không có cuộc gọi hay tin Zalo thật");
  await firstQuestion(page);
  await expect(page.getByTestId("elder-answer")).toHaveText("Bác trả lời: Có");
  await expect(page.getByTestId("messages").getByRole("listitem")).toHaveCount(2);
  for (const text of await page.getByTestId("messages").getByRole("listitem").allInnerTexts()) {
    expect(text).toContain("Đây là trợ lý AI HỏiCon");
    expect(PHONE.test(text)).toBe(false);
  }
  await expect(page.getByTestId("decision")).toContainText("có thể là lừa đảo");
  await expect(page.getByTestId("replay-banner")).toHaveCount(0); // trực tiếp: không có băng rôn bản ghi
  const start = calls.find((c) => c.method === "POST" && c.path === "/v1/sim/runs");
  expect(start?.body).toMatchObject({ scenario_id: "fake_police_safe_account_002", llm: "replay" });
  expect(calls.find((c) => c.path.endsWith("/answer"))?.body).toEqual({ question_id: "q_caller_authority", answer: "yes" });
  expect(calls.find((c) => c.path.endsWith("/decision"))?.body).toEqual({ decision: "emergency_pause" });
});

test("mất mạng giữa lượt: băng rôn BẢN GHI hiện ≤ 6 giây, đủ 3 cột; có mạng ⇒ lượt kế quay về trực tiếp (SC-003)", async ({ page, context }) => {
  await mockApi(page, { sim: new SimMock() });
  await page.goto("/booth?fast=1");
  await firstQuestion(page);
  const t0 = Date.now();
  await context.setOffline(true);
  const banner = page.getByTestId("replay-banner");
  await expect(banner).toContainText("KHÔNG PHẢI TRỰC TIẾP — đang chiếu lại bản ghi đã lưu trước đó", { timeout: 6000 });
  expect(Date.now() - t0).toBeLessThan(6000);
  await expect(page.getByTestId("booth-state")).toContainText("Đang chiếu lại bản ghi đã lưu sẵn");
  await expect(page.getByTestId("col-elder")).toBeVisible();
  await expect(page.getByTestId("col-ai")).toBeVisible();
  await expect(page.getByTestId("col-guardian")).toBeVisible();
  await expect(page.getByTestId("messages").getByRole("listitem")).toHaveCount(2); // bản ghi chạy đủ tới tin cho con
  await context.setOffline(false);
  await expect(banner).toHaveCount(0, { timeout: 20_000 }); // có mạng: lượt kế chạy trực tiếp
});

test("bảng điều khiển: chạy một kịch bản, dừng, đặt lại màn hình; chế độ Bản ghi không gọi máy chủ", async ({ page, context }) => {
  const calls = await mockApi(page, { sim: new SimMock() });
  await page.goto("/booth?fast=1&autoplay=0");
  await expect(page.getByTestId("booth-title")).toHaveText("Sẵn sàng trình diễn");
  const panel = await context.newPage();
  await panel.goto("/demo/console");
  await expect(panel.getByTestId("booth-link")).toContainText("Màn hình gian đã kết nối");
  await panel.getByRole("button", { name: "Dùng bản ghi" }).click();
  await panel.getByRole("button", { name: "Chạy: Giả danh công an" }).click();
  await expect(page.getByTestId("replay-banner")).toBeVisible();
  await expect(page.getByTestId("messages").getByRole("listitem")).toHaveCount(2, { timeout: 15_000 });
  expect(calls.filter((c) => c.path === "/v1/sim/runs")).toHaveLength(0); // chế độ bản ghi không gọi POST
  await expect(panel.getByTestId("results")).toContainText("bản ghi (không tính)");
  await panel.getByRole("button", { name: "Đặt lại cho khách mới" }).click();
  await expect(panel.getByTestId("reset-note")).toContainText("Đã dừng và xóa màn hình gian");
  await expect(panel.getByTestId("reset-command")).toContainText("hoicon.ops.booth reset");
  await expect(page.getByTestId("booth-title")).toHaveText("Sẵn sàng trình diễn");
});

test("bảng điều khiển khi chưa có màn hình gian: nút chạy bị khóa kèm hướng dẫn, nút Dừng luôn bấm được", async ({ page }) => {
  await page.goto("/demo/console");
  await expect(page.getByTestId("booth-state")).toContainText("Chưa có màn hình gian");
  await expect(page.getByTestId("link-help")).toContainText("cùng trình duyệt này");
  await expect(page.getByRole("button", { name: "Chạy cả danh sách (lặp lại)" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Chạy: Giả danh công an" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "⏹ Dừng ngay màn hình gian" })).toBeEnabled();
});

test("cổng mô phỏng tắt (API 404) ⇒ 'Trang này chưa mở'; hết phiên (401) ⇒ về trang đăng nhập", async ({ page }) => {
  await mockApi(page, { simStart: () => ({ status: 404 }) });
  await page.goto("/booth?fast=1");
  await expect(page.locator('main [role="alert"]')).toContainText("Trang này chưa mở");
  const other = await page.context().newPage();
  await mockApi(other, { simStart: () => ({ status: 401 }) });
  await other.goto("/booth?fast=1");
  await other.waitForURL("**/login**");
});

for (const vp of VIEWPORTS) {
  test(`giao diện ${vp.name}px: axe 0 lỗi, không cuộn ngang, chữ chính ≥ 28px, ảnh chụp`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await mockApi(page, { sim: new SimMock() });
    await page.goto("/booth?fast=1");
    await firstQuestion(page);
    await expect(page.getByTestId("messages").getByRole("listitem")).toHaveCount(2);
    const axe = await new AxeBuilder({ page }).analyze();
    expect(axe.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const px = await page.getByTestId("question").evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(px).toBeGreaterThanOrEqual(28);
    mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `booth-${vp.name}.png`), fullPage: true });
  });
}

test("bảng điều khiển: axe 0 lỗi và ảnh chụp", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/demo/console");
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  await page.screenshot({ path: path.join(EVIDENCE_DIR, "console-768.png"), fullPage: true });
});
