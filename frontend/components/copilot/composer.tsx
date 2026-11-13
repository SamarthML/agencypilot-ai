"use client";

import { ArrowUp, Square } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Matches the backend's ChatRequest.question limit. */
const MAX_QUESTION = 1000;
const SHOW_COUNT_AT = 800;

interface ComposerProps {
  streaming: boolean;
  disabledReason: string | null;
  onSend: (question: string) => void;
  onStop: () => void;
}

export function Composer({ streaming, disabledReason, onSend, onStop }: ComposerProps) {
  const [text, setText] = useState("");
  const disabled = disabledReason !== null;
  const canSend = !disabled && !streaming && text.trim().length > 0;

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!canSend) return;
    onSend(text);
    setText("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-3xl px-3 pb-3 sm:px-5 sm:pb-4">
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-card transition-colors focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/30",
          disabled && "opacity-70",
        )}
      >
        <label htmlFor="copilot-question" className="sr-only">
          Ask a question
        </label>
        <textarea
          id="copilot-question"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          maxLength={MAX_QUESTION}
          rows={1}
          disabled={disabled}
          placeholder={disabledReason ?? "Ask about this client's documents…"}
          className="field-sizing-content max-h-40 min-h-9 min-w-0 flex-1 resize-none bg-transparent px-2 py-1.5 text-base outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed md:text-sm"
        />
        {streaming ? (
          <Button type="button" size="icon" variant="secondary" onClick={onStop} aria-label="Stop generating" title="Stop generating" className="rounded-xl">
            <Square aria-hidden className="size-3.5 fill-current" />
          </Button>
        ) : (
          <Button type="submit" size="icon" disabled={!canSend} aria-label="Send question" title="Send" className="rounded-xl">
            <ArrowUp aria-hidden />
          </Button>
        )}
      </div>
      <p className="mt-1.5 flex justify-between gap-2 px-1 text-[11px] text-muted-foreground">
        <span className="max-sm:hidden">Enter to send · Shift+Enter for a new line</span>
        <span className="sm:hidden">Answers cite the client&apos;s documents</span>
        {text.length >= SHOW_COUNT_AT && (
          <span className="tabular-nums">
            {text.length}/{MAX_QUESTION}
          </span>
        )}
      </p>
    </form>
  );
}
