"use client";

import { Background, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";
import { NODE_STATUS_ICON, NODE_STATUS_VI, ROW_HEIGHT, layout, maxDepth, type GraphTopology, type NodeStatus } from "@/lib/sim";

// Sơ đồ đồ thị tác tử (spec 033, FR-011), bố cục tĩnh từ `graph_topology`. Canvas chỉ để NHÌN (aria-hidden): người dùng
// trình đọc màn hình dùng bản chữ bên dưới. Trạng thái nút = màu token + biểu tượng + chữ (luật 15). Hiệu ứng chờ chỉ khi
// người dùng không tắt chuyển động (motion-safe).
const STATUS_CLASS: Record<NodeStatus, string> = {
  idle: "border-dashed border-brand-navy bg-surface-muted text-foreground",
  ran: "border-risk-low-accent bg-risk-low-bg text-risk-low-fg",
  waiting: "border-risk-medium-accent bg-risk-medium-bg text-risk-medium-fg motion-safe:animate-pulse",
  error: "border-risk-critical-accent bg-risk-critical-bg text-risk-critical-fg",
  fallback: "border-risk-high-accent bg-risk-high-bg text-risk-high-fg",
};

interface AgentNodeData extends Record<string, unknown> {
  label: string;
  status: NodeStatus;
  selected: boolean;
}

function AgentNode({ data }: NodeProps<Node<AgentNodeData>>) {
  return (
    <div
      className={`w-56 rounded-card border-2 p-3 text-body ${STATUS_CLASS[data.status]} ${data.selected ? "outline-4 outline-focus-ring" : ""}`}
    >
      <Handle type="target" position={Position.Top} isConnectable={false} />
      <p className="font-bold">
        <span aria-hidden="true">{NODE_STATUS_ICON[data.status]} </span>
        {data.label}
      </p>
      <p>{NODE_STATUS_VI[data.status]}</p>
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}

const NODE_TYPES = { agent: AgentNode };

export default function TraceGraphCanvas({
  topology,
  statuses,
  selected,
  onSelect,
}: {
  topology: GraphTopology;
  statuses: Record<string, NodeStatus>;
  selected: string | null;
  onSelect: (nodeId: string) => void;
}) {
  const positions = useMemo(() => layout(topology), [topology]);
  const nodes: Node<AgentNodeData>[] = topology.nodes.map((n) => ({
    id: n.id,
    type: "agent",
    position: positions[n.id],
    data: { label: n.label_vi, status: statuses[n.id] ?? "idle", selected: selected === n.id },
    draggable: false,
    connectable: false,
    focusable: false, // canvas aria-hidden: không để phần tử nhận Tab nằm trong vùng bị ẩn với trình đọc màn hình
  }));
  const edges: Edge[] = topology.edges.map((e) => ({
    id: `${e.source}->${e.target}`,
    source: e.source,
    target: e.target,
    style: { stroke: "#1f3a5f", strokeWidth: 2, strokeDasharray: e.conditional ? "6 4" : undefined },
    focusable: false,
  }));
  return (
    <div className="w-full overflow-hidden rounded-card border-2 border-surface-muted" data-testid="trace-canvas" style={{ height: (maxDepth(topology) + 1) * ROW_HEIGHT + 40 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.05, minZoom: 0.9, maxZoom: 1 }}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        elementsSelectable
        zoomOnScroll={false}
        preventScrolling={false}
        panOnDrag={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        minZoom={0.9}
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, node) => onSelect(node.id)}
      >
        <Background />
      </ReactFlow>
    </div>
  );
}
