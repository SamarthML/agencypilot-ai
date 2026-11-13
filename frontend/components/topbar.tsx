"use client";

import { usePathname } from "next/navigation";
import { Suspense } from "react";

import { ApiStatus } from "@/components/api-status";
import { ClientSwitcher } from "@/components/client-switcher";
import { CommandMenu } from "@/components/command-menu";
import { ModelSwitcher } from "@/components/model-switcher";
import { MobileSidebar } from "@/components/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Separator } from "@/components/ui/separator";
import { findNavItemForPath } from "@/lib/nav";

const DEFAULT_TITLE = "AgencyPilot AI";

/** Reads the route, so it suspends while prerendering dynamic routes (see NavList in sidebar). */
function PageTitle() {
  return <>{findNavItemForPath(usePathname())?.label ?? DEFAULT_TITLE}</>;
}

export function Topbar() {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-border/60 bg-background/80 px-4 backdrop-blur-md md:px-8 print:hidden">
      <MobileSidebar />
      <p className="min-w-0 flex-1 truncate text-sm font-medium">
        <Suspense fallback={DEFAULT_TITLE}>
          <PageTitle />
        </Suspense>
      </p>
      <div className="flex items-center gap-1.5 sm:gap-2">
        <CommandMenu />
        <ClientSwitcher />
        <ModelSwitcher />
        <Separator orientation="vertical" className="mx-0.5 h-5! max-sm:hidden" />
        <ApiStatus />
        <ThemeToggle />
      </div>
    </header>
  );
}
