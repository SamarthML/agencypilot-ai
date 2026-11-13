"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Compass, X } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { getNavItem } from "@/lib/nav";
import { STORAGE_KEYS } from "@/lib/storage-keys";

type OnboardingState = "open" | "dismissed";
const STATES: readonly OnboardingState[] = ["open", "dismissed"];

/** A suggested first tour: one concrete thing to try in each micro app, using the demo data. */
const STEPS = [
  { href: "/insights", tryThis: "Open the sample data and click Generate for a summary built only from the KPIs." },
  { href: "/seo", tryThis: "Paste any URL: 10 checks, a 0–100 score and AI fixes for what failed." },
  { href: "/copilot", tryThis: "Ask about Bloom Bakery's brief and click a citation to see the source page." },
  { href: "/reports", tryThis: "Generate a monthly report, edit any section, then export it as a PDF." },
] as const;

function Step({ index, href, tryThis }: { index: number; href: string; tryThis: string }) {
  const item = getNavItem(href);
  const Icon = item.icon;
  return (
    <li>
      <Link
        href={href}
        className="group flex h-full gap-3 rounded-xl border border-border/60 bg-background/60 p-3.5 outline-none transition-colors hover:border-border hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-semibold tabular-nums">
          {index + 1}
        </span>
        <span className="min-w-0 space-y-0.5">
          <span className="flex items-center gap-1.5 text-sm font-medium">
            <Icon aria-hidden className="size-3.5 text-muted-foreground" />
            {item.label}
            <ArrowRight aria-hidden className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
          </span>
          <span className="block text-xs leading-relaxed text-muted-foreground">{tryThis}</span>
        </span>
      </Link>
    </li>
  );
}

/** First-visit guide to the four micro apps. Dismissal is remembered in localStorage. */
export function OnboardingBanner() {
  // Hidden on the server so returning visitors who dismissed it never see a flash.
  const [state, setState] = useLocalStorage(STORAGE_KEYS.onboarding, "open", STATES, "dismissed");

  return (
    <AnimatePresence initial={false}>
      {state === "open" && (
        <motion.section
          key="onboarding"
          aria-labelledby="onboarding-heading"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="overflow-hidden"
        >
          <div className="relative rounded-2xl border border-border/60 bg-card p-5 shadow-card md:p-6">
            <Button
              variant="ghost"
              size="icon-sm"
              className="absolute top-3 right-3 text-muted-foreground"
              onClick={() => setState("dismissed")}
              aria-label="Dismiss getting started guide"
            >
              <X aria-hidden />
            </Button>
            <div className="mb-4 flex items-start gap-3 pr-8">
              <span className="bg-brand-gradient flex size-9 shrink-0 items-center justify-center rounded-xl text-white">
                <Compass aria-hidden className="size-4.5" />
              </span>
              <div className="space-y-1">
                <h2 id="onboarding-heading" className="font-semibold tracking-tight">
                  New here? Four micro apps, one workspace
                </h2>
                <p className="text-sm text-muted-foreground">
                  Demo data is already loaded for three clients. Switch client in the top bar, or
                  press <kbd className="rounded border border-border bg-muted px-1 font-sans text-xs">Ctrl/⌘ K</kbd>{" "}
                  to jump anywhere.
                </p>
              </div>
            </div>
            <ol className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
              {STEPS.map((step, index) => (
                <Step key={step.href} index={index} {...step} />
              ))}
            </ol>
            <div className="mt-4 flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setState("dismissed")}>
                Got it
              </Button>
            </div>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
}
