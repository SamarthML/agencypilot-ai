"use client";

import { ArrowRight, Lightbulb, RotateCw, Sparkles, Tags, TriangleAlert, Wrench } from "lucide-react";
import type { ReactNode } from "react";

import { LlmMeta } from "@/components/llm-meta";
import { Stagger, StaggerItem } from "@/components/motion";
import { CopyButton } from "@/components/seo/copy-button";
import { PriorityBadge } from "@/components/seo/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { isInRange, META_RANGE, TITLE_RANGE } from "@/lib/seo";
import type { LlmCallMeta, SeoAiReport, SeoPageSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

function SectionCard({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Sparkles;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Card className="break-inside-avoid">
      <CardHeader className="gap-1">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon aria-hidden className="size-4 text-muted-foreground" /> {title}
        </CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="@container">{children}</CardContent>
    </Card>
  );
}

function LengthNote({ length, range }: { length: number; range: { min: number; max: number } }) {
  const ok = isInRange(length, range);
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs tabular-nums", ok ? "text-muted-foreground" : "text-warning")}>
      {!ok && <TriangleAlert aria-hidden className="size-3.5" />}
      {length} chars{!ok && ` · recommended ${range.min}–${range.max}`}
    </span>
  );
}

interface BeforeAfterProps {
  label: string;
  before: string | null;
  after: string;
  range: { min: number; max: number };
}

function BeforeAfter({ label, before, after, range }: BeforeAfterProps) {
  return (
    <div className="space-y-2 break-inside-avoid">
      <h4 className="text-sm font-medium">{label}</h4>
      <div className="grid gap-2 @xl:grid-cols-[1fr_auto_1fr] @xl:items-stretch">
        <div className="space-y-2 rounded-xl border border-dashed p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Before</span>
            {before ? <LengthNote length={before.length} range={range} /> : null}
          </div>
          <p className={cn("text-sm break-words", !before && "text-muted-foreground italic")}>
            {before ?? "Missing"}
          </p>
        </div>
        <ArrowRight aria-hidden className="hidden size-4 self-center text-muted-foreground @xl:block" />
        <div className="space-y-2 rounded-xl border border-success/30 bg-success/5 p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium tracking-wide text-success uppercase">After</span>
            <div className="flex items-center gap-1">
              <LengthNote length={after.length} range={range} />
              <CopyButton text={after} label={`suggested ${label.toLowerCase()}`} />
            </div>
          </div>
          <p className="text-sm break-words">{after}</p>
        </div>
      </div>
    </div>
  );
}

interface AiReportProps {
  report: SeoAiReport;
  page: SeoPageSummary;
  meta: LlmCallMeta | null;
}

export function AiReport({ report, page, meta }: AiReportProps) {
  return (
    <Stagger className="@container space-y-4">
      <StaggerItem>
        <Card className="relative overflow-hidden break-inside-avoid">
          <div aria-hidden className="bg-brand-gradient absolute inset-x-0 top-0 h-0.5 opacity-80" />
          <CardHeader className="gap-1">
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles aria-hidden className="size-4 text-brand-from" /> AI recommendations
            </CardTitle>
            <CardDescription>Written from the check results and the page&apos;s own content.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed md:text-base">{report.summary}</p>
          </CardContent>
        </Card>
      </StaggerItem>

      <StaggerItem>
        <SectionCard icon={Wrench} title="Top fixes" description="Most important first.">
          <ol className="space-y-3">
            {report.top_fixes.map((fix, index) => (
              <li key={`${index}-${fix.title}`} className="flex gap-3 break-inside-avoid">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium tabular-nums">
                  {index + 1}
                </span>
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium">{fix.title}</p>
                    <PriorityBadge priority={fix.priority} />
                  </div>
                  <p className="text-sm text-muted-foreground">{fix.detail}</p>
                  <p className="text-xs text-muted-foreground">
                    Impact: <span className="text-foreground">{fix.impact}</span>
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </SectionCard>
      </StaggerItem>

      <StaggerItem>
        <SectionCard icon={Sparkles} title="Before vs after" description="Suggested rewrites, ready to paste.">
          <div className="space-y-5">
            <BeforeAfter label="Title" before={page.title} after={report.rewritten_title} range={TITLE_RANGE} />
            <BeforeAfter
              label="Meta description"
              before={page.meta_description}
              after={report.rewritten_meta_description}
              range={META_RANGE}
            />
          </div>
        </SectionCard>
      </StaggerItem>

      <StaggerItem className="grid gap-4 @2xl:grid-cols-2">
        <SectionCard icon={Tags} title="Suggested keywords">
          <ul className="flex flex-wrap gap-2">
            {report.suggested_keywords.map((keyword) => (
              <li key={keyword} className="rounded-full border bg-muted/40 px-3 py-1 text-xs">
                {keyword}
              </li>
            ))}
          </ul>
        </SectionCard>
        <SectionCard icon={Lightbulb} title="Content ideas">
          <ul className="space-y-2">
            {report.content_ideas.map((idea) => (
              <li key={idea} className="flex gap-2 text-sm">
                <Lightbulb aria-hidden className="mt-0.5 size-4 shrink-0 text-warning" />
                <span>{idea}</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      </StaggerItem>

      {meta && (
        <StaggerItem>
          <footer className="rounded-xl border border-dashed px-4 py-3">
            <LlmMeta meta={meta} />
          </footer>
        </StaggerItem>
      )}
    </Stagger>
  );
}

interface AiUnavailableProps {
  error: string | null;
  retrying: boolean;
  onRetry: () => void;
}

/** Shown when the audit succeeded but the LLM step didn't; checks and score are still valid. */
export function AiUnavailable({ error, retrying, onRetry }: AiUnavailableProps) {
  return (
    <Card className="border-warning/30 bg-warning/5">
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <TriangleAlert aria-hidden className="size-5 shrink-0 text-warning" />
        <div className="min-w-0 flex-1 space-y-0.5">
          <p className="text-sm font-medium">AI recommendations unavailable</p>
          <p className="text-sm break-words text-muted-foreground">
            {error ?? "The model didn't return a report."} The score and checks above are complete.
          </p>
        </div>
        <Button variant="outline" onClick={onRetry} disabled={retrying} className="shrink-0 print:hidden">
          <RotateCw data-icon="inline-start" aria-hidden className={cn(retrying && "animate-spin")} />
          {retrying ? "Retrying…" : "Retry AI"}
        </Button>
      </CardContent>
    </Card>
  );
}
