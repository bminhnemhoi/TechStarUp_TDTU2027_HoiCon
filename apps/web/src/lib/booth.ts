import type { Decision } from "@/lib/client";
import type { SimRun } from "@/lib/sim";
import type { AgentStep } from "@/lib/steps";

// Chế độ gian trưng bày (spec 050): danh sách phát, kiểu bản ghi và hằng số nhịp. Mọi kịch bản là hư cấu (`/v1/sim/*`).

export type Answer = "yes" | "no" | "unsure";
export type BoothMode = "live" | "recording";

export interface PlaylistItem {
  scenarioId: string;
  title: string;
  /** Bác trả lời mọi câu hỏi E8 của kịch bản này bằng đáp án này. */
  answer: Answer;
  /** Quyết định của con sau khi nhận tin. */
  decision: Decision;
}

// Giả danh công an · thẻ ngân hàng bị khóa · cuộc gọi hợp lệ (để khách thấy HỏiCon không báo nhầm).
export const PLAYLIST: PlaylistItem[] = [
  { scenarioId: "fake_police_safe_account_002", title: "Giả danh công an", answer: "yes", decision: "emergency_pause" },
  { scenarioId: "fake_bank_card_locked_002", title: "Thẻ ngân hàng bị khóa", answer: "yes", decision: "emergency_pause" },
  { scenarioId: "benign_family_son_rent_002", title: "Con gửi tiền nhà (cuộc gọi hợp lệ)", answer: "no", decision: "safe" },
];

export const isMode = (value: unknown): value is BoothMode | "auto" => value === "live" || value === "recording" || value === "auto";

export const ALERT_LIMIT_MS = 5000; // Gate G4: cảnh báo < 5 giây
export const CALL_TIMEOUT_MS = 3000; // quá hạn này coi như một lần gọi API hỏng
export const FAILS_TO_OFFLINE = 2; // 2 lần hỏng liên tiếp ⇒ chuyển sang bản ghi
export const RUN_CAP_MS = 90_000;
export const POLL_MS = 1000;
export const CHANNEL = "hoicon-booth";
export const REPLAY_BASE = "/booth/replay";

export interface Frame {
  t_ms: number;
  run: SimRun;
}

export interface RecordedStep {
  t_ms: number;
  step: AgentStep;
}

/** Bản ghi một lượt chạy trực tiếp (`llm: "replay"` của đồ thị thật): các khung `sim_run` + các bước theo thời gian. */
export interface Recording {
  scenario_id: string;
  recorded_at: string;
  duration_ms: number;
  frames: Frame[];
  steps: RecordedStep[];
}

const PHONE = /(?:\+?84|0)[\s.-]?[35789](?:[\s.-]?\d){8}/;

/** Kiểm bản ghi: đúng dạng, khung hợp `sim_run.v1` (các trường đóng), tin mở đầu bằng câu công khai AI, không có số điện thoại thô. */
export function recordingProblems(value: unknown): string[] {
  const out: string[] = [];
  const rec = value as Partial<Recording> | null;
  if (!rec || typeof rec !== "object") return ["không phải đối tượng"];
  if (typeof rec.scenario_id !== "string") out.push("thiếu scenario_id");
  if (!Array.isArray(rec.frames) || rec.frames.length === 0) return [...out, "không có khung nào"];
  const keys = ["scenario_id", "is_demo", "llm_mode", "incident_id", "run_id", "state", "level", "pending_question", "guardian_messages", "note"];
  for (const [i, frame] of rec.frames.entries()) {
    const run = frame.run as unknown as Record<string, unknown>;
    if (typeof frame.t_ms !== "number") out.push(`khung ${i}: thiếu t_ms`);
    if (!run || run.is_demo !== true) out.push(`khung ${i}: is_demo phải là true`);
    const missing = keys.filter((k) => !(k in (run ?? {})));
    if (missing.length) out.push(`khung ${i}: thiếu ${missing.join(",")}`);
    for (const m of frame.run?.guardian_messages ?? []) {
      if (!m.text.startsWith("Đây là trợ lý AI HỏiCon")) out.push(`khung ${i}: tin không mở đầu bằng câu công khai AI`);
    }
  }
  // Chỉ quét chữ người xem đọc được (id/thời điểm có thể trùng mẫu số điện thoại).
  const visible = rec.frames.flatMap((f) => [...f.run.guardian_messages.map((m) => m.text), f.run.pending_question?.text ?? "", f.run.note ?? ""]);
  const stepText = (rec.steps ?? []).map((s) => JSON.stringify({ o: s.step?.output ?? null, e: s.step?.error ?? null }));
  if ([...visible, ...stepText].some((text) => PHONE.test(text))) out.push("có chuỗi giống số điện thoại thô");
  return out;
}

/** Khung hiện tại của bản ghi tại thời điểm `t` (khung cuối có `t_ms` ≤ t). */
export function frameAt(rec: Recording, t: number): Frame {
  let current = rec.frames[0];
  for (const frame of rec.frames) if (frame.t_ms <= t) current = frame;
  return current;
}

export function stepsAt(rec: Recording, t: number): AgentStep[] {
  return rec.steps.filter((s) => s.t_ms <= t).map((s) => s.step);
}

// --- Tin nhắn giữa /booth và /demo/console (cùng trình duyệt, BroadcastChannel; không lưu trữ gì) -----------------------

export interface BoothResult {
  scenarioId: string;
  mode: BoothMode;
  tAlertMs: number | null;
  ok: boolean;
  at: number;
}

export type ChannelMessage =
  | { type: "cmd"; cmd: "start"; scenarioId: string }
  | { type: "cmd"; cmd: "playlist" | "stop" | "reset" }
  | { type: "cmd"; cmd: "mode"; mode: BoothMode | "auto" }
  | { type: "status"; mode: BoothMode; offline: boolean; busy: boolean }
  | { type: "result"; result: BoothResult }
  | { type: "recording"; recording: Recording };
