"use client";

import { FileUp, MessagesSquare } from "lucide-react";

import { FadeIn } from "@/components/motion";
import { Button } from "@/components/ui/button";

const BLOOM_BAKERY_QUESTIONS = [
  "What is the Q4 budget and how is it split?",
  "Who is the target audience?",
  "Which past campaign had the best ROAS?",
  "Who are the main competitors?",
];

const GENERIC_QUESTIONS = [
  "Summarise the key points of this client's brief.",
  "What are the campaign goals and KPIs?",
  "What budget is mentioned and how is it allocated?",
  "Who is the target audience?",
];

interface ChatEmptyProps {
  clientId: string;
  clientName: string;
  hasReadyDocs: boolean;
  onAsk: (question: string) => void;
  onOpenDocuments: () => void;
}

export function ChatEmpty({ clientId, clientName, hasReadyDocs, onAsk, onOpenDocuments }: ChatEmptyProps) {
  const questions = clientId === "bloom-bakery" ? BLOOM_BAKERY_QUESTIONS : GENERIC_QUESTIONS;
  return (
    <div className="flex min-h-0 flex-1 overflow-y-auto">
      <FadeIn className="m-auto w-full max-w-2xl px-4 py-8 text-center">
        <div className="mx-auto mb-4 w-fit rounded-2xl bg-linear-to-br from-brand-from/40 to-brand-to/40 p-px">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-card">
            <MessagesSquare aria-hidden className="size-5" />
          </div>
        </div>
        <h2 className="text-lg font-semibold tracking-tight">Ask about {clientName}</h2>
        <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
          {hasReadyDocs
            ? "Answers come only from this client's documents, with page citations. If it isn't in the docs, the Copilot says so."
            : `Upload ${clientName}'s brief, proposal or reports to start asking questions about them.`}
        </p>
        {hasReadyDocs ? (
          <div className="mt-6 grid gap-2 text-left sm:grid-cols-2">
            {questions.map((question) => (
              <button
                key={question}
                type="button"
                onClick={() => onAsk(question)}
                className="rounded-xl border border-border/60 bg-card px-3.5 py-3 text-left text-sm shadow-card transition-colors hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                {question}
              </button>
            ))}
          </div>
        ) : (
          <Button className="mt-5 lg:hidden" variant="outline" onClick={onOpenDocuments}>
            <FileUp data-icon="inline-start" aria-hidden /> Upload documents
          </Button>
        )}
      </FadeIn>
    </div>
  );
}
