"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, isAbortError, streamCopilotChat } from "@/lib/api";
import type { ChatTurn, Citation, CopilotStreamEvent, DoneEvent } from "@/lib/types";

/** Turns (question + answer) of context sent with each question, for follow-up rewriting. */
const HISTORY_TURNS = 4;
const MAX_TURN_CHARS = 8000;
const CONNECTION_LOST = "Connection lost mid-answer.";

export type AnswerStatus = "streaming" | "done" | "stopped" | "error";

export interface UserMessage {
  id: string;
  role: "user";
  content: string;
}

export interface AssistantMessage {
  id: string;
  role: "assistant";
  question: string;
  content: string;
  citations: Citation[];
  done: DoneEvent | null;
  status: AnswerStatus;
  error: string | null;
}

export type ChatMessage = UserMessage | AssistantMessage;
type Threads = Record<string, ChatMessage[]>;

function newId(): string {
  return crypto.randomUUID();
}

/** The last complete question/answer pairs, oldest first. */
function buildHistory(messages: readonly ChatMessage[]): ChatTurn[] {
  const turns = messages
    .filter((m): m is AssistantMessage => m.role === "assistant" && m.status === "done" && m.content.trim() !== "")
    .slice(-HISTORY_TURNS)
    .flatMap((m): ChatTurn[] => [
      { role: "user", content: m.question.slice(0, MAX_TURN_CHARS) },
      { role: "assistant", content: m.content.slice(0, MAX_TURN_CHARS) },
    ]);
  return turns;
}

function applyEvent(message: AssistantMessage, event: CopilotStreamEvent): AssistantMessage {
  switch (event.event) {
    case "token":
      return { ...message, content: message.content + event.data.text };
    case "citations":
      return { ...message, citations: event.data.citations };
    case "done":
      return { ...message, done: event.data, status: "done" };
    case "error":
      return { ...message, status: "error", error: event.data.detail };
  }
}

function failureFor(error: unknown): Pick<AssistantMessage, "status" | "error"> {
  if (isAbortError(error)) return { status: "stopped", error: null };
  return { status: "error", error: error instanceof ApiError ? error.message : CONNECTION_LOST };
}

export interface CopilotChat {
  messages: ChatMessage[];
  streaming: boolean;
  send: (question: string) => void;
  stop: () => void;
  /** Re-ask the question behind an assistant message (retry after an error, or regenerate). */
  retry: (assistantId: string) => void;
  clear: () => void;
}

/** Chat threads kept per client in memory; one answer streams at a time. */
export function useCopilotChat(clientId: string): CopilotChat {
  const [threads, setThreads] = useState<Threads>({});
  const controller = useRef<AbortController | null>(null);
  const messages = useMemo(() => threads[clientId] ?? [], [threads, clientId]);
  const streaming = messages.some((m) => m.role === "assistant" && m.status === "streaming");

  // Switching client (or leaving the page) cancels the answer that is streaming.
  useEffect(() => () => controller.current?.abort(), [clientId]);

  const patch = useCallback(
    (client: string, id: string, update: (m: AssistantMessage) => AssistantMessage) =>
      setThreads((all) => ({
        ...all,
        [client]: (all[client] ?? []).map((m) => (m.id === id && m.role === "assistant" ? update(m) : m)),
      })),
    [],
  );

  const run = useCallback(
    async (client: string, user: UserMessage, prior: ChatMessage[]) => {
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      const answer: AssistantMessage = {
        id: newId(), role: "assistant", question: user.content, content: "",
        citations: [], done: null, status: "streaming", error: null,
      };
      setThreads((all) => ({ ...all, [client]: [...prior, user, answer] }));
      const request = { client, question: user.content, history: buildHistory(prior) };
      try {
        for await (const event of streamCopilotChat(request, abort.signal)) {
          patch(client, answer.id, (m) => applyEvent(m, event));
        }
        patch(client, answer.id, (m) =>
          m.status === "streaming" ? { ...m, status: "error", error: CONNECTION_LOST } : m,
        );
      } catch (error) {
        patch(client, answer.id, (m) => ({ ...m, ...failureFor(error) }));
      } finally {
        if (controller.current === abort) controller.current = null;
      }
    },
    [patch],
  );

  const send = useCallback(
    (question: string) => {
      const text = question.trim();
      if (!text) return;
      void run(clientId, { id: newId(), role: "user", content: text }, messages);
    },
    [clientId, messages, run],
  );

  const retry = useCallback(
    (assistantId: string) => {
      const index = messages.findIndex((m) => m.id === assistantId);
      const user = messages[index - 1];
      if (index < 1 || user?.role !== "user") return;
      void run(clientId, user, messages.slice(0, index - 1));
    },
    [clientId, messages, run],
  );

  const stop = useCallback(() => controller.current?.abort(), []);

  const clear = useCallback(() => {
    controller.current?.abort();
    setThreads((all) => ({ ...all, [clientId]: [] }));
  }, [clientId]);

  return { messages, streaming, send, stop, retry, clear };
}
