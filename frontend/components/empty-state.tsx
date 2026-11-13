import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { FadeIn } from "@/components/motion";
import { Badge } from "@/components/ui/badge";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  /** Small label above the title, e.g. "Coming in Phase 2". */
  badge?: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, badge, action }: EmptyStateProps) {
  return (
    <FadeIn delay={0.08}>
      <div className="relative flex flex-col items-center justify-center overflow-hidden rounded-2xl border border-dashed border-border bg-card/40 px-6 py-16 text-center md:py-24">
        <div
          aria-hidden
          className="bg-brand-gradient pointer-events-none absolute top-0 left-1/2 size-64 -translate-x-1/2 -translate-y-1/2 rounded-full opacity-10 blur-3xl"
        />
        <div className="relative mb-5 rounded-2xl bg-linear-to-br from-brand-from/40 to-brand-to/40 p-px">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-card">
            <Icon aria-hidden className="size-6 text-foreground" />
          </div>
        </div>
        {badge && (
          <Badge variant="secondary" className="relative mb-3">
            {badge}
          </Badge>
        )}
        <h2 className="relative text-lg font-semibold tracking-tight">{title}</h2>
        <p className="relative mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
        {action && <div className="relative mt-6">{action}</div>}
      </div>
    </FadeIn>
  );
}
