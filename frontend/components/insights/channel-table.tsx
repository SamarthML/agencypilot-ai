import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatDeltaPct, formatInteger } from "@/lib/format";
import type { ChannelBreakdown } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChannelTableProps {
  channels: ChannelBreakdown[];
  colors: Record<string, string>;
}

function Delta({ value }: { value: number | null }) {
  const tone =
    value === null || value === 0 ? "text-muted-foreground" : value > 0 ? "text-success" : "text-destructive";
  return <span className={cn("tabular-nums", tone)}>{formatDeltaPct(value)}</span>;
}

const HEADERS = ["Channel", "Sessions", "Δ sessions", "Share", "Conv.", "CVR", "Revenue", "Spend", "ROAS"];

/** The table view of every chart on the page (exact numbers, no colour-only encoding). */
export function ChannelTable({ channels, colors }: ChannelTableProps) {
  return (
    <Card>
      <CardHeader className="gap-1">
        <CardTitle className="text-base">Channel breakdown</CardTitle>
        <CardDescription>Exact figures behind the charts, vs the previous period</CardDescription>
      </CardHeader>
      <CardContent
        tabIndex={0}
        role="region"
        aria-label="Channel breakdown table"
        className="overflow-x-auto rounded-b-2xl outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
      >
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              {HEADERS.map((h, i) => (
                <th key={h} scope="col" className={cn("pb-2 font-medium", i > 0 && "text-right")}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {channels.map((c) => (
              <tr key={c.channel} className="border-b last:border-0">
                <th scope="row" className="py-2.5 text-left font-medium">
                  <span className="flex items-center gap-2">
                    <span aria-hidden className="size-2.5 rounded-sm" style={{ background: colors[c.channel] }} />
                    {c.channel}
                  </span>
                </th>
                <td className="text-right">{formatInteger(c.sessions)}</td>
                <td className="text-right">
                  <Delta value={c.sessions_delta_pct} />
                </td>
                <td className="text-right">{c.sessions_share_pct.toFixed(1)}%</td>
                <td className="text-right">{formatInteger(c.conversions)}</td>
                <td className="text-right">{c.conversion_rate === null ? "—" : `${c.conversion_rate.toFixed(2)}%`}</td>
                <td className="text-right">{formatCurrency(c.revenue)}</td>
                <td className="text-right">{c.spend ? formatCurrency(c.spend) : "—"}</td>
                <td className="text-right">{c.roas === null ? "—" : `${c.roas.toFixed(2)}×`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
