import { Sparkles } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

export function Logo({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <Link
      href="/"
      className="flex items-center gap-2.5 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label="AgencyPilot AI home"
    >
      <span className="bg-brand-gradient flex size-8 shrink-0 items-center justify-center rounded-lg shadow-sm shadow-indigo-500/30">
        <Sparkles className="size-4 text-white" aria-hidden />
      </span>
      <span
        className={cn(
          "truncate text-[15px] font-semibold tracking-tight transition-opacity",
          collapsed && "sr-only",
        )}
      >
        AgencyPilot <span className="text-muted-foreground font-medium">AI</span>
      </span>
    </Link>
  );
}
