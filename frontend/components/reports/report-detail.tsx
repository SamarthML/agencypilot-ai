"use client";

import { ArrowLeft, CircleCheck, Download, FileWarning, LoaderCircle, PencilLine, RotateCcw, Save, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FadeIn } from "@/components/motion";
import { ReportDocument } from "@/components/reports/report-document";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { deleteReport, downloadReportPdf, getReport, updateReport } from "@/lib/api";
import { normalizeContent, validateContent } from "@/lib/reports";
import type { Report, ReportContent, ReportUpdate } from "@/lib/types";

type Busy = "save" | "status" | "pdf" | "delete" | null;

function DeleteButton({ report, busy, onConfirm }: { report: Report; busy: Busy; onConfirm: () => void }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-destructive" disabled={busy !== null}>
          <Trash2 data-icon="inline-start" aria-hidden />
          <span className="max-sm:sr-only">Delete</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete this report?</DialogTitle>
          <DialogDescription>
            {report.client_name} · {report.month_label} will be removed permanently. The underlying data and LLM usage
            log are kept.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button variant="destructive" onClick={onConfirm} disabled={busy === "delete"}>
            {busy === "delete" ? "Deleting…" : "Delete report"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <Skeleton className="h-36 rounded-2xl" />
      <Skeleton className="h-8 w-2/3" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28 rounded-2xl" />
        ))}
      </div>
      <Skeleton className="h-72 rounded-2xl" />
    </div>
  );
}

function NotFound({ message }: { message: string }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 py-16 text-center">
      <FileWarning aria-hidden className="size-8 text-muted-foreground" />
      <p className="font-medium">{message}</p>
      <Button asChild variant="outline">
        <Link href="/reports">Back to reports</Link>
      </Button>
    </div>
  );
}

export function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const fetched = useApi(`report:${id}`, (signal) => getReport(id, { signal, silent: true }));
  const [saved, setSaved] = useState<Report | null>(null);
  const [draft, setDraft] = useState<ReportContent | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const report = saved?.id === id ? saved : fetched.data;

  if (fetched.error && !report) return <NotFound message={fetched.error.message} />;
  if (!report) return <DetailSkeleton />;

  const problem = draft ? validateContent(normalizeContent(draft)) : null;

  async function save(update: ReportUpdate, kind: Busy, message: string) {
    setBusy(kind);
    try {
      setSaved(await updateReport(id, update));
      setDraft(null);
      toast.success(message);
    } catch {
      // apiFetch already showed a toast; keep the draft so nothing is lost.
    } finally {
      setBusy(null);
    }
  }

  async function download(current: Report) {
    setBusy("pdf");
    try {
      await downloadReportPdf(current.id, `agencypilot-${current.client}-${current.month}.pdf`);
    } catch {
      // downloadReportPdf already showed a toast.
    } finally {
      setBusy(null);
    }
  }

  async function remove(current: Report) {
    setBusy("delete");
    try {
      await deleteReport(current.id);
      toast.success("Report deleted", { description: `${current.client_name} · ${current.month_label}` });
      router.push("/reports");
    } catch {
      setBusy(null);
    }
  }

  const editing = draft !== null;
  const isFinal = report.status === "final";
  return (
    <div className="space-y-5">
      <FadeIn className="mx-auto flex max-w-5xl flex-wrap items-center gap-2">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link href="/reports">
            <ArrowLeft data-icon="inline-start" aria-hidden /> Reports
          </Link>
        </Button>
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          {editing ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => setDraft(null)} disabled={busy !== null}>
                <X data-icon="inline-start" aria-hidden /> Cancel
              </Button>
              <Button
                size="sm"
                disabled={problem !== null || busy !== null}
                onClick={() => draft && save({ content: normalizeContent(draft) }, "save", "Report saved")}
              >
                {busy === "save" ? <LoaderCircle data-icon="inline-start" className="animate-spin" aria-hidden /> : <Save data-icon="inline-start" aria-hidden />}
                Save
              </Button>
            </>
          ) : (
            <>
              {!isFinal && (
                <Button variant="outline" size="sm" onClick={() => setDraft(report.content)} disabled={busy !== null}>
                  <PencilLine data-icon="inline-start" aria-hidden /> Edit
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                disabled={busy !== null}
                onClick={() =>
                  save({ status: isFinal ? "draft" : "final" }, "status", isFinal ? "Moved back to draft" : "Marked as final")
                }
              >
                {isFinal ? <RotateCcw data-icon="inline-start" aria-hidden /> : <CircleCheck data-icon="inline-start" aria-hidden />}
                {isFinal ? "Back to draft" : "Mark as final"}
              </Button>
              <Button size="sm" onClick={() => download(report)} disabled={busy !== null}>
                {busy === "pdf" ? <LoaderCircle data-icon="inline-start" className="animate-spin" aria-hidden /> : <Download data-icon="inline-start" aria-hidden />}
                Download PDF
              </Button>
              <DeleteButton report={report} busy={busy} onConfirm={() => remove(report)} />
            </>
          )}
        </div>
        {editing && problem && (
          <p role="status" className="w-full text-right text-xs text-destructive">
            {problem}
          </p>
        )}
      </FadeIn>
      <FadeIn delay={0.05}>
        <ReportDocument report={report} draft={draft} onDraftChange={setDraft} />
      </FadeIn>
    </div>
  );
}
