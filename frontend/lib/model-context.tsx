"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useLocalStorage } from "@/hooks/use-local-storage";
import { DEFAULT_PROVIDER, PROVIDER_IDS, PROVIDERS, type ProviderOption } from "@/lib/providers";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import type { LlmProvider } from "@/lib/types";

interface ModelContextValue {
  provider: LlmProvider;
  providerOption: ProviderOption;
  setProvider: (provider: LlmProvider) => void;
}

const ModelContext = createContext<ModelContextValue | null>(null);

/** Selected LLM provider, persisted in localStorage and sent to the API as X-LLM-Provider. */
export function ModelProvider({ children }: { children: ReactNode }) {
  const [provider, setProvider] = useLocalStorage(
    STORAGE_KEYS.provider,
    DEFAULT_PROVIDER,
    PROVIDER_IDS,
  );

  const value = useMemo<ModelContextValue>(
    () => ({
      provider,
      providerOption: PROVIDERS.find((p) => p.id === provider) ?? PROVIDERS[0],
      setProvider,
    }),
    [provider, setProvider],
  );

  return <ModelContext.Provider value={value}>{children}</ModelContext.Provider>;
}

export function useModel(): ModelContextValue {
  const context = useContext(ModelContext);
  if (!context) throw new Error("useModel must be used inside <ModelProvider>");
  return context;
}
