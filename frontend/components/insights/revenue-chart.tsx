"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_TICK, ChartCard, ChartTooltip, GRID_STROKE } from "@/components/insights/chart-parts";
import { formatCompactCurrency, formatCurrency } from "@/lib/format";
import type { ChannelBreakdown } from "@/lib/types";

interface RevenueChartProps {
  channels: ChannelBreakdown[];
  colors: Record<string, string>;
  description?: string;
}

/** Revenue per channel: magnitude, ranked, one axis, direct value labels. */
export function RevenueChart({ channels, colors, description = "Attributed revenue in the selected period" }: RevenueChartProps) {
  const data = [...channels].sort((a, b) => b.revenue - a.revenue);

  return (
    <ChartCard title="Revenue by channel" description={description}>
      <div style={{ height: Math.max(180, data.length * 40) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 56, bottom: 0, left: 0 }}>
            <CartesianGrid horizontal={false} stroke={GRID_STROKE} />
            <XAxis
              type="number"
              tickFormatter={formatCompactCurrency}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="channel"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={96}
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.5 }}
              content={(props) => <ChartTooltip {...props} formatValue={formatCurrency} />}
            />
            <Bar dataKey="revenue" name="Revenue" radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false}>
              {data.map((row) => (
                <Cell key={row.channel} fill={colors[row.channel]} />
              ))}
              <LabelList
                dataKey="revenue"
                position="right"
                formatter={(value) => formatCompactCurrency(Number(value))}
                className="fill-foreground text-xs tabular-nums"
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}
