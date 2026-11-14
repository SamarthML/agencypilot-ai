"use client";

import { LoaderCircle, RotateCw, ServerCrash } from "lucide-react";
import { useEffect, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { serverWarmup } from "@/lib/api";
import type { WarmupPhase } from "@/lib/warmup";

const serverPhase = (): WarmupPhase => "checking";

/** Shown only while the API cold-starts (free hosting) or if it never answers. */
export function ServerWakeBanner() {
  const phase = useSyncExternalStore(serverWarmup.subscribe, serverWarmup.getPhase, serverPhase);

  useEffect(() => {
    void serverWarmup.ready();
  }, []);

  if (phase === "waking") {
    return (
      <div
        role="status"
        className="flex items-center justify-center gap-2 border-b border-warning/30 bg-warning/10 px-4 py-2 text-center text-sm print:hidden"
      >
        <LoaderCircle className="size-4 shrink-0 animate-spin text-warning" aria-hidden />
        <span>Waking up the server (free hosting, ~30-60 s)…</span>
      </div>
    );
  }
  if (phase === "failed") {
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-center text-sm print:hidden"
      >
        <ServerCrash className="size-4 shrink-0 text-destructive" aria-hidden />
        <span>The server didn&apos;t respond. It may still be starting.</span>
        <Button size="sm" variant="outline" className="h-7" onClick={serverWarmup.retry}>
          <RotateCw aria-hidden />
          Retry
        </Button>
      </div>
    );
  }
  return null;
}
