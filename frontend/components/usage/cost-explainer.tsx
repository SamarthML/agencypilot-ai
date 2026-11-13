import { Calculator, Gauge, Layers, Repeat2, ShieldCheck, Sliders, Timer, type LucideIcon } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface Lever {
  icon: LucideIcon;
  title: string;
  detail: string;
}

function levers(rateLimit: number | null): Lever[] {
  return [
    {
      icon: Gauge,
      title: "Cheap, fast default model",
      detail: "Every feature defaults to an open model on Groq, a fraction of the price of frontier models.",
    },
    {
      icon: Repeat2,
      title: "Response caching",
      detail: "Identical insights summaries (10 min) and SEO audits (1 h) are replayed from cache at $0.",
    },
    {
      icon: ShieldCheck,
      title: "Similarity guardrail",
      detail: "When no document passage is relevant enough, Copilot says so without calling the LLM.",
    },
    {
      icon: Sliders,
      title: "max_tokens caps",
      detail: "Each feature has its own output budget, so a runaway answer can't run up the bill.",
    },
    {
      icon: Calculator,
      title: "Pandas does the maths",
      detail: "KPIs, deltas and scores are computed in code; the LLM only gets compact facts to write about.",
    },
    {
      icon: Layers,
      title: "Provider switcher",
      detail: "Pick Groq, OpenAI or Claude per request to trade cost against quality where it matters.",
    },
    {
      icon: Timer,
      title: "Rate limiting",
      detail: rateLimit
        ? `AI endpoints accept ${rateLimit} requests per minute per client, so a loop can't drain the budget.`
        : "AI endpoints are rate limited per client, so a loop can't drain the budget.",
    },
  ];
}

export function CostExplainer({ rateLimit }: { rateLimit: number | null }) {
  return (
    <Card>
      <CardHeader className="gap-1">
        <CardTitle className="text-base">How AgencyPilot keeps AI costs low</CardTitle>
        <CardDescription>Every number on this page comes from the llm_usage log written by one LLM service layer.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {levers(rateLimit).map(({ icon: Icon, title, detail }) => (
            <li key={title} className="flex gap-3">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-brand-from/10 text-brand-text">
                <Icon aria-hidden className="size-4" />
              </span>
              <div className="min-w-0 space-y-0.5">
                <p className="text-sm font-medium">{title}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{detail}</p>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
