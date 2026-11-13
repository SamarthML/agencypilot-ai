"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, FileText, LoaderCircle, Plus, RotateCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi, type ApiState } from "@/hooks/use-api";
import { ApiError, generateReport, getReportMonths, isAbortError } from "@/lib/api";
import { DEMO_CLIENTS, useClient } from "@/lib/client-context";
import { useIntent } from "@/lib/command-intents";
import { useModel } from "@/lib/model-context";
import { PROVIDERS } from "@/lib/providers";
import type { ReportMonth } from "@/lib/types";
import { cn } from "@/lib/utils";

/** What the backend does, in order. Timed client-side: the request itself is one call. */
const STEPS = [
  { label: "Computing the month's KPIs", ms: 900 },
  { label: "Comparing channels with the previous month", ms: 900 },
  { label: "Checking the latest SEO audit", ms: 900 },
  { label: "Writing the narrative from the numbers", ms: 0 },
] as const;

type Phase = { kind: "form" } | { kind: "running"; startedAt: number } | { kind: "error"; message: string };

function defaultMonth(months: readonly ReportMonth[] | undefined): string | undefined {
  if (!months) return undefined;
  return (months.find((m) => m.complete && m.has_previous) ?? months[0])?.month;
}

/** performance.now(), refreshed every 200 ms while `running`. */
function useNow(running: boolean): number {
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setNow(performance.now()), 200);
    return () => clearInterval(timer);
  }, [running]);
  return now;
}

function activeStep(elapsed: number): number {
  let step = 0;
  let budget = elapsed;
  while (step < STEPS.length - 1 && budget >= STEPS[step].ms) budget -= STEPS[step++].ms;
  return step;
}

function StepIcon({ state }: { state: "done" | "active" | "todo" }) {
  if (state === "done") return <Check aria-hidden className="size-4 text-success" />;
  if (state === "active") return <LoaderCircle aria-hidden className="size-4 animate-spin text-brand-from" />;
  return <span className="size-1.5 rounded-full bg-muted-foreground/50" />;
}

function GenerationProgress({ startedAt }: { startedAt: number }) {
  const now = useNow(true);
  const elapsed = Math.max(0, now - startedAt);
  const active = activeStep(elapsed);
  // Approaches but never reaches 100% until the response arrives.
  const progress = Math.min(95, 100 * (1 - Math.exp(-elapsed / 9000)));
  return (
    <div className="space-y-4 py-2" role="status" aria-live="polite">
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="bg-brand-gradient h-full rounded-full"
          animate={{ width: `${Math.max(progress, 4)}%` }}
          transition={{ ease: "easeOut", duration: 0.4 }}
        />
      </div>
      <ol className="space-y-2.5">
        {STEPS.map((step, index) => {
          const state = index < active ? "done" : index === active ? "active" : "todo";
          return (
            <motion.li
              key={step.label}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: state === "todo" ? 0.45 : 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-center gap-2.5 text-sm"
            >
              <span className="flex size-5 items-center justify-center">
                <StepIcon state={state} />
              </span>
              <span className={cn(state === "active" && "font-medium")}>{step.label}</span>
            </motion.li>
          );
        })}
      </ol>
      <p className="text-xs text-muted-foreground tabular-nums">
        {Math.round(elapsed / 1000)} s · reasoning models can take up to a minute
      </p>
    </div>
  );
}

function MonthPicker({
  months,
  value,
  onChange,
}: {
  months: ApiState<ReportMonth[]>;
  value: string | undefined;
  onChange: (month: string) => void;
}) {
  if (months.loading) return <Skeleton className="h-9 w-full rounded-lg" />;
  if (months.error || !months.data?.length) {
    return (
      <p className="text-sm text-destructive">
        {months.error?.message ?? "This client has no data yet. Upload a CSV on the Insights page."}
      </p>
    );
  }
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id="report-month" className="w-full">
        <SelectValue placeholder="Choose a month" />
      </SelectTrigger>
      <SelectContent>
        {months.data.map((m) => (
          <SelectItem key={m.month} value={m.month}>
            {m.label}
            {!m.complete && <span className="text-muted-foreground">{" (partial)"}</span>}
            {!m.has_previous && <span className="text-muted-foreground">{" · no comparison"}</span>}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function ClientPicker({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id="report-client" className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {DEMO_CLIENTS.map((c) => (
          <SelectItem key={c.id} value={c.id}>
            {c.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** Mounted only while the dialog is open, so every open starts from a fresh form. */
function NewReportBody({ onClose, onRunningChange }: { onClose: () => void; onRunningChange: (running: boolean) => void }) {
  const router = useRouter();
  const { client } = useClient();
  const { provider } = useModel();
  const [clientId, setClientId] = useState(client.id);
  const [month, setMonth] = useState<string>();
  const [phase, setPhase] = useState<Phase>({ kind: "form" });
  const controller = useRef<AbortController | null>(null);
  const months = useApi(`report-months:${clientId}`, (signal) => getReportMonths(clientId, { signal, silent: true }));
  const chosenMonth = month ?? defaultMonth(months.data);
  const providerLabel = PROVIDERS.find((p) => p.id === provider)?.label ?? provider;

  // Closing the dialog mid-generation cancels the request.
  useEffect(() => () => controller.current?.abort(), []);

  function update(next: Phase) {
    setPhase(next);
    onRunningChange(next.kind === "running");
  }

  async function generate() {
    if (!chosenMonth) return;
    const abort = new AbortController();
    controller.current = abort;
    update({ kind: "running", startedAt: performance.now() });
    try {
      const report = await generateReport({ client: clientId, month: chosenMonth }, abort.signal);
      toast.success("Report ready", { description: `${report.client_name} · ${report.month_label}` });
      onRunningChange(false);
      onClose();
      router.push(`/reports/${report.id}`);
    } catch (error) {
      if (isAbortError(error)) return;
      update({ kind: "error", message: error instanceof ApiError ? error.message : "Generation failed." });
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <FileText aria-hidden className="size-4" /> New monthly report
        </DialogTitle>
        <DialogDescription>
          KPIs are computed from the client&apos;s data; {providerLabel} writes the narrative from those numbers
          only.
        </DialogDescription>
      </DialogHeader>
      <AnimatePresence mode="wait" initial={false}>
        {phase.kind === "running" ? (
          <motion.div key="progress" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <GenerationProgress startedAt={phase.startedAt} />
          </motion.div>
        ) : (
          <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="report-client" className="text-sm font-medium">
                Client
              </label>
              <ClientPicker
                value={clientId}
                onChange={(id) => {
                  setClientId(id);
                  setMonth(undefined);
                }}
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="report-month" className="text-sm font-medium">
                Month
              </label>
              <MonthPicker months={months} value={chosenMonth} onChange={setMonth} />
            </div>
            {phase.kind === "error" && (
              <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {phase.message}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      <DialogFooter>
        {phase.kind === "running" ? (
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
        ) : (
          <Button onClick={generate} disabled={!chosenMonth}>
            {phase.kind === "error" && <RotateCw data-icon="inline-start" aria-hidden />}
            {phase.kind === "error" ? "Try again" : "Generate report"}
          </Button>
        )}
      </DialogFooter>
    </>
  );
}

interface NewReportDialogProps {
  /** Opens on the command palette's "New report". Set on one instance per page only. */
  openOnCommand?: boolean;
}

export function NewReportDialog({ openOnCommand = false }: NewReportDialogProps) {
  const [open, setOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [commandRequested, commandHandled] = useIntent("reports:new");
  const isOpen = open || (openOnCommand && commandRequested);

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (next) return;
    setRunning(false);
    commandHandled();
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-brand-gradient border-0 text-white hover:opacity-90">
          <Plus data-icon="inline-start" aria-hidden /> New report
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md" onInteractOutside={(e) => running && e.preventDefault()}>
        <NewReportBody onClose={() => onOpenChange(false)} onRunningChange={setRunning} />
      </DialogContent>
    </Dialog>
  );
}
