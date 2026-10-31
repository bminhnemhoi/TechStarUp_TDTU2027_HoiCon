"use client";

import { LEVEL_STYLE } from "@/components/guardian-ui";
import type { Answer } from "@/lib/booth";
import { LEVEL_ICON, LEVEL_VI, aliasName, describeStep, type Level } from "@/lib/steps";
import type { BoothView } from "@/lib/use-booth-runner";

// Ba cột của gian (spec 050, FR-002): điện thoại của bác · trợ lý AI · Zalo của con. Chữ chính ≥ 28 px (`BIG`), câu đang diễn ra 36 px (`XL`);
// mức rủi ro luôn kèm biểu tượng + chữ (luật 15). Băng rôn MÔ PHỎNG và BẢN GHI dùng màu mô phỏng `sim.*` (không dùng màu rủi ro lẫn màu diễn tập).
const BIG = "text-[1.75rem] leading-[2.5rem]";
const XL = "text-[2.25rem] leading-[3rem]";
const ANSWER_VI: Record<Answer, string> = { yes: "Có", no: "Không", unsure: "Chưa chắc" };
const ALIAS = aliasName("Mẹ");
const CARD = "flex flex-col gap-3 rounded-card border-2 border-brand-navy p-5";
const BANNER = "rounded-card border-sim-accent bg-sim-bg font-bold text-sim-fg p-3";
const timeOf = (iso: string) => new Date(iso).toLocaleTimeString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
const REMINDS: Level[] = ["medium", "high", "critical"];

export function BoothStage({ view, recorded, pace }: { view: BoothView; recorded: boolean; pace: "fast" | "normal" }) {
  const run = view.run;
  const level = (run?.level ?? "none") as Level;
  const messages = run?.guardian_messages ?? [];
  const calm = view.decided === "safe";
  const levelNote = calm ? " — cuộc gọi bình thường" : REMINDS.includes(level) ? " — HỏiCon nhắc bác tạm dừng" : "";
  return (
    <div className="flex flex-col gap-4" data-testid="booth-stage" data-pace={pace}>
      <p data-testid="sim-banner" className={`border-4 ${BANNER} ${BIG}`}>
        <span aria-hidden="true">ⓘ </span>MÔ PHỎNG — dữ liệu hư cấu, không có cuộc gọi hay tin Zalo thật. Không có ai bị lừa thật.
      </p>
      {recorded && (
        <p role="status" data-testid="replay-banner" className={`border-4 ${BANNER} ${BIG}`}>
          <span aria-hidden="true">⏺ </span>KHÔNG PHẢI TRỰC TIẾP — đang chiếu lại bản ghi đã lưu trước đó
        </p>
      )}
      <h1 className="text-display" data-testid="booth-title">
        {view.title ?? "Sẵn sàng trình diễn"}
      </h1>
      {run && (
        <p className={`rounded-card border-2 p-3 font-bold ${XL} ${LEVEL_STYLE[level].card}`} data-testid="booth-level">
          <span aria-hidden="true">{LEVEL_ICON[level]} </span>Mức nguy cơ: {LEVEL_VI[level]}
          {levelNote}
        </p>
      )}
      <div className="grid gap-4 min-[1600px]:grid-cols-3">
        <section aria-label="Điện thoại của bác" className={CARD} data-testid="col-elder">
          <h2 className="text-headline">1. Điện thoại của bác</h2>
          {!run && <p className={BIG}>Đang chờ một cuộc gọi lạ…</p>}
          {run?.note && <p className={BIG}>{run.note}</p>}
          {view.question && (
            <p className={XL} data-testid="question">
              {view.question}
            </p>
          )}
          {view.answered && (
            <p className={`font-bold ${BIG}`} data-testid="elder-answer">
              Bác trả lời: {ANSWER_VI[view.answered]}
            </p>
          )}
          {run && !run.note && (
            <p className={BIG}>
              {calm ? "HỏiCon thấy cuộc gọi này bình thường, bác cứ nghe máy nhé." : REMINDS.includes(level) ? "HỏiCon nhắc bác tạm dừng lại và hỏi con trước khi làm gì tiếp." : "HỏiCon đang theo dõi cuộc gọi."}
            </p>
          )}
        </section>
        <section aria-label="Trợ lý AI" className={CARD} data-testid="col-ai">
          <h2 className="text-headline">2. Trợ lý AI đang làm gì</h2>
          {view.steps.length === 0 && <p className={BIG}>Trợ lý AI đang xem xét cuộc gọi…</p>}
          <ol className="flex flex-col gap-3" data-testid="steps">
            {view.steps.map((step) => (
              <li key={step.id} className={BIG}>
                {describeStep(step, ALIAS).title}
              </li>
            ))}
          </ol>
        </section>
        <section aria-label="Zalo của con (mô phỏng)" className={CARD} data-testid="col-guardian">
          <h2 className="text-headline">3. Zalo của con (mô phỏng)</h2>
          <p className={BIG}>Tin con của bác nhận được:</p>
          {messages.length === 0 && <p className={BIG}>Chưa có tin nào gửi cho con.</p>}
          <ol className="flex flex-col gap-3" data-testid="messages">
            {messages.map((m, index) => (
              <li key={m.at + m.template} className={index === messages.length - 1 ? XL : BIG}>
                <span className="font-bold">{timeOf(m.at)}</span> {m.text}
              </li>
            ))}
          </ol>
          {view.decided && (
            <p role="status" className={`rounded-card border-2 border-brand-navy p-3 font-bold ${BIG}`} data-testid="decision">
              {view.decided === "safe"
                ? "✓ Con đã hỏi thăm bác: cuộc gọi này an toàn."
                : "⏸ Con đã gọi cho bác. Cả hai thấy đây có thể là lừa đảo, nên bác tạm dừng, chưa chuyển tiền."}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
