import { CircleCheck, CircleX, TriangleAlert, type LucideIcon } from "lucide-react";

import type { CheckStatus, FixPriority } from "@/lib/types";
import { cn } from "@/lib/utils";

interface StatusStyle {
  label: string;
  icon: LucideIcon;
  text: string;
  background: string;
}

const STATUS_STYLE: Record<CheckStatus, StatusStyle> = {
  fail: { label: "Fail", icon: CircleX, text: "text-destructive", background: "bg-destructive/10" },
  warn: { label: "Warn", icon: TriangleAlert, text: "text-warning", background: "bg-warning/15" },
  pass: { label: "Pass", icon: CircleCheck, text: "text-success", background: "bg-success/10" },
};

const PRIORITY_STYLE: Record<FixPriority, string> = {
  High: "bg-destructive/10 text-destructive",
  Medium: "bg-warning/15 text-warning",
  Low: "bg-muted text-muted-foreground",
};

const PILL = "inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium";

/** Status is always icon + label, never colour alone. */
export function StatusBadge({ status }: { status: CheckStatus }) {
  const { label, icon: Icon, text, background } = STATUS_STYLE[status];
  return (
    <span className={cn(PILL, text, background)}>
      <Icon aria-hidden className="size-3.5" />
      {label}
    </span>
  );
}

export function StatusIcon({ status, className }: { status: CheckStatus; className?: string }) {
  const { icon: Icon, text } = STATUS_STYLE[status];
  return <Icon aria-hidden className={cn("size-4", text, className)} />;
}

export function PriorityBadge({ priority }: { priority: FixPriority }) {
  return <span className={cn(PILL, PRIORITY_STYLE[priority])}>{priority}</span>;
}
