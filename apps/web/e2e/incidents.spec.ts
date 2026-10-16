import { expect, test } from "@playwright/test";
import { LIST_ITEMS, OPEN_STATES, mockApi } from "./fixtures";

const drill = { ...LIST_ITEMS[0], id: "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ec0", is_drill: true, drill_id: "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ec1", level: "medium" };

test.describe("danh sách sự cố (spec 027, FR-006)", () => {
  test("hai nhóm, thẻ có mức rủi ro bằng biểu tượng + chữ và trạng thái tiếng Việt", async ({ page }) => {
    await mockApi(page);
    await page.goto("/incidents");
    await expect(page.getByRole("heading", { name: "Sự cố của gia đình" })).toBeVisible();
    const open = page.getByRole("region", { name: "Đang cần chú ý" });
    const closed = page.getByRole("region", { name: "Đã xong" });
    await expect(open.getByRole("link")).toHaveCount(1);
    await expect(closed.getByRole("link")).toHaveCount(1);
    await expect(open).toContainText("Mức rủi ro: Cao");
    await expect(open).toContainText("Chờ người nhà quyết định");
    await expect(closed).toContainText("Đã xong: an toàn");
    await expect(open.getByRole("link").first()).toContainText("Mẹ");
    await expect(page.getByText("Đây là trợ lý AI HỏiCon.").first()).toBeVisible();
    await expect(page.getByText("Gia đình thử nghiệm")).toBeVisible();
  });

  test("trang dữ liệu gia đình: no-store, noindex, no-referrer ở tiêu đề phản hồi", async ({ page }) => {
    await mockApi(page);
    const list = await page.goto("/incidents");
    const detail = await page.goto("/incidents/01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e80");
    for (const response of [list, detail]) {
      const headers = response?.headers() ?? {};
      expect(headers["cache-control"]).toContain("no-store");
      expect(headers["x-robots-tag"]).toContain("noindex");
      expect(headers["referrer-policy"]).toBe("no-referrer");
    }
  });

  test("sự cố đã xong không còn tô màu báo động và ghi 'mức rủi ro lúc đó'", async ({ page }) => {
    await mockApi(page);
    await page.goto("/incidents");
    const card = page.getByRole("region", { name: "Đã xong" }).getByRole("link");
    await expect(card).toHaveClass(/bg-surface-muted/);
    await expect(card).toContainText("Mức rủi ro lúc đó: Cao");
    await expect(card).toContainText("mở ");
  });

  test("sự cố diễn tập có nhãn [DIỄN TẬP] và màu riêng", async ({ page }) => {
    await mockApi(page, {
      list: (status) => ({ status: 200, json: { incidents: status === "open" ? [drill] : [], next_cursor: null } }),
    });
    await page.goto("/incidents");
    const card = page.getByRole("region", { name: "Đang cần chú ý" }).getByRole("link");
    await expect(card).toContainText("[DIỄN TẬP]");
    await expect(card).toHaveClass(/bg-drill-bg/);
  });

  test("trạng thái rỗng", async ({ page }) => {
    await mockApi(page, { list: () => ({ status: 200, json: { incidents: [], next_cursor: null } }) });
    await page.goto("/incidents");
    await expect(page.getByText("Hiện không có sự cố nào cần chú ý.")).toBeVisible();
    await expect(page.getByText("Chưa có sự cố nào đã xong.")).toBeVisible();
  });

  test("trạng thái đang tải rồi lỗi và thử lại", async ({ page }) => {
    let failing = true;
    await mockApi(page, {
      list: (status) =>
        failing
          ? { status: 503, json: { detail: "Dịch vụ chưa sẵn sàng" } }
          : { status: 200, json: { incidents: LIST_ITEMS.filter((i) => OPEN_STATES.includes(i.state as string) === (status === "open")), next_cursor: null } },
    });
    await page.goto("/incidents");
    const open = page.getByRole("region", { name: "Đang cần chú ý" });
    await expect(open.locator(`[role="alert"]`)).toContainText("Chưa tải được danh sách");
    failing = false;
    await open.getByRole("button", { name: "Thử lại" }).click();
    await expect(open.getByRole("link")).toHaveCount(1);
  });

  test("nút Tải thêm nối trang kế tiếp, không trùng", async ({ page }) => {
    const second = { ...LIST_ITEMS[0], id: "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ed0", state: "case_open" };
    const calls = await mockApi(page, {
      list: (status, cursor) => {
        if (status === "closed") return { status: 200, json: { incidents: [], next_cursor: null } };
        return cursor
          ? { status: 200, json: { incidents: [second], next_cursor: null } }
          : { status: 200, json: { incidents: [LIST_ITEMS[0]], next_cursor: "TRANG2" } };
      },
    });
    await page.goto("/incidents");
    const open = page.getByRole("region", { name: "Đang cần chú ý" });
    await open.getByRole("button", { name: "Tải thêm" }).click();
    await expect(open.getByRole("link")).toHaveCount(2);
    await expect(open.getByRole("button", { name: "Tải thêm" })).toHaveCount(0);
    expect(calls.some((c) => c.path.includes("cursor=TRANG2"))).toBe(true);
  });

  test("chưa đăng nhập (401) ⇒ chuyển về /login", async ({ page }) => {
    await mockApi(page, {
      me: () => ({ status: 401, json: { detail: "Chưa xác thực người giám hộ" } }),
      list: () => ({ status: 401, json: { detail: "Chưa xác thực người giám hộ" } }),
    });
    await page.goto("/incidents");
    await page.waitForURL(/\/login\?het-han=1$/);
  });

  test("đăng xuất xóa phiên rồi về /login", async ({ page }) => {
    const calls = await mockApi(page);
    await page.goto("/incidents");
    await page.getByRole("button", { name: "Đăng xuất" }).click();
    await page.waitForURL("**/login");
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/v1/guardian/session")).toBe(true);
  });

  test("bấm thẻ mở chi tiết sự cố", async ({ page }) => {
    await mockApi(page);
    await page.goto("/incidents");
    await page.getByRole("region", { name: "Đang cần chú ý" }).getByRole("link").click();
    await page.waitForURL(`**/incidents/${LIST_ITEMS[0].id}`);
  });
});
