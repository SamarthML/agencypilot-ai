import { Minus, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatDeltaPct } from "@/lib/format";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  /** Percentage change vs the previous period, e.g. 8.4 or -12; null when not available. */
  deltaPct?: number | null;
  /** Which direction counts as good; "neutral" (e.g. ad spend) is never coloured. */
  goodWhen?: "up" | "down" | "neutral";
  icon?: LucideIcon;
  /** Comparison period shown after the delta. */
  period?: string;
  /** Shown instead of the delta row when there is no delta (e.g. "across 3 clients"). */
  footnote?: string;
}

function toneFor(deltaPct: number, goodWhen: "up" | "down" | "neutral"): string {
  if (goodWhen === "neutral" || deltaPct === 0) return "bg-muted text-muted-foreground";
  const isGood = deltaPct > 0 === (goodWhen === "up");
  return isGood ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive";
}

function DeltaBadge({ deltaPct, goodWhen }: { deltaPct: number; goodWhen: "up" | "down" | "neutral" }) {
  const TrendIcon = deltaPct > 0 ? TrendingUp : deltaPct < 0 ? TrendingDown : Minus;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-medium tabular-nums",
        toneFor(deltaPct, goodWhen),
      )}
    >
      <TrendIcon aria-hidden className="size-3.5" />
      {formatDeltaPct(deltaPct)}
    </span>
  );
}

export function KpiCard({
  label,
  value,
  deltaPct = null,
  goodWhen = "up",
  icon: Icon,
  period = "vs last month",
  footnote,
}: KpiCardProps) {
  return (
    <Card className="h-full">
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">{label}</p>
          {Icon && (
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
              <Icon aria-hidden className="size-4 text-muted-foreground" />
            </span>
          )}
        </div>
        <p className="text-2xl font-semibold tracking-tight md:text-3xl">{value}</p>
        <div className="flex min-h-5 items-center gap-1.5 text-xs">
          {deltaPct !== null ? (
            <>
              <DeltaBadge deltaPct={deltaPct} goodWhen={goodWhen} />
              <span className="hidden truncate text-muted-foreground sm:inline">{period}</span>
            </>
          ) : (
            <span className="text-muted-foreground">{footnote ?? "No prior period"}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
