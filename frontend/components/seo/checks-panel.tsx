"use client";

import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { StatusBadge, StatusIcon } from "@/components/seo/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { STATUS_LABEL, STATUS_ORDER } from "@/lib/seo";
import type { CheckStatus, SeoCheck } from "@/lib/types";
import { cn } from "@/lib/utils";

function CheckItem({ check }: { check: SeoCheck }) {
  return (
    <li className="break-inside-avoid rounded-xl border border-border/70 bg-background/40 p-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={check.status} />
        <p className="text-sm font-medium">{check.name}</p>
        <span className="ml-auto text-xs text-muted-foreground tabular-nums" title="Share of the score">
          {check.weight} pts
        </span>
      </div>
      <p className="mt-2 font-mono text-xs break-words text-muted-foreground">{check.value}</p>
      {check.status !== "pass" && <p className="mt-1.5 text-sm">{check.recommendation}</p>}
    </li>
  );
}

function CheckGroup({ status, checks }: { status: CheckStatus; checks: SeoCheck[] }) {
  const collapsible = status === "pass";
  const [open, setOpen] = useState(!collapsible);
  const listId = `checks-${status}`;

  return (
    <section className="space-y-2.5">
      <div className="flex items-center gap-2">
        <StatusIcon status={status} />
        <h3 className="text-sm font-medium">
          {STATUS_LABEL[status]} <span className="text-muted-foreground tabular-nums">({checks.length})</span>
        </h3>
        {collapsible && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto text-xs text-muted-foreground print:hidden"
            aria-expanded={open}
            aria-controls={listId}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide" : "Show"}
            <ChevronDown aria-hidden data-icon="inline-end" className={cn("transition-transform", open && "rotate-180")} />
          </Button>
        )}
      </div>
      {/* Collapsed groups stay in the DOM (hidden on screen) so the PDF still lists them. */}
      <motion.ul
        id={listId}
        key={open ? "open" : "closed"}
        initial={open && collapsible ? { opacity: 0, y: -4 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className={cn("grid gap-2 @xl:grid-cols-2", !open && "hidden print:grid")}
      >
        {checks.map((check) => (
          <CheckItem key={check.id} check={check} />
        ))}
      </motion.ul>
    </section>
  );
}

export function ChecksPanel({ checks }: { checks: SeoCheck[] }) {
  const groups = STATUS_ORDER.map((status) => ({
    status,
    checks: checks.filter((c) => c.status === status),
  })).filter((group) => group.checks.length > 0);

  return (
    <Card>
      <CardHeader className="gap-1">
        <CardTitle className="text-base">Checks</CardTitle>
        <CardDescription>10 rule-based checks; points are each check&apos;s share of the score.</CardDescription>
      </CardHeader>
      <CardContent className="@container space-y-6">
        {groups.map((group) => (
          <CheckGroup key={group.status} status={group.status} checks={group.checks} />
        ))}
      </CardContent>
    </Card>
  );
}
