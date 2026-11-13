"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";

import { ApiError, isAbortError } from "@/lib/api";

interface Settled<T> {
  key: string;
  data?: T;
  error?: ApiError;
}

export interface ApiState<T> {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  reload: () => void;
}

/**
 * Fetch `key` with `fetcher`, cancelling the previous request when the key changes.
 * State only changes when a request settles; `loading` is derived (no setState in effect bodies).
 */
export function useApi<T>(key: string, fetcher: (signal: AbortSignal) => Promise<T>): ApiState<T> {
  const [settled, setSettled] = useState<Settled<T>>();
  const [nonce, setNonce] = useState(0);
  const requestKey = `${key}#${nonce}`;
  const run = useEffectEvent((signal: AbortSignal) => fetcher(signal));

  useEffect(() => {
    const controller = new AbortController();
    run(controller.signal).then(
      (data) => setSettled({ key: requestKey, data }),
      (error: unknown) => {
        if (isAbortError(error)) return;
        const apiError = error instanceof ApiError ? error : new ApiError(String(error), null);
        setSettled({ key: requestKey, error: apiError });
      },
    );
    return () => controller.abort();
  }, [requestKey]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const current = settled?.key === requestKey ? settled : undefined;
  return { data: current?.data, error: current?.error, loading: !current, reload };
}
