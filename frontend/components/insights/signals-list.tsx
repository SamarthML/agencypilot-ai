import { CircleCheck, Info, TrendingDown, TrendingUp, TriangleAlert } from "lucide-react";

import type { Signal } from "@/lib/types";
import { cn } from "@/lib/utils";

const TONE: Record<Signal["sentiment"], string> = {
  positive: "border-success/30 bg-success/5",
  negative: "border-destructive/30 bg-destructive/5",
  neutral: "border-border bg-muted/40",
};

function SentimentIcon({ sentiment }: { sentiment: Signal["sentiment"] }) {
  if (sentiment === "positive") return <CircleCheck aria-label="Good" className="size-4 text-success" />;
  if (sentiment === "negative") return <TriangleAlert aria-label="Needs attention" className="size-4 text-destructive" />;
  return <Info aria-label="Note" className="size-4 text-muted-foreground" />;
}

/** Notable changes computed by Pandas (not the LLM): the facts the AI summary must explain. */
export function SignalsList({ signals }: { signals: Signal[] }) {
  if (signals.length === 0) {
    return (
      <p className="rounded-xl border border-dashed px-4 py-3 text-sm text-muted-foreground">
        No changes above ±15% vs the previous period.
      </p>
    );
  }
  return (
    <ul className="grid gap-2 md:grid-cols-2">
      {signals.map((s) => {
        const Trend = s.delta_pct > 0 ? TrendingUp : TrendingDown;
        return (
          <li key={`${s.kind}-${s.metric}-${s.channel}`} className={cn("flex items-start gap-2.5 rounded-xl border px-3 py-2.5 text-sm", TONE[s.sentiment])}>
            <span className="mt-0.5 shrink-0">
              <SentimentIcon sentiment={s.sentiment} />
            </span>
            <span className="flex-1">{s.message}</span>
            <Trend aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          </li>
        );
      })}
    </ul>
  );
}
