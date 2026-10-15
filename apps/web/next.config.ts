import type { NextConfig } from "next";

// Trình duyệt gọi API cùng nguồn (`/v1/*`), Next chuyển tiếp tới FastAPI ⇒ không cần CORS và token `/a/[token]`
// không đi qua máy chủ nào khác. Dev: API cổng 18000 (CLAUDE.md); prod đặt HOICON_API_URL lúc build.
const apiUrl = process.env.HOICON_API_URL ?? "http://127.0.0.1:18000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/v1/:path*", destination: `${apiUrl}/v1/:path*` }];
  },
};

export default nextConfig;
