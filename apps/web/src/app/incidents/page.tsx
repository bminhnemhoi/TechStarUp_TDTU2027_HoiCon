"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  BUTTON_SECONDARY,
  DrillTag,
  ErrorBox,
  GuardianShell,
  RiskBadge,
  isClosedState,
  styleFor,
  useLoginRedirect,
} from "@/components/guardian-ui";
import { api, errorMessage, type GuardianIncidentList, type GuardianIncidentSummary } from "@/lib/client";
import { STATE_VI, aliasName, relativeTime } from "@/lib/steps";

// Danh sách sự cố của gia đình (spec 027, FR-006): hai nhóm "Đang cần chú ý" và "Đã xong", mỗi nhóm phân trang riêng.
type Status = "open" | "closed";

interface Group {
  items: GuardianIncidentSummary[];
  cursor: string | null;
  loading: boolean;
  error: string | null;
  loaded: boolean;
}

const EMPTY: Group = { items: [], cursor: null, loading: true, error: null, loaded: false };

function Card({ incident }: { incident: GuardianIncidentSummary }) {
  const closed = isClosedState(incident.state);
  const style = styleFor(incident.level, incident.is_drill, closed);
  const alias = aliasName(incident.elder_alias, true);
  return (
    <li>
      <Link
        href={`/incidents/${incident.id}`}
        className={`flex min-h-16 flex-col gap-2 rounded-card border-2 p-4 focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-focus-ring ${style.card}`}
      >
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-title">{alias}</span>
          {incident.is_drill && <DrillTag />}
        </span>
        <span className="flex flex-wrap items-center gap-2">
          <RiskBadge level={incident.level} isDrill={incident.is_drill} closed={closed} />
        </span>
        <span className="text-body">
          {STATE_VI[incident.state] ?? "Đang xử lý"} · mở {relativeTime(incident.opened_at)}
        </span>
      </Link>
    </li>
  );
}

function Section({
  title,
  status,
  group,
  onMore,
  onRetry,
}: {
  title: string;
  status: Status;
  group: Group;
  onMore: () => void;
  onRetry: () => void;
}) {
  const headingId = `group-${status}`;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <h2 id={headingId} className="text-headline">
        {title}
      </h2>
      {group.items.length > 0 && (
        <ul className="flex flex-col gap-3">
          {group.items.map((incident) => (
            <Card key={incident.id} incident={incident} />
          ))}
        </ul>
      )}
      {group.loading && (
        <p role="status" className="text-body">
          Đang tải…
        </p>
      )}
      {group.error && (
        <ErrorBox title="Chưa tải được danh sách" onRetry={onRetry}>
          {group.error}
        </ErrorBox>
      )}
      {group.loaded && !group.loading && !group.error && group.items.length === 0 && (
        <p className="rounded-card bg-surface-muted p-4 text-body">
          {status === "open"
            ? "Hiện không có sự cố nào cần chú ý. HỏiCon sẽ nhắn qua Zalo ngay khi có dấu hiệu đáng ngờ."
            : "Chưa có sự cố nào đã xong."}
        </p>
      )}
      {group.cursor && !group.loading && (
        <button type="button" onClick={onMore} className={BUTTON_SECONDARY}>
          Tải thêm
        </button>
      )}
    </section>
  );
}

export default function IncidentsPage() {
  const redirectIfUnauthorized = useLoginRedirect();
  const [groups, setGroups] = useState<Record<Status, Group>>({ open: EMPTY, closed: EMPTY });
  const started = useRef(false);

  const load = useCallback(
    async (status: Status, cursor: string | null) => {
      setGroups((all) => ({ ...all, [status]: { ...all[status], loading: true, error: null } }));
      try {
        const query = new URLSearchParams({ status, ...(cursor ? { cursor } : {}) });
        const page = await api<GuardianIncidentList>(`/v1/guardian/incidents?${query}`);
        setGroups((all) => ({
          ...all,
          [status]: {
            items: cursor ? [...all[status].items, ...page.incidents] : page.incidents,
            cursor: page.next_cursor,
            loading: false,
            error: null,
            loaded: true,
          },
        }));
      } catch (error) {
        if (redirectIfUnauthorized(error)) return;
        setGroups((all) => ({ ...all, [status]: { ...all[status], loading: false, error: errorMessage(error) } }));
      }
    },
    [redirectIfUnauthorized],
  );

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void load("open", null);
    void load("closed", null);
  }, [load]);

  return (
    <GuardianShell>
      <main className="flex flex-col gap-8">
        <div className="flex flex-col gap-3">
          <h1 className="text-display text-balance">Sự cố của gia đình</h1>
          <p className="rounded-card bg-surface-muted p-4 text-body">
            Đây là trợ lý AI HỏiCon. Các sự cố dưới đây do máy phát hiện tự động; anh/chị luôn nên gọi hỏi người thân
            để kiểm tra.
          </p>
        </div>
        <Section
          title="Đang cần chú ý"
          status="open"
          group={groups.open}
          onMore={() => void load("open", groups.open.cursor)}
          onRetry={() => void load("open", groups.open.cursor)}
        />
        <Section
          title="Đã xong"
          status="closed"
          group={groups.closed}
          onMore={() => void load("closed", groups.closed.cursor)}
          onRetry={() => void load("closed", groups.closed.cursor)}
        />
      </main>
    </GuardianShell>
  );
}
