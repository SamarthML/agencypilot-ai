"use client";

import { useEffect, useState } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { API_URL, getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 30_000;

type ApiState =
  | { kind: "checking" }
  | { kind: "online"; version: string }
  | { kind: "degraded"; version: string }
  | { kind: "offline"; reason: string };

const DOT_CLASS: Record<ApiState["kind"], string> = {
  checking: "bg-muted-foreground/50",
  online: "bg-emerald-500",
  degraded: "bg-amber-500",
  offline: "bg-red-500",
};

function describe(state: ApiState): { label: string; detail: string } {
  switch (state.kind) {
    case "checking":
      return { label: "Checking API…", detail: API_URL };
    case "online":
      return { label: "API online", detail: `Database ok · v${state.version}` };
    case "degraded":
      return { label: "API degraded", detail: "API is up but the database is unreachable" };
    case "offline":
      return { label: "API offline", detail: state.reason };
  }
}

async function checkApi(): Promise<ApiState> {
  try {
    const health = await getHealth({ silent: true });
    return health.db === "ok"
      ? { kind: "online", version: health.version }
      : { kind: "degraded", version: health.version };
  } catch (error) {
    return { kind: "offline", reason: error instanceof Error ? error.message : String(error) };
  }
}

/** Status dot that polls GET /health every 30 seconds. */
export function ApiStatus() {
  const [state, setState] = useState<ApiState>({ kind: "checking" });

  useEffect(() => {
    let active = true;
    const poll = () => {
      void checkApi().then((next) => {
        if (active) setState(next);
      });
    };
    poll();
    const timer = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const { label, detail } = describe(state);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={label}
          data-api-state={state.kind}
          className="flex size-8 items-center justify-center rounded-lg outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="relative flex size-2.5">
            {state.kind === "online" && (
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500 opacity-40 [animation-duration:2.5s]" />
            )}
            <span className={cn("relative inline-flex size-2.5 rounded-full", DOT_CLASS[state.kind])} />
          </span>
        </button>
      </TooltipTrigger>
      <TooltipContent side="bottom" align="end">
        <p className="font-medium">{label}</p>
        <p className="opacity-70">{detail}</p>
      </TooltipContent>
    </Tooltip>
  );
}
