"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { hostname } from "@/lib/seo";
import { cn } from "@/lib/utils";

/**
 * The audit is one request, so these steps are paced by typical timings rather than server
 * events: fetching usually takes ~1 s, checks are instant, the AI report takes a few seconds.
 */
const STEPS = [
  { label: "Fetching page", detail: "Safe fetch: public addresses only, 10 s and 2 MB limits", at: 0 },
  { label: "Running 10 checks", detail: "Title, meta, headings, images, canonical, mobile…", at: 1400 },
  { label: "Writing AI recommendations", detail: "Grounded in the check results", at: 2600 },
] as const;
const TICK_MS = 150;

function useElapsed(): number {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const started = performance.now();
    const timer = setInterval(() => setElapsed(performance.now() - started), TICK_MS);
    return () => clearInterval(timer);
  }, []);
  return elapsed;
}

function StepIcon({ state }: { state: "done" | "active" | "pending" }) {
  if (state === "done") {
    return (
      <span className="flex size-7 items-center justify-center rounded-full bg-success/15 text-success">
        <Check aria-hidden className="size-4" />
      </span>
    );
  }
  if (state === "active") {
    return (
      <span className="flex size-7 items-center justify-center rounded-full bg-brand-from/15 text-brand-from">
        <Loader2 aria-hidden className="size-4 animate-spin" />
      </span>
    );
  }
  return <span className="size-7 rounded-full border border-dashed border-border" aria-hidden />;
}

/** Mount with a new `key` per audit so the timer restarts. */
export function AuditProgress({ url }: { url: string }) {
  const elapsed = useElapsed();
  const active = STEPS.reduce((current, step, index) => (elapsed >= step.at ? index : current), 0);
  // Creeps towards 95% so the bar never "finishes" before the response does.
  const progress = Math.min(95, 8 + (elapsed / 6000) * 87);

  return (
    <Card aria-live="polite" aria-busy>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Auditing <span className="font-medium break-all text-foreground">{hostname(url)}</span>
          </p>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="bg-brand-gradient h-full rounded-full"
              initial={{ width: "4%" }}
              animate={{ width: `${progress}%` }}
              transition={{ ease: "easeOut", duration: TICK_MS / 1000 }}
            />
          </div>
        </div>
        <ol className="space-y-3">
          {STEPS.map((step, index) => {
            const state = index < active ? "done" : index === active ? "active" : "pending";
            return (
              <motion.li
                key={step.label}
                className="flex items-start gap-3"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: state === "pending" ? 0.5 : 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <StepIcon state={state} />
                <div className="min-w-0 pt-0.5">
                  <p className={cn("text-sm font-medium", state === "pending" && "text-muted-foreground")}>
                    {step.label}
                  </p>
                  <p className="text-xs text-muted-foreground">{step.detail}</p>
                </div>
              </motion.li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
