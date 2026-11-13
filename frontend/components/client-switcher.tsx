"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DEMO_CLIENTS, useClient } from "@/lib/client-context";

/** Active client selector. On phones the trigger shows only the client's initials. */
export function ClientSwitcher() {
  const { client, setClientId } = useClient();

  return (
    <Select value={client.id} onValueChange={setClientId}>
      <SelectTrigger aria-label="Client" className="gap-2 sm:w-44">
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="end" position="popper">
        {DEMO_CLIENTS.map((option) => (
          <SelectItem key={option.id} value={option.id}>
            <span
              aria-hidden
              className="flex size-5 shrink-0 items-center justify-center rounded-md bg-muted text-[10px] font-semibold text-foreground"
            >
              {option.initials}
            </span>
            <span className="max-sm:in-data-[slot=select-value]:sr-only">{option.name}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
