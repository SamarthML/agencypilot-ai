"use client";

import { FilePlus2, MessageSquarePlus, Moon, Search, SearchCheck, Sun, Users } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { DEMO_CLIENTS, useClient } from "@/lib/client-context";
import { requestIntent, type CommandIntent } from "@/lib/command-intents";
import { NAV_ITEMS } from "@/lib/nav";

interface ActionItem {
  label: string;
  href: string;
  intent: CommandIntent;
  icon: typeof Search;
  keywords: string[];
}

const ACTIONS: readonly ActionItem[] = [
  { label: "New SEO audit", href: "/seo", intent: "seo:new-audit", icon: SearchCheck, keywords: ["url", "scan", "website"] },
  { label: "New report", href: "/reports", intent: "reports:new", icon: FilePlus2, keywords: ["monthly", "pdf", "generate"] },
  { label: "Ask Copilot", href: "/copilot", intent: "copilot:ask", icon: MessageSquarePlus, keywords: ["chat", "question", "documents", "rag"] },
];

const noopSubscribe = () => () => {};

/** "⌘" on Apple platforms, "Ctrl" elsewhere; the server renders "Ctrl". */
function useModifierLabel(): string {
  return useSyncExternalStore(
    noopSubscribe,
    () => (/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl"),
    () => "Ctrl",
  );
}

/** Toggles the palette on Ctrl+K / ⌘+K from anywhere, including inside inputs. */
function useHotkey(toggle: () => void): void {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey) && !event.altKey) {
        event.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggle]);
}

function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="pointer-events-none inline-flex h-5 items-center rounded border border-border bg-muted px-1.5 font-sans text-[10px] font-medium text-muted-foreground">
      {children}
    </kbd>
  );
}

function PaletteTrigger({ onOpen }: { onOpen: () => void }) {
  const modifier = useModifierLabel();
  return (
    <>
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={onOpen} aria-label="Open command menu">
        <Search aria-hidden />
      </Button>
      <Button
        variant="outline"
        onClick={onOpen}
        aria-label="Open command menu"
        aria-keyshortcuts="Control+K Meta+K"
        className="hidden w-44 justify-start gap-2 overflow-hidden px-2.5 font-normal text-muted-foreground lg:flex xl:w-60"
      >
        <Search aria-hidden />
        <span className="min-w-0 flex-1 truncate text-left">
          Search<span className="max-xl:hidden"> or jump to</span>…
        </span>
        <span className="flex shrink-0 gap-0.5">
          <Kbd>{modifier}</Kbd>
          <Kbd>K</Kbd>
        </span>
      </Button>
    </>
  );
}

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const ranCommand = useRef(false);
  const router = useRouter();
  const { client, setClientId } = useClient();
  const { resolvedTheme, setTheme } = useTheme();
  useHotkey(useCallback(() => setOpen((value) => !value), []));

  function run(action: () => void) {
    ranCommand.current = true;
    setOpen(false);
    action();
  }

  // After a command, focus belongs to wherever it led (e.g. the SEO URL field), not the trigger.
  function onCloseAutoFocus(event: Event) {
    if (ranCommand.current) event.preventDefault();
    ranCommand.current = false;
  }

  const nextTheme = resolvedTheme === "dark" ? "light" : "dark";

  return (
    <>
      <PaletteTrigger onOpen={() => setOpen(true)} />
      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Command menu"
        description="Jump to a page, start an action or switch client"
        className="sm:max-w-lg"
        onCloseAutoFocus={onCloseAutoFocus}
      >
        {/* This shadcn style's CommandDialog doesn't add cmdk's root, so it's added here. */}
        <Command loop>
          <CommandInput placeholder="Type a command or search…" />
          <CommandList className="max-h-[min(24rem,60svh)]">
            <CommandEmpty>No matching commands.</CommandEmpty>
            <CommandGroup heading="Actions">
              {ACTIONS.map(({ label, href, intent, icon: Icon, keywords }) => (
                <CommandItem
                  key={intent}
                  keywords={keywords}
                  onSelect={() =>
                    run(() => {
                      requestIntent(intent);
                      router.push(href);
                    })
                  }
                >
                  <Icon aria-hidden />
                  {label}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Go to">
              {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
                <CommandItem key={href} value={`Go to ${label}`} onSelect={() => run(() => router.push(href))}>
                  <Icon aria-hidden />
                  {label}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Client">
              {DEMO_CLIENTS.map((c) => (
                <CommandItem
                  key={c.id}
                  value={`Switch to ${c.name}`}
                  keywords={["client", c.industry]}
                  data-checked={c.id === client.id}
                  onSelect={() => run(() => setClientId(c.id))}
                >
                  <Users aria-hidden />
                  Switch to {c.name}
                  {c.id === client.id && <span className="sr-only">(current client)</span>}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Preferences">
              <CommandItem keywords={["theme", "dark", "light", "mode"]} onSelect={() => run(() => setTheme(nextTheme))}>
                {nextTheme === "dark" ? <Moon aria-hidden /> : <Sun aria-hidden />}
                Switch to {nextTheme} theme
              </CommandItem>
            </CommandGroup>
          </CommandList>
          <div className="flex items-center justify-end gap-3 border-t border-border/60 px-3 py-2 text-[11px] text-muted-foreground max-sm:hidden">
            <span className="flex items-center gap-1"><Kbd>↑</Kbd><Kbd>↓</Kbd> navigate</span>
            <span className="flex items-center gap-1"><Kbd>Enter</Kbd> select</span>
            <span className="flex items-center gap-1"><Kbd>Esc</Kbd> close</span>
          </div>
        </Command>
      </CommandDialog>
    </>
  );
}
