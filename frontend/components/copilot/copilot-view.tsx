"use client";

import { FolderOpen, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { ChatEmpty } from "@/components/copilot/chat-empty";
import { Composer } from "@/components/copilot/composer";
import { DocumentsPanel } from "@/components/copilot/documents-panel";
import { MessageList } from "@/components/copilot/message-list";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { useCopilotChat } from "@/hooks/use-copilot-chat";
import { useCopilotDocuments } from "@/hooks/use-copilot-documents";
import { useClient } from "@/lib/client-context";
import type { CopilotDocument } from "@/lib/types";

const NO_DOCUMENTS: CopilotDocument[] = [];

function disabledReason(documents: CopilotDocument[] | undefined, failed: boolean): string | null {
  if (!documents) return failed ? "Couldn't load documents. Retry from the Docs panel." : "Loading documents…";
  if (documents.some((d) => d.status === "ready")) return null;
  if (documents.some((d) => d.status === "processing")) return "Indexing documents…";
  return "Upload a document to start asking…";
}

export function CopilotView() {
  const { client } = useClient();
  const docs = useCopilotDocuments(client.id);
  const chat = useCopilotChat(client.id);
  const [sheetOpen, setSheetOpen] = useState(false);

  const documents = docs.documents ?? NO_DOCUMENTS;
  const filenames = useMemo(() => documents.map((d) => d.filename), [documents]);
  const blocked = disabledReason(docs.documents, docs.error !== undefined);
  const panel = <DocumentsPanel clientId={client.id} clientName={client.name} docs={docs} className="h-full" />;

  return (
    // Fill the viewport below the topbar (4rem) and main's vertical padding; only the chat scrolls.
    <div className="grid h-[calc(100svh-7rem)] min-h-[30rem] grid-cols-1 gap-6 md:h-[calc(100svh-9rem)] lg:grid-cols-[18.5rem_minmax(0,1fr)]">
      <aside className="hidden min-h-0 overflow-hidden rounded-2xl border border-border/60 bg-card shadow-card lg:block">
        {panel}
      </aside>

      <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-border/60 bg-card/40 shadow-card">
        <header className="flex items-center gap-2 border-b border-border/60 px-3 py-2.5 sm:px-4">
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold">{client.name} Copilot</h1>
            <p className="truncate text-xs text-muted-foreground">
              Grounded in {documents.filter((d) => d.status === "ready").length} document(s) · cites pages
            </p>
          </div>
          <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setSheetOpen(true)}>
            <FolderOpen data-icon="inline-start" aria-hidden />
            Docs<span className="tabular-nums text-muted-foreground">{documents.length}</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={chat.clear} disabled={chat.messages.length === 0} aria-label="Clear chat">
            <Trash2 data-icon="inline-start" aria-hidden />
            <span className="max-sm:hidden">Clear chat</span>
          </Button>
        </header>

        {chat.messages.length === 0 ? (
          <ChatEmpty
            clientId={client.id}
            clientName={client.name}
            hasReadyDocs={blocked === null}
            onAsk={chat.send}
            onOpenDocuments={() => setSheetOpen(true)}
          />
        ) : (
          <MessageList clientId={client.id} messages={chat.messages} filenames={filenames} onRetry={chat.retry} />
        )}
        <Composer streaming={chat.streaming} disabledReason={blocked} onSend={chat.send} onStop={chat.stop} />
      </section>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="left" className="w-[88vw] gap-0 p-0 sm:max-w-sm lg:hidden">
          <SheetTitle className="sr-only">Documents</SheetTitle>
          <SheetDescription className="sr-only">Upload and manage {client.name}&apos;s documents</SheetDescription>
          {panel}
        </SheetContent>
      </Sheet>
    </div>
  );
}
