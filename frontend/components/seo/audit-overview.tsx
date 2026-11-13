import { Clock, Download, ExternalLink, FileCode2, Gauge, RotateCw, Zap, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { ScoreGauge } from "@/components/seo/score-gauge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatInteger } from "@/lib/format";
import { formatBytes } from "@/lib/seo";
import type { SeoAuditResponse } from "@/lib/types";

interface AuditOverviewProps {
  audit: SeoAuditResponse;
  onRerun: () => void;
}

function Fact({ icon: Icon, label, children }: { icon: LucideIcon; label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon aria-hidden className="size-3.5" /> {label}
      </dt>
      <dd className="truncate text-sm font-medium tabular-nums">{children}</dd>
    </div>
  );
}

function issueSummary(audit: SeoAuditResponse): string {
  const fails = audit.checks.filter((c) => c.status === "fail").length;
  const warns = audit.checks.filter((c) => c.status === "warn").length;
  if (fails + warns === 0) return "All 10 checks passed.";
  return `${fails} failed and ${warns} warning${warns === 1 ? "" : "s"} across ${audit.checks.length} checks.`;
}

/** Score gauge with the fetch facts beside it, plus PDF / re-run actions. */
export function AuditOverview({ audit, onRerun }: AuditOverviewProps) {
  const audited = new Date(audit.created_at).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <Card className="@container break-inside-avoid">
      {/* Container queries: this card sits beside a sidebar and a history column, so its
          own width (not the viewport's) decides when the gauge and facts go side by side. */}
      <CardContent className="flex flex-col items-center gap-6 @xl:flex-row @xl:items-center">
        <ScoreGauge score={audit.score} />
        <div className="w-full min-w-0 flex-1 space-y-4">
          <div className="space-y-1 text-center @xl:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 @xl:justify-start">
              <h2 className="text-lg font-semibold tracking-tight">SEO score</h2>
              {audit.cached && (
                <Badge variant="secondary" className="gap-1">
                  <Zap aria-hidden className="size-3" /> Cached result
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">{issueSummary(audit)}</p>
          </div>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 @3xl:grid-cols-4">
            <div className="col-span-2 min-w-0 space-y-1 @3xl:col-span-4">
              <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <ExternalLink aria-hidden className="size-3.5" /> Final URL
              </dt>
              <dd className="truncate text-sm font-medium">
                <a href={audit.final_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                  {audit.final_url}
                </a>
              </dd>
            </div>
            <Fact icon={Clock} label="Load time">
              {formatInteger(audit.load_ms)} ms
            </Fact>
            <Fact icon={FileCode2} label="Page size">
              {formatBytes(audit.html_bytes)}
            </Fact>
            <Fact icon={Gauge} label="Status code">
              HTTP {audit.status_code}
            </Fact>
            <Fact icon={Clock} label="Audited">
              {audited}
            </Fact>
          </dl>
          <div className="flex flex-wrap justify-center gap-2 @xl:justify-start print:hidden">
            <Button variant="outline" onClick={() => window.print()}>
              <Download data-icon="inline-start" aria-hidden /> Download PDF
            </Button>
            <Button variant="ghost" onClick={onRerun}>
              <RotateCw data-icon="inline-start" aria-hidden /> Re-run
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
