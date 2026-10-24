import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { DrillMock, mockApi } from "./fixtures";

// Spec 028 FR-011 (T021): `/drills` đặt lịch + lịch sử, bằng fixture hợp đồng (mạng bị chặn, tất định).
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "028-drills-web");
const ELDER_ID = "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e82"; // member_id của "Mẹ" trong fixture danh sách sự cố

async function fillForm(page: import("@playwright/test").Page) {
  await page.getByLabel("Người nhận diễn tập").selectOption({ label: "Mẹ" });
  await page.getByLabel("Kịch bản").selectOption("drill_bank_card_locked");
  await page.getByLabel("Bắt đầu lúc").fill("2030-01-15T14:00");
  await page.getByLabel("Kéo dài").selectOption("60");
}

test("lịch sử có nhãn [DIỄN TẬP], tên kịch bản, trạng thái bằng chữ và điểm", async ({ page }) => {
  await mockApi(page, { drills: new DrillMock() });
  await page.goto("/drills");
  await expect(page.getByRole("heading", { name: "Diễn tập cho người nhà" })).toBeVisible();
  const item = page.getByTestId("drill-list").getByRole("listitem").first();
  await expect(item).toContainText("[DIỄN TẬP]");
  await expect(item).toContainText("Cuộc gọi báo thẻ bị khóa");
  await expect(item).toContainText("Đã hoàn thành bài");
  await expect(item).toContainText("Làm đúng 4/5 bước");
  await expect(item).toHaveClass(/border-drill-accent/); // màu diễn tập (drill.*), không dùng màu rủi ro
});

test("đặt lịch: thân gửi đi chỉ có 4 trường, giờ có múi +07:00, bài mới hiện đầu danh sách", async ({ page }) => {
  const calls = await mockApi(page, { drills: new DrillMock() });
  await page.goto("/drills");
  await fillForm(page);
  await page.getByRole("button", { name: "Đặt lịch diễn tập" }).click();
  await expect(page.getByTestId("drill-list").getByRole("listitem").first()).toContainText("Đã đặt lịch");
  await expect(page.getByRole("status").filter({ hasText: "Đã đặt lịch" })).toBeVisible();
  const post = calls.find((c) => c.method === "POST" && c.path === "/v1/guardian/drills");
  expect(post?.body).toEqual({
    member_id: ELDER_ID,
    script_id: "drill_bank_card_locked",
    window_start: "2030-01-15T14:00:00+07:00",
    window_end: "2030-01-15T15:00:00+07:00",
  });
});

test("thiếu giờ ⇒ thông báo tiếng Việt (không phải của trình duyệt); chọn giờ ⇒ hiện câu xác nhận ngày/giờ", async ({ page }) => {
  await mockApi(page, { drills: new DrillMock() });
  await page.goto("/drills");
  await page.getByRole("button", { name: "Đặt lịch diễn tập" }).click();
  await expect(page.getByRole("form", { name: "Đặt lịch diễn tập" }).getByRole("alert")).toContainText("chọn giờ bắt đầu");
  await fillForm(page);
  await expect(page.getByTestId("picked-time")).toContainText("14:00 đến 15:00, ngày 15/01/2030 (giờ Việt Nam)");
});

test("bị từ chối ⇒ câu tiếng Việt dễ hiểu, không lộ mã kỹ thuật, danh sách không đổi", async ({ page }) => {
  const mock = new DrillMock();
  mock.refuse = "window_overlaps";
  await mockApi(page, { drills: mock });
  await page.goto("/drills");
  await expect(page.getByTestId("drill-list").getByRole("listitem").first()).toBeVisible();
  const before = await page.getByTestId("drill-list").getByRole("listitem").count();
  await fillForm(page);
  await page.getByRole("button", { name: "Đặt lịch diễn tập" }).click();
  const alert = page.getByRole("form", { name: "Đặt lịch diễn tập" }).getByRole("alert");
  await expect(alert).toContainText("đã có một bài diễn tập");
  await expect(alert).not.toContainText("window_overlaps");
  await expect(page.getByTestId("drill-list").getByRole("listitem")).toHaveCount(before);
  for (const [code, text] of [["consent_missing", "đồng ý"], ["monthly_limit", "trong tháng"], ["window_past", "đã qua"]] as const) {
    mock.refuse = code;
    await page.getByRole("button", { name: "Đặt lịch diễn tập" }).click();
    await expect(page.getByRole("form", { name: "Đặt lịch diễn tập" }).getByRole("alert")).toContainText(text);
  }
});

test("chưa có bài nào / chưa biết người nhận: nói rõ, không hiện biểu mẫu hỏng", async ({ page }) => {
  const empty = new DrillMock();
  empty.drills = [];
  empty.elders = [];
  await mockApi(page, { drills: empty });
  await page.goto("/drills");
  await expect(page.getByText("Chưa có bài diễn tập nào")).toBeVisible();
  await expect(page.getByTestId("no-elders")).toContainText("mời người thân cài ứng dụng");
  await expect(page.getByRole("button", { name: "Đặt lịch diễn tập" })).toHaveCount(0); // không hiện biểu mẫu hỏng
});

test("người nhận chưa đồng ý diễn tập ⇒ nút tắt kèm câu giải thích; chọn người đã đồng ý ⇒ nút bật", async ({ page }) => {
  await mockApi(page, { drills: new DrillMock() });
  await page.goto("/drills");
  const submit = page.getByRole("button", { name: "Đặt lịch diễn tập" });
  await expect(submit).toBeEnabled();
  await page.getByLabel("Người nhận diễn tập").selectOption({ label: "Bà Nội (chưa đồng ý diễn tập)" });
  const disabled = page.getByRole("button", { name: "Chưa đặt lịch được" });
  await expect(disabled).toBeDisabled();
  await expect(disabled).toHaveAttribute("aria-describedby", "no-consent-msg");
  await expect(page.getByTestId("no-consent")).toContainText("chưa đồng ý");
  await page.getByLabel("Người nhận diễn tập").selectOption({ label: "Mẹ" });
  await expect(submit).toBeEnabled();
  await expect(page.getByTestId("no-consent")).toHaveCount(0);
});

test("kịch bản trong ô chọn lấy từ máy chủ, không viết cứng", async ({ page }) => {
  const mock = new DrillMock();
  mock.scripts = [{ id: "drill_bank_card_locked", title: "Kịch bản chỉ có ở máy chủ", summary: "Cuộc gọi giả, 2 bước." }];
  await mockApi(page, { drills: mock });
  await page.goto("/drills");
  await expect(page.getByLabel("Kịch bản").locator("option")).toHaveText(["Kịch bản chỉ có ở máy chủ"]);
  await expect(page.getByTestId("script-summary")).toContainText("Cuộc gọi giả, 2 bước.");
});

for (const view of [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]) {
  test(`axe 0 lỗi nghiêm trọng, không tràn ngang, ảnh · ${view.width}px`, async ({ page }) => {
    await page.setViewportSize(view);
    await mockApi(page, { drills: new DrillMock() });
    await page.goto("/drills");
    await expect(page.getByTestId("drill-list")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
      .options({ rules: { "color-contrast-enhanced": { enabled: true } } })
      .analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
    mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `drills-${view.width}.png`), fullPage: true });
  });
}
