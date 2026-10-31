"use client";

import { useSyncExternalStore } from "react";
import { BoothStage } from "@/components/booth-columns";
import { ErrorBox, useLoginRedirect } from "@/components/guardian-ui";
import { useBoothRunner } from "@/lib/use-booth-runner";

// Màn hình gian trưng bày (spec 050, FR-002): tự chạy danh sách phát qua `/v1/sim/*`; mất mạng thì phát lại bản ghi, có băng rôn.
// `?fast=1` rút các nhịp dừng nhưng CHỈ khi NODE_ENV !== "production" (dev); bản build prod bỏ qua tham số này để khách gõ
// nhầm không làm hỏng buổi trình diễn. Test e2e (chạy trên bản build) bật nhịp nhanh bằng `window.__HOICON_BOOTH_FAST__`.
// `?autoplay=0` chờ lệnh từ /demo/console.

function Kiosk({ fast, autoplay }: { fast: boolean; autoplay: boolean }) {
  const redirectIfUnauthorized = useLoginRedirect();
  const { view, playing, offline, busy, closed, error } = useBoothRunner({ fast, autoplay, handleUnauthorized: redirectIfUnauthorized });
  const recorded = playing === "recording";

  if (closed) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-4 p-6">
        <ErrorBox title="Trang này chưa mở">Chức năng mô phỏng chưa được bật trên máy chủ này. Anh/chị nhờ người quản trị bật giúp.</ErrorBox>
      </main>
    );
  }
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[120rem] flex-col gap-4 px-6 py-6 text-foreground">
      <BoothStage view={view} recorded={recorded} pace={fast ? "fast" : "normal"} />
      <p role="status" data-testid="booth-state" className="text-[1.75rem] leading-[2.5rem]">
        {error ? "Màn hình gian tạm dừng. Nhờ người điều khiển bấm chạy lại." : offline ? "Đang chiếu lại bản ghi đã lưu sẵn." : busy ? "Đang trình diễn…" : "Đang nghỉ giữa hai lượt."}
      </p>
    </main>
  );
}

const subscribe = () => () => {};

export default function BoothPage() {
  // Chuỗi truy vấn đọc ở client (null khi dựng trên máy chủ ⇒ không lệch khi hydrate).
  const search = useSyncExternalStore(subscribe, () => window.location.search, () => null);
  if (search === null) {
    return (
      <p role="status" className="p-6 text-body">
        Đang mở màn hình gian…
      </p>
    );
  }
  const q = new URLSearchParams(search);
  const hooked = (window as unknown as { __HOICON_BOOTH_FAST__?: boolean }).__HOICON_BOOTH_FAST__ === true;
  const fast = hooked || (q.get("fast") === "1" && process.env.NODE_ENV !== "production");
  return <Kiosk fast={fast} autoplay={q.get("autoplay") !== "0"} />;
}
