import { CircleCheck, PencilLine } from "lucide-react";

import type { ReportStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLE: Record<ReportStatus, { label: string; className: string; icon: typeof CircleCheck }> = {
  draft: { label: "Draft", className: "bg-warning/15 text-warning", icon: PencilLine },
  final: { label: "Final", className: "bg-success/10 text-success", icon: CircleCheck },
};

/** Status is always icon + label, never colour alone. */
export function ReportStatusBadge({ status, className }: { status: ReportStatus; className?: string }) {
  const { label, className: tone, icon: Icon } = STYLE[status];
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium",
        tone,
        className,
      )}
    >
      <Icon aria-hidden className="size-3.5" />
      {label}
    </span>
  );
}
