import {
  Ban,
  CloudOff,
  FileWarning,
  Link2Off,
  SearchX,
  ShieldAlert,
  ShieldX,
  Timer,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { ApiError } from "@/lib/api";
import { describeAuditError, type AuditErrorKind } from "@/lib/seo";

const ICONS: Record<AuditErrorKind, LucideIcon> = {
  offline: CloudOff,
  invalid: Link2Off,
  "too-large": FileWarning,
  "blocked-address": ShieldX,
  "not-html": FileWarning,
  timeout: Timer,
  "bot-blocked": ShieldAlert,
  unreachable: Ban,
  "not-found": SearchX,
  unknown: TriangleAlert,
};

interface AuditErrorCardProps {
  error: ApiError;
  url: string | null;
  onRetry: (() => void) | null;
}

/** A friendly explanation for each backend error, with the server's exact message underneath. */
export function AuditErrorCard({ error, url, onRetry }: AuditErrorCardProps) {
  const info = describeAuditError(error);
  const Icon = ICONS[info.kind];

  return (
    <Card role="alert" className="border-destructive/30">
      <CardContent className="flex flex-col items-start gap-4 sm:flex-row">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
          <Icon aria-hidden className="size-5" />
        </span>
        <div className="min-w-0 flex-1 space-y-1.5">
          <h2 className="font-semibold">{info.title}</h2>
          <p className="text-sm text-muted-foreground">{info.hint}</p>
          <p className="rounded-lg bg-muted/60 px-3 py-2 font-mono text-xs break-words text-muted-foreground">
            {url && <span className="text-foreground">{url}: </span>}
            {error.message}
          </p>
        </div>
        {onRetry && info.kind !== "blocked-address" && info.kind !== "invalid" && (
          <Button variant="outline" onClick={onRetry} className="shrink-0">
            Try again
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
