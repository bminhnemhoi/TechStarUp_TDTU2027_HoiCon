import { defineConfig, devices } from "@playwright/test";

// E2E của web người giám hộ (spec 027, FR-009). Chạy trên bản ĐÃ BUILD (`pnpm build` trước): `next start` cổng 3100.
// Mặc định mạng được chặn bằng fixture hợp đồng (e2e/fixtures.ts) nên không cần API hay DB; `live.spec.ts` chỉ chạy khi
// HOICON_E2E_LIVE=1 (xem README).
const PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 7_500 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    locale: "vi-VN",
    timezoneId: "Asia/Ho_Chi_Minh",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm start",
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
