/** Safe localStorage access. Every call tolerates SSR and blocked storage. */

export const STORAGE_CHANGE_EVENT = "ap:local-storage";

export function readStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage can be unavailable (private mode, blocked site data); state still updates in memory.
  }
  window.dispatchEvent(new CustomEvent(STORAGE_CHANGE_EVENT, { detail: key }));
}

/** Subscribe to changes from this tab (custom event) and other tabs (storage event). */
export function subscribeStorage(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  window.addEventListener(STORAGE_CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(STORAGE_CHANGE_EVENT, onChange);
  };
}
