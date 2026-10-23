"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ALERT_LIMIT_MS,
  CALL_TIMEOUT_MS,
  CHANNEL,
  FAILS_TO_OFFLINE,
  PLAYLIST,
  POLL_MS,
  REPLAY_BASE,
  RUN_CAP_MS,
  frameAt,
  isMode,
  recordingProblems,
  stepsAt,
  type Answer,
  type BoothMode,
  type BoothResult,
  type ChannelMessage,
  type Frame,
  type PlaylistItem,
  type RecordedStep,
  type Recording,
} from "@/lib/booth";
import { ApiError, api, type Decision } from "@/lib/client";
import type { SimRun } from "@/lib/sim";
import type { AgentStep } from "@/lib/steps";
import { DECIDABLE_STATES } from "@/lib/steps";

// Bộ chạy của gian (spec 050): chạy danh sách phát qua `/v1/sim/*` (đồ thị thật, `llm: "replay"`), tự chuyển sang bản ghi khi
// mất mạng (D4), đo `t_alert_ms` ở trình duyệt (D5). Không lưu gì vào localStorage/sessionStorage (bất biến 5 của 027).

export interface BoothView {
  title: string | null;
  run: SimRun | null;
  steps: AgentStep[];
  question: string | null;
  answered: Answer | null;
  decided: Decision | null;
}

const EMPTY: BoothView = { title: null, run: null, steps: [], question: null, answered: null, decided: null };

class Cancelled extends Error {}
class OfflineError extends Error {}
class ClosedError extends Error {}

interface Timing {
  poll: number;
  dwell: number;
  gap: number;
  speed: number; // hệ số tốc độ phát lại bản ghi (chỉ test dùng > 1)
}
const NORMAL: Timing = { poll: POLL_MS, dwell: 2500, gap: 6000, speed: 1 };
const FAST: Timing = { poll: 250, dwell: 150, gap: 300, speed: 10 };

export function useBoothRunner(options: { fast?: boolean; autoplay?: boolean; handleUnauthorized?: (e: unknown) => boolean }) {
  const timing = options.fast ? FAST : NORMAL;
  const [view, setView] = useState<BoothView>(EMPTY);
  const [mode, setMode] = useState<BoothMode | "auto">("auto");
  const [playing, setPlaying] = useState<BoothMode | null>(null);
  const [offline, setOffline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [closed, setClosed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<BoothResult[]>([]);

  const epoch = useRef(0);
  const modeRef = useRef(mode);
  const offlineRef = useRef(false);
  const busyRef = useRef(false);
  const cache = useRef(new Map<string, Recording>());
  const channel = useRef<BroadcastChannel | null>(null);
  const loop = useRef(false);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  const setOfflineBoth = (value: boolean) => {
    offlineRef.current = value;
    setOffline(value);
  };

  const wait = useCallback(
    (ms: number, mine: number) =>
      new Promise<void>((resolve, reject) => {
        window.setTimeout(() => (epoch.current === mine ? resolve() : reject(new Cancelled())), ms);
      }),
    [],
  );

  const post = useCallback((message: ChannelMessage) => channel.current?.postMessage(message), []);

  // Nạp sẵn mọi bản ghi lúc mở trang: mất mạng thì vẫn phát được (nếu máy chủ web cũng mất, bản đã nạp vẫn ở bộ nhớ).
  const preload = useCallback(async () => {
    await Promise.all(
      PLAYLIST.map(async (item) => {
        try {
          const res = await fetch(`${REPLAY_BASE}/${item.scenarioId}.json`, { cache: "force-cache" });
          if (!res.ok) return;
          const rec = (await res.json()) as Recording;
          if (recordingProblems(rec).length === 0) cache.current.set(item.scenarioId, rec);
        } catch {
          /* chưa có bản ghi: chỉ ảnh hưởng chế độ bản ghi */
        }
      }),
    );
  }, []);

  const show = useCallback((patch: Partial<BoothView>) => setView((v) => ({ ...v, ...patch })), []);

  async function runLive(item: PlaylistItem, mine: number): Promise<{ result: BoothResult; recording: Recording }> {
    const t0 = performance.now();
    const elapsed = () => Math.round(performance.now() - t0);
    let fails = 0;
    const frames: Frame[] = [];
    const recSteps: RecordedStep[] = [];
    const seenSteps = new Set<string>();
    let lastFrame = "";

    const attempt = async <T,>(fn: () => Promise<T>): Promise<T | null> => {
      if (typeof navigator !== "undefined" && navigator.onLine === false) throw new OfflineError();
      try {
        const value = await fn();
        fails = 0;
        return value;
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) throw new ClosedError();
        if (e instanceof ApiError && (e.status === 0 || e.status >= 500)) {
          fails += 1;
          if (fails >= FAILS_TO_OFFLINE) throw new OfflineError();
          return null;
        }
        throw e;
      }
    };
    const timed = <T,>(path: string, init: RequestInit = {}) => api<T>(path, { ...init, signal: AbortSignal.timeout(CALL_TIMEOUT_MS) });

    setView({ ...EMPTY, title: item.title });
    let run: SimRun | null = null;
    while (!run) {
      run = await attempt(() =>
        timed<SimRun>("/v1/sim/runs", { method: "POST", body: JSON.stringify({ scenario_id: item.scenarioId, llm: "replay" }) }),
      );
      if (!run) await wait(500, mine);
    }

    let tAlert: number | null = null;
    let answeredQuestion: string | null = null;
    let decided = false;
    let settled = 0;
    const consume = (next: SimRun, steps: AgentStep[] | null) => {
      const json = JSON.stringify(next);
      if (json !== lastFrame) {
        lastFrame = json;
        frames.push({ t_ms: elapsed(), run: next });
      }
      for (const step of steps ?? []) {
        if (!seenSteps.has(step.id)) {
          seenSteps.add(step.id);
          recSteps.push({ t_ms: elapsed(), step });
        }
      }
      if (tAlert === null && next.guardian_messages.length > 0) tAlert = elapsed();
      // Giữ câu hỏi trên màn sau khi bác trả lời (người xem còn đọc được câu hỏi cùng đáp án).
      show({ run: next, ...(steps ? { steps } : {}), ...(next.pending_question ? { question: next.pending_question.text } : {}) });
    };
    consume(run, null);

    while (elapsed() < RUN_CAP_MS) {
      if (run.incident_id === null) break; // tình huống không bật nhắc dừng: không có sự cố để chạy tiếp
      await wait(timing.poll, mine);
      const next = await attempt(() => timed<SimRun>(`/v1/sim/runs/${encodeURIComponent(run!.incident_id!)}`));
      if (!next) continue;
      run = next;
      const listed = run.run_id ? await attempt(() => timed<{ steps: AgentStep[] }>(`/v1/runs/${encodeURIComponent(run!.run_id!)}/steps`)) : null;
      consume(run, listed?.steps ?? null);

      if (run.pending_question && answeredQuestion !== run.pending_question.question_id) {
        await wait(timing.dwell, mine);
        const q: string = run.pending_question.question_id;
        const answered = await attempt(() =>
          timed<SimRun>(`/v1/sim/runs/${encodeURIComponent(run!.incident_id!)}/answer`, {
            method: "POST",
            body: JSON.stringify({ question_id: q, answer: item.answer }),
          }),
        );
        if (answered) {
          answeredQuestion = q;
          run = answered;
          show({ answered: item.answer });
          consume(run, null);
        }
      } else if (!decided && !run.pending_question && run.guardian_messages.some((m) => m.template === "detail")) {
        // Tin chi tiết đã tới con (đồ thị đang chờ người giám hộ; `state` vẫn có thể là `detected`): con quyết định.
        await wait(timing.dwell, mine);
        const done = await attempt(() =>
          timed(`/v1/incidents/${encodeURIComponent(run!.incident_id!)}/decision`, {
            method: "POST",
            body: JSON.stringify({ decision: item.decision }),
          }),
        );
        if (done !== null) {
          decided = true;
          show({ decided: item.decision });
        }
      } else if (decided && !DECIDABLE_STATES.includes(run.state ?? "")) {
        settled += 1;
        if (settled >= 2) break;
      }
    }
    await wait(timing.dwell, mine);
    const duration = elapsed();
    const result: BoothResult = {
      scenarioId: item.scenarioId,
      mode: "live",
      tAlertMs: tAlert,
      ok: tAlert !== null && tAlert < ALERT_LIMIT_MS && (decided || run.incident_id === null),
      at: Date.now(),
    };
    const recording: Recording = {
      scenario_id: item.scenarioId,
      recorded_at: new Date().toISOString(),
      duration_ms: duration,
      frames,
      steps: recSteps,
    };
    return { result, recording };
  }

  async function playRecorded(item: PlaylistItem, mine: number): Promise<BoothResult> {
    const rec = cache.current.get(item.scenarioId);
    if (!rec) throw new Error("Chưa có bản ghi cho kịch bản này.");
    setView({ ...EMPTY, title: item.title });
    const t0 = performance.now();
    let t = 0;
    let tAlert: number | null = null;
    let question: string | null = null;
    while (t <= rec.duration_ms) {
      const frame = frameAt(rec, t);
      if (tAlert === null && frame.run.guardian_messages.length > 0) tAlert = frame.t_ms;
      const lastDecided = frame.run.state !== null && !DECIDABLE_STATES.includes(frame.run.state);
      question = frame.run.pending_question?.text ?? question;
      show({
        run: frame.run,
        steps: stepsAt(rec, t),
        question,
        answered: frame.run.pending_question ? null : t > 0 && frame.run.guardian_messages.length > 1 ? item.answer : null,
        decided: lastDecided ? item.decision : null,
      });
      await wait(Math.min(timing.poll, 200), mine);
      t = Math.round((performance.now() - t0) * timing.speed);
    }
    await wait(timing.dwell, mine);
    return { scenarioId: item.scenarioId, mode: "recording", tAlertMs: tAlert, ok: true, at: Date.now() };
  }

  const playItem = useCallback(
    async (item: PlaylistItem, mine: number) => {
      const useRecording = modeRef.current === "recording" || (modeRef.current === "auto" && offlineRef.current);
      let result: BoothResult;
      try {
        if (useRecording) {
          setPlaying("recording");
          result = await playRecorded(item, mine);
        } else {
          setPlaying("live");
          const live = await runLive(item, mine);
          result = live.result;
          post({ type: "recording", recording: live.recording });
        }
      } catch (e) {
        if (e instanceof Cancelled) throw e;
        if (e instanceof ClosedError) {
          setClosed(true);
          throw new Cancelled();
        }
        if (options.handleUnauthorized?.(e)) throw new Cancelled();
        if (e instanceof OfflineError && modeRef.current === "auto") {
          setOfflineBoth(true); // D4: chuyển sang bản ghi ngay trong lượt này
          setPlaying("recording");
          result = await playRecorded(item, mine);
        } else {
          setError(e instanceof Error ? e.message : "Có trục trặc khi chạy.");
          throw new Cancelled();
        }
      }
      setResults((r) => [result, ...r].slice(0, 12));
      post({ type: "result", result });
      return result;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [post, wait],
  );

  // Có mạng trở lại ⇒ quay về trực tiếp ở lượt kế (D4).
  async function probe() {
    if (!offlineRef.current || (typeof navigator !== "undefined" && navigator.onLine === false)) return;
    try {
      await api("/v1/guardian/me", { signal: AbortSignal.timeout(CALL_TIMEOUT_MS) });
      setOfflineBoth(false);
    } catch {
      /* vẫn mất mạng */
    }
  }

  const stop = useCallback(() => {
    epoch.current += 1;
    loop.current = false;
    busyRef.current = false;
    setBusy(false);
    setPlaying(null);
  }, []);

  const reset = useCallback(() => {
    stop();
    setView(EMPTY);
    setResults([]);
    setError(null);
  }, [stop]);

  const begin = useCallback(
    async (items: PlaylistItem[], repeat: boolean) => {
      epoch.current += 1;
      const mine = epoch.current;
      busyRef.current = true;
      loop.current = repeat;
      setBusy(true);
      setError(null);
      try {
        do {
          for (const item of items) {
            await probe();
            await playItem(item, mine);
            await wait(timing.gap, mine);
          }
        } while (loop.current);
      } catch (e) {
        if (!(e instanceof Cancelled)) setError("Có trục trặc khi chạy.");
      } finally {
        if (epoch.current === mine) {
          busyRef.current = false;
          setBusy(false);
          setPlaying(null);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [playItem, wait, timing.gap],
  );

  const startOne = useCallback((id: string) => {
    const item = PLAYLIST.find((p) => p.scenarioId === id);
    if (item) void begin([item], false);
  }, [begin]);
  const startPlaylist = useCallback(() => void begin(PLAYLIST, true), [begin]);

  // Kênh với /demo/console + nhịp tim; nạp sẵn bản ghi; tự chạy danh sách phát nếu `autoplay`.
  useEffect(() => {
    const ch = new BroadcastChannel(CHANNEL);
    channel.current = ch;
    ch.onmessage = (event: MessageEvent<ChannelMessage>) => {
      const m = event.data;
      if (m.type !== "cmd") return;
      if (m.cmd === "start") startOne(m.scenarioId);
      else if (m.cmd === "playlist") startPlaylist();
      else if (m.cmd === "stop") stop();
      else if (m.cmd === "reset") reset();
      else if (m.cmd === "mode" && isMode(m.mode)) setMode(m.mode);
    };
    void preload().then(() => {
      if (options.autoplay) startPlaylist();
    });
    const heartbeat = window.setInterval(
      () => ch.postMessage({ type: "status", mode: modeRef.current === "recording" ? "recording" : "live", offline: offlineRef.current, busy: busyRef.current } satisfies ChannelMessage),
      2000,
    );
    return () => {
      window.clearInterval(heartbeat);
      ch.close();
      channel.current = null;
      epoch.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { view, mode, setMode, playing, offline, busy, closed, error, results, startOne, startPlaylist, stop, reset };
}
