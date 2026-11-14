import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { runWarmup, type WarmupPhase, type WarmupTiming } from "@/lib/warmup";

const TIMING: WarmupTiming = {
  wakingAfterMs: 1_000,
  attemptTimeoutMs: 5_000,
  retryEveryMs: 2_000,
  giveUpAfterMs: 10_000,
};

/** A health check that fails `failures` times (each taking `latencyMs`), then succeeds. */
function flakyCheck(failures: number, latencyMs = 100) {
  let calls = 0;
  const check = vi.fn(
    () =>
      new Promise<boolean>((resolve) => {
        calls += 1;
        setTimeout(() => resolve(calls > failures), latencyMs);
      }),
  );
  return check;
}

describe("runWarmup", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("goes straight to ready when the API answers quickly (no banner)", async () => {
    const phases: WarmupPhase[] = [];
    const result = runWarmup(flakyCheck(0), (p) => phases.push(p), TIMING);

    await vi.runAllTimersAsync();

    expect(await result).toBe(true);
    expect(phases).toEqual(["ready"]);
  });

  it("shows waking while the API cold-starts, then ready", async () => {
    const phases: WarmupPhase[] = [];
    const check = flakyCheck(2);
    const result = runWarmup(check, (p) => phases.push(p), TIMING);

    await vi.runAllTimersAsync();

    expect(await result).toBe(true);
    expect(phases).toEqual(["waking", "ready"]);
    expect(check).toHaveBeenCalledTimes(3);
    expect(check).toHaveBeenCalledWith(TIMING.attemptTimeoutMs);
  });

  it("gives up after giveUpAfterMs and reports failed", async () => {
    const phases: WarmupPhase[] = [];
    const result = runWarmup(flakyCheck(Infinity), (p) => phases.push(p), TIMING);

    await vi.runAllTimersAsync();

    expect(await result).toBe(false);
    expect(phases).toEqual(["waking", "failed"]);
  });
});
