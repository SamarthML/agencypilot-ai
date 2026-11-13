"use client";

import { SeoIssuesKpi } from "@/components/home/seo-issues-kpi";
import { KpiTile } from "@/components/insights/kpi-grid";
import { Stagger, StaggerItem } from "@/components/motion";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { getInsightsOverview } from "@/lib/api";

const DAYS = 30;
const INSIGHT_TILES = 4;

/** Agency-wide KPIs from /api/insights/overview, plus open SEO issues for the selected client. */
export function OverviewKpis() {
  const { data, error } = useApi("overview", (signal) =>
    getInsightsOverview(DAYS, { signal, silent: true }),
  );

  return (
    <section aria-labelledby="kpi-heading" className="space-y-4">
      <h2 id="kpi-heading" className="text-sm font-medium text-muted-foreground">
        Last {DAYS} days · all clients
      </h2>
      <Stagger className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-3 xl:grid-cols-5">
        {error ? (
          <StaggerItem className="col-span-2 lg:col-span-2 xl:col-span-4">
            <p className="flex h-full items-center rounded-2xl border border-dashed px-4 py-6 text-sm text-muted-foreground">
              Live KPIs are unavailable: {error.message}
            </p>
          </StaggerItem>
        ) : data ? (
          data.kpis.map((kpi) => (
            <StaggerItem key={kpi.key}>
              <KpiTile
                kpi={kpi}
                period={`vs prior ${DAYS}d`}
                footnote={kpi.key === "active_clients" ? "with data loaded" : undefined}
              />
            </StaggerItem>
          ))
        ) : (
          Array.from({ length: INSIGHT_TILES }, (_, i) => (
            <Skeleton key={i} className="h-[124px] rounded-2xl" />
          ))
        )}
        {/* Spans 2 of 3 columns at lg so the five tiles fill two rows (3 + 2) without a hole. */}
        <StaggerItem className="col-span-2 xl:col-span-1">
          <SeoIssuesKpi />
        </StaggerItem>
      </Stagger>
    </section>
  );
}
