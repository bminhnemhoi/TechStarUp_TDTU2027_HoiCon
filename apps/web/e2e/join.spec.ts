import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { mockApi } from "./fixtures";

// Spec 050 FR-007 (T013): `/join/[code]` cho khách tại gian + nút tạo mã ở console. Fixture hợp đồng booth_join.v1.
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "050-booth-mode");

test("khách mở liên kết: lời chào chữ lớn, KHÔNG tự đổi mã khi mở trang; bấm nút mới vào xem", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/join/K7M2QX");
  await expect(page.getByRole("heading", { name: /Bạn đang xem bản trình diễn/ })).toBeVisible();
  await expect(page.getByTestId("join-greeting")).toContainText("Mọi dữ liệu là hư cấu");
  expect(calls.filter((c) => c.path === "/v1/booth/join")).toHaveLength(0); // trình quét liên kết không đốt lượt khách
  await page.getByRole("button", { name: "Vào xem bản trình diễn" }).click();
  await expect(page.getByTestId("join-welcome")).toContainText("Gia đình Mẫu");
  const join = calls.find((c) => c.path === "/v1/booth/join");
  expect(join?.body).toEqual({ code: "K7M2QX" });
  await expect(page.getByRole("link", { name: "Xem các sự cố của buổi trình diễn" })).toHaveAttribute("href", "/incidents");
});

test("gõ chữ thường vẫn nhận (đổi thành chữ hoa); mã sai ⇒ câu thân thiện, không lộ mã lỗi", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/join/zzzzzz");
  await page.getByRole("button", { name: "Vào xem bản trình diễn" }).click();
  expect(calls.find((c) => c.path === "/v1/booth/join")?.body).toEqual({ code: "ZZZZZZ" });
  const alert = page.getByRole("main").getByRole("alert");
  await expect(alert).toContainText("Mã chưa đúng hoặc đã hết hạn");
  await expect(alert).not.toContainText("join_code_invalid");
});

test("mã sai định dạng không gửi lên máy chủ; thử sai nhiều ⇒ báo đợi", async ({ page }) => {
  const calls = await mockApi(page, { boothJoin: () => ({ status: 429, json: { detail: "x" } }) });
  await page.goto("/join/ab");
  await page.getByRole("button", { name: "Vào xem bản trình diễn" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("6 ký tự");
  expect(calls.filter((c) => c.path === "/v1/booth/join")).toHaveLength(0);
  await page.goto("/join/K7M2QX");
  await page.getByRole("button", { name: "Vào xem bản trình diễn" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("đợi vài phút");
});

test("console: tạo mã hiện chữ rất lớn + liên kết + hạn; có chỉ dẫn đặt lại sẽ vô hiệu mã", async ({ page }) => {
  await mockApi(page);
  await page.goto("/demo/console");
  await page.getByRole("button", { name: "Tạo mã cho khách" }).click();
  const box = page.getByTestId("join-code");
  await expect(box).toHaveText("K7M2QX");
  await expect(page.getByTestId("join-link")).toContainText("/join/K7M2QX");
  await expect(page.getByTestId("join-code-note")).toContainText("Đặt lại");
  const px = await box.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  expect(px).toBeGreaterThanOrEqual(48);
});

for (const view of [
  { width: 390, height: 844 },
  { width: 1440, height: 900 },
]) {
  test(`axe 0 lỗi nghiêm trọng, không tràn ngang, ảnh · ${view.width}px`, async ({ page }) => {
    await page.setViewportSize(view);
    await mockApi(page);
    await page.goto("/join/K7M2QX");
    await page.getByRole("button", { name: "Vào xem bản trình diễn" }).click();
    await expect(page.getByTestId("join-welcome")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
      .options({ rules: { "color-contrast-enhanced": { enabled: true } } })
      .analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
    mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `join-${view.width}.png`), fullPage: true });
  });
}
