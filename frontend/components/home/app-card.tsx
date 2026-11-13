import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import type { NavItem } from "@/lib/nav";

export function AppCard({ item }: { item: NavItem }) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className="group flex h-full flex-col gap-4 rounded-2xl border border-border/60 bg-card p-5 shadow-card outline-none transition-all duration-200 hover:-translate-y-0.5 hover:border-border focus-visible:ring-2 focus-visible:ring-ring md:p-6"
    >
      <div className="flex items-start justify-between">
        <span className="flex size-10 items-center justify-center rounded-xl bg-muted transition-colors group-hover:bg-accent">
          <Icon aria-hidden className="size-5" />
        </span>
        <ArrowUpRight
          aria-hidden
          className="size-4 text-muted-foreground transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-foreground"
        />
      </div>
      <div className="space-y-1.5">
        <h3 className="font-semibold tracking-tight">{item.label}</h3>
        <p className="text-sm leading-relaxed text-muted-foreground">{item.description}</p>
      </div>
    </Link>
  );
}
