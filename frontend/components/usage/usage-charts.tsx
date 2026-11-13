"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_TICK, ChartCard, ChartLegend, ChartTooltip, GRID_STROKE } from "@/components/insights/chart-parts";
import { formatInteger, formatShortDate } from "@/lib/format";
import type { DailyUsage, FeatureUsage, ModelUsage } from "@/lib/types";
import { featureColor, featureLabel, formatUsdPrecise, seriesColor } from "@/lib/usage";

function EmptyChart({ message }: { message: string }) {
  return <p className="flex h-48 items-center justify-center text-sm text-muted-foreground">{message}</p>;
}

/** Cost per feature: ranked magnitude, one axis, direct value labels. */
export function CostByFeatureChart({ features }: { features: FeatureUsage[] }) {
  const data = features
    .filter((f) => f.cost_usd > 0)
    .map((f) => ({ name: featureLabel(f.feature), feature: f.feature, cost: f.cost_usd }));
  return (
    <ChartCard title="Cost by feature" description="Which features spend the budget">
      {data.length === 0 ? (
        <EmptyChart message="No paid calls in this period." />
      ) : (
        <div style={{ height: Math.max(160, data.length * 40) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 72, bottom: 0, left: 0 }}>
              <CartesianGrid horizontal={false} stroke={GRID_STROKE} />
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" tick={AXIS_TICK} tickLine={false} axisLine={false} width={116} />
              <Tooltip
                cursor={{ fill: "var(--muted)", opacity: 0.5 }}
                content={(props) => <ChartTooltip {...props} formatValue={formatUsdPrecise} />}
              />
              <Bar dataKey="cost" name="Cost" radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false}>
                {data.map((row) => (
                  <Cell key={row.feature} fill={featureColor(row.feature)} />
                ))}
                <LabelList
                  dataKey="cost"
                  position="right"
                  formatter={(value) => formatUsdPrecise(Number(value))}
                  className="fill-foreground text-xs tabular-nums"
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}

const DAY_SERIES = [
  { key: "llm_calls", name: "LLM calls", color: "var(--series-1)" },
  { key: "cache_hits", name: "Cache hits", color: "var(--series-3)" },
] as const;

/** Calls per day, with cache hits as a second series on the same axis. */
export function CallsPerDayChart({ days }: { days: DailyUsage[] }) {
  return (
    <ChartCard
      title="Calls per day"
      description="Provider calls vs requests served from cache (UTC days)"
      legend={<ChartLegend items={DAY_SERIES.map((s) => ({ name: s.name, color: s.color }))} />}
    >
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={days} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid vertical={false} stroke={GRID_STROKE} />
            <XAxis
              dataKey="date"
              tickFormatter={formatShortDate}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              minTickGap={24}
            />
            <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} width={40} />
            <Tooltip
              content={(props) => (
                <ChartTooltip {...props} formatValue={formatInteger} formatLabel={formatShortDate} />
              )}
            />
            {DAY_SERIES.map((s) => (
              <Line
                key={s.key}
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                strokeWidth={2}
                dot={days.length <= 7}
                type="monotone"
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}

/** Cost share per model: part-to-whole, values in the legend so colour never carries it alone. */
export function CostByModelChart({ models }: { models: ModelUsage[] }) {
  const data = useMemo(
    () =>
      models
        .filter((m) => m.cost_usd > 0)
        .map((m, i) => ({ name: m.model, provider: m.provider, cost: m.cost_usd, color: seriesColor(i) })),
    [models],
  );
  const total = data.reduce((sum, m) => sum + m.cost, 0);
  return (
    <ChartCard title="Cost by model" description="Share of spend per provider model">
      {data.length === 0 ? (
        <EmptyChart message="No paid calls in this period." />
      ) : (
        <>
          <div className="relative mx-auto h-52 max-w-60">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip content={(props) => <ChartTooltip {...props} formatValue={formatUsdPrecise} />} />
                <Pie
                  data={data}
                  dataKey="cost"
                  nameKey="name"
                  innerRadius="62%"
                  outerRadius="92%"
                  stroke="var(--card)"
                  strokeWidth={2}
                  isAnimationActive={false}
                >
                  {data.map((m) => (
                    <Cell key={m.name} fill={m.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-lg font-semibold tabular-nums">{formatUsdPrecise(total)}</span>
              <span className="text-xs text-muted-foreground">total</span>
            </div>
          </div>
          <ChartLegend
            items={data.map((m) => ({
              name: m.name,
              color: m.color,
              value: `${((m.cost / total) * 100).toFixed(0)}%`,
            }))}
          />
        </>
      )}
    </ChartCard>
  );
}
