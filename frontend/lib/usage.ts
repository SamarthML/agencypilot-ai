/** Display names for the `feature` tags logged by the backend (see test_usage.py). */
const FEATURE_LABELS: Record<string, string> = {
  insights_summary: "Insights summary",
  insights_ask: "Insights Q&A",
  seo_audit: "SEO audit",
  copilot: "Copilot answer",
  copilot_rewrite: "Copilot rewrite",
  report: "Monthly report",
};

/** Feature colour follows the feature (fixed slot), never its rank. */
const FEATURE_ORDER = Object.keys(FEATURE_LABELS);

export function featureLabel(feature: string): string {
  return FEATURE_LABELS[feature] ?? feature.replace(/_/g, " ");
}

export function featureColor(feature: string): string {
  const slot = FEATURE_ORDER.indexOf(feature);
  return slot >= 0 ? `var(--series-${slot + 1})` : "var(--series-other)";
}

export function seriesColor(index: number): string {
  return index < 8 ? `var(--series-${index + 1})` : "var(--series-other)";
}

/** LLM costs are fractions of a cent: show 6 decimals below $1 and 4 above. */
export function formatUsdPrecise(cost: number): string {
  if (cost === 0) return "$0";
  return `$${cost.toFixed(cost >= 1 ? 4 : 6)}`;
}

export function formatMs(ms: number | null): string {
  if (ms === null) return "—";
  return ms >= 1000 ? `${(ms / 1000).toFixed(ms >= 10_000 ? 0 : 1)} s` : `${Math.round(ms)} ms`;
}

export function formatRate(rate: number | null): string {
  return rate === null ? "—" : `${(rate * 100).toFixed(rate >= 0.1 ? 0 : 1)}%`;
}

export function formatCallTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
