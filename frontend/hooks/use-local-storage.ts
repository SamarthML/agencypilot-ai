"use client";

import { useCallback, useSyncExternalStore } from "react";

import { readStorage, subscribeStorage, writeStorage } from "@/lib/storage";

/**
 * A string-union value persisted in localStorage.
 * Renders `serverValue` (default: `fallback`) on the server and during hydration (no mismatch),
 * then the stored value, or `fallback` when nothing valid is stored. A distinct `serverValue`
 * avoids flashing UI that most returning visitors have hidden, e.g. a dismissed banner.
 * Values not in `allowed` are ignored, so stale or tampered storage can't break the UI.
 */
export function useLocalStorage<T extends string>(
  key: string,
  fallback: T,
  allowed: readonly T[],
  serverValue: T = fallback,
): [T, (value: T) => void] {
  const getSnapshot = (): T => {
    const stored = readStorage(key);
    return stored !== null && (allowed as readonly string[]).includes(stored)
      ? (stored as T)
      : fallback;
  };

  const value = useSyncExternalStore(subscribeStorage, getSnapshot, () => serverValue);
  const setValue = useCallback((next: T) => writeStorage(key, next), [key]);

  return [value, setValue];
}
