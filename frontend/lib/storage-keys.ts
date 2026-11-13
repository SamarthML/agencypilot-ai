/** localStorage keys, namespaced so they never collide with other apps on localhost. */
export const STORAGE_KEYS = {
  provider: "ap.provider",
  client: "ap.client",
  sidebar: "ap.sidebar",
} as const;
