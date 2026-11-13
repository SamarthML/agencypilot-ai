"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

const RESET_MS = 1500;

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), RESET_MS);
    } catch {
      toast.error("Couldn't copy to the clipboard");
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={copy}
      aria-label={copied ? `${label} copied` : `Copy ${label}`}
      title={copied ? "Copied" : "Copy"}
      className="shrink-0 print:hidden"
    >
      {copied ? <Check aria-hidden className="text-success" /> : <Copy aria-hidden />}
    </Button>
  );
}
