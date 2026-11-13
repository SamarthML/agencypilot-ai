import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
