import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server for the Docker image (frontend/Dockerfile); Vercel ignores it.
  output: "standalone",
  // Keep the dev-mode "N" badge clear of the sidebar's Collapse button.
  devIndicators: { position: "bottom-right" },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
