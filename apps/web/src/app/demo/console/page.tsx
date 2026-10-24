"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BUTTON_PRIMARY, BUTTON_SECONDARY } from "@/components/guardian-ui";
import {
  ALERT_LIMIT_MS,
  CHANNEL,
  PLAYLIST,
  recordingProblems,
  type BoothMode,
  type BoothResult,
  type ChannelMessage,
  type Recording,
} from "@/lib/booth";

// Bảng điều khiển gian (spec 050, FR-004): điều khiển màn hình /booth ở cùng trình duyệt qua BroadcastChannel (không gọi API,
// không lưu gì). Bảng lượt gần đây + bộ đếm "đạt liên tiếp" cho kiểm tra tốc độ cảnh báo chỉ là tiện ích của người điều khiển: bằng chứng chính thức
// ghi vào evidence.md. Đo ở trình duyệt này, máy này, chạy phát lại — không phải số ở hội trường.
const RESET_CMD = "uv run --directory backend python -m hoicon.ops.booth reset --confirm-demo";
const MODE_VI: Record<BoothMode, string> = { live: "Trực tiếp", recording: "Bản ghi" };
const STOP = "flex min-h-16 w-full items-center justify-center rounded-button border-4 border-risk-critical-accent bg-risk-critical-bg px-6 text-title font-bold text-risk-critical-fg";

function download(recording: Recording) {
  const blob = new Blob([JSON.stringify(recording, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${recording.scenario_id}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export default function ConsolePage() {
  const channel = useRef<BroadcastChannel | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<{ offline: boolean; busy: boolean } | null>(null);
  const [mode, setMode] = useState<BoothMode | "auto">("auto");
  const [results, setResults] = useState<BoothResult[]>([]);
  const [recordings, setRecordings] = useState<Record<string, Recording>>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const heard = useRef(0);

  useEffect(() => {
    const ch = new BroadcastChannel(CHANNEL);
    channel.current = ch;
    ch.onmessage = (event: MessageEvent<ChannelMessage>) => {
      const m = event.data;
      if (m.type === "status") {
        heard.current = Date.now();
        setConnected(true);
        setStatus({ offline: m.offline, busy: m.busy });
      } else if (m.type === "result") setResults((r) => [m.result, ...r].slice(0, 12));
      else if (m.type === "recording") {
        // Chỉ nhận bản ghi hợp lệ của kịch bản trong danh sách phát (kênh cùng nguồn nhưng không tin nội dung).
        const known = PLAYLIST.some((p) => p.scenarioId === m.recording?.scenario_id);
        if (known && recordingProblems(m.recording).length === 0) setRecordings((r) => ({ ...r, [m.recording.scenario_id]: m.recording }));
      }
    };
    const watchdog = window.setInterval(() => {
      if (Date.now() - heard.current > 5000) setConnected(false);
    }, 1000);
    return () => {
      window.clearInterval(watchdog);
      ch.close();
    };
  }, []);

  const send = useCallback((message: ChannelMessage) => channel.current?.postMessage(message), []);

  // Đạt liên tiếp: các lượt TRỰC TIẾP gần nhất, mới → cũ, dừng ở lượt không đạt.
  let streak = 0;
  for (const r of results.filter((x) => x.mode === "live")) {
    if (!r.ok) break;
    streak += 1;
  }
  const disabled = !connected;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-5 p-4 text-foreground">
      <h1 className="text-headline">Bảng điều khiển gian</h1>
      <p className="rounded-card border-4 border-sim-accent bg-sim-bg p-3 text-body font-bold text-sim-fg">
        <span aria-hidden="true">ⓘ </span>MÔ PHỎNG — dữ liệu hư cấu. Số đo ở đây là ở trình duyệt này, máy này, chạy bằng bản ghi sẵn; không phải số ở hội trường.
      </p>

      <p role="status" data-testid="booth-state" className="rounded-card border-2 border-brand-navy p-3 text-title font-bold">
        {!connected ? "● Chưa có màn hình gian" : status?.busy ? "▶ Đang chạy" : "● Sẵn sàng"}
      </p>

      <section aria-label="Kết nối" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4">
        <p role="status" data-testid="booth-link" className="text-body font-bold">
          {connected ? "✓ Màn hình gian đã kết nối" : "✕ Chưa thấy màn hình gian"}
          {connected && status?.offline ? " · mất mạng, đang dùng bản ghi" : ""}
        </p>
        {!connected && (
          <p className="text-body" data-testid="link-help">
            Bấm &quot;Mở màn hình gian&quot; rồi dùng cùng trình duyệt này (cùng máy). Màn hình ở máy khác sẽ không nhận lệnh.
          </p>
        )}
        <a href="/booth" target="_blank" rel="noreferrer" className={BUTTON_SECONDARY}>
          Mở màn hình gian (tab mới)
        </a>
        <fieldset className="flex flex-col gap-2">
          <legend className="text-body font-bold">Chế độ</legend>
          <div className="flex flex-wrap gap-3">
            {(["auto", "recording"] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={mode === value}
                onClick={() => {
                  setMode(value);
                  send({ type: "cmd", cmd: "mode", mode: value });
                }}
                className={`${mode === value ? BUTTON_PRIMARY : BUTTON_SECONDARY} flex-1`}
              >
                {value === "auto" ? "Trực tiếp" : "Dùng bản ghi"}
              </button>
            ))}
          </div>
          <p className="text-body">Trực tiếp tự chuyển sang bản ghi khi mất mạng. Dùng bản ghi thì không gọi máy chủ.</p>
        </fieldset>
      </section>

      <section aria-label="Chạy" className="flex flex-col gap-4 rounded-card border-2 border-brand-navy p-4">
        <h2 className="text-title">Chạy kịch bản</h2>
        <button type="button" className={STOP} onClick={() => send({ type: "cmd", cmd: "stop" })}>
          ⏹ Dừng ngay màn hình gian
        </button>
        <button type="button" disabled={disabled} className={`${BUTTON_PRIMARY} disabled:opacity-50`} onClick={() => send({ type: "cmd", cmd: "playlist" })}>
          Chạy cả danh sách (lặp lại)
        </button>
        {PLAYLIST.map((item) => (
          <button
            key={item.scenarioId}
            type="button"
            disabled={disabled}
            className={`${BUTTON_SECONDARY} disabled:opacity-50`}
            onClick={() => send({ type: "cmd", cmd: "start", scenarioId: item.scenarioId })}
          >
            Chạy: {item.title}
          </button>
        ))}
        {disabled && <p className="text-body font-bold">Chưa gửi được lệnh vì chưa có màn hình gian.</p>}
      </section>

      <section aria-label="Đặt lại" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4">
        <h2 className="text-title">Đặt lại cho khách mới</h2>
        <button
          type="button"
          className={BUTTON_SECONDARY}
          onClick={() => {
            send({ type: "cmd", cmd: "reset" });
            setNotice("Đã dừng và xóa màn hình gian. Bảng kết quả bên dưới vẫn được giữ.");
          }}
        >
          Đặt lại cho khách mới
        </button>
        {notice && (
          <p role="status" data-testid="reset-note" className="text-body">
            {notice}
          </p>
        )}
        <details className="text-body">
          <summary className="min-h-16 cursor-pointer font-bold">Dành cho kỹ thuật viên: xóa cả dữ liệu mô phỏng trên máy chủ</summary>
          <p className="py-2">Chạy lệnh này (dưới 30 giây), sau khi đã dừng màn hình gian:</p>
          <code data-testid="reset-command" tabIndex={0} className="block overflow-x-auto rounded-card bg-risk-low-bg p-3">
            {RESET_CMD}
          </code>
        </details>
      </section>

      <section aria-label="Kết quả" className="flex flex-col gap-3 rounded-card border-2 border-brand-navy p-4">
        <h2 className="text-title">Kiểm tra tốc độ cảnh báo (phải dưới {ALERT_LIMIT_MS / 1000} giây)</h2>
        <p className="text-body font-bold" data-testid="streak">
          Đạt liên tiếp: {streak}/3 {streak >= 3 ? "— ĐẠT ở máy này ✓" : ""}
        </p>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Bảng kết quả (cuộn ngang được)">
          <table className="w-full min-w-[32rem] text-left text-body" data-testid="results">
            <thead>
              <tr>
                <th scope="col">Kịch bản</th>
                <th scope="col">Chế độ</th>
                <th scope="col">Cảnh báo sau (ms)</th>
                <th scope="col">Kết quả</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.at}>
                  <td>{PLAYLIST.find((p) => p.scenarioId === r.scenarioId)?.title ?? r.scenarioId}</td>
                  <td>{MODE_VI[r.mode]}</td>
                  <td>{r.tAlertMs ?? "—"}</td>
                  <td>{r.mode === "recording" ? "bản ghi (không tính)" : r.ok ? "✓ đạt" : "✕ không đạt"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {results.length > 0 &&
          (clearing ? (
            <div className="flex flex-wrap gap-3" role="alert">
              <p className="text-body font-bold">Xóa cả bảng kết quả? Bằng chứng đã đo sẽ mất.</p>
              <button type="button" className={BUTTON_PRIMARY} onClick={() => { setResults([]); setClearing(false); }}>
                Xóa bảng
              </button>
              <button type="button" className={BUTTON_SECONDARY} onClick={() => setClearing(false)}>
                Giữ lại
              </button>
            </div>
          ) : (
            <button type="button" className={BUTTON_SECONDARY} onClick={() => setClearing(true)}>
              Xóa bảng kết quả…
            </button>
          ))}
        {Object.values(recordings).map((rec) => (
          <button key={rec.scenario_id} type="button" className={BUTTON_SECONDARY} onClick={() => download(rec)}>
            Tải bản ghi: {PLAYLIST.find((p) => p.scenarioId === rec.scenario_id)?.title ?? rec.scenario_id}
          </button>
        ))}
      </section>
    </main>
  );
}
