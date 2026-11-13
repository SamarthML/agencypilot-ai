import { Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { formatInteger, formatUsd } from "@/lib/format";
import { PROVIDERS } from "@/lib/providers";
import type { LlmCallMeta } from "@/lib/types";

/** Provider, model, tokens, latency and cost of the call that produced an AI answer. */
export function LlmMeta({ meta }: { meta: LlmCallMeta }) {
  const provider = PROVIDERS.find((p) => p.id === meta.provider);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span aria-hidden className={`size-2 rounded-full ${provider?.dotClass ?? "bg-muted-foreground"}`} />
        <span className="text-foreground">{provider?.label ?? meta.provider}</span>
        <span className="font-mono">{meta.model}</span>
      </span>
      <span className="tabular-nums">
        {formatInteger(meta.input_tokens)} in · {formatInteger(meta.output_tokens)} out
      </span>
      <span className="tabular-nums">{formatInteger(meta.latency_ms)} ms</span>
      <span className="tabular-nums text-foreground">{formatUsd(meta.cost_usd)}</span>
      {meta.cached && (
        <Badge variant="secondary" className="gap-1">
          <Zap aria-hidden className="size-3" /> Cached
        </Badge>
      )}
    </div>
  );
}
