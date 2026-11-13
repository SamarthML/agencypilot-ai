"use client";

import { ArrowRight, CircleCheck, Sparkles, TriangleAlert, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { LlmMeta } from "@/components/insights/llm-meta";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, generateAiSummary } from "@/lib/api";
import { useModel } from "@/lib/model-context";
import type { Days, InsightSummary } from "@/lib/types";

interface AiSummaryCardProps {
  clientId: string;
  days: Days;
}

interface Keyed<T> {
  key: string;
  value: T;
}

function BulletSection({ title, items, icon: Icon, iconClass }: {
  title: string;
  items: string[];
  icon: LucideIcon;
  iconClass: string;
}) {
  if (items.length === 0) return null;
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</h3>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex gap-2 text-sm leading-relaxed">
            <Icon aria-hidden className={`mt-0.5 size-4 shrink-0 ${iconClass}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SummaryBody({ result }: { result: InsightSummary }) {
  const { summary } = result;
  return (
    <div className="space-y-5">
      <p className="text-base font-semibold text-balance md:text-lg">{summary.headline}</p>
      <div className="grid gap-5 lg:grid-cols-3">
        <BulletSection title="Highlights" items={summary.highlights} icon={CircleCheck} iconClass="text-success" />
        <BulletSection title="Concerns" items={summary.concerns} icon={TriangleAlert} iconClass="text-destructive" />
        <BulletSection title="Next steps" items={summary.recommendations} icon={ArrowRight} iconClass="text-muted-foreground" />
      </div>
      <LlmMeta meta={result.meta} />
    </div>
  );
}

function SummarySkeleton({ providerLabel }: { providerLabel: string }) {
  return (
    <div className="space-y-3" aria-live="polite">
      <p className="text-sm text-muted-foreground">Asking {providerLabel} to explain the computed KPIs…</p>
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

export function AiSummaryCard({ clientId, days }: AiSummaryCardProps) {
  const { provider, providerOption } = useModel();
  const contextKey = `${clientId}:${days}:${provider}`;
  const [result, setResult] = useState<Keyed<InsightSummary>>();
  const [error, setError] = useState<Keyed<string>>();
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  async function generate() {
    const key = contextKey;
    setPendingKey(key);
    try {
      setResult({ key, value: await generateAiSummary(clientId, days) });
      setError(undefined);
    } catch (e) {
      setError({ key, value: e instanceof ApiError ? e.message : "Something went wrong." });
    } finally {
      setPendingKey((current) => (current === key ? null : current));
    }
  }

  const summary = result?.key === contextKey ? result.value : undefined;
  const errorMessage = error?.key === contextKey ? error.value : undefined;
  const loading = pendingKey === contextKey;

  return (
    <Card className="relative overflow-hidden">
      <div aria-hidden className="bg-brand-gradient absolute inset-x-0 top-0 h-0.5 opacity-80" />
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles aria-hidden className="size-4 text-brand-from" /> AI summary
          </CardTitle>
          <CardDescription>Written only from the computed KPIs: no raw rows reach the model.</CardDescription>
        </div>
        {!summary && (
          <Button onClick={generate} disabled={loading} className="bg-brand-gradient shrink-0 border-0 text-white hover:opacity-90">
            <Sparkles data-icon="inline-start" aria-hidden />
            {loading ? "Generating…" : "Generate"}
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {loading ? (
          <SummarySkeleton providerLabel={providerOption.label} />
        ) : summary ? (
          <SummaryBody result={summary} />
        ) : errorMessage ? (
          <p className="text-sm text-destructive">{errorMessage}</p>
        ) : (
          <p className="text-sm text-muted-foreground">
            Generate a short, grounded summary of the last {days} days with {providerOption.label}.
            Repeat requests are served from cache at $0.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
