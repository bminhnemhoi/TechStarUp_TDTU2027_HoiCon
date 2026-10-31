import type { Metadata } from "next";

// `/login/<token>` chứa token đăng nhập một lần: không để trình duyệt gửi nó qua Referer, không cho máy tìm kiếm lập
// chỉ mục (cùng với tiêu đề `Referrer-Policy`/`X-Robots-Tag` đặt trong next.config.ts).
export const metadata: Metadata = {
  title: "Đăng nhập HỏiCon",
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function LoginLayout({ children }: LayoutProps<"/login">) {
  return children;
}
