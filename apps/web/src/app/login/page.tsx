// Trang /login (không token): chỉ hướng dẫn cách lấy liên kết đăng nhập qua Zalo (spec 027, FR-005).
export default async function LoginPage({ searchParams }: { searchParams: Promise<{ "het-han"?: string }> }) {
  const expired = (await searchParams)["het-han"] === "1";
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-lg flex-col justify-center gap-6 px-4 py-8 text-foreground">
      <h1 className="text-headline text-balance">Đăng nhập HỏiCon</h1>
      {expired && (
        <p role="status" className="rounded-card border-2 border-risk-medium-accent bg-risk-medium-bg p-4 text-body text-risk-medium-fg">
          Phiên đăng nhập đã hết hạn. Anh/chị lấy liên kết mới theo các bước dưới đây.
        </p>
      )}
      <p className="rounded-card bg-surface-muted p-4 text-body">
        Đây là trợ lý AI HỏiCon. Trang này dành cho con cháu nhận cảnh báo trong gia đình. Nếu anh/chị là người cao tuổi
        dùng HỏiCon, anh/chị không cần đăng nhập ở đây.
      </p>
      <p className="text-body-large">HỏiCon không dùng mật khẩu. Anh/chị nhận liên kết đăng nhập qua Zalo:</p>
      <ol className="flex list-decimal flex-col gap-3 pl-6 text-body-large">
        <li>Mở Zalo, vào cuộc trò chuyện với HỏiCon.</li>
        <li>
          Nhắn số <strong>4</strong>.
        </li>
        <li>Bấm vào liên kết HỏiCon gửi lại (dùng một lần, hết hạn sau 15 phút).</li>
      </ol>
      <p className="text-body">
        Chưa nhận được tin? Anh/chị cần là người đã kết nối Zalo với HỏiCon trong gia đình. Nếu chưa, hãy nhờ người cài
        HỏiCon cho người thân gửi mã kết nối mới.
      </p>
    </main>
  );
}
