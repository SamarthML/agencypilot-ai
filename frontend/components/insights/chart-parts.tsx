import type { ReactNode } from "react";
import type { TooltipContentProps, TooltipValueType } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Recessive chart chrome shared by every Insights chart. */
export const AXIS_TICK = { fill: "var(--muted-foreground)", fontSize: 12 } as const;
export const GRID_STROKE = "var(--chart-grid)";

interface ChartCardProps {
  title: string;
  description?: string;
  legend?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function ChartCard({ title, description, legend, children, className }: ChartCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="gap-1">
        <CardTitle className="text-base">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        {legend}
        {children}
      </CardContent>
    </Card>
  );
}

export interface LegendItem {
  name: string;
  color: string;
  /** Optional value shown after the name (e.g. "38%"). */
  value?: string;
}

export function ChartLegend({ items }: { items: LegendItem[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {items.map((item) => (
        <li key={item.name} className="flex items-center gap-1.5">
          <span aria-hidden className="size-2.5 rounded-sm" style={{ background: item.color }} />
          <span className="text-foreground">{item.name}</span>
          {item.value && <span className="tabular-nums">{item.value}</span>}
        </li>
      ))}
    </ul>
  );
}

type TooltipState = Partial<
  Pick<TooltipContentProps<TooltipValueType, string | number>, "active" | "payload" | "label">
>;

interface ChartTooltipProps extends TooltipState {
  formatValue: (value: number) => string;
  formatLabel?: (label: string) => string;
}

/** Tooltip: text in ink colours; a colour swatch carries series identity. */
export function ChartTooltip({ active, payload, label, formatValue, formatLabel }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const rows = [...payload].sort((a, b) => Number(b.value ?? 0) - Number(a.value ?? 0));
  const heading = label === undefined ? undefined : String(label);
  return (
    <div className="min-w-40 rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      {heading && (
        <p className="mb-1.5 font-medium text-foreground">
          {formatLabel ? formatLabel(heading) : heading}
        </p>
      )}
      <ul className="space-y-1">
        {rows.map((row) => (
          <li key={String(row.dataKey ?? row.name)} className="flex items-center gap-2">
            <span
              aria-hidden
              className="size-2.5 shrink-0 rounded-sm"
              style={{ background: row.color ?? row.payload?.fill }}
            />
            <span className="text-muted-foreground">{row.name}</span>
            <span className="ml-auto pl-3 font-medium text-foreground tabular-nums">
              {formatValue(Number(row.value ?? 0))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
