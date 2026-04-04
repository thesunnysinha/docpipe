import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@mui/material", "@mui/icons-material"],
};

export default nextConfig;
