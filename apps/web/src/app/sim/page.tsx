"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  BUTTON,
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  ErrorBox,
  GuardianShell,
  Icon,
  LINK_TOUCH,
  useLoginRedirect,
} from "@/components/guardian-ui";
import { TraceView } from "@/components/trace-graph";
import { ApiError, api, errorMessage, type Decision } from "@/lib/client";
import { decisionCopy } from "@/lib/decision-copy";
import type { SimRun, SimScenario } from "@/lib/sim";
import { useRunStream } from "@/lib/stream";
import { LEVEL_VI, STATE_VI, aliasName, levelOf } from "@/lib/steps";

// Điện thoại mô phỏng cho BGK (spec 033, FR-010): chọn kịch bản hư cấu → bác trả lời → con quyết định, xem trợ lý AI làm gì.
// Dữ liệu hoàn toàn mô phỏng: tin Zalo chỉ là bản ghi, không có cuộc gọi thật.
const ANSWERS: { value: "yes" | "no" | "unsure"; label: string }[] = [
  { value: "yes", label: "Có" },
  { value: "no", label: "Không" },
  { value: "unsure", label: "Chưa chắc" },
];
const POLL_MS = 2000;
const ALIAS = aliasName("Mẹ");
type Tab = "elder" | "ai" | "guardian";
const TABS: { id: Tab; label: string }[] = [
  { id: "elder", label: "Điện thoại của bác" },
  { id: "ai", label: "Trợ lý AI" },
  { id: "guardian", label: "Zalo của con" },
];

function speak(text: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "vi-VN";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

const timeOf = (iso: string) => new Date(iso).toLocaleTimeString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });

export default function SimPage() {
  const redirectIfUnauthorized = useLoginRedirect();
  const [scenarios, setScenarios] = useState<SimScenario[] | null>(null);
  const [closed, setClosed] = useState(false); // API trả 404 ⇒ cổng mô phỏng đang tắt
  const [loadError, setLoadError] = useState<string | null>(null);
  const [scenarioId, setScenarioId] = useState("");
  const [llm, setLlm] = useState<"replay" | "live">("replay");
  const [run, setRun] = useState<SimRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("elder");
  const [pending, setPending] = useState<Decision | null>(null);
  const [done, setDone] = useState<Decision | null>(null);
  const [answered, setAnswered] = useState(false);
  const [lostConnection, setLostConnection] = useState(false);
  const started = useRef(false);
  const confirmRef = useRef<HTMLParagraphElement>(null);

  const loadScenarios = useCallback(async () => {
    try {
      const list = await api<{ scenarios: SimScenario[] }>("/v1/sim/scenarios");
      setScenarios(list.scenarios);
      setScenarioId((current) => current || list.scenarios.find((s) => s.id === "fake_police_safe_account_002")?.id || list.scenarios[0]?.id || "");
      setLoadError(null);
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      if (error instanceof ApiError && error.status === 404) setClosed(true);
      else setLoadError(errorMessage(error));
    }
  }, [redirectIfUnauthorized]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void loadScenarios();
  }, [loadScenarios]);

  useEffect(() => {
    if (pending) confirmRef.current?.focus();
  }, [pending]);

  const incidentId = run?.incident_id ?? null;
  // Thăm dò khung nhìn mỗi 2 giây khi trang đang hiện (tin Zalo mô phỏng, câu hỏi mới của bác).
  useEffect(() => {
    if (!incidentId) return;
    let alive = true;
    const tick = async () => {
      if (document.hidden) return;
      try {
        const next = await api<SimRun>(`/v1/sim/runs/${encodeURIComponent(incidentId)}`);
        if (alive) {
          setRun(next);
          setLostConnection(false);
        }
      } catch (error) {
        if (!alive || redirectIfUnauthorized(error)) return;
        if (error instanceof ApiError && error.status === 404) setNotice("Lượt mô phỏng này đã hết hạn. Anh/chị bấm Bắt đầu để chạy lại.");
        else setLostConnection(true);
      }
    };
    const timer = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [incidentId, redirectIfUnauthorized]);

  const { steps, status } = useRunStream(run?.run_id ?? null);

  async function start() {
    setBusy(true);
    setNotice(null);
    setDone(null);
    setPending(null);
    setAnswered(false);
    try {
      const next = await api<SimRun>("/v1/sim/runs", { method: "POST", body: JSON.stringify({ scenario_id: scenarioId, llm }) });
      setRun(next);
      setTab("elder");
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      if (error instanceof ApiError && error.status === 429) setNotice("Anh/chị đã chạy nhiều lượt liên tiếp. Chờ vài phút rồi bấm nút bên dưới nhé.");
      else if (error instanceof ApiError && error.status === 404) setClosed(true);
      else setNotice(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function answer(value: "yes" | "no" | "unsure") {
    if (!run?.pending_question || !incidentId) return;
    setBusy(true);
    setNotice(null);
    try {
      const next = await api<SimRun>(`/v1/sim/runs/${encodeURIComponent(incidentId)}/answer`, {
        method: "POST",
        body: JSON.stringify({ question_id: run.pending_question.question_id, answer: value }),
      });
      setRun(next);
      setAnswered(true);
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      setNotice(error instanceof ApiError && error.status === 409 ? "Câu hỏi này đã được trả lời. Đang cập nhật." : errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function decide(decision: Decision) {
    if (!incidentId) return;
    setBusy(true);
    setNotice(null);
    try {
      await api(`/v1/incidents/${encodeURIComponent(incidentId)}/decision`, { method: "POST", body: JSON.stringify({ decision }) });
      setDone(decision);
      setPending(null);
      setRun(await api<SimRun>(`/v1/sim/runs/${encodeURIComponent(incidentId)}`));
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      setNotice(error instanceof ApiError && error.status === 409 ? "Sự cố đã được xử lý. Đang cập nhật." : "Chưa gửi được. Anh/chị bấm lại.");
      setPending(null);
    } finally {
      setBusy(false);
    }
  }

  const chosen = scenarios?.find((s) => s.id === scenarioId) ?? null;
  const decidable = run?.state === "detected" || run?.state === "assessing" || run?.state === "awaiting_guardian";

  let body;
  if (closed) {
    body = (
      <ErrorBox title="Trang này chưa mở">
        Chức năng mô phỏng chưa được bật trên máy chủ này. Anh/chị nhờ người quản trị bật giúp.
      </ErrorBox>
    );
  } else if (loadError) {
    body = (
      <ErrorBox title="Chưa tải được danh sách kịch bản" onRetry={() => void loadScenarios()}>
        {loadError}
      </ErrorBox>
    );
  } else if (!scenarios) {
    body = (
      <p role="status" className="text-body">
        Đang tải kịch bản…
      </p>
    );
  } else {
    body = (
      <>
        <section aria-label="Chọn kịch bản" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4">
          <label htmlFor="scenario" className="text-body font-bold">
            Kịch bản
          </label>
          <select
            id="scenario"
            value={scenarioId}
            onChange={(e) => setScenarioId(e.target.value)}
            className="min-h-16 rounded-button border-2 border-brand-navy bg-background px-3 text-body"
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id}
                {s.draft ? " (kịch bản nháp)" : ""}
              </option>
            ))}
          </select>
          {chosen && (
            <p className="text-body" data-testid="script">
              {chosen.draft && <span className="mr-2 rounded-2xl border-2 border-drill-accent bg-drill-bg px-2 font-bold text-drill-fg">Kịch bản nháp</span>}
              {chosen.is_benign && <span className="mr-2 font-bold">Cuộc gọi hợp lệ.</span>}
              {chosen.script_vi}
            </p>
          )}
          <fieldset className="flex flex-wrap gap-4">
            <legend className="text-body font-bold">Cách chạy trợ lý AI</legend>
            <label className="flex min-h-11 items-center gap-2 text-body">
              <input type="radio" name="llm" checked={llm === "replay"} onChange={() => setLlm("replay")} className="size-6" />
              Phát lại bản đã ghi (luôn cho kết quả giống nhau)
            </label>
            <label className="flex min-h-11 items-center gap-2 text-body">
              <input type="radio" name="llm" checked={llm === "live"} onChange={() => setLlm("live")} className="size-6" />
              Chạy thật với trợ lý AI (chưa cài chìa khóa kết nối thì dùng câu soạn sẵn)
            </label>
          </fieldset>
          <button type="button" disabled={busy || !scenarioId} onClick={() => void start()} className={BUTTON_PRIMARY}>
            {busy ? "Đang chạy…" : run ? "Chạy lại kịch bản này" : "Bắt đầu"}
          </button>
          {notice && (
            <p role="alert" className="rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-3 text-body text-risk-medium-fg">
              {notice}
            </p>
          )}
        </section>

        {lostConnection && (
          <p role="status" className="rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-3 text-body text-risk-medium-fg">
            <Icon>⚠</Icon>Đang mất kết nối, HỏiCon sẽ thử lại.
          </p>
        )}
        {run && run.incident_id === null && (
          <p role="status" className="rounded-card border-2 border-brand-navy bg-surface-muted p-4 text-body" data-testid="sim-note">
            {run.note}
          </p>
        )}
        {run && run.llm_mode === "fallback" && run.incident_id !== null && (
          <p className="rounded-card bg-surface-muted p-4 text-body">
            Đang dùng câu mẫu soạn sẵn thay cho trợ lý AI (không có bản ghi phát lại hoặc khóa API).
          </p>
        )}

        {run && run.incident_id !== null && (
          <>
            <div role="tablist" aria-label="Ba màn hình" className="flex flex-wrap gap-2 lg:hidden">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  id={`tab-${t.id}`}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.id}
                  aria-controls={`panel-${t.id}`}
                  onClick={() => setTab(t.id)}
                  className={`min-h-11 min-w-0 flex-1 basis-40 break-words rounded-button border-2 border-brand-navy px-2 text-body font-bold ${tab === t.id ? "bg-brand-navy text-text-on-primary" : "bg-background text-foreground"}`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr_1fr]">
              <section
                id="panel-elder"
                role="tabpanel"
                aria-labelledby="tab-elder"
                aria-label="Điện thoại của bác (mô phỏng)"
                className={`${tab === "elder" ? "flex" : "hidden lg:flex"} flex-col gap-3 rounded-card border-2 border-surface-muted p-4`}
              >
                <h2 className="text-title">Điện thoại của bác (mô phỏng)</h2>
                {run.pending_question ? (
                  <>
                    <p className="text-body-large" data-testid="question">
                      {run.pending_question.text}
                    </p>
                    <button type="button" onClick={() => speak(run.pending_question?.text ?? "")} className={BUTTON_SECONDARY}>
                      <Icon>🔊</Icon>Nghe lại câu hỏi
                    </button>
                    {ANSWERS.map((a) => (
                      <button key={a.value} type="button" disabled={busy} onClick={() => void answer(a.value)} className={`${BUTTON_SECONDARY} text-title`}>
                        {a.label}
                      </button>
                    ))}
                  </>
                ) : (
                  <p className="text-body">{answered ? "Cảm ơn bác. HỏiCon đang báo cho con." : "Hiện chưa có câu hỏi nào cho bác."}</p>
                )}
              </section>

              <section
                id="panel-ai"
                role="tabpanel"
                aria-labelledby="tab-ai"
                aria-label="Trợ lý AI (mô phỏng)"
                className={`${tab === "ai" ? "flex" : "hidden lg:flex"} min-w-0 flex-col gap-3 rounded-card border-2 border-surface-muted p-4`}
              >
                <h2 className="text-title">Trợ lý AI (mô phỏng)</h2>
                <p role="status" aria-live="polite" className="text-body font-bold" data-testid="level">
                  Mức rủi ro hiện tại: {LEVEL_VI[levelOf(run.level) ?? "none"]} · {STATE_VI[run.state ?? ""] ?? "Đang xử lý"}
                </p>
                <TraceView steps={steps} finished={status === "done" || status === "failed"} alias={ALIAS} />
              </section>

              <section
                id="panel-guardian"
                role="tabpanel"
                aria-labelledby="tab-guardian"
                aria-label="Zalo của con (mô phỏng)"
                className={`${tab === "guardian" ? "flex" : "hidden lg:flex"} flex-col gap-3 rounded-card border-2 border-surface-muted p-4`}
              >
                <h2 className="text-title">Zalo của con (mô phỏng)</h2>
                <ol className="flex flex-col gap-2" data-testid="messages">
                  {run.guardian_messages.map((m, index) => (
                    <li key={`${m.at}-${index}`} className="rounded-card bg-surface-muted p-3 text-body">
                      <p>{m.text}</p>
                      <p className="text-brand-navy">{timeOf(m.at)}</p>
                    </li>
                  ))}
                </ol>
                {run.guardian_messages.length === 0 && <p className="text-body">Chưa có tin nào gửi cho con.</p>}
                {done && (
                  <p role="status" className="rounded-card border-2 border-brand-navy bg-surface-muted p-3 text-body">
                    ✓ {decisionCopy(done, ALIAS, false).done}
                  </p>
                )}
                {decidable && pending && (
                  <div aria-label="Xác nhận" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-3">
                    <p ref={confirmRef} tabIndex={-1} className="text-body-large font-bold outline-none">
                      {decisionCopy(pending, ALIAS, false).ask}
                    </p>
                    <button type="button" disabled={busy} onClick={() => void decide(pending)} className={BUTTON_PRIMARY}>
                      Đúng, gửi xác nhận
                    </button>
                    <button type="button" disabled={busy} onClick={() => setPending(null)} className={BUTTON_SECONDARY}>
                      Chưa, quay lại
                    </button>
                  </div>
                )}
                {decidable && !pending && (
                  <div className="flex flex-col gap-3">
                    <button type="button" onClick={() => setPending("safe")} className={`${BUTTON} bg-risk-low-fg text-text-on-primary`}>
                      <Icon>✓</Icon>Đã gọi được, {ALIAS} an toàn
                    </button>
                    <button type="button" onClick={() => setPending("emergency_pause")} className={`${BUTTON} bg-risk-critical-fg text-text-on-primary`}>
                      <Icon>⚠</Icon>Tôi nghi {ALIAS} đang bị lừa
                    </button>
                    <button type="button" onClick={() => setPending("false_alarm")} className={BUTTON_SECONDARY}>
                      HỏiCon báo nhầm
                    </button>
                  </div>
                )}
              </section>
            </div>
          </>
        )}
      </>
    );
  }

  return (
    <GuardianShell wide>
      <main className="flex flex-col gap-5">
        <h1 className="text-headline">Mô phỏng một tình huống</h1>
        <p role="note" className="sticky top-0 z-10 rounded-card border-2 border-drill-accent bg-drill-bg p-4 text-body font-bold text-drill-fg" data-testid="sim-banner">
          <Icon>ⓘ</Icon>MÔ PHỎNG — dữ liệu hư cấu, không có cuộc gọi hay tin Zalo thật
        </p>
        {body}
        <Link href="/incidents" className={`${LINK_TOUCH} self-start`}>
          ← Về danh sách sự cố
        </Link>
      </main>
    </GuardianShell>
  );
}
