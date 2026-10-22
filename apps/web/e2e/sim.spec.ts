import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { BENIGN_ID, SimMock, mockApi } from "./fixtures";

// Spec 033, FR-010/FR-013: `/sim` đi hết một kịch bản bằng fixture hợp đồng (mạng bị chặn, tất định).
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "033-sim-trace");
const PHONE = /(?:\+?84|0)[\s.-]?[35789](?:[\s.-]?\d){8}/;

async function playScam(page: Page) {
  await page.getByRole("button", { name: "Bắt đầu" }).click(); // thao tác 1
  await expect(page.getByTestId("question")).toContainText("Đây là trợ lý AI HỏiCon");
  await page.getByRole("button", { name: "Có", exact: true }).click(); // thao tác 2
  await expect(page.getByTestId("messages").getByRole("listitem")).toHaveCount(2);
  await page.getByRole("button", { name: /Tôi nghi .* đang bị lừa/ }).click(); // thao tác 3
  await page.getByRole("button", { name: "Đúng, gửi xác nhận" }).click(); // thao tác 4
  await expect(page.getByRole("status").filter({ hasText: "Đã ghi nhận: nghi lừa đảo" })).toBeVisible();
}

test("kịch bản lừa đảo: Bắt đầu → trả lời → quyết định 'nghi lừa đảo' trong 4 thao tác", async ({ page }) => {
  const sim = new SimMock();
  const calls = await mockApi(page, { sim });
  await page.goto("/sim");
  await expect(page.getByTestId("sim-banner")).toContainText("MÔ PHỎNG — dữ liệu hư cấu, không có cuộc gọi hay tin Zalo thật");
  await expect(page.getByTestId("script")).toContainText("Kịch bản nháp"); // kịch bản draft có nhãn
  await playScam(page);
  // Mọi bước hiện ở bản chữ; mọi tin Zalo mô phỏng mở đầu bằng câu công khai AI (luật 6).
  await expect(page.getByTestId("steps").getByRole("listitem").first()).toBeVisible();
  for (const text of await page.getByTestId("messages").getByRole("listitem").allInnerTexts()) {
    expect(text.startsWith("Đây là trợ lý AI HỏiCon")).toBe(true);
  }
  expect(calls.filter((c) => c.method === "POST" && c.path === "/v1/sim/runs")).toHaveLength(1);
  expect(calls.find((c) => c.path.endsWith("/decision"))?.body).toEqual({ decision: "emergency_pause" });
  const answer = calls.find((c) => c.path.endsWith("/answer"));
  expect(answer?.body).toEqual({ question_id: "q_caller_authority", answer: "yes" }); // không có `note` tự do
});

test("kịch bản hợp lệ không bật luật: hiện lời giải thích, không có sự cố", async ({ page }) => {
  await mockApi(page, { sim: new SimMock() });
  await page.goto("/sim");
  await page.getByRole("combobox", { name: "Kịch bản" }).selectOption(BENIGN_ID);
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  await expect(page.getByTestId("sim-note")).toHaveText("Máy không bật nhắc dừng lại với tình huống này");
  await expect(page.getByTestId("question")).toHaveCount(0);
});

test("chạy hai lần cho cùng dãy bước và cùng chữ tin (SC-002)", async ({ page }) => {
  const sim = new SimMock();
  await mockApi(page, { sim });
  await page.goto("/sim");
  const snapshots: string[][] = [];
  for (let i = 0; i < 2; i += 1) {
    sim.stage = "idle";
    await page.reload();
    await playScam(page);
    snapshots.push([
      ...(await page.getByTestId("steps").getByRole("listitem").allInnerTexts()).map((t) => t.replace(/\d{1,2}:\d{2}:\d{2}/g, "")),
      ...(await page.getByTestId("messages").getByRole("listitem").allInnerTexts()).map((t) => t.replace(/\d{1,2}:\d{2}:\d{2}/g, "")),
    ]);
  }
  expect(snapshots[0].length).toBeGreaterThan(3);
  expect(snapshots[1]).toEqual(snapshots[0]);
});

test("DOM không có số điện thoại, h1 hay tên gói app (SC-006)", async ({ page }) => {
  await mockApi(page, { sim: new SimMock() });
  await page.goto("/sim");
  await playScam(page);
  const visible = await page.evaluate(() => document.body.innerText);
  const html = await page.evaluate(() => document.querySelector("main")?.innerHTML ?? "");
  const text = visible + html;
  expect(visible.match(PHONE)?.[0] ?? null).toBeNull(); // số điện thoại chỉ có thể nằm ở chữ nhìn thấy (HTML có số thập phân của SVG)
  expect(text).not.toMatch(/[0-9a-f]{64}/);
  expect(text).not.toMatch(/vn\.hoicon\.demo/);
});

test("cổng mô phỏng tắt (API 404): 'Trang này chưa mở'", async ({ page }) => {
  await mockApi(page, { simScenarios: () => ({ status: 404, json: { detail: "Không tìm thấy" } }) });
  await page.goto("/sim");
  await expect(page.getByRole("heading", { name: "Trang này chưa mở" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Bắt đầu" })).toHaveCount(0);
});

test("hết hạn mức (429): báo chờ, không treo giao diện", async ({ page }) => {
  await mockApi(page, { simStart: () => ({ status: 429, json: { detail: "x" }, headers: { "Retry-After": "30" } }) });
  await page.goto("/sim");
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Anh/chị đã chạy nhiều lượt liên tiếp" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Bắt đầu" })).toBeEnabled();
});

test("nút trả lời của bác cao ≥ 64 px và có xác nhận trước khi quyết định", async ({ page }) => {
  await mockApi(page, { sim: new SimMock() });
  await page.goto("/sim");
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  for (const name of ["Có", "Không", "Chưa chắc"]) {
    const box = await page.getByRole("button", { name, exact: true }).boundingBox();
    expect(box!.height, name).toBeGreaterThanOrEqual(63.5);
  }
  await page.getByRole("button", { name: "Có", exact: true }).click();
  await page.getByRole("button", { name: /Tôi nghi .* đang bị lừa/ }).click();
  await expect(page.getByText("Anh/chị nghi Mẹ đang bị lừa? HỏiCon sẽ giữ cảnh báo mở để theo dõi.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Chưa, quay lại" })).toBeVisible();
});

for (const view of [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]) {
  test(`axe 0 lỗi nghiêm trọng, không tràn ngang, ảnh · ${view.width}px`, async ({ page }) => {
    await page.setViewportSize(view);
    await mockApi(page, { sim: new SimMock() });
    await page.goto("/sim");
    await page.getByRole("button", { name: "Bắt đầu" }).click();
    await expect(page.getByTestId("question")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    if (view.width < 1024) {  // dưới 1024 px: ba thẻ có tab; từ 1024 px: ba cột
      await expect(page.getByRole("tablist")).toBeVisible();
      await page.getByRole("tab", { name: "Zalo của con" }).click();
      await expect(page.getByRole("heading", { name: "Zalo của con (mô phỏng)" })).toBeVisible();
    } else {
      await expect(page.getByRole("tablist")).toBeHidden();
      await expect(page.getByRole("heading", { name: "Trợ lý AI" })).toBeVisible(); // ba cột cùng hiện
    }
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
      .options({ rules: { "color-contrast-enhanced": { enabled: true } } })
      .analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
    mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `sim-${view.width}.png`), fullPage: true });
  });
}
