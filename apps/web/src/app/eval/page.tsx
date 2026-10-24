"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorBox, GuardianShell, Icon, LINK_TOUCH, SimBanner, useLoginRedirect } from "@/components/guardian-ui";
import { ApiError, api, errorMessage } from "@/lib/client";
import type { components } from "@/lib/api/schema";

// Kết quả đánh giá trợ lý AI cho BGK (spec 033, FR-012, P3): đọc các baseline ĐÃ COMMIT qua `GET /v1/eval/summary` (cùng cổng và
// phiên người giám hộ demo với /sim). Số trên cassette `synthetic` hoặc kịch bản nháp là "số rào tất định", CHƯA PHẢI số M3.
type Summary = components["schemas"]["EvalSummary"];

const pct = (v: number) => `${Math.round(v * 1000) / 10}%`;
const ms = (v: number) => `${Math.round(v)} mili giây`;
const ROWS: { key: string; label: string; format: (v: number) => string }[] = [
  { key: "cases_total", label: "Số ca đã chạy", format: String },
  { key: "cases_scam", label: "Ca lừa đảo", format: String },
  { key: "cases_benign", label: "Ca cuộc gọi hợp lệ", format: String },
  { key: "escalation_recall", label: "Số ca cần cảnh báo được cảnh báo", format: pct },
  { key: "false_escalation_rate", label: "Báo nhầm (cuộc gọi hợp lệ bị cảnh báo)", format: pct },
  { key: "safety_violations", label: "Vi phạm an toàn", format: String },
  { key: "ai_disclosure_rate", label: "Tin có câu “Đây là trợ lý AI HỏiCon”", format: pct },
  { key: "fallback_rate", label: "Lần dùng câu soạn sẵn thay cho trợ lý AI", format: pct },
  { key: "latency_p50_ms", label: "Thời gian xử lý (trung vị)", format: ms }, // gitleaks:allow — tên chỉ số, không phải khóa
  { key: "latency_p95_ms", label: "Thời gian xử lý (chậm nhất 5%)", format: ms }, // gitleaks:allow — tên chỉ số, không phải khóa
  { key: "cost_usd", label: "Chi phí gọi model (USD)", format: (v) => v.toFixed(2) },
];
const SUITE_VI: Record<string, string> = { smoke: "Bộ nhanh (smoke)", full: "Bộ đầy đủ", injection: "Bộ chống chèn lệnh" };

export default function EvalPage() {
  const redirectIfUnauthorized = useLoginRedirect();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [closed, setClosed] = useState(false); // 404 ⇒ cổng mô phỏng đang tắt
  const started = useRef(false);

  const load = useCallback(async () => {
    try {
      setSummary(await api<Summary>("/v1/eval/summary"));
      setError(null);
    } catch (e) {
      if (redirectIfUnauthorized(e)) return;
      if (e instanceof ApiError && e.status === 404) setClosed(true);
      else setError(errorMessage(e));
    }
  }, [redirectIfUnauthorized]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void load();
  }, [load]);

  let body;
  if (closed) {
    body = (
      <ErrorBox title="Trang này chưa mở">
        Chức năng mô phỏng chưa được bật trên máy chủ này. Anh/chị nhờ người quản trị bật giúp.
      </ErrorBox>
    );
  } else if (error) {
    body = (
      <ErrorBox title="Chưa tải được kết quả" onRetry={() => void load()}>
        {error}
      </ErrorBox>
    );
  } else if (!summary) {
    body = (
      <p role="status" className="text-body">
        Đang tải kết quả…
      </p>
    );
  } else if (summary.suites.length === 0) {
    body = <p className="text-body-large">Chưa có kết quả đánh giá nào được lưu.</p>;
  } else {
    body = (
      <>
        {summary.suites.map(({ suite, baseline, gate }) => (
          <section key={suite} aria-labelledby={`h-${suite}`} className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4" data-testid={`suite-${suite}`}>
            <h2 id={`h-${suite}`} className="text-title">
              {SUITE_VI[suite] ?? suite}
            </h2>
            <p className="text-body">
              Lưu ngày {baseline.created} · mã bản {baseline.git_sha} · bản ghi {baseline.cassette_source === "recorded" ? "từ model thật" : "tổng hợp (synthetic)"}
            </p>
            {gate.verdict !== "recorded" && (
              <div role="note" className="rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-3 text-body text-risk-medium-fg" data-testid="gate">
                <p className="font-bold">
                  <Icon>⚠</Icon>Số rào tất định — CHƯA PHẢI SỐ M3
                </p>
                <ul className="list-disc pl-6">
                  {gate.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
            <table className="w-full text-left text-body">
              <caption className="sr-only">Chỉ số của {SUITE_VI[suite] ?? suite}</caption>
              <thead>
                <tr>
                  <th scope="col" className="py-1 pr-3">Chỉ số</th>
                  <th scope="col" className="py-1">Kết quả</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.filter((r) => typeof baseline.metrics[r.key] === "number").map((r) => (
                  <tr key={r.key} className="border-t border-surface-muted">
                    <th scope="row" className="py-2 pr-3 font-normal">{r.label}</th>
                    <td className="py-2 font-bold">{r.format(baseline.metrics[r.key] as number)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
        <p className="text-body">
          Đây là kết quả đã lưu trong kho mã, không phải lượt chạy trực tiếp. Bảng theo từng nhóm thủ đoạn sẽ có khi máy chủ gửi kèm số liệu theo nhóm.
        </p>
      </>
    );
  }

  return (
    <GuardianShell wide>
      <main className="flex flex-col gap-5">
        <h1 className="text-headline">Kết quả đánh giá trợ lý AI</h1>
        <SimBanner />
        {body}
        <Link href="/incidents" className={`${LINK_TOUCH} self-start`}>
          ← Về danh sách sự cố
        </Link>
      </main>
    </GuardianShell>
  );
}
