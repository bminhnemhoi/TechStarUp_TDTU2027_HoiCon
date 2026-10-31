"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";
import { nodeStatuses, waitingNode, type GraphTopology } from "@/lib/sim";
import { describeStep, type AgentStep } from "@/lib/steps";

// Sơ đồ + bản chữ của một lượt chạy (spec 033, FR-011). `@xyflow/react` nạp động (ssr: false) nên trang danh sách 027 không
// nặng thêm. Bản chữ (danh sách bước theo thứ tự) là nội dung chính cho trình đọc màn hình (plan D7).
const Canvas = dynamic(() => import("@/components/trace-graph-canvas"), {
  ssr: false,
  loading: () => (
    <p role="status" className="rounded-card bg-surface-muted p-4 text-body">
      Đang vẽ sơ đồ…
    </p>
  ),
});

export function useGraphTopology(): { topology: GraphTopology | null; failed: boolean } {
  const [topology, setTopology] = useState<GraphTopology | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    api<GraphTopology>("/v1/graphs/incident")
      .then((t) => alive && setTopology(t))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, []);
  return { topology, failed };
}

export function TraceView({
  steps,
  finished,
  alias,
  testId = "steps",
}: {
  steps: AgentStep[];
  finished: boolean;
  alias: string;
  testId?: string;
}) {
  const { topology, failed } = useGraphTopology();
  const [selected, setSelected] = useState<string | null>(null);
  const waiting = waitingNode(steps, finished);
  const statuses = topology ? nodeStatuses(topology, steps, waiting, finished) : {};
  const chosen = topology?.nodes.find((n) => n.id === selected) ?? null;
  const chosenSteps = chosen ? steps.filter((s) => chosen.step_nodes.includes(s.node)) : [];

  return (
    <div className="flex flex-col gap-3">
      {topology ? (
        <div aria-hidden="true">
          <Canvas topology={topology} statuses={statuses} selected={selected} onSelect={setSelected} />
        </div>
      ) : (
        <p role="status" className="rounded-card bg-surface-muted p-4 text-body">
          {failed ? "Chưa tải được sơ đồ. Các bước vẫn hiện ở danh sách bên dưới." : "Đang tải sơ đồ…"}
        </p>
      )}
      <p aria-hidden="true" className="text-body">
        Ký hiệu trên sơ đồ: ✓ đã chạy · ◔ đang chờ người · ↩ dùng cách có sẵn · ✕ gặp trục trặc · ○ chưa tới.
      </p>
      <h3 id="steps-title" className="text-title">
        Các bước đã làm
      </h3>
      <p role="status" className="sr-only">
        {steps.length === 0 ? "Chưa có bước nào." : `Đã có ${steps.length} bước. Bước mới nhất: ${describeStep(steps[steps.length - 1], alias).title}`}
      </p>
      {steps.length === 0 && finished && <p className="text-body">Chưa có bước nào được ghi lại.</p>}
      <ol aria-labelledby="steps-title" className="flex flex-col gap-2" data-testid={testId}>
        {steps.map((step) => {
          const text = describeStep(step, alias);
          const node = topology?.nodes.find((n) => n.step_nodes.includes(step.node));
          const isSelected = node !== undefined && node.id === selected;
          const body = (
            <>
              <span className="text-body font-bold">{text.title}</span>
              {text.detail && <span className="text-body">{text.detail}</span>}
              <span className="text-body text-brand-navy">
                {new Date(step.at).toLocaleTimeString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}
              </span>
            </>
          );
          return (
            <li key={step.id} className={`rounded-card border-2 ${isSelected ? "border-brand-navy" : "border-surface-muted"} bg-background`}>
              {node ? (
                <button
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setSelected(node.id)}
                  className="flex min-h-11 w-full flex-col items-start p-3 text-left focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-focus-ring"
                >
                  {body}
                </button>
              ) : (
                <div className="flex w-full flex-col items-start p-3 text-left">{body}</div>
              )}
            </li>
          );
        })}
      </ol>
      <p className="text-body">Sơ đồ vẽ bằng React Flow (giấy phép MIT).</p>
      {chosen && (
        <section aria-label="Chi tiết bước đã chọn" className="rounded-card border-2 border-brand-navy p-4" data-testid="node-detail">
          <h3 className="text-title">{chosen.label_vi}</h3>
          {chosenSteps.length === 0 ? (
            <p className="text-body">Bước này chưa chạy.</p>
          ) : (
            <ul className="mt-2 flex flex-col gap-1">
              {chosenSteps.map((s) => {
                const text = describeStep(s, alias);
                return (
                  <li key={s.id} className="text-body">
                    <span className="font-bold">{text.title}</span>
                    {text.detail ? `: ${text.detail}` : ""}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
