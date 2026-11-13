/** localStorage keys, namespaced so they never collide with other apps on localhost. */
export const STORAGE_KEYS = {
  provider: "ap.provider",
  client: "ap.client",
  sidebar: "ap.sidebar",
  insightsDays: "ap.insights.days",
} as const;
