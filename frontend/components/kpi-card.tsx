import { TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  /** Percentage change vs the previous period, e.g. 8.4 or -12. */
  deltaPct: number;
  /** Which direction counts as good. Defaults to "up". */
  goodWhen?: "up" | "down";
  icon?: LucideIcon;
  /** Comparison period shown after the delta. */
  period?: string;
}

function formatDelta(deltaPct: number): string {
  const sign = deltaPct > 0 ? "+" : "";
  return `${sign}${deltaPct.toFixed(1)}%`;
}

export function KpiCard({
  label,
  value,
  deltaPct,
  goodWhen = "up",
  icon: Icon,
  period = "vs last month",
}: KpiCardProps) {
  const isUp = deltaPct >= 0;
  const isGood = isUp === (goodWhen === "up");
  const TrendIcon = isUp ? TrendingUp : TrendingDown;

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
        <p className="text-2xl font-semibold tracking-tight tabular-nums md:text-3xl">{value}</p>
        <div className="flex items-center gap-1.5 text-xs">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-medium tabular-nums",
              isGood ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive",
            )}
          >
            <TrendIcon aria-hidden className="size-3.5" />
            {formatDelta(deltaPct)}
          </span>
          <span className="text-muted-foreground">{period}</span>
        </div>
      </CardContent>
    </Card>
  );
}
