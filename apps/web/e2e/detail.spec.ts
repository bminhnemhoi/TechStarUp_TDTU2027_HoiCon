import { expect, test } from "@playwright/test";
import { RUN_ID, STEPS, detail, doneFrame, mockApi, sse, step, stepFrame } from "./fixtures";

const INCIDENT_ID = "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e80";
const PHONE = /(\+84|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[0-9]{7}/;
const live = (id: string, node: string, output: Json | null = { level: "high" }) =>
  step(id, node, output, "2026-12-01T02:16:30.000000Z");
type Json = Record<string, unknown>;

test.describe("chi tiết sự cố (spec 027, FR-007, FR-008)", () => {
  test("tiêu đề có mức rủi ro, trạng thái, câu công khai AI và lịch sử chuyển trạng thái", async ({ page }) => {
    await mockApi(page);
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByRole("heading", { level: 1, name: "Mẹ" })).toBeVisible();
    await expect(page.getByText("Mức rủi ro: Cao")).toBeVisible();
    await expect(page.getByText("Chờ người nhà quyết định").first()).toBeVisible();
    await expect(page.getByText("Đây là trợ lý AI HỏiCon.").first()).toBeVisible();
    const history = page.getByTestId("transitions").getByRole("listitem");
    await expect(history.first()).toContainText("Vừa phát hiện");
    await expect(history.first()).toContainText("Điện thoại của người thân");
    expect(await page.locator("body").innerText()).not.toMatch(PHONE);
  });

  test("diễn tập: nhãn [DIỄN TẬP] và màu riêng", async ({ page }) => {
    await mockApi(page, { detail: () => ({ status: 200, json: detail({ is_drill: true, drill_id: "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6eb0" }) }) });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByText("[DIỄN TẬP] Đây là bài tập")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 }).locator("xpath=ancestor::article")).toHaveClass(/bg-drill-bg/);
  });

  test("trace: nạp lịch sử rồi nhận bước mới từ luồng, bỏ trùng theo id, dừng khi done", async ({ page }) => {
    const fresh = live("01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ea1", "intervention");
    const calls = await mockApi(page, {
      stream: () => ({ body: sse([stepFrame(STEPS[0]), stepFrame(fresh), stepFrame(fresh), doneFrame(STEPS.length + 1)]) }),
    });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    const steps = page.getByTestId("steps").getByRole("listitem");
    await expect(page.getByTestId("stream-status")).toHaveText("Trợ lý AI đã làm xong các bước");
    await expect(steps).toHaveCount(STEPS.length + 1); // lịch sử + 1 bước mới, không trùng
    await expect(steps.last()).toContainText("Gửi tóm tắt cho người nhà");
    await expect(page.getByText("Nhận tín hiệu từ điện thoại của Mẹ")).toBeVisible();
    // Sau `done` không mở lại luồng.
    await page.waitForTimeout(1200);
    expect(calls.filter((c) => c.path.endsWith("/stream"))).toHaveLength(1);
    expect(await page.getByTestId("steps").innerText()).not.toContain("{");
  });

  test("mất kết nối ⇒ 'Đang kết nối lại…' rồi nối lại không trùng bước", async ({ page }) => {
    const fresh = live("01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ea2", "verify", { dangerous: 1, warning: 0, level_before: "high", level_after: "critical" });
    await mockApi(page, {
      stream: (attempt) =>
        attempt === 1
          ? { body: sse([stepFrame(STEPS[0])]) } // đóng không có done ⇒ trình duyệt tự nối lại
          : { body: sse([stepFrame(STEPS[0]), stepFrame(fresh), doneFrame(STEPS.length + 1)]), delayMs: 1200 },
    });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByTestId("stream-status")).toHaveText("Đang kết nối lại…");
    await expect(page.getByTestId("stream-status")).toHaveText("Trợ lý AI đã làm xong các bước", { timeout: 15_000 });
    await expect(page.getByTestId("steps").getByRole("listitem")).toHaveCount(STEPS.length + 1);
    await expect(page.getByText("1 mục rất đáng ngờ")).toBeVisible();
  });

  test("khung error không thể thử lại ⇒ báo lỗi và có nút Thử lại", async ({ page }) => {
    await mockApi(page, {
      stream: () => ({ body: `retry: 300\n\nevent: error\ndata: {"retryable":false}\n\n` }),
    });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByTestId("stream-status")).toHaveText("Chưa theo dõi trực tiếp được. Anh/chị bấm Thử lại.");
    await expect(page.getByRole("button", { name: "Thử lại" }).first()).toBeVisible();
  });

  test("node lạ ⇒ 'Bước khác của trợ lý AI'; không bao giờ in JSON thô", async ({ page }) => {
    const odd = step("01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ea3", "buoc_moi_la", { khoa_la: "gia_tri_la", h: { x: 1 } }, "2026-12-01T02:17:00.000000Z");
    await mockApi(page, {
      steps: () => ({ status: 200, json: { run_id: RUN_ID, status: "done", is_drill: false, is_demo: true, steps: [...STEPS, odd] } }),
    });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByText("Bước khác của trợ lý AI")).toBeVisible();
    const text = await page.getByTestId("steps").innerText();
    expect(text).not.toContain("gia_tri_la");
    expect(text).not.toContain("khoa_la");
  });

  test("sự cố chưa có lượt chạy ⇒ nói rõ, không mở luồng", async ({ page }) => {
    const calls = await mockApi(page, { detail: () => ({ status: 200, json: detail({ run_id: null }) }) });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByText("Chưa có bước nào của trợ lý AI cho sự cố này.")).toBeVisible();
    expect(calls.some((c) => c.path.includes("/v1/runs/"))).toBe(false);
  });

  test("nút gọi là thẻ tel: KHÔNG kèm số", async ({ page }) => {
    await mockApi(page);
    await page.goto(`/incidents/${INCIDENT_ID}`);
    const call = page.getByRole("link", { name: /Mở bàn phím gọi điện/ });
    await expect(call).toHaveAttribute("href", "tel:");
  });

  test("quyết định có bước xác nhận; 'Quay lại' không gửi gì", async ({ page }) => {
    const calls = await mockApi(page);
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await page.getByRole("button", { name: /Đã gọi được/ }).click();
    await expect(page.getByText(/đã nói chuyện trực tiếp với Mẹ/)).toBeVisible();
    await page.getByRole("button", { name: "Quay lại" }).click();
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
    await expect(page.getByRole("button", { name: /Đã gọi được/ })).toBeVisible();
  });

  for (const [label, decision] of [
    [/Đã gọi được/, "safe"],
    [/đang bị lừa/, "emergency_pause"],
    [/HỏiCon báo nhầm/, "false_alarm"],
  ] as const) {
    test(`xác nhận '${decision}' gửi đúng một lệnh rồi tải lại sự cố`, async ({ page }) => {
      let decided = false;
      const calls = await mockApi(page, {
        detail: () => ({ status: 200, json: decided ? detail({ state: "resolved_safe", outcome: "safe" }) : detail() }),
        decision: () => {
          decided = true;
          return { status: 200, json: { success: true, incident_id: INCIDENT_ID, state: "resolved_safe", outcome: "safe" } };
        },
      });
      await page.goto(`/incidents/${INCIDENT_ID}`);
      await page.getByRole("button", { name: label }).click();
      await page.getByRole("button", { name: "Đúng, gửi xác nhận" }).click();
      await expect(page.getByText("✓ Đã ghi nhận")).toBeVisible();
      const posts = calls.filter((c) => c.method === "POST");
      expect(posts).toHaveLength(1);
      expect(posts[0].path).toBe(`/v1/incidents/${INCIDENT_ID}/decision`);
      expect(posts[0].body).toEqual({ decision });
      await expect(page.getByText("Đã xong: an toàn").first()).toBeVisible();
      await expect(page.getByRole("button", { name: /Đã gọi được/ })).toHaveCount(0); // đã quyết: hết nút
    });
  }

  test("diễn tập: câu xác nhận và 'đã ghi nhận' nói rõ chỉ là bài tập, không như sự cố thật", async ({ page }) => {
    await mockApi(page, {
      detail: () => ({ status: 200, json: detail({ is_drill: true, drill_id: "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6eb0" }) }),
    });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await page.getByRole("button", { name: /đang bị lừa/ }).click();
    await expect(page.getByText(/^\[DIỄN TẬP\] Anh\/chị nghi Mẹ đang bị lừa/)).toBeVisible();
    await page.getByRole("button", { name: "Đúng, gửi xác nhận" }).click();
    const done = page.getByRole("status").filter({ hasText: "Đã ghi nhận" });
    await expect(done).toContainText("Đây chỉ là bài tập, không có nguy hiểm thật");
    await expect(done).not.toContainText("không chuyển tiền");
  });

  test("không có tên gọi ⇒ dùng 'người thân' (viết hoa khi đứng đầu câu)", async ({ page }) => {
    await mockApi(page, { detail: () => ({ status: 200, json: detail({ elder_alias: "  " }) }) });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByRole("heading", { level: 1, name: "Người thân" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Đã gọi được, người thân an toàn/ })).toBeVisible();
  });

  test("hành động nằm ngay dưới thẻ rủi ro, trong màn hình đầu ở 360 px", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await mockApi(page);
    await page.goto(`/incidents/${INCIDENT_ID}`);
    const unsure = page.getByRole("button", { name: /đang bị lừa/ });
    await expect(unsure).toBeVisible();
    const box = await unsure.boundingBox();
    expect(box!.y + box!.height).toBeLessThanOrEqual(800);
  });

  test("409 ⇒ 'Sự cố đã được xử lý ở nơi khác' rồi tải lại", async ({ page }) => {
    let calls409 = 0;
    await mockApi(page, {
      detail: () => ({ status: 200, json: calls409 ? detail({ state: "resolved_prevented", outcome: "prevented" }) : detail() }),
      decision: () => {
        calls409 += 1;
        return { status: 409, json: { detail: "Sự cố này đã được xử lý trước đó." } };
      },
    });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await page.getByRole("button", { name: /đang bị lừa/ }).click();
    await page.getByRole("button", { name: "Đúng, gửi xác nhận" }).click();
    await expect(page.locator(`main [role="alert"]`)).toContainText("Sự cố đã được xử lý ở nơi khác");
    await expect(page.getByText("Đã xong: đã ngăn chặn").first()).toBeVisible();
    await expect(page.getByRole("button", { name: /đang bị lừa/ })).toHaveCount(0);
  });

  test("lỗi mạng khi gửi ⇒ báo thử lại, vẫn còn nút để bấm lại", async ({ page }) => {
    await mockApi(page, { decision: () => ({ status: 503, json: { detail: "Dịch vụ chưa sẵn sàng" } }) });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await page.getByRole("button", { name: /Đã gọi được/ }).click();
    await page.getByRole("button", { name: "Đúng, gửi xác nhận" }).click();
    await expect(page.locator(`main [role="alert"]`)).toContainText("Chưa gửi được");
    await expect(page.getByRole("button", { name: "Đúng, gửi xác nhận" })).toBeVisible();
  });

  test("sự cố đã xong thì không có nút quyết định", async ({ page }) => {
    await mockApi(page, { detail: () => ({ status: 200, json: detail({ state: "resolved_safe", outcome: "safe" }) }) });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.getByText("Đã xong: an toàn").first()).toBeVisible();
    await expect(page.getByRole("button", { name: /đang bị lừa/ })).toHaveCount(0);
  });

  test("sự cố nhà khác / không tồn tại (404) ⇒ báo không tìm thấy", async ({ page }) => {
    await mockApi(page, { detail: () => ({ status: 404, json: { detail: "Không tìm thấy sự cố" } }) });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await expect(page.locator(`main [role="alert"]`)).toContainText("Không tìm thấy sự cố này");
  });

  test("phiên hết hạn (401) ⇒ về /login", async ({ page }) => {
    await mockApi(page, {
      me: () => ({ status: 401 }),
      detail: () => ({ status: 401, json: { detail: "Chưa xác thực người giám hộ" } }),
    });
    await page.goto(`/incidents/${INCIDENT_ID}`);
    await page.waitForURL(/\/login\?het-han=1$/);
  });
});
