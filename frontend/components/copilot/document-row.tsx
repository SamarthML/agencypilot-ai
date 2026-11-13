"use client";

import { CircleCheck, CircleX, FileText, LoaderCircle, Trash2, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

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
import { deleteCopilotDocument } from "@/lib/api";
import type { CopilotDocument, DocumentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS: Record<DocumentStatus, { label: string; icon: LucideIcon; className: string }> = {
  processing: { label: "Processing", icon: LoaderCircle, className: "bg-warning/15 text-warning" },
  ready: { label: "Ready", icon: CircleCheck, className: "bg-success/10 text-success" },
  failed: { label: "Failed", icon: CircleX, className: "bg-destructive/10 text-destructive" },
};

function StatusBadge({ status }: { status: DocumentStatus }) {
  const { label, icon: Icon, className } = STATUS[status];
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium",
        className,
      )}
    >
      <Icon aria-hidden className={cn("size-3", status === "processing" && "animate-spin")} />
      {label}
    </span>
  );
}

function details(document: CopilotDocument): string {
  if (document.status === "processing") return "Extracting and embedding…";
  if (document.status === "failed") return document.error ?? "Processing failed";
  const pages = `${document.pages} page${document.pages === 1 ? "" : "s"}`;
  return `${pages} · ${document.chunk_count} chunk${document.chunk_count === 1 ? "" : "s"}`;
}

interface DocumentRowProps {
  document: CopilotDocument;
  onDeleted: (id: string) => void;
}

export function DocumentRow({ document, onDeleted }: DocumentRowProps) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function confirmDelete() {
    setDeleting(true);
    try {
      await deleteCopilotDocument(document.id);
      setOpen(false);
      onDeleted(document.id);
      toast.success(`Deleted ${document.filename}`);
    } catch {
      // apiFetch already showed a toast.
    } finally {
      setDeleting(false);
    }
  }

  return (
    <li className="group flex items-start gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-muted/50">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted">
        <FileText aria-hidden className="size-4 text-muted-foreground" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium" title={document.filename}>
          {document.filename}
        </p>
        <div className="mt-1 flex min-w-0 items-center gap-2">
          <StatusBadge status={document.status} />
          <span className="truncate text-xs text-muted-foreground" title={details(document)}>
            {details(document)}
          </span>
        </div>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Delete ${document.filename}`}
            className="shrink-0 text-muted-foreground hover:text-destructive lg:opacity-0 lg:group-hover:opacity-100 lg:focus-visible:opacity-100"
          >
            <Trash2 aria-hidden />
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete this document?</DialogTitle>
            <DialogDescription className="[overflow-wrap:anywhere]">
              <span className="font-medium text-foreground">{document.filename}</span> and its indexed chunks
              will be removed, so the Copilot can no longer cite it.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting ? "Deleting…" : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </li>
  );
}
