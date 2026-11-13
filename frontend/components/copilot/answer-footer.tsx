import { Search, ShieldCheck } from "lucide-react";

import { LlmMeta } from "@/components/llm-meta";
import { formatInteger } from "@/lib/format";
import type { DoneEvent, LlmCallMeta } from "@/lib/types";

function toMeta(done: DoneEvent): LlmCallMeta {
  return {
    provider: done.provider,
    model: done.model,
    input_tokens: done.input_tokens,
    output_tokens: done.output_tokens,
    latency_ms: done.latency_ms,
    cost_usd: done.cost_usd,
    cached: false,
  };
}

/** The guardrail answered without calling the answer model. */
function GuardrailNote({ done }: { done: DoneEvent }) {
  const noCalls = done.input_tokens === 0 && done.output_tokens === 0;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      <span
        className="inline-flex items-center gap-1.5 rounded-md bg-success/10 px-1.5 py-0.5 font-medium text-success"
        title="No passage was similar enough, so the answer model was never called."
      >
        <ShieldCheck aria-hidden className="size-3.5" />
        {/* With history, the follow-up rewrite still ran; its cost is shown, not hidden. */}
        {noCalls ? "No LLM call · $0" : "Guardrail · no answer call · rewrite only"}
      </span>
      {noCalls ? (
        <span className="tabular-nums">{formatInteger(done.latency_ms)} ms</span>
      ) : (
        <LlmMeta meta={toMeta(done)} />
      )}
    </div>
  );
}

export function AnswerFooter({ done }: { done: DoneEvent }) {
  return (
    <div className="mt-3 space-y-1.5 border-t border-border/60 pt-2.5">
      {done.rewritten_query && (
        <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <Search aria-hidden className="mt-0.5 size-3 shrink-0" />
          <span className="[overflow-wrap:anywhere]">
            Searched for: <span className="text-foreground/80">{done.rewritten_query}</span>
          </span>
        </p>
      )}
      {done.grounded ? <LlmMeta meta={toMeta(done)} /> : <GuardrailNote done={done} />}
    </div>
  );
}
