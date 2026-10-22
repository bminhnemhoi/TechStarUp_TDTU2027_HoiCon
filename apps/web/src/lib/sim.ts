import type { components } from "@/lib/api/schema";
import type { AgentStep } from "@/lib/steps";

// Kiểu của `/v1/sim/*` và `/v1/graphs/incident` (spec 033), sinh từ OpenAPI; hàm suy trạng thái nút của sơ đồ.
export type SimRun = components["schemas"]["SimRunOut"];
export type SimScenario = components["schemas"]["SimScenarioOut"];
export type GraphTopology = components["schemas"]["GraphTopologyOut"];
export type TopologyNode = components["schemas"]["TopologyNode"];

export type NodeStatus = "idle" | "ran" | "waiting" | "error" | "fallback";

export const NODE_STATUS_VI: Record<NodeStatus, string> = {
  idle: "chưa tới",
  ran: "đã chạy",
  waiting: "đang chờ người",
  error: "gặp trục trặc",
  fallback: "dùng cách có sẵn",
};

// Biểu tượng riêng cho từng trạng thái (không chỉ dựa vào màu) — CLAUDE.md luật 15.
export const NODE_STATUS_ICON: Record<NodeStatus, string> = { idle: "○", ran: "✓", waiting: "◔", error: "✕", fallback: "↩" };

/** Nút nào của đồ thị đang chờ người (suy từ bước cuối; lượt đã xong ⇒ không nút nào chờ). */
export function waitingNode(steps: AgentStep[], finished: boolean): string | null {
  const last = steps.at(-1);
  if (finished || !last) return null;
  if (last.node === "risk_scorer" && typeof last.output?.question === "string" && last.output.question) return "ask_elder";
  if (last.node === "intervention" || last.node === "await_guardian") return "await_guardian";
  return null;
}

export function nodeStatuses(
  topology: GraphTopology,
  steps: AgentStep[],
  waiting: string | null,
  finished = false,
): Record<string, NodeStatus> {
  const out: Record<string, NodeStatus> = {};
  for (const node of topology.nodes) {
    const own = steps.filter((s) => node.step_nodes.includes(s.node));
    let status: NodeStatus = "idle";
    if (own.length > 0) status = "ran";
    if (own.some((s) => s.fallback_used)) status = "fallback";
    if (own.some((s) => s.error) && !own.some((s) => s.fallback_used)) status = "error"; // có cách dự phòng thì không báo lỗi đỏ
    if (waiting === node.id) status = "waiting";
    out[node.id] = status;
  }
  out.__start__ = steps.length > 0 ? "ran" : "idle";
  out.__end__ = finished ? "ran" : "idle";
  return out;
}

/** Hàng của từng nút (chiều dọc): khoảng cách ngắn nhất từ `__start__` theo cạnh xuôi (cạnh quay lại không làm lệch bố cục). */
export const ROW_HEIGHT = 150;

export function maxDepth(topology: GraphTopology): number {
  return Math.max(...Object.values(layout(topology)).map((p) => p.y / ROW_HEIGHT));
}

export function layout(topology: GraphTopology): Record<string, { x: number; y: number }> {
  const depth: Record<string, number> = { __start__: 0 };
  const queue = ["__start__"];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const edge of topology.edges) {
      if (edge.source === current && edge.target !== current && !(edge.target in depth)) {
        depth[edge.target] = depth[current] + 1;
        queue.push(edge.target);
      }
    }
  }
  const rows: Record<number, number> = {};
  const positions: Record<string, { x: number; y: number }> = {};
  for (const node of topology.nodes) {
    const d = depth[node.id] ?? 0;
    const row = rows[d] ?? 0;
    rows[d] = row + 1;
    positions[node.id] = { x: row * 250, y: d * ROW_HEIGHT }; // dọc: vừa cột hẹp của /sim, đọc từ trên xuống
  }
  return positions;
}
