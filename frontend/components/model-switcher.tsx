"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useModel } from "@/lib/model-context";
import { isProvider, PROVIDERS } from "@/lib/providers";
import { cn } from "@/lib/utils";

/** Groq / OpenAI / Claude switcher. Below lg the trigger shrinks to just the provider dot. */
export function ModelSwitcher() {
  const { provider, setProvider } = useModel();

  return (
    <Select value={provider} onValueChange={(value) => isProvider(value) && setProvider(value)}>
      <SelectTrigger aria-label="LLM provider" className="gap-2 lg:w-32">
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="end" position="popper">
        {PROVIDERS.map((option) => (
          <SelectItem key={option.id} value={option.id}>
            <span className={cn("size-2 shrink-0 rounded-full", option.dotClass)} aria-hidden />
            <span className="max-lg:in-data-[slot=select-value]:sr-only">{option.label}</span>
            <span className="text-muted-foreground in-data-[slot=select-value]:hidden text-xs">
              {option.description}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
