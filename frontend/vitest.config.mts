import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

// Unit tests for pure lib/ helpers (no DOM needed), so the default node environment is enough.
export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL(".", import.meta.url)) },
  },
  test: {
    include: ["**/*.test.ts"],
    exclude: ["node_modules/**", ".next/**"],
  },
});
