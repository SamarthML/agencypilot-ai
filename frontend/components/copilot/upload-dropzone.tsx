"use client";

import { FileUp } from "lucide-react";
import { useId, useState, type DragEvent } from "react";

import { ApiError, uploadCopilotDocument } from "@/lib/api";
import type { CopilotDocument } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_MB = 10;
const EXTENSIONS = [".pdf", ".txt", ".md"];
const ACCEPT = ".pdf,.txt,.md,application/pdf,text/plain,text/markdown";

interface Upload {
  filename: string;
  progress: number;
}

function validate(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `${file.name}: only PDF, .txt and .md files are supported.`;
  }
  if (file.size > MAX_MB * 1024 * 1024) return `${file.name} is larger than ${MAX_MB} MB.`;
  if (file.size === 0) return `${file.name} is empty.`;
  return null;
}

interface UploadDropzoneProps {
  clientId: string;
  onUploaded: (document: CopilotDocument) => void;
}

export function UploadDropzone({ clientId, onUploaded }: UploadDropzoneProps) {
  const inputId = useId();
  const [dragging, setDragging] = useState(false);
  const [upload, setUpload] = useState<Upload | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  async function uploadOne(file: File): Promise<string | null> {
    const invalid = validate(file);
    if (invalid) return invalid;
    setUpload({ filename: file.name, progress: 0 });
    try {
      const document = await uploadCopilotDocument(clientId, file, (progress) =>
        setUpload({ filename: file.name, progress }),
      );
      onUploaded(document);
      return null;
    } catch (error) {
      return `${file.name}: ${error instanceof ApiError ? error.message : "upload failed."}`;
    }
  }

  async function uploadAll(files: File[]) {
    if (files.length === 0) return;
    setErrors([]);
    const problems: string[] = [];
    for (const file of files) {
      const problem = await uploadOne(file);
      if (problem) problems.push(problem);
    }
    setUpload(null);
    setErrors(problems);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    if (!upload) void uploadAll(Array.from(event.dataTransfer.files));
  }

  return (
    <div className="space-y-2">
      <label
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        aria-busy={upload !== null}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed px-4 py-5 text-center transition-colors focus-within:ring-3 focus-within:ring-ring/50",
          dragging ? "border-brand-from bg-muted/60" : "hover:bg-muted/40",
          upload && "pointer-events-none",
        )}
      >
        <FileUp aria-hidden className={cn("size-6 text-muted-foreground", dragging && "text-foreground")} />
        {upload ? (
          <UploadProgress upload={upload} />
        ) : (
          <>
            <span className="text-sm font-medium">Drop files or click to upload</span>
            <span className="text-xs text-muted-foreground">PDF, .txt or .md · up to {MAX_MB} MB</span>
          </>
        )}
        <input
          id={inputId}
          type="file"
          accept={ACCEPT}
          multiple
          disabled={upload !== null}
          className="sr-only"
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            e.target.value = "";
            void uploadAll(files);
          }}
        />
      </label>
      {errors.length > 0 && (
        <div role="alert" className="space-y-1 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {errors.map((message) => (
            <p key={message} className="[overflow-wrap:anywhere]">
              {message}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function UploadProgress({ upload }: { upload: Upload }) {
  const percent = Math.round(upload.progress * 100);
  return (
    <div className="w-full space-y-1.5">
      <p className="truncate text-sm font-medium" title={upload.filename}>
        Uploading {upload.filename}
      </p>
      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Uploading ${upload.filename}`}
        className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
      >
        <div className="bg-brand-gradient h-full rounded-full transition-[width]" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-xs text-muted-foreground tabular-nums">{percent}%</p>
    </div>
  );
}
