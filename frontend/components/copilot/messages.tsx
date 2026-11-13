"use client";

import { motion } from "framer-motion";
import { AlertTriangle, CircleStop, RotateCw, Sparkles } from "lucide-react";
import { memo, useCallback, useMemo } from "react";

import { AnswerFooter } from "@/components/copilot/answer-footer";
import { AnswerMarkdown } from "@/components/copilot/answer-markdown";
import { MessageActions } from "@/components/copilot/message-actions";
import { CitationChip, SourceCards } from "@/components/copilot/sources";
import { Button } from "@/components/ui/button";
import type { AssistantMessage, UserMessage } from "@/hooks/use-copilot-chat";
import { citationFor, numberCitations, stripCitations } from "@/lib/citations";
import type { Citation } from "@/lib/types";

const ENTER = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.25, ease: [0.22, 1, 0.36, 1] as const },
};

export const UserBubble = memo(function UserBubble({ message }: { message: UserMessage }) {
  return (
    <motion.div {...ENTER} className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm whitespace-pre-wrap text-primary-foreground [overflow-wrap:anywhere]">
        {message.content}
      </div>
    </motion.div>
  );
});

function TypingIndicator() {
  return (
    <div className="flex h-5 items-center gap-1" role="status" aria-label="Copilot is thinking">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-muted-foreground"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}

function ErrorNote({ error, onRetry }: { error: string | null; onRetry: () => void }) {
  return (
    <div role="alert" className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
      <AlertTriangle aria-hidden className="size-4 shrink-0" />
      <span className="min-w-0 flex-1 [overflow-wrap:anywhere]">{error ?? "Something went wrong."}</span>
      <Button size="sm" variant="outline" onClick={onRetry}>
        <RotateCw data-icon="inline-start" aria-hidden /> Retry
      </Button>
    </div>
  );
}

interface AssistantBubbleProps {
  clientId: string;
  message: AssistantMessage;
  filenames: readonly string[];
  isLast: boolean;
  onRetry: (id: string) => void;
}

export const AssistantBubble = memo(function AssistantBubble({
  clientId,
  message,
  filenames,
  isLast,
  onRetry,
}: AssistantBubbleProps) {
  const { markdown, refs } = useMemo(() => numberCitations(message.content, filenames), [message.content, filenames]);
  const { citations, status } = message;
  const retry = useCallback(() => onRetry(message.id), [onRetry, message.id]);

  const renderCitation = useCallback(
    (n: number) => <CitationChip n={n} source={refs[n - 1]} citation={citationFor(refs[n - 1], citations)} />,
    [refs, citations],
  );
  const numberOf = useCallback(
    (citation: Citation) => {
      const index = refs.findIndex((r) => citationFor(r, [citation]) !== undefined);
      return index >= 0 ? index + 1 : undefined;
    },
    [refs],
  );

  const empty = message.content === "";
  const settled = status !== "streaming";
  return (
    <motion.div {...ENTER} className="flex gap-3" aria-busy={!settled}>
      <div className="bg-brand-gradient mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-white shadow-sm">
        <Sparkles aria-hidden className="size-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="rounded-2xl rounded-tl-md border border-border/60 bg-card px-4 py-3 shadow-card">
          {status === "streaming" && empty ? <TypingIndicator /> : <AnswerMarkdown markdown={markdown} renderCitation={renderCitation} />}
          {status === "stopped" && (
            <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
              <CircleStop aria-hidden className="size-3.5" /> Stopped{empty && " before the answer started"}
            </p>
          )}
          {status === "error" && <ErrorNote error={message.error} onRetry={retry} />}
          {status === "done" && <SourceCards citations={citations} numberOf={numberOf} />}
          {message.done && <AnswerFooter done={message.done} />}
        </div>
        {settled && status !== "error" && (
          <MessageActions
            clientId={clientId}
            message={message}
            copyText={stripCitations(message.content, filenames)}
            onRegenerate={isLast ? retry : undefined}
          />
        )}
      </div>
    </motion.div>
  );
});
