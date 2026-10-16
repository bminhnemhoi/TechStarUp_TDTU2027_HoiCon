import { expect, test } from "@playwright/test";
import { FAKE_TOKEN, SESSION, mockApi } from "./fixtures";

test.describe("đăng nhập (spec 027, FR-005, SC-001, SC-003)", () => {
  test("/login không token chỉ hướng dẫn nhắn 4 cho bot", async ({ page }) => {
    await mockApi(page);
    const response = await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Đăng nhập HỏiCon" })).toBeVisible();
    await expect(page.getByText("Nhắn số", { exact: false })).toBeVisible();
    await expect(page.getByText("Đây là trợ lý AI HỏiCon.")).toBeVisible();
    expect(response?.headers()["x-robots-tag"]).toContain("noindex");
  });

  test("phiên hết hạn: /login?het-han=1 báo rõ lý do và hướng dẫn lấy liên kết mới", async ({ page }) => {
    await mockApi(page);
    await page.goto("/login?het-han=1");
    await expect(page.getByRole("status")).toContainText("Phiên đăng nhập đã hết hạn");
    await expect(page.getByText("Nhắn số", { exact: false })).toBeVisible();
  });

  test("lỗi 410 có nút dẫn về hướng dẫn lấy liên kết mới", async ({ page }) => {
    await mockApi(page, { exchange: () => ({ status: 410, json: { detail: "x" } }) });
    await page.goto(`/login/${FAKE_TOKEN}`);
    await page.getByRole("link", { name: "Xem cách lấy liên kết mới" }).click();
    await page.waitForURL("**/login");
    await expect(page.getByRole("heading", { name: "Đăng nhập HỏiCon" })).toBeVisible();
  });

  test("URL không còn token sau khi đăng nhập; token chỉ đi trong thân POST", async ({ page }) => {
    const calls = await mockApi(page);
    const urls: string[] = [];
    const urlWhenExchanging: string[] = [];
    page.on("framenavigated", (frame) => urls.push(frame.url()));
    page.on("request", (request) => {
      if (request.method() === "POST" && request.url().endsWith("/v1/guardian/session")) urlWhenExchanging.push(page.url());
    });
    const response = await page.goto(`/login/${FAKE_TOKEN}`);
    await page.waitForURL("**/incidents");

    expect(response?.headers()["referrer-policy"]).toBe("no-referrer");
    expect(response?.headers()["x-robots-tag"]).toContain("noindex");
    expect(response?.headers()["cache-control"]).toContain("no-store"); // review bảo mật 027: kiểm thật trên `next start`
    // Địa chỉ trên thanh URL bỏ token NGAY (replaceState chạy trước khi gọi API) và không bao giờ quay lại có token.
    const firstClean = urls.findIndex((u) => !u.includes(FAKE_TOKEN));
    expect(firstClean).toBeGreaterThan(0);
    expect(urls.slice(firstClean).filter((u) => u.includes(FAKE_TOKEN))).toEqual([]);
    expect(urlWhenExchanging).toHaveLength(1);
    expect(urlWhenExchanging[0]).not.toContain(FAKE_TOKEN);
    expect(page.url()).not.toContain(FAKE_TOKEN);
    // Mọi lời gọi API: token không nằm trên URL; đúng một lần đổi phiên và thân chỉ có `token`.
    expect(calls.filter((c) => c.path.includes(FAKE_TOKEN))).toEqual([]);
    const exchanges = calls.filter((c) => c.method === "POST" && c.path === "/v1/guardian/session");
    expect(exchanges).toHaveLength(1);
    expect(exchanges[0].body).toEqual({ token: FAKE_TOKEN });
  });

  test("trang có token đặt noindex và no-referrer trong <head>", async ({ page }) => {
    await mockApi(page, { exchange: () => ({ status: 410, json: { detail: "x" } }) });
    await page.goto(`/login/${FAKE_TOKEN}`);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
    await expect(page.locator('meta[name="referrer"]')).toHaveAttribute("content", "no-referrer");
  });

  test("410 ⇒ thông báo tiếng Việt kèm hướng dẫn, URL đã về /login", async ({ page }) => {
    await mockApi(page, { exchange: () => ({ status: 410, json: { detail: "Liên kết đăng nhập không dùng được." } }) });
    await page.goto(`/login/${FAKE_TOKEN}`);
    await expect(page.locator(`main [role="alert"]`)).toContainText("Liên kết đăng nhập không dùng được");
    await expect(page.locator(`main [role="alert"]`)).toContainText("Nhắn số 4 cho HỏiCon trên Zalo");
    expect(new URL(page.url()).pathname).toBe("/login");
    expect(await page.locator("body").innerText()).not.toContain(FAKE_TOKEN);
  });

  test("lỗi mạng ⇒ cho thử lại và thử lại được", async ({ page }) => {
    let attempt = 0;
    await mockApi(page, {
      exchange: () => (++attempt === 1 ? { status: 0, abort: true } : { status: 200, json: SESSION }),
    });
    await page.goto(`/login/${FAKE_TOKEN}`);
    await expect(page.locator(`main [role="alert"]`)).toContainText("Chưa đăng nhập được");
    await page.getByRole("button", { name: "Thử lại" }).click();
    await page.waitForURL("**/incidents");
    expect(attempt).toBe(2);
  });

  test("lỗi máy chủ 503 ⇒ báo bận, không nói liên kết hỏng", async ({ page }) => {
    await mockApi(page, { exchange: () => ({ status: 503, json: { detail: "Dịch vụ chưa sẵn sàng" } }) });
    await page.goto(`/login/${FAKE_TOKEN}`);
    await expect(page.locator(`main [role="alert"]`)).toContainText("Máy chủ đang bận");
    await expect(page.getByRole("button", { name: "Thử lại" })).toBeVisible();
  });
});
