"use client";

import { MotionConfig } from "framer-motion";
import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ClientProvider } from "@/lib/client-context";
import { ModelProvider } from "@/lib/model-context";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
      <MotionConfig reducedMotion="user">
        <TooltipProvider delayDuration={150}>
          <ModelProvider>
            <ClientProvider>
              {children}
              <Toaster position="bottom-right" richColors closeButton />
            </ClientProvider>
          </ModelProvider>
        </TooltipProvider>
      </MotionConfig>
    </ThemeProvider>
  );
}
