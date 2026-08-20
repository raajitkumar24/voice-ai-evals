import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    const api = process.env.VOICE_EVALS_API_INTERNAL_URL ?? "http://localhost:8000";
    return [{source: "/api/:path*", destination: `${api}/api/:path*`}];
  },
};

export default nextConfig;
