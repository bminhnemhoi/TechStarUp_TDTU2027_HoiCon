"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  ErrorBox,
  GuardianShell,
  Icon,
  LINK_TOUCH,
  useLoginRedirect,
} from "@/components/guardian-ui";
import { ApiError, api, errorMessage, type CaseFile, type CaseFileAction } from "@/lib/client";
import { LEVEL_ICON, LEVEL_VI, levelOf } from "@/lib/steps";

// Hồ sơ vụ việc (spec 031, FR-010): bản nháp do trợ lý AI soạn từ dữ kiện đã ghi, người giám hộ đọc, duyệt rồi in/lưu PDF.
// Các ô TỰ ĐIỀN (số điện thoại, tài khoản, số tiền…) chỉ nằm trong trình duyệt: không thuộc <form>, không có `name`, không gửi
// đi, không lưu localStorage (ADR-006) — máy chủ không bao giờ thấy chúng.
const STATUS_VI: Record<CaseFile["status"], { icon: string; text: string }> = {
  draft: { icon: "✎", text: "Bản nháp — chưa duyệt" },
  approved: { icon: "✓", text: "Đã duyệt — sẵn sàng để in" },
  sent: { icon: "✓", text: "Đã đánh dấu: anh/chị đã nộp hồ sơ" },
  discarded: { icon: "✕", text: "Đã bỏ hồ sơ này" },
};
const ASK: Record<CaseFileAction, string> = {
  approve: "Anh/chị đã đọc kỹ và muốn duyệt hồ sơ này? Sau khi duyệt, anh/chị có thể in hoặc lưu PDF.",
  discard: "Anh/chị muốn bỏ hồ sơ này? HỏiCon sẽ đóng sự cố. Việc này không hoàn lại được.",
  mark_sent: "Anh/chị đã mang hồ sơ này đi trình báo? HỏiCon sẽ ghi nhận và đóng sự cố.",
};
const CONFIRM: Record<CaseFileAction, string> = {
  approve: "Đúng, duyệt hồ sơ",
  discard: "Đúng, bỏ hồ sơ",
  mark_sent: "Đúng, tôi đã nộp",
};
const INPUT_MODE: Record<string, "tel" | "numeric" | "text"> = { caller_phone: "tel", account_number: "numeric", amount: "numeric" };

/** "2026-12-19" ⇒ "19/12/2026" (cùng kiểu ngày với dòng thời gian). */
const listDate = (version: string) => (/^\d{4}-\d{2}-\d{2}$/.test(version) ? version.split("-").reverse().join("/") : version);

const when = (iso: string) =>
  new Date(iso).toLocaleString("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

function plainText(file: CaseFile, fields: Record<string, string>): string {
  const c = file.content;
  const lines = [
    "HỒ SƠ VỤ VIỆC — do trợ lý AI HỏiCon soạn từ dữ kiện đã ghi",
    "",
    c.summary,
    "",
    `Mức rủi ro: ${LEVEL_VI[levelOf(c.level) ?? "high"]}`,
    ...c.reasons.map((r) => `- ${r}`),
    `Luật trên điện thoại: ${c.rule}`,
    c.caller_last3 ? `Số gọi tới: đuôi ${c.caller_last3}` : "",
    "",
    "Dòng thời gian:",
    ...c.timeline.map((t) => `- ${when(t.at)}: ${t.text}`),
    "",
    ...c.local_fields.map((f) => `${f.label}: ${fields[f.key] ?? ""}`),
    "",
    "HỏiCon không tự gửi hồ sơ này cho cơ quan nào.",
  ];
  return lines.filter((line, i) => line !== "" || lines[i - 1] !== "").join("\n");
}

export default function CaseFilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const redirectIfUnauthorized = useLoginRedirect();
  const [file, setFile] = useState<CaseFile | null>(null);
  const [loadError, setLoadError] = useState<{ status: number; message: string } | null>(null);
  const [pending, setPending] = useState<CaseFileAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  // Giá trị các ô tự điền chỉ sống trong state của trang này (mất khi đóng/tải lại): không form, không lưu, không gửi.
  const [fields, setFields] = useState<Record<string, string>>({});
  const started = useRef(false);
  const confirmRef = useRef<HTMLParagraphElement>(null);

  const load = useCallback(async () => {
    try {
      setFile(await api<CaseFile>(`/v1/guardian/incidents/${encodeURIComponent(id)}/case-file`));
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
    if (pending) confirmRef.current?.focus();
  }, [pending]);

  async function submit(action: CaseFileAction) {
    setBusy(true);
    setNotice(null);
    try {
      // Thân chỉ có `action`: không có chỗ nào cho giá trị ô tự điền.
      setFile(await api<CaseFile>(`/v1/guardian/incidents/${encodeURIComponent(id)}/case-file`, { method: "POST", body: JSON.stringify({ action }) }));
      setPending(null);
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      if (error instanceof ApiError && error.status === 409) {
        setNotice("Hồ sơ đã được xử lý ở nơi khác. HỏiCon đang cập nhật lại.");
        setPending(null);
        await load();
      } else {
        setNotice("Chưa gửi được. Hồ sơ của anh/chị vẫn nguyên. Anh/chị kiểm tra mạng rồi bấm lại.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!file) return;
    try {
      await navigator.clipboard.writeText(plainText(file, fields));
      setCopied(true);
    } catch {
      setNotice("Chưa sao chép được. Anh/chị dùng nút In / lưu PDF.");
    }
  }

  let body;
  if (loadError) {
    body =
      loadError.status === 404 ? (
        <ErrorBox title="Chưa có hồ sơ cho sự cố này">
          Sự cố này chưa có hồ sơ. HỏiCon chỉ soạn hồ sơ khi anh/chị chọn “nghi lừa đảo” ở trang sự cố.{" "}
          <Link href={`/incidents/${encodeURIComponent(id)}`} className={LINK_TOUCH}>
            Về trang sự cố
          </Link>
        </ErrorBox>
      ) : (
        <ErrorBox title="Chưa tải được hồ sơ" onRetry={() => void load()}>
          {loadError.message}
        </ErrorBox>
      );
  } else if (!file) {
    body = (
      <p role="status" className="text-body">
        Đang tải hồ sơ…
      </p>
    );
  } else {
    const c = file.content;
    const level = levelOf(c.level) ?? "high";
    const open = file.status === "draft" || file.status === "approved";
    body = (
      <>
        <h1 className="text-headline">Hồ sơ vụ việc của {c.elder_alias}</h1>
        <div className="flex flex-col gap-2 rounded-card border-2 border-brand-navy bg-surface-muted p-4" data-testid="ai-box">
          <p className="text-body" data-testid="ai-label">
            <Icon>ⓘ</Icon>
            {c.ai_label}
          </p>
          <p className="text-body font-bold">Anh/chị đọc kỹ trước khi duyệt. HỏiCon không tự gửi hồ sơ này cho cơ quan nào.</p>
        </div>
        <p className="text-body-large font-bold" data-testid="status" aria-live="polite">
          <Icon>{STATUS_VI[file.status].icon}</Icon>
          {STATUS_VI[file.status].text}
        </p>
        {file.is_demo && (
          <p className="text-body font-bold">
            <Icon>ⓘ</Icon>Dữ liệu mô phỏng.
          </p>
        )}

        {open && (
          <ol className="flex list-decimal flex-col gap-1 pl-7 text-body-large print:hidden" data-testid="steps-guide">
            <li className={file.status === "draft" ? "font-bold" : ""}>Đọc kỹ hồ sơ bên dưới rồi bấm Duyệt.</li>
            <li className={file.status === "approved" ? "font-bold" : ""}>In hoặc lưu PDF.</li>
            <li>
              Làm theo <a href="#guide-title" className="underline">“Các bước nên làm”</a> ở cuối hồ sơ. Nếu đã chuyển tiền, gọi ngân hàng ngay.
            </li>
          </ol>
        )}
        {file.status === "sent" && (
          <p role="status" className="rounded-card border-2 border-brand-navy p-4 text-body">
            Cảm ơn anh/chị. HỏiCon đã ghi nhận anh/chị đã nộp hồ sơ và đóng sự cố.{" "}
            <Link href={`/incidents/${encodeURIComponent(id)}`} className={LINK_TOUCH}>
              Về trang sự cố
            </Link>
          </p>
        )}
        {file.status === "discarded" && (
          <p role="status" className="rounded-card border-2 border-brand-navy p-4 text-body">
            Hồ sơ này đã được bỏ. Nếu cần, anh/chị quay lại trang sự cố.{" "}
            <Link href={`/incidents/${encodeURIComponent(id)}`} className={LINK_TOUCH}>
              Về trang sự cố
            </Link>
          </p>
        )}

        {notice && (
          <p role="alert" className="rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-4 text-body text-risk-medium-fg print:hidden">
            {notice}
          </p>
        )}

        {file.status !== "discarded" && (
        <>
        <section aria-labelledby="summary-title" className="flex flex-col gap-2 print:break-inside-avoid">
          <h2 id="summary-title" className="text-title">
            Tóm tắt diễn biến
          </h2>
          <p className="text-body-large">{c.summary}</p>
          <p className="text-body">
            {file.summary_source === "llm"
              ? "Đoạn này do trợ lý AI soạn — anh/chị đọc kỹ trước khi duyệt."
              : "Đoạn này được ghép từ các dữ kiện đã ghi."}
          </p>
        </section>

        <section aria-labelledby="facts-title" className="flex flex-col gap-2 print:break-inside-avoid">
          <h2 id="facts-title" className="text-title">
            Dấu hiệu đã ghi
          </h2>
          <h3 className="text-body-large font-bold">Mức rủi ro</h3>
          <p className="text-body font-bold">
            <span aria-hidden="true">{LEVEL_ICON[level]} </span>Mức rủi ro: {LEVEL_VI[level]}
          </p>
          <h3 className="text-body-large font-bold">HỏiCon đã ghi nhận</h3>
          <ul className="list-disc pl-6 text-body">
            {c.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="text-body">Điện thoại phát hiện: {c.rule}</p>
          <p className="text-body">Số gọi tới: {c.caller_last3 ? `đuôi ${c.caller_last3} (HỏiCon không lưu số đầy đủ)` : "không có cuộc gọi"}</p>
          {c.elder_answers.length > 0 && (
            <>
              <h3 className="text-body-large font-bold">{c.elder_alias} trả lời</h3>
              <ul className="list-disc pl-6 text-body">
                {c.elder_answers.map((a) => (
                  <li key={a.question}>
                    {a.question} — {a.answer}
                  </li>
                ))}
              </ul>
            </>
          )}
          {c.verifications.length > 0 && (
            <>
              <h3 className="text-body-large font-bold">Kết quả tra cứu</h3>
              <ul className="list-disc pl-6 text-body">
                {c.verifications.map((v, i) => (
                  <li key={i}>
                    {v.kind === "phone" ? "Số điện thoại" : "Đường dẫn"}:{" "}
                    {v.verdict === "dangerous" ? "rất đáng ngờ" : v.verdict === "warning" ? "cần chú ý" : "chưa thấy cảnh báo"} (nguồn: {v.source}
                    {v.list_version ? `, cập nhật ${listDate(v.list_version)}` : ""})
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section aria-labelledby="timeline-title" className="flex flex-col gap-2 print:break-inside-avoid">
          <h2 id="timeline-title" className="text-title">
            Dòng thời gian
          </h2>
          <ol className="flex flex-col gap-2">
            {c.timeline.map((t, i) => (
              <li key={`${t.at}-${i}`} className="rounded-card border-2 border-surface-muted p-3 text-body print:break-inside-avoid">
                <span className="font-bold">{when(t.at)}</span> — {t.text}
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="local-title" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4 print:break-inside-avoid">
          <h2 id="local-title" className="text-title">
            Anh/chị tự điền thêm
          </h2>
          <p className="text-body font-bold">Các ô này chỉ nằm trên máy của anh/chị, HỏiCon không nhận được.</p>
          <p className="text-body print:hidden">Số anh/chị điền sẽ mất khi đóng trang. Hãy in hoặc lưu PDF trước khi thoát.</p>
          {c.local_fields.map((f) => (
            <div key={f.key} className="flex flex-col gap-1">
              <label htmlFor={`local-${f.key}`} className="text-body font-bold">
                {f.label}
              </label>
              <input
                id={`local-${f.key}`}
                type="text"
                autoComplete="off"
                spellCheck={false}
                inputMode={INPUT_MODE[f.key] ?? "text"}
                value={fields[f.key] ?? ""}
                onChange={(e) => setFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                className="min-h-14 rounded-button border-2 border-brand-navy bg-background px-3 text-body print:min-h-10 print:rounded-none print:border-0 print:border-b-2"
              />
            </div>
          ))}
        </section>

        <section aria-labelledby="guide-title" className="flex flex-col gap-2 print:break-inside-avoid" data-testid="guidance">
          <h2 id="guide-title" className="text-title">
            Các bước nên làm
          </h2>
          <p className="text-body">Dành cho người nhà đang giữ hồ sơ này.</p>
          {file.guidance.approved && file.guidance.steps.length > 0 ? (
            <ol className="flex list-decimal flex-col gap-2 pl-7 text-body-large">
              {file.guidance.steps.map((step) => (
                <li key={step.id}>
                  {step.text_vi}
                  {step.source_ref && <span className="block text-body">Nguồn: {step.source_ref}</span>}
                </li>
              ))}
            </ol>
          ) : (
            <>
              <p className="text-body-large">{file.guidance.fallback_vi}</p>
              <p className="text-body">HỏiCon chưa có hướng dẫn chi tiết đã được kiểm duyệt nên chỉ nêu lời khuyên chung.</p>
            </>
          )}
        </section>
        <p className="hidden text-body print:block">
          Hồ sơ do trợ lý AI HỏiCon soạn từ dữ kiện đã ghi, người giám hộ đã đọc và duyệt
          {file.approved_at ? ` ngày ${when(file.approved_at)}` : ""}. HỏiCon không tự gửi hồ sơ này cho cơ quan nào. Mã hồ sơ: {file.id}.
        </p>
        </>
        )}

        {pending && (
          <section aria-label="Xác nhận" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4 print:hidden">
            <p ref={confirmRef} tabIndex={-1} className="text-body-large font-bold outline-none">
              {ASK[pending]}
            </p>
            <button type="button" disabled={busy} onClick={() => void submit(pending)} className={BUTTON_PRIMARY}>
              {busy ? "Đang gửi…" : CONFIRM[pending]}
            </button>
            <button type="button" disabled={busy} onClick={() => setPending(null)} className={BUTTON_SECONDARY}>
              Chưa, quay lại
            </button>
          </section>
        )}

        {!pending && open && (
          <section aria-label="Việc anh/chị có thể làm" className="flex flex-col gap-3 print:hidden">
            {file.status === "draft" && (
              <button type="button" onClick={() => setPending("approve")} className={BUTTON_PRIMARY}>
                <Icon>✓</Icon>Duyệt hồ sơ
              </button>
            )}
            {file.status === "approved" && (
              <>
                <button type="button" onClick={() => window.print()} className={BUTTON_PRIMARY}>
                  <Icon>🖨</Icon>In / lưu PDF
                </button>
                <button type="button" onClick={() => void copy()} className={BUTTON_SECONDARY}>
                  Sao chép chữ
                </button>
                {copied && (
                  <p role="status" className="text-body font-bold">
                    ✓ Đã sao chép.
                  </p>
                )}
                <button type="button" onClick={() => setPending("mark_sent")} className={BUTTON_SECONDARY}>
                  <Icon>✓</Icon>Tôi đã nộp hồ sơ này
                </button>
              </>
            )}
            <button type="button" onClick={() => setPending("discard")} className={`${LINK_TOUCH} mt-6 self-start`}>
              Bỏ hồ sơ này
            </button>
          </section>
        )}
      </>
    );
  }

  return (
    <GuardianShell>
      <main className="flex flex-col gap-5">
        <Link href={`/incidents/${encodeURIComponent(id)}`} className={`${LINK_TOUCH} self-start print:hidden`}>
          <span aria-hidden="true">← </span>Về trang sự cố
        </Link>
        {body}
      </main>
    </GuardianShell>
  );
}
