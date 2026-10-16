"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import {
  BUTTON,
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  DrillBanner,
  DrillTag,
  ErrorBox,
  GuardianShell,
  Icon,
  LINK_TOUCH,
  RiskBadge,
  isClosedState,
  styleFor,
  useLoginRedirect,
} from "@/components/guardian-ui";
import { ApiError, api, errorMessage, type Decision, type GuardianIncidentDetail } from "@/lib/client";
import { useRunStream, type StreamStatus } from "@/lib/stream";
import { DECIDABLE_STATES, STATE_VI, aliasName, describeStep, relativeTime } from "@/lib/steps";

// Chi tiết một sự cố (spec 027, FR-007): lịch sử chuyển trạng thái, trace trực tiếp của trợ lý AI, quyết định có xác nhận.
const ACTOR_VI: Record<string, string> = {
  device: "Điện thoại của người thân",
  agent: "Trợ lý AI",
  guardian: "Người nhà",
  timer: "Bộ hẹn giờ",
  system: "Hệ thống",
};

const DRILL_DONE =
  "[DIỄN TẬP] Đã ghi nhận. Đây chỉ là bài tập, không có nguy hiểm thật. Cảm ơn anh/chị đã tham gia.";

/** Câu hỏi xác nhận và câu đã ghi nhận; diễn tập không bao giờ nói như sự cố thật (luật 8). */
function copy(decision: Decision, name: string, isDrill: boolean): { ask: string; done: string } {
  const tag = isDrill ? "[DIỄN TẬP] " : "";
  switch (decision) {
    case "safe":
      return {
        ask: `${tag}Anh/chị đã nói chuyện trực tiếp với ${name} và chắc chắn ${name} an toàn? HỏiCon sẽ đóng cảnh báo này.`,
        done: isDrill ? DRILL_DONE : `Đã ghi nhận: ${name} an toàn. HỏiCon đóng cảnh báo này.`,
      };
    case "emergency_pause":
      return {
        ask: `${tag}Anh/chị nghi ${name} đang bị lừa? HỏiCon sẽ giữ cảnh báo mở để theo dõi.`,
        done: isDrill
          ? DRILL_DONE
          : `Đã ghi nhận: nghi lừa đảo. HỏiCon giữ cảnh báo mở để theo dõi và không tự báo cho cơ quan nào. Anh/chị hãy gọi ngay cho ${name}, nhắc tuyệt đối không chuyển tiền.`,
      };
    case "false_alarm":
      return {
        ask: `${tag}Anh/chị xác nhận đây là HỏiCon báo nhầm?`,
        done: isDrill ? DRILL_DONE : "Đã ghi nhận: HỏiCon báo nhầm. Cảm ơn anh/chị đã cho biết.",
      };
  }
}

const STREAM_TEXT: Record<StreamStatus, string> = {
  loading: "Đang tải các bước…",
  live: "Đang theo dõi trực tiếp",
  reconnecting: "Đang kết nối lại…",
  done: "Trợ lý AI đã làm xong các bước",
  failed: "Lượt xử lý này gặp trục trặc",
  error: "Chưa theo dõi trực tiếp được. Anh/chị bấm Thử lại.",
  unauthorized: "Phiên đã hết hạn",
};

const when = (iso: string) =>
  new Date(iso).toLocaleString("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

function Trace({ runId, alias }: { runId: string | null; alias: string }) {
  const { steps, status, retry } = useRunStream(runId);
  const redirectIfUnauthorized = useLoginRedirect();
  useEffect(() => {
    if (status === "unauthorized") redirectIfUnauthorized(new ApiError(401, ""));
  }, [status, redirectIfUnauthorized]);

  return (
    <section aria-labelledby="trace-title" className="flex flex-col gap-3">
      <h2 id="trace-title" className="text-headline">
        Trợ lý AI đang làm gì
      </h2>
      <p className="rounded-card bg-surface-muted p-4 text-body">
        Đây là trợ lý AI HỏiCon. Các bước dưới đây do máy tự ghi lại, không kèm số điện thoại hay nội dung cuộc gọi.
      </p>
      {runId === null ? (
        <p className="text-body">Chưa có bước nào của trợ lý AI cho sự cố này.</p>
      ) : (
        <>
          <p role="status" aria-live="polite" className="text-body font-bold" data-testid="stream-status">
            {STREAM_TEXT[status]}
          </p>
          {status === "error" && (
            <button type="button" onClick={retry} className={BUTTON_SECONDARY}>
              Thử lại
            </button>
          )}
          <ol className="flex flex-col gap-2" data-testid="steps">
            {steps.map((step) => {
              const text = describeStep(step, alias);
              return (
                <li key={step.id} className="rounded-card border-2 border-surface-muted bg-background p-3">
                  <p className="text-body font-bold">{text.title}</p>
                  {text.detail && <p className="text-body">{text.detail}</p>}
                  <p className="text-body text-brand-navy">
                    {new Date(step.at).toLocaleTimeString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}
                  </p>
                </li>
              );
            })}
          </ol>
          {steps.length === 0 && status !== "loading" && <p className="text-body">Chưa có bước nào được ghi lại.</p>}
        </>
      )}
    </section>
  );
}

export default function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const redirectIfUnauthorized = useLoginRedirect();
  const [incident, setIncident] = useState<GuardianIncidentDetail | null>(null);
  const [loadError, setLoadError] = useState<{ status: number; message: string } | null>(null);
  const [pending, setPending] = useState<Decision | null>(null);
  const [done, setDone] = useState<Decision | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const started = useRef(false);
  const confirmRef = useRef<HTMLParagraphElement>(null);

  const load = useCallback(async () => {
    try {
      const detail = await api<GuardianIncidentDetail>(`/v1/guardian/incidents/${encodeURIComponent(id)}`);
      setIncident(detail);
      setLoadError(null);
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      setLoadError({ status: error instanceof ApiError ? error.status : 0, message: errorMessage(error) });
    }
  }, [id, redirectIfUnauthorized]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void load();
  }, [load]);

  useEffect(() => {
    if (pending) confirmRef.current?.focus(); // mở khung xác nhận ⇒ trình đọc màn hình đọc câu hỏi ngay
  }, [pending]);

  async function submit(decision: Decision) {
    setSubmitting(true);
    setNotice(null);
    try {
      await api(`/v1/incidents/${encodeURIComponent(id)}/decision`, { method: "POST", body: JSON.stringify({ decision }) });
      setDone(decision);
      setPending(null);
      await load();
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      if (error instanceof ApiError && error.status === 409) {
        setNotice("Sự cố đã được xử lý ở nơi khác. HỏiCon đang cập nhật lại.");
        setPending(null);
        await load();
      } else {
        setNotice("Chưa gửi được. Anh/chị kiểm tra mạng rồi bấm lại.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  let body;
  if (loadError) {
    body =
      loadError.status === 404 ? (
        <ErrorBox title="Không tìm thấy sự cố này">
          Sự cố không có trong gia đình của anh/chị.{" "}
          <Link href="/incidents" className={LINK_TOUCH}>
            Về danh sách sự cố
          </Link>
        </ErrorBox>
      ) : (
        <ErrorBox title="Chưa tải được sự cố" onRetry={() => void load()}>
          {loadError.message}
        </ErrorBox>
      );
  } else if (!incident) {
    body = (
      <p role="status" className="text-body">
        Đang tải sự cố…
      </p>
    );
  } else {
    const name = aliasName(incident.elder_alias);
    const title = aliasName(incident.elder_alias, true);
    const closed = isClosedState(incident.state);
    const style = styleFor(incident.level, incident.is_drill, closed);
    const decidable = DECIDABLE_STATES.includes(incident.state);
    body = (
      <>
        {incident.is_drill && <DrillBanner />}
        <article className={`flex flex-col gap-3 rounded-card border-2 p-5 ${style.card}`}>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-headline text-balance">{title}</h1>
            {incident.is_drill && <DrillTag />}
          </div>
          <div>
            <RiskBadge level={incident.level} isDrill={incident.is_drill} closed={closed} />
          </div>
          <p className="text-body-large font-bold">{STATE_VI[incident.state] ?? "Đang xử lý"}</p>
          <p className="text-body">Mở {relativeTime(incident.opened_at)}</p>
        </article>
        <p className="rounded-card bg-surface-muted p-4 text-body">
          Đây là trợ lý AI HỏiCon. Anh/chị nên gọi hỏi {name} để kiểm tra.
        </p>

        {done && (
          <section role="status" className="rounded-card border-2 border-brand-navy bg-surface-muted p-5">
            <h2 className="text-title">✓ Đã ghi nhận</h2>
            <p className="mt-2 text-body">{copy(done, name, incident.is_drill).done}</p>
          </section>
        )}
        {notice && (
          <p role="alert" className="rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-4 text-body text-risk-medium-fg">
            {notice}
          </p>
        )}

        {decidable && pending && (
          <section aria-label="Xác nhận" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4">
            <p ref={confirmRef} tabIndex={-1} className="text-body-large font-bold outline-none">
              {copy(pending, name, incident.is_drill).ask}
            </p>
            <button type="button" disabled={submitting} onClick={() => void submit(pending)} className={BUTTON_PRIMARY}>
              {submitting ? "Đang gửi…" : "Đúng, gửi xác nhận"}
            </button>
            <button type="button" disabled={submitting} onClick={() => setPending(null)} className={BUTTON_SECONDARY}>
              Chưa, quay lại
            </button>
          </section>
        )}

        {decidable && !pending && (
          <section aria-label="Anh/chị quyết định" className="flex flex-col gap-3">
            {/* Máy chủ không giữ số điện thoại (ADR-006) ⇒ `tel:` KHÔNG kèm số: chỉ mở bàn phím gọi, anh/chị tự bấm số. */}
            <a href="tel:" className={BUTTON_PRIMARY}>
              <Icon>📞</Icon>Mở bàn phím gọi điện
            </a>
            <button type="button" onClick={() => setPending("safe")} className={`${BUTTON} bg-risk-low-fg text-text-on-primary`}>
              <Icon>✓</Icon>Đã gọi được, {name} an toàn
            </button>
            <button
              type="button"
              onClick={() => setPending("emergency_pause")}
              className={`${BUTTON} bg-risk-critical-fg text-text-on-primary`}
            >
              <Icon>⚠</Icon>Tôi nghi {name} đang bị lừa
            </button>
            <button type="button" onClick={() => setPending("false_alarm")} className={BUTTON_SECONDARY}>
              HỏiCon báo nhầm
            </button>
            <p className="text-body">Lưu ý: HỏiCon không lưu số điện thoại, nên nút gọi chỉ mở bàn phím. Anh/chị tự bấm số của {name}.</p>
          </section>
        )}
        {!decidable && (
          <>
            <a href="tel:" className={BUTTON_PRIMARY}>
              <Icon>📞</Icon>Mở bàn phím gọi điện
            </a>
            <p className="text-body">HỏiCon không lưu số điện thoại. Anh/chị tự bấm số của {name}.</p>
          </>
        )}

        <Trace runId={incident.run_id ?? null} alias={name} />

        <section aria-labelledby="history-title" className="flex flex-col gap-3">
          <h2 id="history-title" className="text-headline">
            Lịch sử
          </h2>
          <ol className="flex flex-col gap-2" data-testid="transitions">
            {incident.transitions.map((t, index) => (
              <li key={`${t.at}-${index}`} className="rounded-card border-2 border-surface-muted p-3">
                <p className="text-body font-bold">
                  {t.from_state ? `${STATE_VI[t.from_state] ?? t.from_state} → ` : ""}
                  {STATE_VI[t.to_state] ?? t.to_state}
                </p>
                <p className="text-body">
                  {ACTOR_VI[t.actor] ?? "Hệ thống"} · {when(t.at)}
                </p>
              </li>
            ))}
          </ol>
          <p className="text-body">Mở lúc {when(incident.opened_at)}.</p>
        </section>
      </>
    );
  }

  return (
    <GuardianShell>
      <main className="flex flex-col gap-5">
        <Link href="/incidents" className={`${LINK_TOUCH} self-start`}>
          ← Về danh sách sự cố
        </Link>
        {body}
      </main>
    </GuardianShell>
  );
}
