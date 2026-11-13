"use client";

import { FileSpreadsheet, RotateCcw, Upload } from "lucide-react";
import { useId, useState, type DragEvent } from "react";
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
import { ApiError, loadSampleData, uploadInsightsCsv } from "@/lib/api";
import { cn } from "@/lib/utils";

const MAX_MB = 5;
const REQUIRED_COLUMNS = "date, channel, sessions, conversions, revenue, spend";

interface UploadDialogProps {
  clientId: string;
  clientName: string;
  onDataChanged: () => void;
}

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".csv")) return "Choose a .csv file.";
  if (file.size > MAX_MB * 1024 * 1024) return `The file is larger than ${MAX_MB} MB.`;
  return null;
}

export function UploadDialog({ clientId, clientName, onDataChanged }: UploadDialogProps) {
  const inputId = useId();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"upload" | "sample" | null>(null);
  const [dragging, setDragging] = useState(false);

  function choose(next: File | undefined) {
    if (!next) return;
    setFile(next);
    setError(validateFile(next));
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    choose(event.dataTransfer.files[0]);
  }

  function finish(message: string, description?: string) {
    toast.success(message, { description });
    setOpen(false);
    setFile(null);
    onDataChanged();
  }

  async function upload() {
    if (!file || error) return;
    setBusy("upload");
    try {
      const result = await uploadInsightsCsv(clientId, clientName, file);
      finish(`Loaded ${result.dataset.row_count.toLocaleString()} rows for ${clientName}`, result.warnings.join(" ") || undefined);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setBusy(null);
    }
  }

  async function resetToSample() {
    setBusy("sample");
    try {
      const result = await loadSampleData();
      finish(`Sample data reloaded for ${result.datasets.length} clients`);
    } catch {
      // apiFetch already showed a toast.
    } finally {
      setBusy(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { setOpen(next); if (!next) { setFile(null); setError(null); } }}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Upload data-icon="inline-start" aria-hidden /> Upload CSV
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload data for {clientName}</DialogTitle>
          <DialogDescription>
            One row per day and channel with columns: <span className="font-mono text-xs">{REQUIRED_COLUMNS}</span>.
            An optional <span className="font-mono text-xs">client</span> column selects this client&apos;s rows. Replaces the current data.
          </DialogDescription>
        </DialogHeader>
        <label
          htmlFor={inputId}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            "flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed px-4 py-8 text-center transition-colors",
            dragging ? "border-brand-from bg-muted/60" : "hover:bg-muted/40",
          )}
        >
          <FileSpreadsheet aria-hidden className="size-8 text-muted-foreground" />
          <span className="text-sm font-medium">{file ? file.name : "Drop a CSV here or click to browse"}</span>
          <span className="text-xs text-muted-foreground">
            {file ? `${(file.size / 1024).toFixed(1)} KB` : `Up to ${MAX_MB} MB`}
          </span>
          <input id={inputId} type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => choose(e.target.files?.[0])} />
        </label>
        {error && (
          <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}
        <DialogFooter className="gap-2 sm:justify-between">
          <Button variant="ghost" onClick={resetToSample} disabled={busy !== null}>
            <RotateCcw data-icon="inline-start" aria-hidden />
            {busy === "sample" ? "Reloading…" : "Reset all to sample data"}
          </Button>
          <Button onClick={upload} disabled={!file || !!error || busy !== null}>
            {busy === "upload" ? "Uploading…" : "Upload"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
