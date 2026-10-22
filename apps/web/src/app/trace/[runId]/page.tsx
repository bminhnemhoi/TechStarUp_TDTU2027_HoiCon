"use client";

import Link from "next/link";
import { use, useEffect } from "react";
import { BUTTON_SECONDARY, ErrorBox, GuardianShell, Icon, LINK_TOUCH, useLoginRedirect } from "@/components/guardian-ui";
import { TraceView } from "@/components/trace-graph";
import { ApiError } from "@/lib/client";
import { useRunStream, type StreamStatus } from "@/lib/stream";

// Sơ đồ + bản chữ của MỘT lượt xử lý (spec 033, FR-011). Dữ liệu: `GET /v1/runs/{id}/steps` + SSE (spec 025/027), đã che PII.
const STATUS_ICON: Record<StreamStatus, string> = {
  loading: "⟳",
  live: "●",
  reconnecting: "⟳",
  done: "✓",
  failed: "⚠",
  error: "⚠",
  unauthorized: "⚠",
  notfound: "⚠",
};
const STATUS_TEXT: Record<StreamStatus, string> = {
  loading: "Đang tải các bước…",
  live: "Đang theo dõi trực tiếp",
  reconnecting: "Đang kết nối lại…",
  done: "Trợ lý AI đã làm xong các bước",
  failed: "Lượt xử lý này gặp trục trặc",
  error: "Chưa theo dõi trực tiếp được. Anh/chị bấm Thử lại.",
  unauthorized: "Phiên đã hết hạn",
  notfound: "Không tìm thấy",
};

export default function TracePage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = use(params);
  const { steps, status, retry } = useRunStream(runId);
  const redirectIfUnauthorized = useLoginRedirect();
  useEffect(() => {
    if (status === "unauthorized") redirectIfUnauthorized(new ApiError(401, ""));
  }, [status, redirectIfUnauthorized]);

  return (
    <GuardianShell wide>
      <main className="flex flex-col gap-5">
        <Link href="/incidents" className={`${LINK_TOUCH} self-start`}>
          ← Về danh sách sự cố
        </Link>
        <h1 className="text-headline">Các bước của trợ lý AI</h1>
        <p className="rounded-card bg-surface-muted p-4 text-body">
          Đây là trợ lý AI HỏiCon. Các bước do máy tự ghi lại, không kèm số điện thoại hay nội dung cuộc gọi.
        </p>
        {status === "notfound" ? (
          <ErrorBox title="Không tìm thấy">
            Lượt xử lý này không có trong gia đình của anh/chị.{" "}
            <Link href="/incidents" className={LINK_TOUCH}>
              Về danh sách sự cố
            </Link>
          </ErrorBox>
        ) : (
          <>
            <p role="status" aria-live="polite" className="text-body font-bold" data-testid="stream-status">
              <Icon>{STATUS_ICON[status]}</Icon>
              {STATUS_TEXT[status]}
            </p>
            {status === "error" && (
              <button type="button" onClick={retry} className={BUTTON_SECONDARY}>
                Thử lại
              </button>
            )}
            <TraceView steps={steps} finished={status === "done" || status === "failed"} alias="" />
          </>
        )}
      </main>
    </GuardianShell>
  );
}
