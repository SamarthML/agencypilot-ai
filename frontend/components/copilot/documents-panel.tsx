"use client";

import { FolderOpen, RotateCw } from "lucide-react";

import { DocumentRow } from "@/components/copilot/document-row";
import { UploadDropzone } from "@/components/copilot/upload-dropzone";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CopilotDocuments } from "@/hooks/use-copilot-documents";
import { cn } from "@/lib/utils";

interface DocumentsPanelProps {
  clientId: string;
  clientName: string;
  docs: CopilotDocuments;
  className?: string;
}

export function DocumentsPanel({ clientId, clientName, docs, className }: DocumentsPanelProps) {
  const count = docs.documents?.length;
  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      {/* Below lg the panel lives in a Sheet whose close button sits top-right. */}
      <div className="flex items-baseline justify-between gap-2 px-4 pt-4 max-lg:pr-12">
        <h2 className="text-sm font-semibold">Documents</h2>
        {count !== undefined && <span className="text-xs text-muted-foreground tabular-nums">{count}</span>}
      </div>
      <p className="px-4 text-xs text-muted-foreground">What the Copilot knows about {clientName}.</p>
      <div className="p-4 pb-2">
        <UploadDropzone clientId={clientId} onUploaded={docs.add} />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        <DocumentList docs={docs} />
      </div>
    </div>
  );
}

function DocumentList({ docs }: { docs: CopilotDocuments }) {
  if (docs.error) {
    return (
      <div role="alert" className="mx-2 space-y-2 rounded-xl bg-destructive/10 p-3 text-sm text-destructive">
        <p>{docs.error.message}</p>
        <Button size="sm" variant="outline" onClick={docs.reload}>
          <RotateCw data-icon="inline-start" aria-hidden /> Retry
        </Button>
      </div>
    );
  }
  if (!docs.documents) {
    return (
      <div className="space-y-3 px-2 pt-1" aria-label="Loading documents">
        {[0, 1].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="size-8 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (docs.documents.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 px-4 py-8 text-center text-muted-foreground">
        <FolderOpen aria-hidden className="size-6" />
        <p className="text-sm">No documents yet.</p>
        <p className="text-xs">Upload a brief, proposal or report to start asking questions.</p>
      </div>
    );
  }
  return (
    <ul className="space-y-0.5">
      {docs.documents.map((document) => (
        <DocumentRow key={document.id} document={document} onDeleted={docs.remove} />
      ))}
    </ul>
  );
}
