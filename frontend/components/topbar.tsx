"use client";

import { usePathname } from "next/navigation";

import { ApiStatus } from "@/components/api-status";
import { ClientSwitcher } from "@/components/client-switcher";
import { ModelSwitcher } from "@/components/model-switcher";
import { MobileSidebar } from "@/components/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Separator } from "@/components/ui/separator";
import { findNavItemForPath } from "@/lib/nav";

export function Topbar() {
  const pathname = usePathname();
  const title = findNavItemForPath(pathname)?.label ?? "AgencyPilot AI";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-border/60 bg-background/80 px-4 backdrop-blur-md md:px-8">
      <MobileSidebar />
      <p className="min-w-0 flex-1 truncate text-sm font-medium">{title}</p>
      <div className="flex items-center gap-1.5 sm:gap-2">
        <ClientSwitcher />
        <ModelSwitcher />
        <Separator orientation="vertical" className="mx-0.5 h-5! max-sm:hidden" />
        <ApiStatus />
        <ThemeToggle />
      </div>
    </header>
  );
}
