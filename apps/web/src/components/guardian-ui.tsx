"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { ApiError, api, isUnauthorized, type GuardianSession } from "@/lib/client";
import { LEVEL_ICON, LEVEL_VI, OPEN_STATES, levelOf, type Level } from "@/lib/steps";

// Web người giám hộ (spec 027): người trưởng thành, không phải app người cao tuổi ⇒ chữ ≥ 16 px (token `body` = 20 px),
// vùng chạm ≥ 44 px, nút chính ≥ 64 px (`min-h-16`). Màu rủi ro luôn đi kèm biểu tượng + chữ; diễn tập dùng màu riêng.

export const BUTTON =
  "flex min-h-16 w-full items-center justify-center rounded-button px-6 text-center text-body font-bold focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-focus-ring disabled:opacity-60";
export const BUTTON_PRIMARY = `${BUTTON} bg-brand-navy text-text-on-primary`;
export const BUTTON_SECONDARY = `${BUTTON} border-2 border-brand-navy bg-background text-foreground`;
export const LINK_TOUCH =
  "-mx-3 inline-flex min-h-11 items-center rounded-button px-3 text-body font-bold underline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-focus-ring";

// Lớp Tailwind tĩnh (không ghép chuỗi) để trình biên dịch thấy; màu từ tokens.css, chữ ≥ 7:1.
export const LEVEL_STYLE: Record<Level, { card: string; badge: string }> = {
  critical: { card: "bg-risk-critical-bg border-risk-critical-accent text-risk-critical-fg", badge: "bg-risk-critical-fg" },
  high: { card: "bg-risk-high-bg border-risk-high-accent text-risk-high-fg", badge: "bg-risk-high-fg" },
  medium: { card: "bg-risk-medium-bg border-risk-medium-accent text-risk-medium-fg", badge: "bg-risk-medium-fg" },
  low: { card: "bg-risk-low-bg border-risk-low-accent text-risk-low-fg", badge: "bg-risk-low-fg" },
  none: { card: "bg-surface-muted border-brand-navy text-foreground", badge: "bg-brand-navy" },
};
// Luật 8: diễn tập luôn dùng màu riêng, không mượn màu rủi ro thật.
export const DRILL_STYLE = { card: "bg-drill-bg border-drill-accent text-drill-fg", badge: "bg-drill-fg" };

// Sự cố đã xong không còn "báo động": khung trung tính (diễn tập vẫn giữ màu riêng).
const CLOSED_STYLE = { card: "bg-surface-muted border-brand-navy text-foreground", badge: "bg-brand-navy" };

export function styleFor(level: string, isDrill: boolean, closed = false) {
  if (isDrill) return DRILL_STYLE;
  return closed ? CLOSED_STYLE : LEVEL_STYLE[levelOf(level) ?? "high"];
}

export const isClosedState = (state: string) => !OPEN_STATES.includes(state);

export function Icon({ children }: { children: string }) {
  return <span aria-hidden="true">{children} </span>; // biểu tượng không để trình đọc màn hình đọc tên emoji
}

/** Băng "MÔ PHỎNG" dính đầu trang của /sim và /trace của lượt mô phỏng (màu `sim.*`, khác màu diễn tập — luật 15). */
export function SimBanner() {
  return (
    <p
      role="note"
      className="sticky top-0 z-10 rounded-card border-2 border-sim-accent bg-sim-bg p-4 text-body font-bold text-sim-fg"
      data-testid="sim-banner"
    >
      <Icon>ⓘ</Icon>MÔ PHỎNG — dữ liệu hư cấu, không có cuộc gọi hay tin Zalo thật
    </p>
  );
}

export function RiskBadge({ level, isDrill, closed = false }: { level: string; isDrill: boolean; closed?: boolean }) {
  const known = levelOf(level) ?? "high";
  return (
    <span
      className={`inline-flex max-w-full items-center gap-2 rounded-2xl px-3 py-1 text-left text-body font-bold text-text-on-primary ${styleFor(level, isDrill, closed).badge}`}
    >
      <span aria-hidden="true">{LEVEL_ICON[known]}</span>
      <span>
        {closed ? "Mức rủi ro lúc đó" : "Mức rủi ro"}: {LEVEL_VI[known]}
      </span>
    </span>
  );
}

export function DrillTag() {
  return (
    <span className="inline-flex items-center rounded-2xl border-2 border-drill-accent bg-drill-bg px-3 py-1 text-body font-bold text-drill-fg">
      [DIỄN TẬP]
    </span>
  );
}

export function DrillBanner() {
  return (
    <p className="rounded-card border-2 border-drill-accent bg-drill-bg p-4 text-body font-bold text-drill-fg">
      [DIỄN TẬP] Đây là bài tập nhận biết lừa đảo của gia đình, không phải sự cố thật.
    </p>
  );
}

export function ErrorBox({ title, children, onRetry }: { title: string; children?: ReactNode; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col gap-3 rounded-card border-2 border-risk-critical-accent bg-risk-critical-bg p-5 text-risk-critical-fg">
      <h2 className="text-title">{title}</h2>
      {children && <div className="text-body">{children}</div>}
      {onRetry && (
        <button type="button" onClick={onRetry} className={BUTTON_PRIMARY}>
          Thử lại
        </button>
      )}
    </div>
  );
}

/** Chuyển về /login khi phiên hết hạn hoặc chưa đăng nhập; trả true nếu đã chuyển. */
export function useLoginRedirect() {
  const router = useRouter();
  return (error: unknown): boolean => {
    if (!isUnauthorized(error)) return false;
    router.replace("/login?het-han=1");
    return true;
  };
}

export function GuardianShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  const router = useRouter();
  const [session, setSession] = useState<GuardianSession | null>(null);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    let alive = true;
    api<GuardianSession>("/v1/guardian/me")
      .then((me) => alive && setSession(me))
      .catch((error: unknown) => {
        if (alive && isUnauthorized(error)) router.replace("/login?het-han=1");
      });
    return () => {
      alive = false;
    };
  }, [router]);

  async function logout() {
    setLeaving(true);
    try {
      await api<void>("/v1/guardian/session", { method: "DELETE" });
    } catch (error) {
      if (!(error instanceof ApiError)) throw error; // lỗi mạng: vẫn đưa về trang đăng nhập, cookie sẽ tự hết hạn
    }
    router.replace("/login");
  }

  return (
    <div className={`mx-auto flex min-h-screen w-full ${wide ? "max-w-7xl" : "max-w-3xl"} flex-col gap-5 px-4 py-5 text-foreground`}>
      <header className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-brand-navy pb-3 print:hidden">
        <div>
          <p className="text-body font-bold">HỏiCon</p>
          <p className="text-body" aria-live="polite">
            {session ? session.family_name : "Đang kiểm tra phiên…"}
          </p>
        </div>
        <button type="button" onClick={() => void logout()} disabled={leaving} className={`${LINK_TOUCH} disabled:opacity-60`}>
          {leaving ? "Đang đăng xuất…" : "Đăng xuất"}
        </button>
      </header>
      {children}
    </div>
  );
}
