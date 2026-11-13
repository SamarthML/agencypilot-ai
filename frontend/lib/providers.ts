import type { LlmProvider } from "@/lib/types";

export interface ProviderOption {
  id: LlmProvider;
  label: string;
  description: string;
  /** Tailwind class for the small identity dot. */
  dotClass: string;
}

/** Display metadata only. Actual model IDs are configured in backend/.env. */
export const PROVIDERS: readonly ProviderOption[] = [
  { id: "groq", label: "Groq", description: "Llama 3.3 70B · fastest", dotClass: "bg-orange-500" },
  { id: "openai", label: "OpenAI", description: "GPT-4o mini", dotClass: "bg-emerald-500" },
  { id: "claude", label: "Claude", description: "Claude Haiku", dotClass: "bg-amber-600" },
];

export const DEFAULT_PROVIDER: LlmProvider = "groq";
export const PROVIDER_IDS: readonly LlmProvider[] = PROVIDERS.map((p) => p.id);

export function isProvider(value: string | null): value is LlmProvider {
  return value !== null && (PROVIDER_IDS as readonly string[]).includes(value);
}
