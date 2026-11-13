"use client";

import { ArrowDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AssistantBubble, UserBubble } from "@/components/copilot/messages";
import { Button } from "@/components/ui/button";
import type { ChatMessage } from "@/hooks/use-copilot-chat";

/** Within this many px of the bottom counts as "following" the stream. */
const FOLLOW_THRESHOLD_PX = 80;

interface MessageListProps {
  clientId: string;
  messages: ChatMessage[];
  filenames: readonly string[];
  onRetry: (id: string) => void;
}

export function MessageList({ clientId, messages, filenames, onRetry }: MessageListProps) {
  const scroller = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const [showJump, setShowJump] = useState(false);
  const lastId = messages.at(-1)?.id;

  // A new question always jumps to the bottom and resumes following.
  useEffect(() => {
    following.current = true;
  }, [messages.length]);

  // Keep the latest tokens in view unless the reader scrolled up.
  useEffect(() => {
    const el = scroller.current;
    if (el && following.current) el.scrollTop = el.scrollHeight;
  });

  function onScroll() {
    const el = scroller.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < FOLLOW_THRESHOLD_PX;
    following.current = atBottom;
    setShowJump(!atBottom);
  }

  function jumpToLatest() {
    const el = scroller.current;
    if (!el) return;
    following.current = true;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={scroller} onScroll={onScroll} className="h-full overflow-x-hidden overflow-y-auto overscroll-contain">
        <div className="mx-auto flex max-w-3xl flex-col gap-5 px-3 py-5 sm:px-5" role="log" aria-live="polite" aria-relevant="additions">
          {messages.map((message) =>
            message.role === "user" ? (
              <UserBubble key={message.id} message={message} />
            ) : (
              <AssistantBubble
                key={message.id}
                clientId={clientId}
                message={message}
                filenames={filenames}
                isLast={message.id === lastId}
                onRetry={onRetry}
              />
            ),
          )}
        </div>
      </div>
      {showJump && (
        <Button
          size="sm"
          variant="secondary"
          onClick={jumpToLatest}
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full shadow-card"
        >
          <ArrowDown data-icon="inline-start" aria-hidden /> Jump to latest
        </Button>
      )}
    </div>
  );
}
