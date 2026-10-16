import type { Metadata } from "next";

// Dữ liệu của gia đình: không cho máy tìm kiếm lập chỉ mục, không gửi Referer đi nơi khác.
export const metadata: Metadata = {
  title: "Sự cố của gia đình — HỏiCon",
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function IncidentsLayout({ children }: LayoutProps<"/incidents">) {
  return children;
}
