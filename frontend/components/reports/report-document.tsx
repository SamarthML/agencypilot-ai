"use client";

import { Globe, ShieldAlert, ThumbsUp, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { KpiTile } from "@/components/insights/kpi-grid";
import { RevenueChart } from "@/components/insights/revenue-chart";
import { SessionsChart } from "@/components/insights/sessions-chart";
import { LlmMeta } from "@/components/llm-meta";
import { Stagger, StaggerItem } from "@/components/motion";
import { ListEditor, TextEditor } from "@/components/reports/section-editors";
import { ReportStatusBadge } from "@/components/reports/report-status-badge";
import { channelColors, orderChannels } from "@/lib/channels";
import { ITEM_MAX, LIST_LIMITS, sectionLabel, TEXT_LIMITS, type ListKey, type TextKey } from "@/lib/reports";
import { scoreBand } from "@/lib/seo";
import type { Report, ReportContent, ReportSeo } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ReportDocumentProps {
  report: Report;
  /** When set, sections render as editors bound to this draft. */
  draft: ReportContent | null;
  onDraftChange: (draft: ReportContent) => void;
}

function Section({ title, icon, children, className }: { title: string; icon?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("min-w-0 space-y-3", className)}>
      <h3 className="flex items-center gap-2 text-sm font-semibold tracking-wide text-brand-from uppercase dark:text-brand-to">
        <span aria-hidden className="bg-brand-gradient h-4 w-1 rounded-full" />
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

function Prose({ text, className }: { text: string; className?: string }) {
  return <p className={cn("text-sm leading-relaxed whitespace-pre-line md:text-[15px]", className)}>{text}</p>;
}

function Bullets({ items, numbered = false }: { items: string[]; numbered?: boolean }) {
  return (
    <ol className="space-y-2.5">
      {items.map((item, index) => (
        <li key={index} className="flex gap-3 text-sm leading-relaxed md:text-[15px]">
          <span
            aria-hidden
            className={cn(
              "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
              numbered ? "bg-brand-from/15 text-brand-from dark:text-brand-to" : "bg-muted text-muted-foreground",
            )}
          >
            {numbered ? index + 1 : "•"}
          </span>
          <span className="min-w-0">{item}</span>
        </li>
      ))}
    </ol>
  );
}

const SCORE_TONE = { poor: "bg-destructive/10 text-destructive", fair: "bg-warning/15 text-warning", good: "bg-success/10 text-success" };

function SeoFacts({ seo }: { seo: ReportSeo }) {
  return (
    <div className="space-y-3 rounded-xl border border-border/60 bg-muted/30 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={cn("rounded-lg px-2.5 py-1 text-lg font-semibold tabular-nums", SCORE_TONE[scoreBand(seo.score)])}>
          {seo.score}
          <span className="text-xs font-normal">/100</span>
        </span>
        <span className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
          <Globe aria-hidden className="size-3.5 shrink-0" />
          <span className="truncate">{seo.url}</span>
        </span>
      </div>
      {seo.top_issues.length > 0 && (
        <ul className="space-y-1.5 text-xs">
          {seo.top_issues.map((issue) => (
            <li key={issue.name} className="flex gap-2">
              <TriangleAlert aria-hidden className={cn("mt-0.5 size-3.5 shrink-0", issue.status === "fail" ? "text-destructive" : "text-warning")} />
              <span>
                <span className="font-medium">{issue.name}</span>: {issue.value}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ReportDocument({ report, draft, onDraftChange }: ReportDocumentProps) {
  const content = draft ?? report.content;
  const { metrics } = report;
  const channels = orderChannels(metrics.channels.map((c) => c.channel));
  const colors = channelColors(channels);
  const previousShort = metrics.period.previous_label.split(" ")[0];

  function text(key: TextKey, read: ReactNode, rows = "min-h-28") {
    if (!draft) return read;
    return (
      <TextEditor
        id={`edit-${key}`}
        label={sectionLabel(key)}
        value={draft[key] ?? ""}
        max={TEXT_LIMITS[key]}
        className={rows}
        placeholder={key === "seo_highlights" ? "Leave empty to omit this section" : undefined}
        onChange={(value) => onDraftChange({ ...draft, [key]: value })}
      />
    );
  }

  function list(key: ListKey, numbered = false) {
    if (!draft) return <Bullets items={content[key]} numbered={numbered} />;
    const { min, max } = LIST_LIMITS[key];
    return (
      <ListEditor
        id={`edit-${key}`} label={sectionLabel(key)} items={draft[key]} min={min} max={max} itemMax={ITEM_MAX}
        onChange={(items) => onDraftChange({ ...draft, [key]: items })}
      />
    );
  }

  const showSeo = metrics.seo !== null && (draft !== null || Boolean(content.seo_highlights));

  return (
    <article className="mx-auto max-w-5xl overflow-hidden rounded-2xl border border-border/60 bg-card shadow-card">
      <header className="bg-brand-gradient relative px-5 py-8 text-white md:px-10 md:py-10">
        <p className="text-[11px] font-semibold tracking-[0.18em] uppercase opacity-80">AgencyPilot AI · Monthly performance report</p>
        <p className="mt-3 text-2xl font-semibold tracking-tight md:text-4xl">{report.client_name}</p>
        <p className="mt-1 text-sm opacity-90 md:text-base">
          {report.month_label}
          {metrics.period.has_previous && <span className="opacity-80"> · compared with {metrics.period.previous_label}</span>}
        </p>
      </header>

      <div className="space-y-10 px-5 py-7 md:px-10 md:py-10">
        <div className="space-y-3">
          <ReportStatusBadge status={report.status} />
          {text("title", <h1 className="text-xl font-semibold tracking-tight text-balance md:text-2xl">{content.title}</h1>, "min-h-12 text-lg font-semibold")}
        </div>

        <Section title="Executive summary">{text("executive_summary", <Prose text={content.executive_summary} />, "min-h-36")}</Section>

        <Section title="Key metrics">
          <Stagger className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {metrics.kpis.map((kpi) => (
              <StaggerItem key={kpi.key}>
                <KpiTile kpi={kpi} period={`vs ${previousShort}`} footnote="No previous month" />
              </StaggerItem>
            ))}
          </Stagger>
        </Section>

        <div className="grid min-w-0 gap-4 lg:grid-cols-2">
          <div className="min-w-0">
            <SessionsChart timeseries={metrics.timeseries} channels={channels} colors={colors} description={`Daily sessions in ${report.month_label}`} />
          </div>
          <div className="min-w-0">
            <RevenueChart channels={metrics.channels} colors={colors} description={`Attributed revenue in ${report.month_label}`} />
          </div>
        </div>

        <div className="grid gap-10 md:grid-cols-2 md:gap-8">
          <Section title="Wins" icon={<ThumbsUp aria-hidden className="size-3.5" />}>{list("wins")}</Section>
          <Section title="Challenges" icon={<ShieldAlert aria-hidden className="size-3.5" />}>{list("challenges")}</Section>
        </div>

        <Section title="Channel performance">{text("channel_commentary", <Prose text={content.channel_commentary} />, "min-h-36")}</Section>

        {showSeo && metrics.seo && (
          <Section title="SEO highlights">
            <SeoFacts seo={metrics.seo} />
            {text("seo_highlights", <Prose text={content.seo_highlights ?? ""} />)}
          </Section>
        )}

        <Section title="Plan for next month">{list("next_month_plan", true)}</Section>

        <div className="border-l-2 border-brand-from/50 pl-4">
          {text("closing_note", <Prose text={content.closing_note} className="text-muted-foreground italic" />, "min-h-20")}
        </div>
      </div>

      <footer className="flex flex-col gap-2 border-t border-border/60 bg-muted/20 px-5 py-4 md:flex-row md:items-center md:justify-between md:px-10">
        <LlmMeta meta={report.meta} />
        <p className="text-xs text-muted-foreground">Numbers computed from the data · narrative written from them</p>
      </footer>
    </article>
  );
}
