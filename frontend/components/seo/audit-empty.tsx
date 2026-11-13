import { Gauge, ListChecks, Sparkles, type LucideIcon } from "lucide-react";

import { Stagger, StaggerItem } from "@/components/motion";

const FEATURES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: ListChecks,
    title: "10 rule-based checks",
    body: "Title, meta description, H1, heading order, alt text, canonical, viewport, HTTPS, Open Graph and content length.",
  },
  {
    icon: Gauge,
    title: "A 0–100 score",
    body: "Weighted in code from the check results, never guessed by the model, so it's repeatable.",
  },
  {
    icon: Sparkles,
    title: "AI recommendations",
    body: "Prioritised fixes, rewritten title and meta description, keywords and content ideas.",
  },
];

/** What the user gets, shown before the first audit. */
export function AuditEmpty() {
  return (
    <Stagger className="grid gap-3 md:grid-cols-3">
      {FEATURES.map(({ icon: Icon, title, body }) => (
        <StaggerItem key={title}>
          <div className="h-full rounded-2xl border border-dashed border-border bg-card/40 p-5">
            <span className="mb-3 flex size-9 items-center justify-center rounded-lg bg-muted">
              <Icon aria-hidden className="size-4 text-muted-foreground" />
            </span>
            <p className="text-sm font-medium">{title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{body}</p>
          </div>
        </StaggerItem>
      ))}
    </Stagger>
  );
}
