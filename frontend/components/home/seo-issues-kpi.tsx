"use client";

import { SearchCheck } from "lucide-react";
import Link from "next/link";

import { KpiCard } from "@/components/kpi-card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { getSeoHistory } from "@/lib/api";
import { useClient } from "@/lib/client-context";
import { hostname } from "@/lib/seo";

/** "Open SEO issues": fail + warn checks in the selected client's latest audit. */
export function SeoIssuesKpi() {
  const { client } = useClient();
  const { data, error } = useApi(`seo-issues:${client.id}`, (signal) =>
    getSeoHistory(client.id, { signal, silent: true }),
  );

  if (!data && !error) return <Skeleton className="h-[124px] rounded-2xl" />;

  const latest = data?.[0];
  const footnote = error
    ? "Unavailable"
    : latest
      ? `${client.name} · ${hostname(latest.final_url)} · score ${latest.score}`
      : `No audits for ${client.name} yet`;

  return (
    <Link
      href="/seo"
      className="block h-full rounded-2xl focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
    >
      <KpiCard
        label="Open SEO issues"
        value={latest ? String(latest.issue_count) : "—"}
        icon={SearchCheck}
        footnote={footnote}
      />
    </Link>
  );
}
