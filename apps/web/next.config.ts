import type { NextConfig } from "next";

// Trình duyệt gọi API cùng nguồn (`/v1/*`), Next chuyển tiếp tới FastAPI ⇒ không cần CORS và token `/a/[token]`
// không đi qua máy chủ nào khác. Dev: API cổng 18000 (CLAUDE.md); prod đặt HOICON_API_URL lúc build.
const apiUrl = process.env.HOICON_API_URL ?? "http://127.0.0.1:18000";

// Trang có token đăng nhập một lần: không gửi Referer đi nơi khác, không cho máy tìm kiếm lập chỉ mục (spec 027, SC-003).
// Trang sự cố là dữ liệu gia đình: cùng chính sách. Đặt ở tiêu đề phản hồi, ngoài <meta> trong layout.
const privateHeaders = [
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Robots-Tag", value: "noindex, nofollow" },
  { key: "Cache-Control", value: "no-store" },
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      { source: "/login/:path*", headers: privateHeaders },
      { source: "/incidents/:path*", headers: privateHeaders },
      { source: "/trace/:path*", headers: privateHeaders },
      { source: "/sim/:path*", headers: privateHeaders },
      { source: "/sim", headers: privateHeaders },
      { source: "/eval", headers: privateHeaders },
      { source: "/drills", headers: privateHeaders },
      { source: "/a/:path*", headers: privateHeaders }, // trang hành động có token trong URL (rà soát 037 T009 #10)
    ];
  },
  async rewrites() {
    return [{ source: "/v1/:path*", destination: `${apiUrl}/v1/:path*` }];
  },
};

export default nextConfig;
