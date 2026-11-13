"use client";

import { CalendarDays, FileBarChart, RotateCw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { Stagger, StaggerItem } from "@/components/motion";
import { PageHeader } from "@/components/page-header";
import { NewReportDialog } from "@/components/reports/new-report-dialog";
import { ReportStatusBadge } from "@/components/reports/report-status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { listReports } from "@/lib/api";
import { DEMO_CLIENTS, useClient } from "@/lib/client-context";
import type { ReportSummary } from "@/lib/types";

type Scope = "client" | "all";

function formatCreated(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function initialsOf(report: ReportSummary): string {
  return (
    DEMO_CLIENTS.find((c) => c.id === report.client)?.initials ??
    report.client_name
      .split(/\s+/)
      .map((word) => word[0])
      .join("")
      .slice(0, 2)
      .toUpperCase()
  );
}

function ReportCard({ report }: { report: ReportSummary }) {
  return (
    <Link
      href={`/reports/${report.id}`}
      className="group flex h-full flex-col gap-4 rounded-2xl border border-border/60 bg-card p-5 shadow-card transition-colors hover:border-border hover:bg-muted/30 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="bg-brand-gradient flex size-10 shrink-0 items-center justify-center rounded-xl text-sm font-semibold text-white">
            {initialsOf(report)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{report.client_name}</p>
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <CalendarDays aria-hidden className="size-3.5" /> {report.month_label}
            </p>
          </div>
        </div>
        <ReportStatusBadge status={report.status} />
      </div>
      <p className="line-clamp-2 flex-1 text-sm leading-snug font-medium group-hover:underline group-hover:underline-offset-2">
        {report.title}
      </p>
      <p className="text-xs text-muted-foreground">Created {formatCreated(report.created_at)}</p>
    </Link>
  );
}

function ReportGridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-44 rounded-2xl" />
      ))}
    </div>
  );
}

export function ReportsView() {
  const { client } = useClient();
  const [scope, setScope] = useState<Scope>("client");
  const filter = scope === "client" ? client.id : null;
  const reports = useApi(`reports:${filter ?? "all"}`, (signal) => listReports(filter, { signal, silent: true }));

  return (
    <div className="space-y-6 md:space-y-8">
      <PageHeader
        title="Reports"
        description="Monthly client reports: KPIs computed from the data, a narrative written only from those numbers, editable and exportable as PDF."
        actions={<NewReportDialog openOnCommand />}
      />
      <Tabs value={scope} onValueChange={(value) => setScope(value as Scope)}>
        <TabsList>
          <TabsTrigger value="client">{client.name}</TabsTrigger>
          <TabsTrigger value="all">All clients</TabsTrigger>
        </TabsList>
      </Tabs>
      {reports.error ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 rounded-2xl bg-destructive/10 p-4 text-sm text-destructive">
          <span className="flex-1">{reports.error.message}</span>
          <Button size="sm" variant="outline" onClick={reports.reload}>
            <RotateCw data-icon="inline-start" aria-hidden /> Retry
          </Button>
        </div>
      ) : !reports.data ? (
        <ReportGridSkeleton />
      ) : reports.data.length === 0 ? (
        <EmptyState
          icon={FileBarChart}
          title={scope === "client" ? `No reports for ${client.name} yet` : "No reports yet"}
          description="Pick a client and a month: the KPIs are computed from the data and the narrative is written from them. You can edit every section before exporting."
          action={<NewReportDialog />}
        />
      ) : (
        <Stagger className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {reports.data.map((report) => (
            <StaggerItem key={report.id}>
              <ReportCard report={report} />
            </StaggerItem>
          ))}
        </Stagger>
      )}
    </div>
  );
}
