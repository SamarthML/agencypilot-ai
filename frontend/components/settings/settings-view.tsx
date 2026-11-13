"use client";

import { CircleCheck, CircleDashed, KeyRound, RotateCw, Star } from "lucide-react";
import type { ReactNode } from "react";

import { Stagger, StaggerItem } from "@/components/motion";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { getAppSettings } from "@/lib/api";
import { PROVIDERS } from "@/lib/providers";
import type { AppSettings, ProviderSettings } from "@/lib/types";
import { cn } from "@/lib/utils";

function ProviderCard({ provider }: { provider: ProviderSettings }) {
  const meta = PROVIDERS.find((p) => p.id === provider.id);
  return (
    <Card className="h-full" size="sm">
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <p className="flex items-center gap-2 font-medium">
            <span aria-hidden className={cn("size-2.5 rounded-full", meta?.dotClass ?? "bg-muted-foreground")} />
            {provider.label}
          </p>
          {provider.is_default && (
            <span className="inline-flex items-center gap-1 rounded-md bg-brand-from/10 px-1.5 py-0.5 text-[11px] font-medium text-brand-from dark:text-brand-to">
              <Star aria-hidden className="size-3" /> Default
            </span>
          )}
        </div>
        <p className="truncate rounded bg-muted px-2 py-1 font-mono text-xs" title={provider.model}>
          {provider.model}
        </p>
        <p
          className={cn(
            "flex items-center gap-1.5 text-sm",
            provider.configured ? "text-success" : "text-muted-foreground",
          )}
        >
          {provider.configured ? <CircleCheck aria-hidden className="size-4" /> : <CircleDashed aria-hidden className="size-4" />}
          {provider.configured ? "API key configured" : "No API key"}
        </p>
      </CardContent>
    </Card>
  );
}

function Row({ label, hint, children }: { label: string; hint: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <div className="min-w-0">
        <dt className="text-sm font-medium">{label}</dt>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
      <dd className="shrink-0 font-mono text-sm tabular-nums">{children}</dd>
    </div>
  );
}

function onOff(value: boolean): string {
  return value ? "On" : "Off";
}

function ConfigList({ settings }: { settings: AppSettings }) {
  return (
    <Card>
      <CardHeader className="gap-1">
        <CardTitle className="text-base">Runtime configuration</CardTitle>
        <CardDescription>Read-only. Change these in backend/.env and restart the API.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="divide-y divide-border/60">
          <Row label="Copilot similarity threshold" hint="COPILOT_MIN_SIMILARITY: below this, Copilot answers 'not found' without an LLM call">
            {settings.copilot_min_similarity}
          </Row>
          <Row label="Copilot passages per answer" hint="COPILOT_TOP_K">{settings.copilot_top_k}</Row>
          <Row label="Embedding model" hint="EMBEDDING_MODEL: runs locally, no API cost">
            <span className="break-all">{settings.embedding_model}</span>
          </Row>
          <Row label="AI rate limit" hint="RATE_LIMIT_ENABLED / RATE_LIMIT_PER_MINUTE, per client IP">
            {settings.rate_limit_enabled ? `${settings.rate_limit_per_minute} / min` : "Off"}
          </Row>
          <Row label="Demo data seeding" hint="SEED_DEMO_DATA: fixture SEO audits for demo clients at startup">
            {onOff(settings.seed_demo_data)}
          </Row>
          <Row label="Cache lifetimes" hint="Insights summary / SEO audit">
            {settings.insights_cache_ttl_seconds / 60} min / {settings.seo_cache_ttl_seconds / 60} min
          </Row>
          <Row label="LLM timeout and retries" hint="LLM_TIMEOUT_SECONDS / LLM_MAX_RETRIES">
            {settings.llm_timeout_seconds} s · {settings.llm_max_retries} retries
          </Row>
          <Row label="Upload limits" hint="Insights CSV / Copilot documents">
            {settings.insights_max_upload_mb} MB / {settings.copilot_max_upload_mb} MB
          </Row>
        </dl>
      </CardContent>
    </Card>
  );
}

export function SettingsView() {
  const settings = useApi("app-settings", (signal) => getAppSettings({ signal, silent: true }));

  return (
    <div className="space-y-6 md:space-y-8">
      <PageHeader
        title="Settings"
        description="LLM providers and runtime configuration, read from the backend. API keys never leave the server."
      />
      {settings.error ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 rounded-2xl bg-destructive/10 p-4 text-sm text-destructive">
          <span className="flex-1">{settings.error.message}</span>
          <Button size="sm" variant="outline" onClick={settings.reload}>
            <RotateCw data-icon="inline-start" aria-hidden /> Retry
          </Button>
        </div>
      ) : !settings.data ? (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-36 rounded-2xl" />
            ))}
          </div>
          <Skeleton className="h-96 rounded-2xl" />
        </div>
      ) : (
        <>
          <section className="space-y-3">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <KeyRound aria-hidden className="size-4" /> LLM providers
            </h2>
            <Stagger className="grid gap-4 md:grid-cols-3">
              {settings.data.providers.map((provider) => (
                <StaggerItem key={provider.id}>
                  <ProviderCard provider={provider} />
                </StaggerItem>
              ))}
            </Stagger>
          </section>
          <ConfigList settings={settings.data} />
        </>
      )}
    </div>
  );
}
