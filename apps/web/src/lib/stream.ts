"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import { NODE_ORDER, type AgentStep } from "@/lib/steps";

// Trace trực tiếp của một lượt chạy (spec 027, FR-008): nạp lịch sử `/v1/runs/{id}/steps`, rồi mở `EventSource` cùng
// nguồn tới `/v1/runs/{id}/stream` (cookie phiên tự gửi, tự nối lại theo `retry`, tự gửi `Last-Event-ID`). Phép đo T004
// cho thấy rewrite của Next không đệm/nén luồng nên không cần route handler dự phòng.
// Bỏ trùng theo `id` (luồng mới mở phát lại từ đầu); dừng khi nhận `done`; đóng khi rời trang hoặc tab ẩn > 5 phút.

export type StreamStatus = "loading" | "live" | "reconnecting" | "done" | "failed" | "error" | "unauthorized";

interface State {
  steps: AgentStep[];
  status: StreamStatus;
  attempt: number; // tăng để mở lại luồng (sau lỗi / sau khi tab ẩn lâu)
}

type Action =
  | { type: "history"; steps: AgentStep[] }
  | { type: "step"; step: AgentStep }
  | { type: "status"; status: StreamStatus }
  | { type: "retry" };

const rank = (node: string) => {
  const index = NODE_ORDER.indexOf(node);
  return index === -1 ? NODE_ORDER.length : index;
};
// Theo thời điểm; cùng thời điểm thì theo trình tự node của đồ thị rồi mới theo id (UUIDv7 không đảm bảo thứ tự trong cùng ms).
const compare = (a: AgentStep, b: AgentStep) =>
  a.at < b.at ? -1 : a.at > b.at ? 1 : rank(a.node) - rank(b.node) || (a.id < b.id ? -1 : 1);

function merge(steps: AgentStep[], incoming: AgentStep[]): AgentStep[] {
  const seen = new Set(steps.map((s) => s.id));
  const fresh = incoming.filter((s) => !seen.has(s.id) && seen.add(s.id));
  return fresh.length === 0 ? steps : [...steps, ...fresh].sort(compare);
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "history":
      return { ...state, steps: merge(state.steps, action.steps) };
    case "step":
      return { ...state, steps: merge(state.steps, [action.step]) };
    case "status":
      // `done`/`failed` là trạng thái cuối: không để sự kiện đến muộn ghi đè.
      return state.status === "done" || state.status === "failed" ? state : { ...state, status: action.status };
    case "retry":
      return { ...state, status: "loading", attempt: state.attempt + 1 };
  }
}

const HIDDEN_LIMIT_MS = 5 * 60 * 1000;

function parse<T>(data: string): T | null {
  try {
    return JSON.parse(data) as T;
  } catch {
    return null;
  }
}

export function useRunStream(runId: string | null) {
  const [state, dispatch] = useReducer(reducer, { steps: [], status: "loading", attempt: 0 });
  const hiddenSince = useRef<number | null>(null);

  useEffect(() => {
    if (!runId) return;
    let closed = false;
    let source: EventSource | null = null;
    const base = `/v1/runs/${encodeURIComponent(runId)}`;

    const close = () => {
      closed = true;
      source?.close();
      source = null;
    };

    const open = () => {
      source = new EventSource(`${base}/stream`);
      source.onopen = () => dispatch({ type: "status", status: "live" });
      source.addEventListener("step", (event) => {
        const step = parse<AgentStep>((event as MessageEvent<string>).data);
        if (step) dispatch({ type: "step", step });
      });
      source.addEventListener("done", (event) => {
        const done = parse<{ status: "done" | "failed" }>((event as MessageEvent<string>).data);
        dispatch({ type: "status", status: done?.status === "failed" ? "failed" : "done" });
        close(); // dừng hẳn: không để EventSource tự nối lại sau khi máy chủ đóng
      });
      // Tên sự kiện `error` dùng chung cho khung `event: error` của máy chủ (có `data`) và lỗi kết nối của trình duyệt.
      source.addEventListener("error", (event) => {
        const data = event instanceof MessageEvent ? parse<{ retryable?: boolean }>(event.data) : null;
        if (data && data.retryable === false) {
          dispatch({ type: "status", status: "error" });
          close();
        } else if (source?.readyState === EventSource.CLOSED) {
          dispatch({ type: "status", status: "error" }); // máy chủ từ chối (401/404/429/503): EventSource không tự nối lại
          close();
        } else {
          dispatch({ type: "status", status: "reconnecting" });
        }
      });
    };

    void (async () => {
      try {
        const res = await fetch(`${base}/steps`, { cache: "no-store", credentials: "same-origin" });
        if (closed) return;
        if (res.status === 401) return dispatch({ type: "status", status: "unauthorized" });
        if (!res.ok) return dispatch({ type: "status", status: "error" });
        const history = (await res.json()) as { steps: AgentStep[]; status: string };
        if (closed) return;
        dispatch({ type: "history", steps: history.steps });
        if (history.status === "done" || history.status === "failed") {
          return dispatch({ type: "status", status: history.status });
        }
        open();
      } catch {
        if (!closed) dispatch({ type: "status", status: "error" });
      }
    })();

    const onVisibility = () => {
      if (document.hidden) {
        hiddenSince.current = Date.now();
        return;
      }
      const away = hiddenSince.current === null ? 0 : Date.now() - hiddenSince.current;
      hiddenSince.current = null;
      if (away > HIDDEN_LIMIT_MS && !closed) dispatch({ type: "retry" }); // tab ẩn quá lâu ⇒ dựng lại luồng
    };
    const timer = window.setInterval(() => {
      // Tab ẩn quá 5 phút ⇒ nhả luồng cho máy chủ (mỗi người tối đa 3 luồng).
      if (document.hidden && hiddenSince.current !== null && Date.now() - hiddenSince.current > HIDDEN_LIMIT_MS) {
        source?.close();
        source = null;
      }
    }, 30_000);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
      close();
    };
  }, [runId, state.attempt]);

  const retry = useCallback(() => dispatch({ type: "retry" }), []);
  return { steps: state.steps, status: state.status, retry };
}
