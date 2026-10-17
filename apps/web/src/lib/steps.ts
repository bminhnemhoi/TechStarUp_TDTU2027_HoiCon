// Bảng dịch bước của tác tử sang tiếng Việt (spec 027, plan §5): cố định, không LLM, không bao giờ in JSON thô.
// Khóa lạ ⇒ "Bước khác của trợ lý AI". Chỉ dùng các khóa enum/số trong `output` đã che (docs/schemas/agent_step.v1.json).

export interface AgentStep {
  id: string;
  run_id: string;
  node: string;
  error: string | null;
  fallback_used: boolean;
  output: Record<string, unknown> | null;
  at: string;
}

export type Level = "none" | "low" | "medium" | "high" | "critical";

export const LEVEL_VI: Record<Level, string> = {
  none: "Chưa thấy nguy cơ",
  low: "Thấp",
  medium: "Trung bình",
  high: "Cao",
  critical: "Rất cao",
};

// Mỗi mức rủi ro có biểu tượng riêng (không chỉ dựa vào màu) — CLAUDE.md luật 15.
export const LEVEL_ICON: Record<Level, string> = {
  none: "○",
  low: "●",
  medium: "◆",
  high: "▲",
  critical: "⬣",
};

export const STATE_VI: Record<string, string> = {
  detected: "Vừa phát hiện",
  assessing: "Đang đánh giá",
  awaiting_guardian: "Chờ người nhà quyết định",
  verifying: "Đang xác minh",
  rescore: "Đang đánh giá lại",
  case_open: "Đang theo dõi (nghi lừa đảo)",
  resolved_safe: "Đã xong: an toàn",
  resolved_prevented: "Đã xong: đã ngăn chặn",
  resolved_false_alarm: "Đã xong: HỏiCon báo nhầm",
  resolved_no_response: "Đã xong: chưa ai phản hồi",
  closed: "Đã đóng",
};

export const OPEN_STATES = ["detected", "assessing", "awaiting_guardian", "verifying", "rescore", "case_open"];
// Trạng thái còn chờ người giám hộ quyết định (khớp GUARDIAN_DECIDABLE ở backend).
export const DECIDABLE_STATES = ["detected", "assessing", "awaiting_guardian"];

/** Cách gọi người được bảo vệ; trống/khoảng trắng ⇒ "người thân" (viết hoa khi đứng đầu câu/tiêu đề). */
export function aliasName(alias: string | null | undefined, capital = false): string {
  const name = alias?.trim() || "người thân";
  return capital ? name.charAt(0).toUpperCase() + name.slice(1) : name;
}

// Thứ tự các node của đồ thị: dùng để xếp các bước cùng một thời điểm đúng trình tự thật.
export const NODE_ORDER = ["ingest", "fast_alert", "risk_scorer", "ask_elder", "verify", "verification", "intervention", "await_guardian", "resolve"];

export function levelOf(value: unknown): Level | null {
  return typeof value === "string" && value in LEVEL_VI ? (value as Level) : null;
}

const ANSWER_VI: Record<string, string> = { yes: "Có", no: "Không", unsure: "Chưa chắc" };
const OUTCOME_VI: Record<string, string> = {
  safe: "người nhà xác nhận an toàn",
  scam: "người nhà nghi lừa đảo, hồ sơ được giữ mở",
  prevented: "đã ngăn chặn được",
  false_alarm: "HỏiCon báo nhầm",
  no_response: "chưa ai phản hồi",
  decided: "đã có người nhà quyết định",
};
const RESUME_VI: Record<string, string> = {
  safe: "Người nhà đã quyết định",
  scam: "Người nhà đã quyết định",
  t1: "Đã nhắc lại người nhà",
  t2: "Đã báo người nhà thứ hai",
  t3: "Đã hết thời gian chờ",
  evidence: "Đã báo người nhà kết quả tra cứu đáng ngờ",
  decided: "Đã có người nhà quyết định",
};

export interface StepText {
  /** Câu chính, một dòng. */
  title: string;
  /** Chi tiết ngắn (không bắt buộc). */
  detail?: string;
}

function count(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;
}

export function describeStep(step: Pick<AgentStep, "node" | "output" | "error" | "fallback_used">, alias: string): StepText {
  const out = step.output ?? {};
  const name = aliasName(alias);
  const level = levelOf(out.level);
  let text: StepText;
  switch (step.node) {
    case "ingest": {
      const parts: string[] = [];
      if (level) parts.push(`mức ban đầu: ${LEVEL_VI[level]}`);
      if (out.threat === "flagged") parts.push("số gọi đến có trong danh sách cảnh báo");
      text = { title: `Nhận tín hiệu từ điện thoại của ${name}`, detail: parts.join("; ") || undefined };
      break;
    }
    case "fast_alert":
      text = { title: "Đã gửi cảnh báo nhanh cho người nhà" };
      break;
    case "risk_scorer": {
      const parts: string[] = [];
      if (level) parts.push(`mức: ${LEVEL_VI[level]}`);
      if (typeof out.question === "string" && out.question) parts.push(`sẽ hỏi ${name} một câu ngắn`);
      text = { title: "Đánh giá mức rủi ro", detail: parts.join("; ") || undefined };
      break;
    }
    case "ask_elder": {
      const answer = typeof out.answer === "string" ? out.answer : "timeout";
      text =
        answer === "timeout"
          ? { title: `${name} chưa trả lời` }
          : { title: `${name} đã trả lời câu hỏi`, detail: ANSWER_VI[answer] ? `trả lời: ${ANSWER_VI[answer]}` : undefined };
      break;
    }
    case "verify":
    case "verification": {
      const dangerous = count(out.dangerous);
      const warning = count(out.warning);
      const parts: string[] = [];
      if (dangerous) parts.push(`${dangerous} mục rất đáng ngờ, anh/chị nên gọi hỏi ${name}`);
      if (warning) parts.push(`${warning} mục cần chú ý`);
      text = { title: "Đã tra số điện thoại và đường dẫn trong danh sách cảnh báo của HỏiCon", detail: parts.join("; ") || undefined };
      break;
    }
    case "intervention":
      text = {
        title: "Gửi tóm tắt cho người nhà",
        detail: typeof out.skipped === "string" ? "bỏ qua vì đã có người quyết định" : undefined,
      };
      break;
    case "await_guardian": {
      const resumed = typeof out.resumed_with === "string" ? out.resumed_with : "";
      text = { title: RESUME_VI[resumed] ?? "Đang chờ người nhà quyết định" };
      break;
    }
    case "resolve": {
      const outcome = typeof out.outcome === "string" ? out.outcome : "";
      text = { title: `Kết thúc: ${OUTCOME_VI[outcome] ?? "đã đóng sự cố"}` };
      break;
    }
    default:
      text = { title: "Bước khác của trợ lý AI" };
  }
  if (step.error) {
    text = { ...text, detail: [text.detail, "Bước phân tích tự động bị gián đoạn nên HỏiCon dùng cách xử lý có sẵn; cảnh báo vẫn được gửi"].filter(Boolean).join(". ") };
  } else if (step.fallback_used) {
    text = { ...text, detail: [text.detail, "HỏiCon dùng cách xử lý có sẵn"].filter(Boolean).join(". ") };
  }
  return text;
}

/** Thời điểm tương đối bằng tiếng Việt ("2 phút trước"; luôn đặt sau chữ "mở" để "vừa xong" không bị hiểu là "đã xử lý xong"). */
export function relativeTime(iso: string, now: number = Date.now()): string {
  const diff = Math.round((now - new Date(iso).getTime()) / 1000);
  if (!Number.isFinite(diff)) return "";
  if (diff < 45) return "vừa xong";
  if (diff < 3600) return `${Math.max(1, Math.round(diff / 60))} phút trước`;
  if (diff < 86400) return `${Math.round(diff / 3600)} giờ trước`;
  if (diff < 7 * 86400) return `${Math.round(diff / 86400)} ngày trước`;
  return new Date(iso).toLocaleDateString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
}
