import { ArrowLeft, Compass } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { getNavItem, MICRO_APP_HREFS } from "@/lib/nav";

export const metadata: Metadata = { title: "Page not found" };

/** Unmatched URLs render here, inside the root layout (no sidebar), so it carries its own nav. */
export default function NotFound() {
  return (
    <main className="relative flex min-h-svh flex-col items-center justify-center overflow-hidden px-4 py-16">
      <div
        aria-hidden
        className="bg-brand-gradient pointer-events-none absolute top-0 left-1/2 size-[28rem] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-15 blur-3xl"
      />
      <div className="relative w-full max-w-lg text-center">
        <div className="mb-10 flex justify-center">
          <Logo />
        </div>
        <div className="mx-auto mb-5 flex size-14 items-center justify-center rounded-2xl border border-border/60 bg-card shadow-card">
          <Compass aria-hidden className="size-6" />
        </div>
        <p className="text-brand-gradient text-sm font-semibold">404</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-balance md:text-3xl">
          This page went off the map
        </h1>
        <p className="mx-auto mt-3 max-w-sm text-sm text-muted-foreground md:text-base">
          The link may be old or mistyped. Head back home, or jump straight into one of the micro
          apps.
        </p>
        <Button asChild size="lg" className="bg-brand-gradient mt-6 border-0 text-white hover:opacity-90">
          <Link href="/">
            <ArrowLeft data-icon="inline-start" aria-hidden /> Back to home
          </Link>
        </Button>
        <nav aria-label="Micro apps" className="mt-10">
          <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {MICRO_APP_HREFS.map((href) => {
              const { label, icon: Icon } = getNavItem(href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className="flex flex-col items-center gap-2 rounded-xl border border-border/60 bg-card p-3 text-sm font-medium shadow-card outline-none transition-colors hover:border-border hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Icon aria-hidden className="size-4 text-muted-foreground" />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </main>
  );
}
