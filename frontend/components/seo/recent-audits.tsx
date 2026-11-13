"use client";

import { History } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { getSeoHistory } from "@/lib/api";
import { formatRelativeTime, hostname, scoreBand, type ScoreBand } from "@/lib/seo";
import type { SeoAuditSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

const SCORE_PILL: Record<ScoreBand, string> = {
  poor: "bg-destructive/10 text-destructive",
  fair: "bg-warning/15 text-warning",
  good: "bg-success/10 text-success",
};

interface RecentAuditsProps {
  clientId: string;
  clientName: string;
  /** Bump to refetch after a new audit is saved. */
  version: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function pathOf(url: string): string {
  try {
    const { pathname, search } = new URL(url);
    return pathname === "/" && !search ? "" : `${pathname}${search}`;
  } catch {
    return "";
  }
}

function AuditRow({ audit, selected, onSelect }: { audit: SeoAuditSummary; selected: boolean; onSelect: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-current={selected ? "true" : undefined}
        className={cn(
          "flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left transition-colors",
          "hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
          selected && "bg-muted",
        )}
      >
        <span
          className={cn(
            "flex size-10 shrink-0 items-center justify-center rounded-lg text-sm font-semibold tabular-nums",
            SCORE_PILL[scoreBand(audit.score)],
          )}
          aria-label={`Score ${audit.score}`}
        >
          {audit.score}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">
            {hostname(audit.final_url)}
            <span className="font-normal text-muted-foreground">{pathOf(audit.final_url)}</span>
          </span>
          <span className="block text-xs text-muted-foreground">
            {audit.issue_count === 0 ? "No issues" : `${audit.issue_count} issue${audit.issue_count === 1 ? "" : "s"}`}{" "}
            · {formatRelativeTime(audit.created_at)}
          </span>
        </span>
      </button>
    </li>
  );
}

export function RecentAudits({ clientId, clientName, version, selectedId, onSelect }: RecentAuditsProps) {
  const { data, error } = useApi(`${clientId}:${version}`, (signal) =>
    getSeoHistory(clientId, { signal, silent: true }),
  );

  return (
    <Card className="lg:sticky lg:top-20">
      <CardHeader className="gap-1">
        <CardTitle className="flex items-center gap-2 text-base">
          <History aria-hidden className="size-4 text-muted-foreground" /> Recent audits
        </CardTitle>
        <CardDescription>Last 10 for {clientName}</CardDescription>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="text-sm text-muted-foreground">Couldn&apos;t load history: {error.message}</p>
        ) : !data ? (
          <div className="space-y-2" aria-busy>
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-14 rounded-xl" />
            ))}
          </div>
        ) : data.length === 0 ? (
          <p className="rounded-xl border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
            No audits for {clientName} yet. Run one above.
          </p>
        ) : (
          <ul className="-mx-2.5 space-y-0.5">
            {data.map((audit) => (
              <AuditRow
                key={audit.id}
                audit={audit}
                selected={audit.id === selectedId}
                onSelect={() => onSelect(audit.id)}
              />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
