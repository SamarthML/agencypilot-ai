"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { useClient } from "@/lib/client-context";
import { useModel } from "@/lib/model-context";

function greetingFor(hour: number): string {
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

const noopSubscribe = () => () => {};

/** Greeting uses the viewer's local time; the server renders a neutral fallback. */
function useGreeting(): string {
  return useSyncExternalStore(
    noopSubscribe,
    () => greetingFor(new Date().getHours()),
    () => "Welcome back",
  );
}

export function HeroCard() {
  const greeting = useGreeting();
  const { client } = useClient();
  const { providerOption } = useModel();

  return (
    <section className="relative overflow-hidden rounded-2xl border border-border/60 bg-card p-6 shadow-card md:p-8">
      <div
        aria-hidden
        className="bg-brand-gradient pointer-events-none absolute -top-24 -right-16 size-72 rounded-full opacity-20 blur-3xl"
      />
      <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Viewing <span className="font-medium text-foreground">{client.name}</span> · using{" "}
            <span className="font-medium text-foreground">{providerOption.label}</span>
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-balance md:text-4xl">
            {greeting}, here&apos;s your agency{" "}
            <span className="text-brand-gradient">at a glance</span>
          </h1>
          <p className="max-w-xl text-sm text-muted-foreground md:text-base">
            Four AI micro apps for client work: insights, SEO, document Q&amp;A and reporting.
            Every LLM call is tracked for tokens, latency and cost.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button asChild size="lg" className="bg-brand-gradient border-0 text-white hover:opacity-90">
            <Link href="/insights">
              Open Insights <ArrowRight data-icon="inline-end" aria-hidden />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/usage">View usage</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
