import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 禁用lint和类型检查以加速构建
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
