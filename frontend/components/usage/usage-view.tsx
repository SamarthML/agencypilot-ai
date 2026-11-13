"use client";

import { RotateCw } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { KpiGridSkeleton } from "@/components/insights/kpi-grid";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CostExplainer } from "@/components/usage/cost-explainer";
import { RecentCalls } from "@/components/usage/recent-calls";
import { CallsPerDayChart, CostByFeatureChart, CostByModelChart } from "@/components/usage/usage-charts";
import { UsageKpis } from "@/components/usage/usage-kpis";
import { useApi } from "@/hooks/use-api";
import { getAppSettings, getRecentUsage, getUsageSummary } from "@/lib/api";
import type { UsageDays } from "@/lib/types";

const WINDOWS: { value: UsageDays; label: string }[] = [
  { value: 7, label: "7 days" },
  { value: 30, label: "30 days" },
  { value: "all", label: "All time" },
];

function parseWindow(value: string): UsageDays {
  return value === "all" ? "all" : value === "7" ? 7 : 30;
}

export function UsageView() {
  const [days, setDays] = useState<UsageDays>(30);
  const summary = useApi(`usage-summary:${days}`, (signal) => getUsageSummary(days, { signal, silent: true }));
  const recent = useApi("usage-recent", (signal) => getRecentUsage(50, { signal, silent: true }));
  const settings = useApi("app-settings", (signal) => getAppSettings({ signal, silent: true }));

  return (
    <div className="space-y-6 md:space-y-8">
      <PageHeader
        title="Usage & cost"
        description="Every LLM request the app makes: tokens, latency and estimated cost, plus what caching and the guardrail saved."
        actions={
          <Tabs value={String(days)} onValueChange={(value) => setDays(parseWindow(value))}>
            <TabsList>
              {WINDOWS.map((w) => (
                <TabsTrigger key={w.label} value={String(w.value)}>
                  {w.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        }
      />

      {summary.error ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 rounded-2xl bg-destructive/10 p-4 text-sm text-destructive">
          <span className="flex-1">{summary.error.message}</span>
          <Button size="sm" variant="outline" onClick={summary.reload}>
            <RotateCw data-icon="inline-start" aria-hidden /> Retry
          </Button>
        </div>
      ) : !summary.data ? (
        <div className="space-y-6">
          <KpiGridSkeleton count={6} />
          <div className="grid gap-4 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-72 rounded-2xl" />
            ))}
          </div>
        </div>
      ) : (
        <>
          <UsageKpis totals={summary.data.totals} />
          <div className="grid gap-4 md:gap-6 lg:grid-cols-2 xl:grid-cols-3">
            <div className="min-w-0 lg:col-span-2 xl:col-span-1">
              <CostByFeatureChart features={summary.data.by_feature} />
            </div>
            <div className="min-w-0">
              <CallsPerDayChart days={summary.data.by_day} />
            </div>
            <div className="min-w-0">
              <CostByModelChart models={summary.data.by_model} />
            </div>
          </div>
        </>
      )}

      <RecentCalls calls={recent.data} />
      <CostExplainer rateLimit={settings.data?.rate_limit_enabled ? settings.data.rate_limit_per_minute : null} />
    </div>
  );
}
