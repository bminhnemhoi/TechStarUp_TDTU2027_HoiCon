import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { FAKE_TOKEN, LIST_ITEMS, RUN_ID, SimMock, mockApi } from "./fixtures";

// Sơ đồ xyflow nạp động: lần đầu có thể chậm khi nhiều worker tranh CPU (vượt hạn 7,5 s mặc định). Cùng điều kiện, chỉ chờ lâu hơn.
const XYFLOW_LOAD_MS = 20_000;

// SC-005 (spec 027): 4 trang × 360/768/1280 px (+ cỡ chữ 200%): không tràn ngang, chữ ≥ 16 px, vùng chạm ≥ 44 px,
// nút chính ≥ 64 px, axe-core 0 vi phạm serious/critical (kể cả tương phản nâng cao 7:1 cho chữ thân).
const EVIDENCE_DIR = path.join(os.homedir(), "hoicon-evidence", "027-guardian-web");
const INCIDENT_ID = "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e80";
const drill = { ...LIST_ITEMS[0], id: "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ec0", is_drill: true, drill_id: "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6ec1", level: "medium" };

interface Screen {
  name: string;
  open: (page: Page) => Promise<void>;
}

const SCREENS: Screen[] = [
  {
    name: "login",
    open: async (page) => {
      await mockApi(page);
      await page.goto("/login");
      await expect(page.getByRole("heading", { name: "Đăng nhập HỏiCon" })).toBeVisible();
    },
  },
  {
    name: "loi-lien-ket",
    open: async (page) => {
      await mockApi(page, { exchange: () => ({ status: 410, json: { detail: "x" } }) });
      await page.goto(`/login/${FAKE_TOKEN}`);
      await expect(page.locator('main [role="alert"]')).toBeVisible();
    },
  },
  {
    name: "danh-sach",
    open: async (page) => {
      await mockApi(page, {
        list: (status) => ({
          status: 200,
          json: { incidents: status === "open" ? [LIST_ITEMS[0], drill] : [LIST_ITEMS[1]], next_cursor: status === "open" ? "TRANG2" : null },
        }),
      });
      await page.goto("/incidents");
      await expect(page.getByRole("region", { name: "Đã xong" }).getByRole("link")).toHaveCount(1);
      await expect(page.getByRole("region", { name: "Đang cần chú ý" }).getByRole("link")).toHaveCount(2);
    },
  },
  {
    name: "chi-tiet",
    open: async (page) => {
      await mockApi(page);
      await page.goto(`/incidents/${INCIDENT_ID}`);
      await expect(page.getByTestId("stream-status")).toContainText("Trợ lý AI đã làm xong các bước");
    },
  },
  {
    name: "so-do",
    open: async (page) => {
      await mockApi(page);
      await page.goto(`/trace/${RUN_ID}`);
      await expect(page.getByTestId("stream-status")).toContainText("Trợ lý AI đã làm xong các bước");
      await expect(page.locator(".react-flow__node:visible").first()).toBeVisible({ timeout: XYFLOW_LOAD_MS });
    },
  },
  {
    name: "mo-phong",
    open: async (page) => {
      await mockApi(page, { sim: new SimMock() });
      await page.goto("/sim");
      await page.getByRole("button", { name: "Bắt đầu" }).click();
      await expect(page.getByTestId("question")).toBeVisible();
    },
  },
];

const VIEWS = [
  { width: 360, height: 800, zoom: false },
  { width: 768, height: 1024, zoom: false },
  { width: 1280, height: 800, zoom: false },
  { width: 360, height: 800, zoom: true },
  { width: 1280, height: 800, zoom: true },
];

for (const screen of SCREENS) {
  for (const view of VIEWS) {
    const label = `${screen.name} · ${view.width}px${view.zoom ? " · chữ 200%" : ""}`;
    test(label, async ({ page }) => {
      await page.setViewportSize({ width: view.width, height: view.height });
      await screen.open(page);
      if (view.zoom) await page.addStyleTag({ content: "html { font-size: 200% !important; }" });

      // 1) Không tràn ngang.
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, "tràn ngang (px)").toBeLessThanOrEqual(0);

      // 2) Chữ ≥ 16 px (web người giám hộ), 3) vùng chạm ≥ 44 px, nút chính ≥ 64 px.
      const problems = await page.evaluate(() => {
        const out: string[] = [];
        const visible = (el: Element) => {
          const box = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return box.width > 0 && box.height > 0 && style.visibility !== "hidden" && style.display !== "none";
        };
        for (const el of document.body.querySelectorAll("*")) {
          if (!visible(el)) continue;
          const own = Array.from(el.childNodes).some((n) => n.nodeType === Node.TEXT_NODE && (n.textContent ?? "").trim() !== "");
          if (own && parseFloat(getComputedStyle(el).fontSize) < 16) out.push(`chữ nhỏ: <${el.tagName.toLowerCase()}> ${(el.textContent ?? "").trim().slice(0, 30)}`);
        }
        for (const el of document.body.querySelectorAll("a, button")) {
          if (!visible(el)) continue;
          const box = el.getBoundingClientRect();
          const label = (el.textContent ?? "").trim().slice(0, 30);
          if (box.height < 43.5 || box.width < 43.5) out.push(`vùng chạm nhỏ (${Math.round(box.width)}x${Math.round(box.height)}): ${label}`);
          if (el.classList.contains("min-h-16") && box.height < 63.5) out.push(`nút chính thấp hơn 64px (${Math.round(box.height)}): ${label}`);
        }
        return out;
      });
      expect(problems).toEqual([]);

      // 4) axe-core: 0 vi phạm serious/critical, có cả luật tương phản nâng cao (7:1).
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
        .options({ rules: { "color-contrast-enhanced": { enabled: true } } })
        .analyze();
      const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(blocking.map((v) => `${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);

      // 5) Ảnh bằng chứng (luật 16).
      mkdirSync(EVIDENCE_DIR, { recursive: true });
      await page.screenshot({ path: path.join(EVIDENCE_DIR, `${screen.name}-${view.width}${view.zoom ? "-200" : ""}.png`), fullPage: true });
    });
  }
}
