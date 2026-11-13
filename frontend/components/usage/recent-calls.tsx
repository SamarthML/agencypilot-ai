"use client";

import { ChevronDown, ChevronUp, CircleAlert, RotateCw, ShieldCheck, Zap } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatInteger } from "@/lib/format";
import { PROVIDERS } from "@/lib/providers";
import type { UsageCall } from "@/lib/types";
import { featureColor, featureLabel, formatCallTime, formatMs, formatUsdPrecise } from "@/lib/usage";
import { cn } from "@/lib/utils";

const PILL = "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap";

function StatusBadge({ call }: { call: UsageCall }) {
  if (!call.success) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button type="button" className={cn(PILL, "cursor-help bg-destructive/10 text-destructive")}>
            <CircleAlert aria-hidden className="size-3" /> Error
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-72 break-words">{call.error ?? "Unknown error"}</TooltipContent>
      </Tooltip>
    );
  }
  if (call.cached) {
    return (
      <span className={cn(PILL, "bg-success/10 text-success")}>
        <Zap aria-hidden className="size-3" /> Cached
      </span>
    );
  }
  if (call.skipped) {
    return (
      <span className={cn(PILL, "bg-brand-from/10 text-brand-text")}>
        <ShieldCheck aria-hidden className="size-3" /> Guardrail
      </span>
    );
  }
  return <span className={cn(PILL, "bg-muted text-muted-foreground")}>OK</span>;
}

function FeatureBadge({ feature }: { feature: string }) {
  return (
    <span className={cn(PILL, "bg-muted text-foreground")}>
      <span aria-hidden className="size-2 rounded-sm" style={{ background: featureColor(feature) }} />
      {featureLabel(feature)}
    </span>
  );
}

function ModelCell({ call }: { call: UsageCall }) {
  const provider = PROVIDERS.find((p) => p.id === call.provider);
  return (
    <span className="flex items-center gap-1.5 whitespace-nowrap">
      <span aria-hidden className={cn("size-2 rounded-full", provider?.dotClass ?? "bg-muted-foreground")} />
      <span className="sr-only">{provider?.label ?? call.provider}</span>
      <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{call.model}</span>
    </span>
  );
}

function costCell(call: UsageCall): string {
  if (call.cached && call.saved_cost_usd) return `$0 (saved ${formatUsdPrecise(call.saved_cost_usd)})`;
  return formatUsdPrecise(call.cost_usd);
}

const HEAD = "px-3 py-2 text-left text-xs font-medium whitespace-nowrap text-muted-foreground";
const NUM = "px-3 py-2.5 text-right tabular-nums whitespace-nowrap";

/** Rows shown before "Show all": keeps the page scannable, especially on phones. */
const COLLAPSED_ROWS = 10;

interface RecentCallsProps {
  calls: UsageCall[] | undefined;
  /** Load error message; replaces the skeleton so a failed request doesn't look like loading. */
  error?: string;
  onRetry?: () => void;
}

export function RecentCalls({ calls, error, onRetry }: RecentCallsProps) {
  const [expanded, setExpanded] = useState(false);
  const visible = calls && !expanded ? calls.slice(0, COLLAPSED_ROWS) : calls;
  const hidden = (calls?.length ?? 0) - (visible?.length ?? 0);

  return (
    <Card className="gap-0 pb-0">
      <CardHeader className="gap-1 pb-4">
        <CardTitle className="text-base">Recent calls</CardTitle>
        <CardDescription>The latest {calls?.length || 50} requests across every feature, newest first</CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        {!calls && error ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 px-(--card-spacing) pb-6 text-sm text-muted-foreground">
            <span className="flex-1">Couldn&apos;t load recent calls. {error}</span>
            <Button size="sm" variant="outline" onClick={onRetry}>
              <RotateCw data-icon="inline-start" aria-hidden /> Retry
            </Button>
          </div>
        ) : !calls ? (
          <div className="space-y-2 px-(--card-spacing) pb-6">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : calls.length === 0 ? (
          <p className="px-(--card-spacing) pb-6 text-sm text-muted-foreground">No LLM requests logged yet.</p>
        ) : (
          // Focusable so keyboard users can scroll the table sideways on narrow screens.
          <div tabIndex={0} role="region" aria-label="Recent LLM calls" className="overflow-x-auto border-t border-border/60 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className={HEAD}>Time</th>
                  <th className={HEAD}>Feature</th>
                  <th className={HEAD}>Model</th>
                  <th className={cn(HEAD, "text-right")}>Tokens in / out</th>
                  <th className={cn(HEAD, "text-right")}>Latency</th>
                  <th className={cn(HEAD, "text-right")}>Cost</th>
                  <th className={HEAD}>Status</th>
                </tr>
              </thead>
              <tbody>
                {(visible ?? []).map((call) => (
                  <tr key={call.id} className="border-t border-border/60 hover:bg-muted/30">
                    <td className="px-3 py-2.5 text-xs whitespace-nowrap text-muted-foreground">{formatCallTime(call.created_at)}</td>
                    <td className="px-3 py-2.5"><FeatureBadge feature={call.feature} /></td>
                    <td className="px-3 py-2.5"><ModelCell call={call} /></td>
                    <td className={NUM}>{formatInteger(call.input_tokens)} / {formatInteger(call.output_tokens)}</td>
                    <td className={NUM}>{formatMs(call.latency_ms)}</td>
                    <td className={NUM}>{costCell(call)}</td>
                    <td className="px-3 py-2.5"><StatusBadge call={call} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {calls && calls.length > COLLAPSED_ROWS && (
          <div className="border-t border-border/60 p-2 text-center">
            <Button variant="ghost" size="sm" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>
              {expanded ? <ChevronUp data-icon="inline-start" aria-hidden /> : <ChevronDown data-icon="inline-start" aria-hidden />}
              {expanded ? "Show fewer" : `Show ${hidden} more`}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
