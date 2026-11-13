"use client";

import { MessageSquareText, SendHorizontal } from "lucide-react";
import { useState, type FormEvent } from "react";

import { LlmMeta } from "@/components/llm-meta";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { askInsights } from "@/lib/api";
import { useModel } from "@/lib/model-context";
import type { AskResponse, Days } from "@/lib/types";

const SUGGESTIONS = [
  "Which channel changed the most?",
  "Is paid advertising paying off?",
  "Why did revenue change?",
];
const MAX_QUESTION_LENGTH = 500;

interface AskBoxProps {
  clientId: string;
  days: Days;
}

interface Thread {
  key: string;
  answers: AskResponse[];
}

export function AskBox({ clientId, days }: AskBoxProps) {
  const { provider } = useModel();
  const contextKey = `${clientId}:${days}:${provider}`;
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<Thread>();
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const answers = thread?.key === contextKey ? thread.answers : [];
  const loading = pendingKey === contextKey;

  async function ask(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < 3 || loading) return;
    const key = contextKey;
    setPendingKey(key);
    try {
      const answer = await askInsights(clientId, days, trimmed);
      setThread((prev) => ({ key, answers: [answer, ...(prev?.key === key ? prev.answers : [])] }));
      setQuestion("");
    } catch {
      // apiFetch already showed a toast; keep the question so it can be retried.
    } finally {
      setPendingKey((current) => (current === key ? null : current));
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(question);
  }

  return (
    <Card className="h-full">
      <CardHeader className="gap-1">
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageSquareText aria-hidden className="size-4 text-muted-foreground" /> Ask about this data
        </CardTitle>
        <CardDescription>Answers use only this period&apos;s computed KPIs.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={onSubmit} className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Which channel hurt us most?"
            maxLength={MAX_QUESTION_LENGTH}
            aria-label="Question about this client's data"
            disabled={loading}
          />
          <Button type="submit" size="icon" disabled={loading || question.trim().length < 3} aria-label="Ask">
            <SendHorizontal aria-hidden />
          </Button>
        </form>
        {answers.length === 0 && !loading && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <Button key={s} variant="outline" size="sm" className="h-auto py-1 text-xs font-normal" onClick={() => void ask(s)}>
                {s}
              </Button>
            ))}
          </div>
        )}
        {loading && (
          <div className="space-y-2" aria-live="polite">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        )}
        <ul className="space-y-4">
          {answers.map((a) => (
            <li key={`${a.question}-${a.meta.latency_ms}-${a.meta.output_tokens}`} className="space-y-1.5 rounded-xl bg-muted/50 p-3">
              <p className="text-xs font-medium text-muted-foreground">{a.question}</p>
              <p className="text-sm leading-relaxed whitespace-pre-line">{a.answer}</p>
              <LlmMeta meta={a.meta} />
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
