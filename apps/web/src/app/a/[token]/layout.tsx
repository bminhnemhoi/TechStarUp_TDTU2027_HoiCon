import type { Metadata } from "next";

// URL chứa token một lần: không để trình duyệt gửi nó qua Referer, không cho máy tìm kiếm lập chỉ mục.
export const metadata: Metadata = {
  title: "Cảnh báo HỏiCon",
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function ActionLayout({ children }: LayoutProps<"/a/[token]">) {
  return children;
}
