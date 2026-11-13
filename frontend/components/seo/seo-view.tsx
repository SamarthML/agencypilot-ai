"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { AiReport, AiUnavailable } from "@/components/seo/ai-report";
import { AuditEmpty } from "@/components/seo/audit-empty";
import { AuditErrorCard } from "@/components/seo/audit-error";
import { AuditHero } from "@/components/seo/audit-hero";
import { AuditOverview } from "@/components/seo/audit-overview";
import { AuditProgress } from "@/components/seo/audit-progress";
import { ChecksPanel } from "@/components/seo/checks-panel";
import { RecentAudits } from "@/components/seo/recent-audits";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getSeoAudit, runSeoAudit } from "@/lib/api";
import { useClient } from "@/lib/client-context";
import type { SeoAuditResponse } from "@/lib/types";

type View =
  | { kind: "idle" }
  | { kind: "running"; url: string; run: number }
  | { kind: "loading"; id: string }
  | { kind: "result"; audit: SeoAuditResponse; retrying: boolean }
  | { kind: "error"; error: ApiError; url: string | null };

function asApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError(String(error), null);
}

function viewKey(view: View): string {
  if (view.kind === "result") return `result-${view.audit.id}`;
  if (view.kind === "running") return `running-${view.run}`;
  return view.kind;
}

function PrintHeader({ audit }: { audit: SeoAuditResponse }) {
  return (
    <div className="hidden border-b pb-3 print:block">
      <p className="text-xs text-muted-foreground">AgencyPilot AI · SEO audit report</p>
      <p className="text-lg font-semibold break-all">{audit.final_url}</p>
      <p className="text-xs text-muted-foreground">{new Date(audit.created_at).toLocaleString("en-US")}</p>
    </div>
  );
}

function AuditResult({ view, onRerun, onRetryAi }: {
  view: Extract<View, { kind: "result" }>;
  onRerun: () => void;
  onRetryAi: () => void;
}) {
  const { audit } = view;
  return (
    <div className="space-y-4 md:space-y-6">
      <PrintHeader audit={audit} />
      <AuditOverview audit={audit} onRerun={onRerun} />
      <ChecksPanel checks={audit.checks} />
      {audit.ai ? (
        <AiReport report={audit.ai} page={audit.page} meta={audit.meta} />
      ) : (
        <AiUnavailable error={audit.ai_error} retrying={view.retrying} onRetry={onRetryAi} />
      )}
    </div>
  );
}

export function SeoView() {
  const { client } = useClient();
  const [view, setView] = useState<View>({ kind: "idle" });
  const [historyVersion, setHistoryVersion] = useState(0);
  // The latest action wins: responses from superseded runs are ignored.
  const latestRun = useRef(0);

  async function audit(url: string) {
    const run = ++latestRun.current;
    setView({ kind: "running", url, run });
    try {
      const result = await runSeoAudit({ url, client_id: client.id });
      if (run !== latestRun.current) return;
      setView({ kind: "result", audit: result, retrying: false });
      setHistoryVersion((v) => v + 1);
    } catch (error) {
      if (run === latestRun.current) setView({ kind: "error", error: asApiError(error), url });
    }
  }

  async function open(id: string) {
    const run = ++latestRun.current;
    setView({ kind: "loading", id });
    try {
      const result = await getSeoAudit(id, { silent: true });
      if (run === latestRun.current) setView({ kind: "result", audit: result, retrying: false });
    } catch (error) {
      if (run === latestRun.current) setView({ kind: "error", error: asApiError(error), url: null });
    }
  }

  /** Re-runs the audit in place; the backend never caches a failed AI report. */
  async function retryAi(current: SeoAuditResponse) {
    const run = ++latestRun.current;
    setView({ kind: "result", audit: current, retrying: true });
    try {
      const result = await runSeoAudit({ url: current.url, client_id: client.id });
      if (run !== latestRun.current) return;
      setView({ kind: "result", audit: result, retrying: false });
      setHistoryVersion((v) => v + 1);
      if (!result.ai) toast.error("AI is still unavailable", { description: result.ai_error ?? undefined });
    } catch (error) {
      if (run !== latestRun.current) return;
      setView({ kind: "result", audit: current, retrying: false });
      toast.error("Retry failed", { description: asApiError(error).message });
    }
  }

  const selectedId = view.kind === "result" ? view.audit.id : view.kind === "loading" ? view.id : null;
  const retryUrl = view.kind === "error" ? view.url : null;

  return (
    <div className="space-y-6 md:space-y-8">
      <AuditHero clientName={client.name} running={view.kind === "running"} onAudit={audit} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px] xl:grid-cols-[minmax(0,1fr)_340px] print:block">
        <div className="min-w-0">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={viewKey(view)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2 }}
            >
              {view.kind === "idle" && <AuditEmpty />}
              {view.kind === "running" && <AuditProgress url={view.url} />}
              {view.kind === "loading" && <Skeleton className="h-64 rounded-2xl" />}
              {view.kind === "error" && (
                <AuditErrorCard
                  error={view.error}
                  url={view.url}
                  onRetry={retryUrl ? () => void audit(retryUrl) : null}
                />
              )}
              {view.kind === "result" && (
                <AuditResult
                  view={view}
                  onRerun={() => void audit(view.audit.url)}
                  onRetryAi={() => void retryAi(view.audit)}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
        <aside className="min-w-0 print:hidden">
          <RecentAudits
            clientId={client.id}
            clientName={client.name}
            version={historyVersion}
            selectedId={selectedId}
            onSelect={(id) => void open(id)}
          />
        </aside>
      </div>
    </div>
  );
}
