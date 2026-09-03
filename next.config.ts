import type { NextConfig } from "next";

const isGitHubPages = process.env.GITHUB_PAGES === "true";
const repoName = "AUTOMINDS-AFRICA-BID-FINDER";
const basePath = isGitHubPages ? `/${repoName}` : "";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  output: isGitHubPages ? "export" : undefined,
  trailingSlash: isGitHubPages,
  basePath,
  assetPrefix: basePath,
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

export default nextConfig;
