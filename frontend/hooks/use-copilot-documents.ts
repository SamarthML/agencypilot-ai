"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";
import { toast } from "sonner";

import { ApiError, getCopilotDocuments, isAbortError } from "@/lib/api";
import type { CopilotDocument, DocumentStatus } from "@/lib/types";

const POLL_MS = 2000;

interface DocsState {
  clientId: string;
  documents?: CopilotDocument[];
  error?: ApiError;
}

export interface CopilotDocuments {
  documents: CopilotDocument[] | undefined;
  error: ApiError | undefined;
  loading: boolean;
  reload: () => void;
  /** Show a just-uploaded document straight away; polling takes it from there. */
  add: (document: CopilotDocument) => void;
  remove: (id: string) => void;
}

function announceFinished(document: CopilotDocument): void {
  if (document.status === "ready") {
    toast.success(`${document.filename} is ready`, {
      description: `${document.pages} page${document.pages === 1 ? "" : "s"} indexed`,
    });
  } else if (document.status === "failed") {
    toast.error(`Couldn't process ${document.filename}`, { description: document.error ?? undefined });
  }
}

/**
 * The client's documents. Keeps showing the current list while it refreshes, and polls every
 * 2 s while any document is still processing, toasting when one finishes.
 */
export function useCopilotDocuments(clientId: string): CopilotDocuments {
  const [state, setState] = useState<DocsState>();
  const [nonce, setNonce] = useState(0);
  const statuses = useRef(new Map<string, DocumentStatus>());

  const loaded = useEffectEvent((documents: CopilotDocument[]) => {
    for (const doc of documents) {
      if (statuses.current.get(doc.id) === "processing" && doc.status !== "processing") announceFinished(doc);
    }
    statuses.current = new Map(documents.map((d) => [d.id, d.status]));
  });

  useEffect(() => {
    const controller = new AbortController();
    getCopilotDocuments(clientId, { signal: controller.signal, silent: true }).then(
      (documents) => {
        loaded(documents);
        setState({ clientId, documents });
      },
      (error: unknown) => {
        if (isAbortError(error)) return;
        const apiError = error instanceof ApiError ? error : new ApiError(String(error), null);
        // Keep showing the last list if a background poll fails.
        setState((prev) => ({
          clientId,
          documents: prev?.clientId === clientId ? prev.documents : undefined,
          error: apiError,
        }));
      },
    );
    return () => controller.abort();
  }, [clientId, nonce]);

  const current = state?.clientId === clientId ? state : undefined;
  const processing = current?.documents?.some((d) => d.status === "processing") ?? false;

  useEffect(() => {
    if (!processing) return;
    const timer = setTimeout(() => setNonce((n) => n + 1), POLL_MS);
    return () => clearTimeout(timer);
  }, [processing, state]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  const add = useCallback((document: CopilotDocument) => {
    statuses.current.set(document.id, document.status);
    setState((prev) => ({
      clientId: document.client,
      documents: [document, ...(prev?.clientId === document.client ? (prev.documents ?? []) : [])],
    }));
  }, []);

  const remove = useCallback((id: string) => {
    statuses.current.delete(id);
    setState((prev) => prev && { ...prev, documents: prev.documents?.filter((d) => d.id !== id) });
  }, []);

  return {
    documents: current?.documents,
    error: current?.documents ? undefined : current?.error,
    loading: !current,
    reload,
    add,
    remove,
  };
}
