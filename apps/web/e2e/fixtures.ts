import { readFileSync } from "node:fs";
import path from "node:path";
import type { Page, Route } from "@playwright/test";

// Chặn mạng bằng FIXTURE HỢP ĐỒNG trong docs/schemas/fixtures/ (spec 027, plan D5): test tất định, không cần API/DB.
// Số điện thoại, token và tên đều hư cấu.
type Json = Record<string, unknown>;

const FIXTURE_DIR = path.resolve(__dirname, "../../../docs/schemas/fixtures");
const load = <T = Json[]>(name: string): T => JSON.parse(readFileSync(path.join(FIXTURE_DIR, name), "utf-8")) as T;
const strip = (doc: Json): Json => Object.fromEntries(Object.entries(doc).filter(([key]) => !key.startsWith("_")));

export const OPEN_STATES = ["detected", "assessing", "awaiting_guardian", "verifying", "rescore", "case_open"];
export const FAKE_TOKEN = "aBcDeFgHiJkLmNoPqRsTuVwXyZ012345-_aBcDeFg"; // gitleaks:allow — token GIẢ 41 ký tự
export const SESSION: Json = strip(load("guardian_session.v1.valid.json").find((d) => d._as === "response")!);

const LIST_DOC = load("incident_list.v1.valid.json")[0];
export const LIST_ITEMS = (LIST_DOC.incidents as Json[]).map((i) => ({ ...i }));
const DETAIL_DOC = strip(load("incident.v1.valid.json").find((d) => d._as === "detail")!);
const RUNS = load("run_steps.v1.valid.json");
export const RUN_ID = "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e90";
export const STEPS = (strip(RUNS[0]).steps as Json[]).map((s) => ({ ...s }));

export function detail(overrides: Json = {}): Json {
  return { ...DETAIL_DOC, elder_alias: "Mẹ", run_id: RUN_ID, state: "awaiting_guardian", outcome: null, closed_at: null, ...overrides };
}

export function step(id: string, node: string, output: Json | null, at: string): Json {
  return {
    id,
    run_id: RUN_ID,
    node,
    model_profile: null,
    model: null,
    prompt_version: null,
    latency_ms: 1,
    tokens_in: 0,
    tokens_out: 0,
    cost_usd: "0.000000",
    fallback_used: false,
    error: null,
    output,
    at,
  };
}

export interface SseFrame {
  event: string;
  id?: string;
  data: Json;
}

export function sse(frames: SseFrame[]): string {
  const body = frames
    .map((f) => `${f.id ? `id: ${f.id}\n` : ""}event: ${f.event}\ndata: ${JSON.stringify(f.data)}\n\n`)
    .join("");
  return `retry: 300\n\n${body}`;
}

export const stepFrame = (s: Json): SseFrame => ({ event: "step", id: s.id as string, data: s });
export const doneFrame = (total: number): SseFrame => ({
  event: "done",
  data: { run_id: RUN_ID, status: "done", total_steps: total, cost_usd: "0.000000", is_drill: false, is_demo: true },
});

export interface Call {
  method: string;
  path: string;
  body: unknown;
}

export interface MockOptions {
  me?: () => { status: number; json?: Json };
  exchange?: (body: Json) => { status: number; json?: Json; abort?: boolean };
  list?: (status: string, cursor: string | null) => { status: number; json?: Json };
  detail?: () => { status: number; json?: Json };
  steps?: () => { status: number; json?: Json };
  stream?: (attempt: number) => { body: string; delayMs?: number; status?: number };
  decision?: (body: Json) => { status: number; json?: Json };
}

/** Cài bộ chặn `/v1/**`; trả danh sách lời gọi để test kiểm tra (thân lời gọi, số lần, thứ tự). */
export async function mockApi(page: Page, options: MockOptions = {}): Promise<Call[]> {
  const calls: Call[] = [];
  let streamAttempt = 0;
  const reply = (route: Route, status: number, json?: Json) =>
    route.fulfill({ status, contentType: "application/json", body: json === undefined ? "" : JSON.stringify(json) });

  await page.route("**/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const body = request.postData() ? (JSON.parse(request.postData()!) as unknown) : null;
    calls.push({ method, path: url.pathname + url.search, body });
    const p = url.pathname;

    if (p === "/v1/guardian/me") {
      const r = options.me?.() ?? { status: 200, json: SESSION };
      return reply(route, r.status, r.json);
    }
    if (p === "/v1/guardian/session" && method === "POST") {
      const r = options.exchange?.(body as Json) ?? { status: 200, json: SESSION };
      if (r.abort) return route.abort("connectionfailed");
      return reply(route, r.status, r.json);
    }
    if (p === "/v1/guardian/session" && method === "DELETE") return route.fulfill({ status: 204 });
    if (p === "/v1/guardian/incidents") {
      const status = url.searchParams.get("status") ?? "open";
      const cursor = url.searchParams.get("cursor");
      const r =
        options.list?.(status, cursor) ?? {
          status: 200,
          json: {
            incidents: LIST_ITEMS.filter((i) => OPEN_STATES.includes(i.state as string) === (status === "open")),
            next_cursor: null,
          },
        };
      return reply(route, r.status, r.json);
    }
    if (/^\/v1\/guardian\/incidents\/[^/]+$/.test(p)) {
      const r = options.detail?.() ?? { status: 200, json: detail() };
      return reply(route, r.status, r.json);
    }
    if (/^\/v1\/runs\/[^/]+\/steps$/.test(p)) {
      const r = options.steps?.() ?? {
        status: 200,
        json: { run_id: RUN_ID, status: "running", is_drill: false, is_demo: true, steps: STEPS },
      };
      return reply(route, r.status, r.json);
    }
    if (/^\/v1\/runs\/[^/]+\/stream$/.test(p)) {
      streamAttempt += 1;
      const r = options.stream?.(streamAttempt) ?? { body: sse([doneFrame(STEPS.length)]) };
      if (r.delayMs) await new Promise((resolve) => setTimeout(resolve, r.delayMs));
      return route.fulfill({
        status: r.status ?? 200,
        headers: { "Cache-Control": "no-cache, no-transform" },
        contentType: "text/event-stream; charset=utf-8",
        body: r.body,
      });
    }
    if (/^\/v1\/incidents\/[^/]+\/decision$/.test(p)) {
      const r = options.decision?.(body as Json) ?? { status: 200, json: { success: true } };
      return reply(route, r.status, r.json);
    }
    return reply(route, 404, { detail: "chưa có fixture" });
  });
  return calls;
}
