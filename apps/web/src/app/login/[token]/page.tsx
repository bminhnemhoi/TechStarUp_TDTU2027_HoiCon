"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useCallback, useEffect, useRef, useState } from "react";
import { BUTTON_PRIMARY, BUTTON_SECONDARY } from "@/components/guardian-ui";
import { ApiError, api, type GuardianSession } from "@/lib/client";

// Đổi token đăng nhập một lần lấy phiên (spec 027, FR-005). Token nằm trên đường dẫn ⇒ THAY URL NGAY bằng `/login` (trước
// khi gọi API) để token không ở lại lịch sử trình duyệt. Token chỉ sống trong bộ nhớ của trang này (không storage).
type Phase = "exchanging" | "gone" | "failed";

export default function LoginTokenPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const router = useRouter();
  const secret = useRef(token);
  const started = useRef(false);
  const [phase, setPhase] = useState<Phase>("exchanging");
  const [message, setMessage] = useState("");

  const exchange = useCallback(async () => {
    setPhase("exchanging");
    try {
      await api<GuardianSession>("/v1/guardian/session", { method: "POST", body: JSON.stringify({ token: secret.current }) });
      secret.current = ""; // đã đổi xong: không giữ token nữa
      router.replace("/incidents");
    } catch (error) {
      if (error instanceof ApiError && (error.status === 410 || error.status === 422)) {
        secret.current = "";
        setPhase("gone");
      } else {
        setMessage(error instanceof ApiError ? error.message : "Không kết nối được. Anh/chị kiểm tra mạng rồi thử lại.");
        setPhase("failed");
      }
    }
  }, [router]);

  useEffect(() => {
    if (started.current) return; // chế độ dev chạy effect hai lần: chỉ đổi token MỘT lần
    started.current = true;
    window.history.replaceState(null, "", "/login");
    void exchange();
  }, [exchange]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-lg flex-col justify-center gap-6 px-4 py-8 text-foreground">
      {phase === "exchanging" && (
        <p role="status" className="text-title">
          Đây là trợ lý AI HỏiCon. Đang đăng nhập…
        </p>
      )}
      {phase === "gone" && (
        <div role="alert" className="flex flex-col gap-3 rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-5 text-risk-medium-fg">
          <h1 className="text-title">Liên kết đăng nhập không dùng được</h1>
          <p className="text-body">Đây là trợ lý AI HỏiCon.</p>
          <ul className="list-disc pl-6 text-body">
            <li>Liên kết có thể đã được mở rồi (mỗi liên kết chỉ dùng một lần).</li>
            <li>Liên kết đã quá 15 phút.</li>
            <li>Anh/chị vừa xin liên kết mới hơn (hãy dùng liên kết mới nhất).</li>
          </ul>
          <p className="text-body-large font-bold">Nhắn số 4 cho HỏiCon trên Zalo để nhận liên kết mới.</p>
          <Link href="/login" className={BUTTON_SECONDARY}>
            Xem cách lấy liên kết mới
          </Link>
        </div>
      )}
      {phase === "failed" && (
        <div role="alert" className="flex flex-col gap-3 rounded-card border-2 border-risk-critical-accent bg-risk-critical-bg p-5 text-risk-critical-fg">
          <h1 className="text-title">Chưa đăng nhập được</h1>
          <p className="text-body">Đây là trợ lý AI HỏiCon.</p>
          <p className="text-body">{message}</p>
          <button type="button" onClick={() => void exchange()} className={BUTTON_PRIMARY}>
            Thử lại
          </button>
        </div>
      )}
    </main>
  );
}
