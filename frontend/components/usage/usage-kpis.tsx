import { Activity, Coins, Gauge, PiggyBank, Timer, Zap } from "lucide-react";

import { KpiCard } from "@/components/kpi-card";
import { Stagger, StaggerItem } from "@/components/motion";
import { formatCompactNumber, formatInteger } from "@/lib/format";
import type { UsageTotals } from "@/lib/types";
import { formatMs, formatRate, formatUsdPrecise } from "@/lib/usage";

function plural(count: number, word: string): string {
  return `${formatInteger(count)} ${word}${count === 1 ? "" : "s"}`;
}

export function UsageKpis({ totals }: { totals: UsageTotals }) {
  const cards = [
    {
      label: "LLM calls",
      value: formatInteger(totals.llm_calls),
      icon: Activity,
      footnote: `${plural(totals.requests, "request")} · ${plural(totals.errors, "error")}`,
    },
    {
      label: "Total tokens",
      value: totals.total_tokens >= 10_000 ? formatCompactNumber(totals.total_tokens) : formatInteger(totals.total_tokens),
      icon: Coins,
      footnote: `${formatCompactNumber(totals.input_tokens)} in · ${formatCompactNumber(totals.output_tokens)} out`,
    },
    {
      label: "Total cost",
      value: formatUsdPrecise(totals.cost_usd),
      icon: Gauge,
      footnote: "Estimated from per-model token prices",
    },
    {
      label: "Avg latency",
      value: formatMs(totals.avg_latency_ms),
      icon: Timer,
      footnote: `p95 ${formatMs(totals.p95_latency_ms)} · successful calls`,
    },
    {
      label: "Cache hit rate",
      value: formatRate(totals.cache_hit_rate),
      icon: Zap,
      footnote: `${plural(totals.cache_hits, "hit")} · ${plural(totals.guardrail_skips, "guardrail skip")}`,
    },
    {
      label: "Saved by cache",
      value: formatUsdPrecise(totals.saved_usd),
      icon: PiggyBank,
      footnote: totals.saved_includes_estimates
        ? "Original call costs (some estimated)"
        : "Cost of the original calls replayed",
    },
  ];
  return (
    <Stagger className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-3 2xl:grid-cols-6">
      {cards.map((card) => (
        <StaggerItem key={card.label}>
          <KpiCard {...card} />
        </StaggerItem>
      ))}
    </Stagger>
  );
}
