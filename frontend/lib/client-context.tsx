"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useLocalStorage } from "@/hooks/use-local-storage";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import type { DemoClient } from "@/lib/types";

export const DEMO_CLIENTS: readonly DemoClient[] = [
  { id: "bloom-bakery", name: "Bloom Bakery", industry: "Food & beverage", initials: "BB" },
  { id: "apex-fitness", name: "Apex Fitness", industry: "Health & fitness", initials: "AF" },
  { id: "nova-dental", name: "Nova Dental", industry: "Healthcare", initials: "ND" },
];

const CLIENT_IDS = DEMO_CLIENTS.map((c) => c.id);

interface ClientContextValue {
  client: DemoClient;
  setClientId: (id: string) => void;
}

const ClientContext = createContext<ClientContextValue | null>(null);

export function ClientProvider({ children }: { children: ReactNode }) {
  const [clientId, setClientId] = useLocalStorage(STORAGE_KEYS.client, CLIENT_IDS[0], CLIENT_IDS);

  const value = useMemo<ClientContextValue>(
    () => ({
      client: DEMO_CLIENTS.find((c) => c.id === clientId) ?? DEMO_CLIENTS[0],
      setClientId,
    }),
    [clientId, setClientId],
  );

  return <ClientContext.Provider value={value}>{children}</ClientContext.Provider>;
}

export function useClient(): ClientContextValue {
  const context = useContext(ClientContext);
  if (!context) throw new Error("useClient must be used inside <ClientProvider>");
  return context;
}
