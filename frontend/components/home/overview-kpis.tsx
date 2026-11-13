"use client";

import { KpiGridSkeleton, KpiTile } from "@/components/insights/kpi-grid";
import { Stagger, StaggerItem } from "@/components/motion";
import { useApi } from "@/hooks/use-api";
import { getInsightsOverview } from "@/lib/api";

const DAYS = 30;

/** Agency-wide KPIs across every client's dataset, from /api/insights/overview. */
export function OverviewKpis() {
  const { data, error } = useApi("overview", (signal) =>
    getInsightsOverview(DAYS, { signal, silent: true }),
  );

  return (
    <section aria-labelledby="kpi-heading" className="space-y-4">
      <h2 id="kpi-heading" className="text-sm font-medium text-muted-foreground">
        Last {DAYS} days · all clients
      </h2>
      {error ? (
        <p className="rounded-2xl border border-dashed px-4 py-6 text-sm text-muted-foreground">
          Live KPIs are unavailable: {error.message}
        </p>
      ) : data ? (
        <Stagger className="grid grid-cols-2 gap-3 md:gap-4 xl:grid-cols-4">
          {data.kpis.map((kpi) => (
            <StaggerItem key={kpi.key}>
              <KpiTile
                kpi={kpi}
                period={`vs prior ${DAYS}d`}
                footnote={kpi.key === "active_clients" ? "with data loaded" : undefined}
              />
            </StaggerItem>
          ))}
        </Stagger>
      ) : (
        <KpiGridSkeleton count={4} />
      )}
    </section>
  );
}
