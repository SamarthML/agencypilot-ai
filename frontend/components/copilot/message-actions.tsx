"use client";

import { RefreshCw, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { CopyButton } from "@/components/copy-button";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import type { AssistantMessage } from "@/hooks/use-copilot-chat";
import { sendCopilotFeedback } from "@/lib/api";
import type { Rating } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_COMMENT = 2000;
const MAX_ANSWER = 20000;

interface MessageActionsProps {
  clientId: string;
  message: AssistantMessage;
  copyText: string;
  onRegenerate?: () => void;
}

export function MessageActions({ clientId, message, copyText, onRegenerate }: MessageActionsProps) {
  const [rating, setRating] = useState<Rating | null>(null);
  const [sending, setSending] = useState(false);
  const [commentOpen, setCommentOpen] = useState(false);
  const [comment, setComment] = useState("");
  const canRate = message.status === "done" && message.content.trim() !== "";

  async function rate(value: Rating, note?: string) {
    setSending(true);
    try {
      await sendCopilotFeedback({
        client: clientId,
        message_id: message.done?.message_id ?? null,
        question: message.question.slice(0, 1000),
        answer: message.content.slice(0, MAX_ANSWER),
        rating: value,
        comment: note?.trim() ? note.trim().slice(0, MAX_COMMENT) : null,
      });
      setRating(value);
      setCommentOpen(false);
      toast.success("Thanks for the feedback", {
        description: value === "up" ? "Glad that helped." : "We'll use it to improve answers.",
      });
    } catch {
      // apiFetch already showed a toast.
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mt-2 flex items-center gap-0.5 text-muted-foreground">
      {copyText && <CopyButton text={copyText} label="answer" />}
      {onRegenerate && (
        <Button variant="ghost" size="icon-sm" onClick={onRegenerate} aria-label="Regenerate answer" title="Regenerate">
          <RefreshCw aria-hidden />
        </Button>
      )}
      {canRate && (
        <>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => rate("up")}
            disabled={sending || rating !== null}
            aria-label="Good answer"
            aria-pressed={rating === "up"}
            title="Good answer"
            className={cn(rating === "up" && "text-success disabled:opacity-100")}
          >
            <ThumbsUp aria-hidden className={cn(rating === "up" && "fill-current")} />
          </Button>
          <Popover open={commentOpen} onOpenChange={setCommentOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                disabled={sending || rating !== null}
                aria-label="Bad answer"
                aria-pressed={rating === "down"}
                title="Bad answer"
                className={cn(rating === "down" && "text-destructive disabled:opacity-100")}
              >
                <ThumbsDown aria-hidden className={cn(rating === "down" && "fill-current")} />
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-80 max-w-[calc(100vw-2rem)]">
              <form
                className="space-y-2.5"
                onSubmit={(e) => {
                  e.preventDefault();
                  void rate("down", comment);
                }}
              >
                <label htmlFor={`fb-${message.id}`} className="text-sm font-medium">
                  What was wrong? <span className="font-normal text-muted-foreground">(optional)</span>
                </label>
                <Textarea
                  id={`fb-${message.id}`}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  maxLength={MAX_COMMENT}
                  placeholder="e.g. wrong number, missing a source…"
                  className="max-h-40 min-h-20"
                />
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="ghost" size="sm" onClick={() => setCommentOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={sending}>
                    {sending ? "Sending…" : "Send feedback"}
                  </Button>
                </div>
              </form>
            </PopoverContent>
          </Popover>
        </>
      )}
    </div>
  );
}
