import { FlaskConical } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export const DEMO_AUDIT_HINT = "Seeded from bundled HTML - audit a real URL for live results";

const PILL =
  "inline-flex shrink-0 items-center gap-1 rounded-md bg-brand-from/10 px-1.5 py-0.5 font-medium text-brand-text";

/** Marks an audit seeded by the demo data (fictional site, no live fetch), with a tooltip. */
export function DemoAuditBadge({ className }: { className?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          aria-label={`Demo audit: ${DEMO_AUDIT_HINT}`}
          className={cn(
            PILL,
            "cursor-help text-xs focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none",
            className,
          )}
        >
          <FlaskConical aria-hidden className="size-3.5" />
          Demo audit
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-64">{DEMO_AUDIT_HINT}</TooltipContent>
    </Tooltip>
  );
}

/** Non-interactive version for use inside buttons (e.g. history rows). */
export function DemoAuditTag() {
  return (
    <span className={cn(PILL, "text-[10px]")} title={DEMO_AUDIT_HINT}>
      <FlaskConical aria-hidden className="size-3" />
      Demo
    </span>
  );
}
