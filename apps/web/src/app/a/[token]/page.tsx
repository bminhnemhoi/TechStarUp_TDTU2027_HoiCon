"use client";

import { use, useCallback, useEffect, useState } from "react";

// Hợp đồng: docs/schemas/action_view.v1.json (GET /v1/action/{token}) · incident_decision.v1.json (POST …/decision).
type Level = "none" | "low" | "medium" | "high" | "critical";
type Decision = "safe" | "false_alarm" | "emergency_pause";

interface ActionView {
  token_valid: boolean;
  scope: string;
  expires_at: string;
  used_at: string | null;
  incident: {
    id: string;
    state: string;
    level: Level;
    rule_floor: Level;
    is_drill: boolean;
    opened_at: string;
    closed_at: string | null;
    summary_text: string;
    protected_member_label: string;
    device_label: string | null;
  };
}

// Lớp Tailwind tĩnh (không ghép chuỗi) để trình biên dịch thấy; màu từ tokens.css, chữ ≥ 7:1 (spec 010).
const LEVEL: Record<Level, { label: string; card: string; badge: string }> = {
  critical: { label: "Rất nguy hiểm", card: "bg-risk-critical-bg border-risk-critical-accent text-risk-critical-fg", badge: "bg-risk-critical-fg" },
  high: { label: "Rủi ro cao", card: "bg-risk-high-bg border-risk-high-accent text-risk-high-fg", badge: "bg-risk-high-fg" },
  medium: { label: "Cần chú ý", card: "bg-risk-medium-bg border-risk-medium-accent text-risk-medium-fg", badge: "bg-risk-medium-fg" },
  low: { label: "Rủi ro thấp", card: "bg-risk-low-bg border-risk-low-accent text-risk-low-fg", badge: "bg-risk-low-fg" },
  none: { label: "Bình thường", card: "bg-surface-muted border-brand-navy text-foreground", badge: "bg-brand-navy" },
};
// Luật 8: diễn tập luôn dùng màu riêng, không mượn màu rủi ro thật.
const DRILL = { label: "Diễn tập", card: "bg-drill-bg border-drill-accent text-drill-fg", badge: "bg-drill-fg" };

const CONFIRM: Record<Decision, { ask: string; done: string }> = {
  safe: { ask: "Anh/chị đã gọi được và chắc chắn mọi thứ an toàn?", done: "Đã ghi nhận: người thân an toàn. HỏiCon đóng cảnh báo này." },
  emergency_pause: {
    ask: "Anh/chị vẫn thấy đáng ngờ, nghi là lừa đảo?",
    done: "Đã ghi nhận: nghi lừa đảo. HỏiCon giữ sự cố mở để theo dõi. Anh/chị hãy gọi ngay cho người thân, nhắc tuyệt đối không chuyển tiền.",
  },
  false_alarm: { ask: "Anh/chị xác nhận đây là HỏiCon báo nhầm?", done: "Đã ghi nhận: HỏiCon báo nhầm. Cảm ơn anh/chị đã cho biết." },
};

const BUTTON = "flex min-h-16 w-full items-center justify-center rounded-button px-6 text-center text-body font-bold disabled:opacity-60";

function CallButton({ label }: { label: string }) {
  // Máy chủ không giữ số điện thoại thô (luật 1) ⇒ chỉ mở bàn phím gọi; người giám hộ tự chọn số của người thân.
  return (
    <a href="tel:" className={`${BUTTON} bg-brand-navy text-text-on-primary`}>
      📞 Gọi điện cho {label}
    </a>
  );
}

export default function ActionPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const path = `/v1/action/${encodeURIComponent(token)}`;

  const [view, setView] = useState<ActionView | null>(null);
  const [expired, setExpired] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pending, setPending] = useState<Decision | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [done, setDone] = useState<Decision | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const res = await fetch(path, { cache: "no-store" });
      if (res.status === 404) throw new Error("Không tìm thấy liên kết này. Có thể liên kết bị chép thiếu.");
      if (!res.ok) throw new Error("Máy chủ đang bận. Anh/chị thử lại sau ít phút.");
      const data = (await res.json()) as ActionView;
      setExpired(!data.token_valid && !data.used_at && new Date(data.expires_at).getTime() < Date.now());
      setView(data);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Không tải được cảnh báo. Anh/chị kiểm tra mạng rồi thử lại.");
    }
  }, [path]);

  useEffect(() => {
    // Tải dữ liệu từ máy chủ khi mở trang (đồng bộ với hệ bên ngoài, đúng mục đích của effect).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function submit(decision: Decision) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await fetch(`${path}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      if (res.ok) {
        setDone(decision);
      } else if (res.status === 409 || res.status === 410) {
        setPending(null);
        await load(); // đã có người xử lý hoặc liên kết hết hạn: hiện đúng trạng thái mới
      } else {
        throw new Error();
      }
    } catch {
      setSubmitError("Chưa gửi được. Anh/chị kiểm tra mạng rồi bấm lại.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!view) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-lg flex-col items-center justify-center gap-6 px-4 py-8 text-center text-foreground">
        {loadError ? (
          <>
            <div role="alert" className="w-full rounded-card border-2 border-risk-critical-accent bg-risk-critical-bg p-5 text-risk-critical-fg">
              <h1 className="text-title">Chưa mở được cảnh báo</h1>
              <p className="mt-2 text-body">{loadError}</p>
            </div>
            <button type="button" onClick={() => void load()} className={`${BUTTON} bg-brand-navy text-text-on-primary`}>
              Thử lại
            </button>
            <p className="text-body">Nếu lo lắng, anh/chị hãy gọi ngay cho người thân.</p>
          </>
        ) : (
          <p role="status" className="text-body">Đang tải cảnh báo…</p>
        )}
      </main>
    );
  }

  const { incident } = view;
  const level = incident.is_drill ? DRILL : (LEVEL[incident.level] ?? LEVEL.high);
  const name = incident.protected_member_label;
  const closed = !done && !view.token_valid && !expired;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-lg flex-col gap-5 px-4 py-6 text-foreground">
      {incident.is_drill && (
        <p className="rounded-card border-2 border-drill-accent bg-drill-bg p-4 text-center text-body font-bold text-drill-fg">
          [DIỄN TẬP] Đây là bài tập nhận biết lừa đảo của gia đình, không phải sự cố thật.
        </p>
      )}

      <p className="rounded-card bg-surface-muted p-4 text-body">
        Đây là trợ lý AI HỏiCon. Cảnh báo do máy phát hiện tự động; anh/chị hãy gọi cho người thân để kiểm tra.
      </p>

      <article className={`rounded-card border-2 p-5 ${level.card}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-headline">{name}</h1>
          <span className={`rounded-full px-3 py-1 text-body font-bold text-text-on-primary ${level.badge}`}>
            ⚠ {level.label}
          </span>
        </div>
        <p className="mt-3 text-body-large">{incident.summary_text}</p>
        <p className="mt-3 text-body">
          Lúc {new Date(incident.opened_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}
          {incident.device_label ? ` · ${incident.device_label}` : ""}
        </p>
      </article>

      {done && (
        <section role="status" className="rounded-card border-2 border-brand-navy bg-surface-muted p-5 text-foreground">
          <h2 className="text-title">✓ Đã ghi nhận</h2>
          <p className="mt-2 text-body">{CONFIRM[done].done}</p>
        </section>
      )}

      {closed && (
        <section role="status" className="rounded-card border-2 border-risk-low-accent bg-risk-low-bg p-5 text-risk-low-fg">
          <h2 className="text-title">✓ Cảnh báo này đã được xử lý</h2>
          <p className="mt-2 text-body">Một người trong gia đình đã trả lời rồi. Anh/chị không cần làm gì thêm.</p>
        </section>
      )}

      {expired && (
        <section role="status" className="rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-5 text-risk-medium-fg">
          <h2 className="text-title">Liên kết đã hết hạn</h2>
          <p className="mt-2 text-body">Liên kết chỉ dùng được trong 24 giờ. Nếu còn lo lắng, anh/chị hãy gọi cho người thân.</p>
        </section>
      )}

      {submitError && (
        <p role="alert" className="rounded-card border-2 border-risk-critical-accent bg-risk-critical-bg p-4 text-body text-risk-critical-fg">
          {submitError}
        </p>
      )}

      {view.token_valid && !done && pending && (
        <section aria-label="Xác nhận" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4">
          <p className="text-body-large font-bold">{CONFIRM[pending].ask}</p>
          <button
            type="button"
            disabled={submitting}
            onClick={() => void submit(pending)}
            className={`${BUTTON} bg-brand-navy text-text-on-primary`}
          >
            {submitting ? "Đang gửi…" : "Đúng, gửi xác nhận"}
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => setPending(null)}
            className={`${BUTTON} border-2 border-brand-navy bg-background text-foreground`}
          >
            Quay lại
          </button>
        </section>
      )}

      {view.token_valid && !done && !pending && (
        <section aria-label="Anh/chị trả lời" className="flex flex-col gap-3">
          <CallButton label={name} />
          <button type="button" onClick={() => setPending("safe")} className={`${BUTTON} bg-risk-low-fg text-text-on-primary`}>
            ✓ Đã gọi được, {name} an toàn
          </button>
          <button
            type="button"
            onClick={() => setPending("emergency_pause")}
            className={`${BUTTON} bg-risk-critical-fg text-text-on-primary`}
          >
            ⚠ Vẫn thấy đáng ngờ, nghi lừa đảo
          </button>
          <button
            type="button"
            onClick={() => setPending("false_alarm")}
            className={`${BUTTON} border-2 border-brand-navy bg-surface-muted text-foreground`}
          >
            HỏiCon báo nhầm
          </button>
        </section>
      )}

      {(done || closed || expired) && <CallButton label={name} />}
    </main>
  );
}
