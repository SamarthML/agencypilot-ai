/**
 * Cold-start warm-up. Free hosting sleeps the API after ~15 idle minutes and takes 30-60 s to
 * wake, so on first load we poll /health once and hold every API request until it answers.
 * This shows one friendly banner instead of a burst of timeout toasts.
 */

export type WarmupPhase = "checking" | "waking" | "ready" | "failed";

export interface WarmupTiming {
  /** Show the "waking up" banner if the first answer takes longer than this. */
  wakingAfterMs: number;
  /** Per-attempt timeout, and the pause between failed attempts. */
  attemptTimeoutMs: number;
  retryEveryMs: number;
  /** Stop polling and report failure after this long (requests then fail normally). */
  giveUpAfterMs: number;
}

export const DEFAULT_TIMING: WarmupTiming = {
  wakingAfterMs: 1_500,
  attemptTimeoutMs: 10_000,
  retryEveryMs: 3_000,
  giveUpAfterMs: 120_000,
};

/** One health probe: resolves true when the API answered, false (never throws) otherwise. */
export type HealthCheck = (timeoutMs: number) => Promise<boolean>;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Poll `check` until it succeeds or time runs out, reporting each phase change. */
export async function runWarmup(
  check: HealthCheck,
  onPhase: (phase: WarmupPhase) => void,
  timing: WarmupTiming = DEFAULT_TIMING,
): Promise<boolean> {
  const started = Date.now();
  let settled = false;
  const wakingTimer = setTimeout(() => !settled && onPhase("waking"), timing.wakingAfterMs);
  try {
    while (Date.now() - started < timing.giveUpAfterMs) {
      if (await check(timing.attemptTimeoutMs)) {
        settled = true;
        onPhase("ready");
        return true;
      }
      await sleep(timing.retryEveryMs);
    }
    settled = true;
    onPhase("failed");
    return false;
  } finally {
    clearTimeout(wakingTimer);
  }
}

export interface Warmup {
  /** Resolves once the API answered or warm-up gave up; never rejects. */
  ready: () => Promise<void>;
  retry: () => void;
  subscribe: (listener: () => void) => () => void;
  getPhase: () => WarmupPhase;
}

/** A process-wide warm-up store (useSyncExternalStore-compatible). Server-side it's a no-op. */
export function createWarmup(check: HealthCheck, timing: WarmupTiming = DEFAULT_TIMING): Warmup {
  let phase: WarmupPhase = "checking";
  let pending: Promise<void> | null = null;
  const listeners = new Set<() => void>();

  const setPhase = (next: WarmupPhase) => {
    phase = next;
    listeners.forEach((listener) => listener());
  };
  const ready = () => {
    if (typeof window === "undefined") return Promise.resolve();
    pending ??= runWarmup(check, setPhase, timing).then(() => undefined);
    return pending;
  };

  return {
    ready,
    retry: () => {
      pending = null;
      setPhase("checking");
      void ready();
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    getPhase: () => phase,
  };
}
