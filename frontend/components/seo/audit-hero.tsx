"use client";

import { ArrowRight, Globe, Loader2, SearchCheck } from "lucide-react";
import { useState, type FormEvent } from "react";

import { FadeIn } from "@/components/motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EXAMPLE_URLS, hostname } from "@/lib/seo";

interface AuditHeroProps {
  clientName: string;
  running: boolean;
  onAudit: (url: string) => void;
}

/** Large URL input + example chips. The audit is saved to the client chosen in the top bar. */
export function AuditHero({ clientName, running, onAudit }: AuditHeroProps) {
  const [url, setUrl] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (url.trim()) onAudit(url.trim());
  }

  function runExample(example: string) {
    setUrl(example);
    onAudit(example);
  }

  return (
    <FadeIn>
      <section className="relative overflow-hidden rounded-2xl border border-border/60 bg-card p-5 shadow-card md:p-8 print:hidden">
        <div
          aria-hidden
          className="bg-brand-gradient pointer-events-none absolute -top-28 -right-20 size-72 rounded-full opacity-15 blur-3xl"
        />
        <div className="relative space-y-5">
          <div className="space-y-2">
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <SearchCheck aria-hidden className="size-4" />
              SEO Audit · saved to <span className="font-medium text-foreground">{clientName}</span>
            </p>
            <h1 className="text-2xl font-semibold tracking-tight text-balance md:text-3xl">
              Audit any page in <span className="text-brand-gradient">seconds</span>
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground md:text-base">
              10 rule-based checks, a 0–100 score computed in code, and AI recommendations grounded
              in the results.
            </p>
          </div>

          <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Globe
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                type="text"
                inputMode="url"
                autoComplete="url"
                spellCheck={false}
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/page"
                aria-label="Page URL to audit"
                className="h-12 pl-10 text-base md:text-base"
                maxLength={2048}
                disabled={running}
              />
            </div>
            <Button
              type="submit"
              disabled={running || !url.trim()}
              className="bg-brand-gradient h-12 border-0 px-6 text-base text-white hover:opacity-90"
            >
              {running ? (
                <Loader2 data-icon="inline-start" aria-hidden className="animate-spin" />
              ) : null}
              {running ? "Auditing…" : "Run audit"}
              {!running && <ArrowRight data-icon="inline-end" aria-hidden />}
            </Button>
          </form>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Try:</span>
            {EXAMPLE_URLS.map((example) => (
              <Button
                key={example}
                type="button"
                variant="outline"
                size="sm"
                className="h-7 rounded-full font-normal"
                disabled={running}
                onClick={() => runExample(example)}
              >
                {hostname(example)}
              </Button>
            ))}
          </div>
        </div>
      </section>
    </FadeIn>
  );
}
