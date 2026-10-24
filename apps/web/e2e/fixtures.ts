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

// --- Spec 033: `/v1/sim/*` và sơ đồ đồ thị (hợp đồng + sơ đồ sinh từ backend, tệp graph-incident.json) ---------------------
export const TOPOLOGY = JSON.parse(readFileSync(path.join(__dirname, "graph-incident.json"), "utf-8")) as Json;
const SIM_RUNS = load("sim_run.v1.valid.json").map(strip);
export const SIM_INCIDENT = "5b0c1f3e-0000-4000-8000-000000000001";
export const SCAM_ID = "fake_police_safe_account_002";
export const BENIGN_ID = "benign_official_residence_005";
const QUESTION = {
  incident_id: SIM_INCIDENT,
  question_id: "q_caller_authority",
  text: "Đây là trợ lý AI HỏiCon. Người đang gọi có tự xưng là công an, viện kiểm sát, tòa án hoặc cán bộ cơ quan nhà nước không ạ?",
  is_drill: false,
  answers: ["yes", "no", "unsure"],
  expires_at: "2026-12-20T09:05:00Z",
};
const FAST = { at: "2026-12-20T09:00:05Z", template: "fast_alert", text: "Đây là trợ lý AI HỏiCon. Mẹ vừa nghe một số lạ rồi mở ứng dụng ngân hàng. Anh/chị gọi hỏi Mẹ ngay nhé." };
const DETAIL = { at: "2026-12-20T09:00:09Z", template: "detail", text: "Đây là trợ lý AI HỏiCon. Mức nguy cơ: rất cao. Anh/chị gọi ngay cho Mẹ và giữ máy." };
export const SIM_SCENARIO_LIST = [
  { id: SCAM_ID, category: "fake_police", title_vi: "Giả danh công an · ca 2", is_benign: false, injection: false, draft: true, script_vi: "Người gọi xưng công an (hư cấu) báo bác dính vụ án và yêu cầu chuyển tiền vào tài khoản an toàn." },
  { id: BENIGN_ID, category: "benign_official", title_vi: "Cuộc gọi thật: cơ quan · ca 5", is_benign: true, injection: false, draft: false, script_vi: "Bác gọi hỏi thủ tục cư trú ở phường (hư cấu), không mở ứng dụng ngân hàng." },
];

/** Máy trạng thái của một lượt mô phỏng giả (hợp đồng sim_run.v1): bắt đầu → câu hỏi E8 → tin cho con → quyết định. */
export class SimMock {
  stage: "idle" | "asked" | "answered" | "decided" = "idle";
  started = 0;
  view(): Json {
    const base = { scenario_id: SCAM_ID, is_demo: true, llm_mode: "replay", incident_id: SIM_INCIDENT, run_id: RUN_ID, note: null };
    if (this.stage === "asked") return { ...base, state: "assessing", level: "high", pending_question: QUESTION, guardian_messages: [FAST] };
    if (this.stage === "answered") return { ...base, state: "awaiting_guardian", level: "critical", pending_question: null, guardian_messages: [FAST, DETAIL] };
    return { ...base, state: "case_open", level: "critical", pending_question: null, guardian_messages: [FAST, DETAIL] };
  }
}

// --- Spec 031: hồ sơ vụ việc (fixture hợp đồng case_file.v1) -----------------------------------------------------------
const CASE_DOC = strip(load("case_file.v1.valid.json")[0]);
export const CASE_ACTIONS: Record<string, Record<string, string>> = {
  draft: { approve: "approved", discard: "discarded" },
  approved: { mark_sent: "sent", discard: "discarded" },
};

// Hướng dẫn trình báo (case_file.v1.guidance): chưa duyệt ⇒ không có bước, chỉ câu chung; đã duyệt ⇒ có bước (chữ thử, không phải nội dung Minh duyệt).
export const GUIDANCE_UNAPPROVED: Json = { approved: false, steps: [], fallback_vi: "Anh/chị liên hệ công an nơi cư trú và ngân hàng của người thân." };
export const GUIDANCE_APPROVED: Json = {
  approved: true,
  fallback_vi: "Anh/chị liên hệ công an nơi cư trú và ngân hàng của người thân.",
  steps: [
    { id: "contact_bank", text_vi: "Gọi tổng đài ghi sau thẻ của ngân hàng người thân để nhờ kiểm tra giao dịch.", source_ref: null },
    { id: "contact_police", text_vi: "Mang bản hồ sơ này tới công an phường hoặc xã nơi người thân cư trú.", source_ref: "Nguồn thử nghiệm" },
  ],
};

export class CaseMock {
  status = "draft";
  guidance: Json = GUIDANCE_UNAPPROVED;
  view(): Json {
    return { ...CASE_DOC, guidance: this.guidance, status: this.status, approved_at: this.status === "draft" ? null : "2026-12-20T09:03:00Z" };
  }
}

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
  sim?: SimMock;
  simScenarios?: () => { status: number; json?: Json };
  simStart?: (body: Json) => { status: number; json?: Json; headers?: Record<string, string> };
  topology?: () => { status: number; json?: Json };
  caseFile?: CaseMock;
  caseFileGet?: () => { status: number; json?: Json };
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
        json: { run_id: RUN_ID, status: "running", is_drill: false, is_demo: true, is_sim: false, steps: STEPS },
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
      if (r.status === 200 && options.sim) options.sim.stage = "decided";
      return reply(route, r.status, r.json);
    }
    if (/^\/v1\/guardian\/incidents\/[^/]+\/case-file$/.test(p)) {
      if (method === "GET") {
        const r = options.caseFileGet?.() ?? { status: 200, json: (options.caseFile ?? new CaseMock()).view() };
        return reply(route, r.status, r.json);
      }
      const mock = options.caseFile ?? new CaseMock();
      const next = CASE_ACTIONS[mock.status]?.[(body as Json).action as string];
      if (!next) return reply(route, 409, { detail: "x" });
      mock.status = next;
      return reply(route, 200, mock.view());
    }
    if (p === "/v1/graphs/incident") {
      const r = options.topology?.() ?? { status: 200, json: TOPOLOGY };
      return reply(route, r.status, r.json);
    }
    if (p === "/v1/sim/scenarios") {
      const r = options.simScenarios?.() ?? { status: 200, json: { scenarios: SIM_SCENARIO_LIST } };
      return reply(route, r.status, r.json);
    }
    if (p === "/v1/sim/runs" && method === "POST") {
      const custom = options.simStart?.(body as Json);
      if (custom) return route.fulfill({ status: custom.status, contentType: "application/json", headers: custom.headers, body: JSON.stringify(custom.json ?? {}) });
      const sim = options.sim ?? new SimMock();
      sim.started += 1;
      if ((body as Json).scenario_id === BENIGN_ID) {
        return reply(route, 200, { ...SIM_RUNS[2], scenario_id: BENIGN_ID });
      }
      sim.stage = "asked";
      return reply(route, 200, sim.view());
    }
    if (/^\/v1\/sim\/runs\/[^/]+\/answer$/.test(p) && options.sim) {
      options.sim.stage = "answered";
      return reply(route, 200, options.sim.view());
    }
    if (/^\/v1\/sim\/runs\/[^/]+$/.test(p) && options.sim) return reply(route, 200, options.sim.view());
    return reply(route, 404, { detail: "chưa có fixture" });
  });
  return calls;
}
