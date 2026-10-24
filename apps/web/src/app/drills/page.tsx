"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { BUTTON_PRIMARY, DrillTag, ErrorBox, GuardianShell, Icon, LINK_TOUCH, useLoginRedirect } from "@/components/guardian-ui";
import { ApiError, api, errorMessage, type GuardianDrill, type GuardianDrillList, type GuardianIncidentList } from "@/lib/client";
import { DRILL_DURATIONS, DRILL_REFUSAL_VI, DRILL_SCRIPTS, DRILL_STATUS_VI } from "@/lib/drills";
import { aliasName } from "@/lib/steps";

// Diễn tập cho người nhà (spec 028, FR-011): đặt lịch một bài và xem lịch sử. Bài diễn tập là cuộc gọi GIẢ do HỏiCon tổ chức,
// luôn có nhãn [DIỄN TẬP] và màu diễn tập riêng (drill.*). Thân gửi đi chỉ có 4 trường (không văn bản tự do).
// Người nhận lấy từ danh sách sự cố của gia đình (hợp đồng chưa có danh sách thành viên).
interface Elder {
  id: string;
  alias: string;
}

const VN_DAY = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric" });
const VN_HOUR = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit" });
/** "14:00 đến 16:00, ngày 02/11/2026"; qua nửa đêm thì ghi đủ ngày hai đầu. */
function whenRange(start: string, end: string): string {
  const [a, b] = [new Date(start), new Date(end)];
  return VN_DAY.format(a) === VN_DAY.format(b)
    ? `${VN_HOUR.format(a)} đến ${VN_HOUR.format(b)}, ngày ${VN_DAY.format(a)}`
    : `${VN_HOUR.format(a)} ngày ${VN_DAY.format(a)} đến ${VN_HOUR.format(b)} ngày ${VN_DAY.format(b)}`;
}

/** "2030-01-15T14:00" (giờ Việt Nam, từ ô nhập) + số phút ⇒ cặp thời điểm có múi giờ +07:00. */
function windowOf(local: string, minutes: number): { window_start: string; window_end: string } | null {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(local)) return null;
  const start = new Date(`${local}:00+07:00`);
  if (Number.isNaN(start.getTime())) return null;
  const end = new Date(start.getTime() + minutes * 60_000);
  const vn = new Date(end.getTime() + 7 * 3_600_000).toISOString().slice(0, 16);
  return { window_start: `${local}:00+07:00`, window_end: `${vn}:00+07:00` };
}

function DrillItem({ drill }: { drill: GuardianDrill }) {
  const status = DRILL_STATUS_VI[drill.status] ?? { icon: "…", text: "Đang cập nhật trạng thái" };
  return (
    <li className="flex flex-col gap-2 rounded-card border-2 border-drill-accent bg-drill-bg p-4 text-drill-fg">
      <span className="flex flex-wrap items-center gap-2">
        <DrillTag />
        <h3 className="text-title">{drill.script_title}</h3>
      </span>
      <span className="text-body">
        Cho {aliasName(drill.member_alias, true)} · {whenRange(drill.window_start, drill.window_end)}
      </span>
      <span className="text-body font-bold">
        <Icon>{status.icon}</Icon>
        {status.text}
        {drill.score !== null && drill.score !== undefined ? ` · Làm đúng ${drill.score}/5 bước` : ""}
      </span>
    </li>
  );
}

export default function DrillsPage() {
  const redirectIfUnauthorized = useLoginRedirect();
  const [drills, setDrills] = useState<GuardianDrill[] | null>(null);
  const [elders, setElders] = useState<Elder[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [memberId, setMemberId] = useState("");
  const [scriptId, setScriptId] = useState(DRILL_SCRIPTS[0].id);
  const [start, setStart] = useState("");
  const [minutes, setMinutes] = useState(60);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const started = useRef(false);

  const load = useCallback(async () => {
    try {
      const [list, open, closed] = await Promise.allSettled([
        api<GuardianDrillList>("/v1/guardian/drills"),
        api<GuardianIncidentList>("/v1/guardian/incidents?status=open"),
        api<GuardianIncidentList>("/v1/guardian/incidents?status=closed"),
      ]);
      if (list.status === "rejected") throw list.reason; // thiếu danh sách người nhận thì vẫn xem được lịch sử
      const seen = new Map<string, string>();
      const incidents = [open, closed].flatMap((r) => (r.status === "fulfilled" ? r.value.incidents : []));
      for (const i of incidents) if (!seen.has(i.member_id)) seen.set(i.member_id, aliasName(i.elder_alias, true));
      const found = [...seen].map(([id, alias]) => ({ id, alias }));
      setDrills(list.value.drills);
      setElders(found);
      setMemberId((current) => current || found[0]?.id || "");
      setLoadError(null);
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      setLoadError(errorMessage(error));
    }
  }, [redirectIfUnauthorized]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void load();
  }, [load]);

  const [minStart] = useState(() => new Date(Date.now() + 7 * 3_600_000).toISOString().slice(0, 16));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setProblem(null);
    setDone(null);
    const window = windowOf(start, minutes);
    if (!memberId) {
      setProblem("Anh/chị chọn người nhận trước khi đặt lịch.");
      return;
    }
    if (!window) {
      setProblem("Anh/chị chọn giờ bắt đầu trước khi đặt lịch.");
      document.getElementById("drill-start")?.focus();
      return;
    }
    setBusy(true);
    try {
      const created = await api<GuardianDrillList>("/v1/guardian/drills", {
        method: "POST",
        body: JSON.stringify({ member_id: memberId, script_id: scriptId, ...window }),
      });
      setDrills((current) => [...created.drills, ...(current ?? [])]);
      setDone("Đã đặt lịch diễn tập. Đến giờ, HỏiCon sẽ mời người nhận làm bài và báo kết quả cho anh/chị.");
    } catch (error) {
      if (redirectIfUnauthorized(error)) return;
      setProblem(error instanceof ApiError && error.code ? (DRILL_REFUSAL_VI[error.code] ?? errorMessage(error)) : errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  const noElders = elders !== null && elders.length === 0;
  const picked = windowOf(start, minutes);
  const field = "min-h-16 rounded-button border-2 border-brand-navy bg-background px-3 text-body";

  let body;
  if (loadError) {
    body = (
      <ErrorBox title="Chưa tải được diễn tập" onRetry={() => void load()}>
        {loadError}
      </ErrorBox>
    );
  } else if (!drills || !elders) {
    body = (
      <p role="status" className="text-body">
        Đang tải…
      </p>
    );
  } else {
    body = (
      <>
        {noElders ? (
          <p className="rounded-card border-2 border-brand-navy p-4 text-body-large" data-testid="no-elders">
            Chưa có người thân nào dùng HỏiCon để diễn tập. Anh/chị mời người thân cài ứng dụng rồi quay lại nhé.
          </p>
        ) : (
        <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4" aria-label="Đặt lịch diễn tập">
          <h2 className="text-title">Đặt lịch một bài diễn tập</h2>
          <label htmlFor="drill-member" className="text-body font-bold">
            Người nhận diễn tập
          </label>
          <select id="drill-member" className={field} value={memberId} onChange={(e) => setMemberId(e.target.value)} >
            {elders.map((e) => (
              <option key={e.id} value={e.id}>
                {e.alias}
              </option>
            ))}
          </select>
          <label htmlFor="drill-script" className="text-body font-bold">
            Kịch bản
          </label>
          <select id="drill-script" className={field} value={scriptId} onChange={(e) => setScriptId(e.target.value)}>
            {DRILL_SCRIPTS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
          <label htmlFor="drill-start" className="text-body font-bold">
            Bắt đầu lúc (giờ Việt Nam)
          </label>
          <input id="drill-start" type="datetime-local" className={field} value={start} min={minStart} onChange={(e) => setStart(e.target.value)} />
          <label htmlFor="drill-length" className="text-body font-bold">
            Kéo dài
          </label>
          <select id="drill-length" className={field} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
            {DRILL_DURATIONS.map((d) => (
              <option key={d.minutes} value={d.minutes}>
                {d.label}
              </option>
            ))}
          </select>
          {picked && (
            <p className="text-body font-bold" data-testid="picked-time">
              Sẽ diễn ra {whenRange(picked.window_start, picked.window_end)} (giờ Việt Nam).
            </p>
          )}
          <p className="text-body">Trong khoảng giờ này, người nhận có thể làm bài bất cứ lúc nào. Bài luôn được nói rõ là diễn tập.</p>
          {problem && (
            <p role="alert" className="rounded-card border-2 border-brand-navy bg-surface-muted p-4 text-body font-bold">
              <Icon>!</Icon>
              {problem}
            </p>
          )}
          {done && (
            <p role="status" className="rounded-card border-2 border-brand-navy p-4 text-body font-bold">
              <Icon>✓</Icon>
              {done}
            </p>
          )}
          <button type="submit" disabled={busy} className={BUTTON_PRIMARY}>
            {busy ? "Đang đặt lịch…" : "Đặt lịch diễn tập"}
          </button>
        </form>
        )}

        <section aria-labelledby="history-title" className="flex flex-col gap-3">
          <h2 id="history-title" className="text-title">
            Lịch và lịch sử
          </h2>
          {drills.length === 0 ? (
            <p className="text-body-large">Chưa có bài diễn tập nào. Anh/chị đặt lịch bài đầu tiên ở trên.</p>
          ) : (
            <ul className="flex flex-col gap-3" data-testid="drill-list">
              {drills.map((d) => (
                <DrillItem key={d.drill_id} drill={d} />
              ))}
            </ul>
          )}
        </section>
      </>
    );
  }

  return (
    <GuardianShell>
      <main className="flex flex-col gap-5">
        <h1 className="text-display text-balance">Diễn tập cho người nhà</h1>
        <p className="flex flex-wrap items-center gap-2 rounded-card border-2 border-drill-accent bg-drill-bg p-4 text-body text-drill-fg">
          <DrillTag />
          <span>
            Đây là trợ lý AI HỏiCon. Diễn tập là cuộc gọi giả để người thân luyện nhận biết lừa đảo. Không ai bị lừa thật và HỏiCon luôn nói rõ đây là diễn tập.
          </span>
        </p>
        {body}
        <Link href="/incidents" className={`${LINK_TOUCH} min-h-16 self-start`}>
          ← Về danh sách sự cố
        </Link>
      </main>
    </GuardianShell>
  );
}
