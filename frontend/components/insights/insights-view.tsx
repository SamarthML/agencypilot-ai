"use client";

import { Database, RotateCw, TriangleAlert } from "lucide-react";
import { useMemo } from "react";

import { EmptyState } from "@/components/empty-state";
import { AiSummaryCard } from "@/components/insights/ai-summary-card";
import { AskBox } from "@/components/insights/ask-box";
import { ChannelTable } from "@/components/insights/channel-table";
import { KpiGrid, KpiGridSkeleton } from "@/components/insights/kpi-grid";
import { RevenueChart } from "@/components/insights/revenue-chart";
import { SessionsChart } from "@/components/insights/sessions-chart";
import { ShareChart } from "@/components/insights/share-chart";
import { SignalsList } from "@/components/insights/signals-list";
import { UploadDialog } from "@/components/insights/upload-dialog";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { getInsightsDashboard } from "@/lib/api";
import { channelColors, orderChannels } from "@/lib/channels";
import { useClient } from "@/lib/client-context";
import { formatInteger, formatShortDate } from "@/lib/format";
import { getNavItem } from "@/lib/nav";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import type { Days, InsightsDashboard } from "@/lib/types";

const DAY_OPTIONS = ["7", "30", "90"] as const;
type DayOption = (typeof DAY_OPTIONS)[number];

function PeriodTabs({ value, onChange }: { value: DayOption; onChange: (v: DayOption) => void }) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as DayOption)}>
      <TabsList aria-label="Period">
        {DAY_OPTIONS.map((d) => (
          <TabsTrigger key={d} value={d}>
            {d}d
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

function DatasetLine({ data }: { data: InsightsDashboard }) {
  const { dataset, period } = data;
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
      <Database aria-hidden className="size-3.5" />
      <span className="font-medium text-foreground">{dataset.filename}</span>
      <span>· {dataset.source === "sample" ? "sample data" : "uploaded"}</span>
      <span>· {formatInteger(dataset.row_count)} rows</span>
      <span>
        · showing {formatShortDate(period.start)} – {formatShortDate(period.end)}
        {period.has_previous
          ? ` vs ${formatShortDate(period.previous_start)} – ${formatShortDate(period.previous_end)}`
          : " (no earlier data to compare)"}
      </span>
    </p>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-busy>
      <Skeleton className="h-4 w-72" />
      <KpiGridSkeleton />
      <Skeleton className="h-40 rounded-2xl" />
      <Skeleton className="h-80 rounded-2xl" />
    </div>
  );
}

function SectionTitle({ children }: { children: string }) {
  return <h2 className="text-sm font-medium text-muted-foreground">{children}</h2>;
}

function Dashboard({ data, days }: { data: InsightsDashboard; days: Days }) {
  const channels = useMemo(() => orderChannels(data.dataset.channels), [data.dataset.channels]);
  const colors = useMemo(() => channelColors(data.dataset.channels), [data.dataset.channels]);
  const clientId = data.dataset.client_id;

  return (
    <div className="space-y-6 md:space-y-8">
      <DatasetLine data={data} />
      <KpiGrid kpis={data.kpis} days={days} />
      <section className="space-y-3">
        <SectionTitle>Notable changes</SectionTitle>
        <SignalsList signals={data.signals} />
      </section>
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <AiSummaryCard clientId={clientId} days={days} />
        </div>
        <AskBox clientId={clientId} days={days} />
      </div>
      <SessionsChart timeseries={data.timeseries} channels={channels} colors={colors} />
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <RevenueChart channels={data.channels} colors={colors} />
        </div>
        <div className="lg:col-span-2">
          <ShareChart channels={data.channels} colors={colors} />
        </div>
      </div>
      <ChannelTable channels={data.channels} colors={colors} />
    </div>
  );
}

export function InsightsView() {
  const { client } = useClient();
  const [dayOption, setDayOption] = useLocalStorage<DayOption>(STORAGE_KEYS.insightsDays, "30", DAY_OPTIONS);
  const days = Number(dayOption) as Days;
  const { data, error, reload } = useApi(`${client.id}:${days}`, (signal) =>
    getInsightsDashboard(client.id, days, { signal, silent: true }),
  );

  return (
    <div className="space-y-6 md:space-y-8">
      <PageHeader
        title={`Insights · ${client.name}`}
        description={getNavItem("/insights").description}
        actions={
          <>
            <PeriodTabs value={dayOption} onChange={setDayOption} />
            <UploadDialog clientId={client.id} clientName={client.name} onDataChanged={reload} />
          </>
        }
      />
      {error ? (
        <EmptyState
          icon={TriangleAlert}
          title={error.status === 404 ? `No data for ${client.name} yet` : "Couldn't load insights"}
          description={error.message}
          action={
            <Button variant="outline" onClick={reload}>
              <RotateCw data-icon="inline-start" aria-hidden /> Try again
            </Button>
          }
        />
      ) : data ? (
        <Dashboard data={data} days={days} />
      ) : (
        <DashboardSkeleton />
      )}
    </div>
  );
}
