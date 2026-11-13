"use client";

import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  AXIS_TICK,
  ChartCard,
  ChartLegend,
  ChartTooltip,
  GRID_STROKE,
} from "@/components/insights/chart-parts";
import { formatCompactNumber, formatInteger, formatShortDate } from "@/lib/format";
import type { TimeSeriesPoint } from "@/lib/types";

interface SessionsChartProps {
  timeseries: TimeSeriesPoint[];
  channels: string[];
  colors: Record<string, string>;
}

type Row = { date: string } & Record<string, number | string>;

/** Daily sessions per channel: change over time, one line per channel on one axis. */
export function SessionsChart({ timeseries, channels, colors }: SessionsChartProps) {
  const data = useMemo<Row[]>(
    () => timeseries.map((p) => ({ date: p.date, ...p.by_channel })),
    [timeseries],
  );

  return (
    <ChartCard
      title="Sessions by channel"
      description="Daily sessions in the selected period"
      legend={<ChartLegend items={channels.map((c) => ({ name: c, color: colors[c] }))} />}
    >
      <div className="h-64 md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid vertical={false} stroke={GRID_STROKE} />
            <XAxis
              dataKey="date"
              tickFormatter={formatShortDate}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              minTickGap={24}
            />
            <YAxis
              tickFormatter={formatCompactNumber}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip
              cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "3 3" }}
              content={(props) => (
                <ChartTooltip {...props} formatValue={formatInteger} formatLabel={formatShortDate} />
              )}
            />
            {channels.map((channel) => (
              <Line
                key={channel}
                type="monotone"
                dataKey={channel}
                name={channel}
                stroke={colors[channel]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: "var(--card)", strokeWidth: 2 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}
