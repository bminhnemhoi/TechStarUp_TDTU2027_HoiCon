import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { CaseMock, mockApi } from "./fixtures";

// Spec 031, FR-010/FR-014: trang hồ sơ vụ việc bằng fixture hợp đồng case_file.v1 (mạng bị chặn, tất định).
const INCIDENT = "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e80";
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "031-case-file");
const FAKE_PHONE = "0900000555";
const FAKE_ACCOUNT = "9704000011112222";

async function open(page: Page, mock = new CaseMock()) {
  await mockApi(page, { caseFile: mock });
  await page.goto(`/incidents/${INCIDENT}/case-file`);
  await expect(page.getByTestId("status")).toBeVisible();
  return mock;
}

test("hiện bản nháp, nhãn trợ lý AI và câu 'không tự gửi cho cơ quan nào'", async ({ page }) => {
  await open(page);
  await expect(page.getByTestId("ai-label")).toContainText("Đây là trợ lý AI HỏiCon");
  await expect(page.getByTestId("status")).toContainText("Bản nháp");
  await expect(page.getByText("HỏiCon không tự gửi hồ sơ này cho cơ quan nào.").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /In \/ lưu PDF/ })).toHaveCount(0); // chỉ hiện sau khi duyệt
  await expect(page.getByTestId("steps-guide")).toContainText("Mang bản in tới công an");
});

test("duyệt có xác nhận ⇒ hiện nút in", async ({ page }) => {
  await open(page);
  await page.getByRole("button", { name: /Duyệt hồ sơ/ }).click();
  await expect(page.getByText("Anh/chị đã đọc kỹ và muốn duyệt hồ sơ này?")).toBeVisible();
  await page.getByRole("button", { name: "Chưa, quay lại" }).click();
  await expect(page.getByTestId("status")).toContainText("Bản nháp");
  await page.getByRole("button", { name: /Duyệt hồ sơ/ }).click();
  await page.getByRole("button", { name: "Đúng, duyệt hồ sơ" }).click();
  await expect(page.getByTestId("status")).toContainText("Đã duyệt");
  await expect(page.getByRole("button", { name: /In \/ lưu PDF/ })).toBeVisible();
});

test("bỏ hồ sơ ⇒ trạng thái đã bỏ, không còn nút duyệt", async ({ page }) => {
  await open(page);
  await page.getByRole("button", { name: "Bỏ hồ sơ này" }).click();
  await expect(page.getByText("Việc này không hoàn lại được.")).toBeVisible();
  await page.getByRole("button", { name: "Đúng, bỏ hồ sơ" }).click();
  await expect(page.getByTestId("status")).toContainText("Đã bỏ");
  await expect(page.getByRole("button", { name: /Duyệt hồ sơ/ })).toHaveCount(0);
});

test("ô tự điền không đi qua mạng khi điền, duyệt và in (SC-003)", async ({ page }) => {
  const seen: string[] = [];
  page.on("request", (request) => seen.push(`${request.method()} ${request.url()} ${request.postData() ?? ""}`));
  await page.addInitScript(() => {
    (window as unknown as { __printed: number }).__printed = 0;
    window.print = () => {
      (window as unknown as { __printed: number }).__printed += 1;
    };
  });
  await open(page);
  await page.getByLabel(/Số điện thoại đã gọi tới/).fill(FAKE_PHONE);
  await page.getByLabel(/Số tiền đã chuyển/).fill(`20 triệu vào ${FAKE_ACCOUNT}`);
  await page.getByRole("button", { name: /Duyệt hồ sơ/ }).click();
  await page.getByRole("button", { name: "Đúng, duyệt hồ sơ" }).click();
  await expect(page.getByRole("button", { name: /In \/ lưu PDF/ })).toBeVisible();
  await page.getByRole("button", { name: /In \/ lưu PDF/ }).click();
  expect(await page.evaluate(() => (window as unknown as { __printed: number }).__printed)).toBe(1);
  const apiCalls = seen.filter((line) => line.includes("/v1/"));
  expect(apiCalls.length).toBeGreaterThan(0);
  for (const value of [FAKE_PHONE, FAKE_ACCOUNT, "20 triệu", encodeURIComponent("20 triệu")]) {
    expect(seen.filter((line) => line.includes(value)), value).toEqual([]);
  }
  // Không lưu trong trình duyệt (luật ADR-006): localStorage/sessionStorage không có giá trị nào.
  const stored = await page.evaluate(() => JSON.stringify([{ ...localStorage }, { ...sessionStorage }]));
  expect(stored).not.toContain(FAKE_PHONE);
  expect(stored).not.toContain(FAKE_ACCOUNT);
  await expect(page.locator("form")).toHaveCount(0); // ô tự điền không nằm trong form gửi đi
});

test("sự cố chưa có hồ sơ (404): thông báo dễ hiểu", async ({ page }) => {
  await mockApi(page, { caseFileGet: () => ({ status: 404, json: { detail: "x" } }) });
  await page.goto(`/incidents/${INCIDENT}/case-file`);
  await expect(page.getByRole("heading", { name: "Chưa có hồ sơ cho sự cố này" })).toBeVisible();
});

test("bản in ẩn nút và điều hướng nhưng giữ nội dung và ô tự điền", async ({ page }) => {
  await open(page, Object.assign(new CaseMock(), { status: "approved" }));
  await page.getByLabel(/Số điện thoại đã gọi tới/).fill(FAKE_PHONE);
  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("button", { name: /In \/ lưu PDF/ })).toBeHidden();
  await expect(page.getByRole("link", { name: /Về trang sự cố/ })).toBeHidden();
  await expect(page.getByRole("heading", { name: "Tóm tắt diễn biến" })).toBeVisible();
  await expect(page.getByText("HỏiCon không tự gửi hồ sơ này cho cơ quan nào. Mã hồ sơ:")).toBeVisible(); // câu in ở chân bản in
  await expect(page.getByLabel(/Số điện thoại đã gọi tới/)).toHaveValue(FAKE_PHONE);
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  await page.pdf({ path: path.join(EVIDENCE_DIR, "case-file-print.pdf"), format: "A4" });
});

for (const view of [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]) {
  test(`axe 0 lỗi nghiêm trọng, không tràn ngang, ảnh · ${view.width}px`, async ({ page }) => {
    await page.setViewportSize(view);
    await open(page, Object.assign(new CaseMock(), { status: "approved" }));
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
      .options({ rules: { "color-contrast-enhanced": { enabled: true } } })
      .analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
    mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `case-file-${view.width}.png`), fullPage: true });
  });
}
