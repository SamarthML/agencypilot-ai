"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * One-shot "do this when you mount" requests from the command palette, e.g. "New SEO audit"
 * navigates to /seo and asks the URL field to focus itself.
 *
 * A tiny external store instead of URL params: search params would suspend these pages under
 * Cache Components, and the request must not survive a reload or be shareable as a link.
 */
export type CommandIntent = "seo:new-audit" | "reports:new" | "copilot:ask";

let pending: CommandIntent | null = null;
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function requestIntent(intent: CommandIntent): void {
  pending = intent;
  notify();
}

export function clearIntent(intent: CommandIntent): void {
  if (pending !== intent) return;
  pending = null;
  notify();
}

/** Whether `intent` is waiting to be handled, plus a callback to mark it handled. */
export function useIntent(intent: CommandIntent): [requested: boolean, done: () => void] {
  const requested = useSyncExternalStore(
    subscribe,
    () => pending === intent,
    () => false,
  );
  const done = useCallback(() => clearIntent(intent), [intent]);
  return [requested, done];
}
