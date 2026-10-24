"use client";

import Link from "next/link";
import { use, useState } from "react";
import { BUTTON_PRIMARY, ErrorBox, GuardianShell, Icon, LINK_TOUCH } from "@/components/guardian-ui";
import { ApiError, api } from "@/lib/client";

// Khách tại gian vào xem bản trình diễn bằng mã tham gia (spec 050, FR-007). Mở trang KHÔNG tự đổi mã (trình quét liên kết/xem
// trước sẽ đốt lượt của khách thật): phải bấm nút. Phiên nhận được chỉ xem + quyết định trên sự cố mô phỏng (máy chủ ép).
const CODE = /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$/;

interface Joined {
  family_alias: string;
  expires_at: string;
}

export default function JoinPage({ params }: { params: Promise<{ code: string }> }) {
  const { code: raw } = use(params);
  const code = decodeURIComponent(raw).trim().toUpperCase();
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [joined, setJoined] = useState<Joined | null>(null);

  async function enter() {
    setProblem(null);
    if (!CODE.test(code)) {
      setProblem("Mã tham gia gồm 6 ký tự (chữ in hoa và số). Anh/chị hỏi người trình bày để lấy mã mới.");
      return;
    }
    setBusy(true);
    try {
      setJoined(await api<Joined>("/v1/booth/join", { method: "POST", body: JSON.stringify({ code }) }));
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        setProblem("Đã thử nhiều lần. Anh/chị đợi vài phút rồi thử lại, hoặc hỏi người trình bày.");
      } else if (error instanceof ApiError && error.status === 0) {
        setProblem(error.message);
      } else {
        setProblem("Mã chưa đúng hoặc đã hết hạn. Anh/chị hỏi người trình bày để lấy mã mới.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <GuardianShell>
      <main className="flex flex-col gap-5">
        <h1 className="text-display text-balance">Bạn đang xem bản trình diễn</h1>
        <p
          role="note"
          className="rounded-card border-2 border-sim-accent bg-sim-bg p-4 text-body-large font-bold text-sim-fg"
          data-testid="join-greeting"
        >
          <Icon>ⓘ</Icon>Mọi dữ liệu là hư cấu: không có cuộc gọi thật, không có ai bị lừa thật và không có tin Zalo thật.
        </p>
        {joined ? (
          <section className="flex flex-col gap-4" data-testid="join-welcome" aria-label="Đã vào xem">
            <p role="status" className="text-body-large font-bold">
              <Icon>✓</Icon>Đã vào xem bản trình diễn của {joined.family_alias}.
            </p>
            <p className="text-body-large">
              Anh/chị xem được các sự cố mô phỏng và có thể bấm quyết định (an toàn, nghi lừa đảo) như người nhà thật. Đây là trợ lý AI HỏiCon.
            </p>
            <Link href="/incidents" className={`${BUTTON_PRIMARY} text-center`}>
              Xem các sự cố của buổi trình diễn
            </Link>
          </section>
        ) : (
          <>
            <p className="text-body-large">
              Bấm nút dưới đây để vào xem. Mã của anh/chị: <strong className="tracking-widest">{code}</strong>
            </p>
            {problem && (
              <ErrorBox title="Chưa vào được">{problem}</ErrorBox>
            )}
            <button type="button" onClick={() => void enter()} disabled={busy} className={BUTTON_PRIMARY}>
              {busy ? "Đang vào…" : "Vào xem bản trình diễn"}
            </button>
          </>
        )}
        <Link href="/" className={`${LINK_TOUCH} min-h-16 self-start`}>
          ← Về trang chính
        </Link>
      </main>
    </GuardianShell>
  );
}
