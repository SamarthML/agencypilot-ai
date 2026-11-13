"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { ChartCard, ChartLegend, ChartTooltip } from "@/components/insights/chart-parts";
import { formatCompactNumber, formatInteger } from "@/lib/format";
import type { ChannelBreakdown } from "@/lib/types";

interface ShareChartProps {
  channels: ChannelBreakdown[];
  colors: Record<string, string>;
}

/** Share of sessions: part-to-whole, labelled in the legend so colour never carries it alone. */
export function ShareChart({ channels, colors }: ShareChartProps) {
  const data = channels.filter((c) => c.sessions > 0);
  const total = data.reduce((sum, c) => sum + c.sessions, 0);
  const legend = data.map((c) => ({
    name: c.channel,
    color: colors[c.channel],
    value: `${c.sessions_share_pct.toFixed(1)}%`,
  }));

  return (
    <ChartCard title="Traffic mix" description="Share of sessions by channel">
      <div className="relative mx-auto h-52 max-w-60">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={(props) => <ChartTooltip {...props} formatValue={formatInteger} />} />
            <Pie
              data={data}
              dataKey="sessions"
              nameKey="channel"
              innerRadius="62%"
              outerRadius="92%"
              stroke="var(--card)"
              strokeWidth={2}
              isAnimationActive={false}
            >
              {data.map((c) => (
                <Cell key={c.channel} fill={colors[c.channel]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-semibold">{formatCompactNumber(total)}</span>
          <span className="text-xs text-muted-foreground">sessions</span>
        </div>
      </div>
      <ChartLegend items={legend} />
    </ChartCard>
  );
}
