"use client";

import { FileText } from "lucide-react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { CitationRef } from "@/lib/citations";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

function formatMatch(similarity: number): string {
  return `${Math.round(similarity * 100)}% match`;
}

function SourceDetails({ source, citation }: { source: CitationRef; citation: Citation | undefined }) {
  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <FileText aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0">
          <p className="font-medium [overflow-wrap:anywhere]">{source.filename}</p>
          <p className="text-xs text-muted-foreground">
            Page {source.page}
            {citation && ` · ${formatMatch(citation.similarity)}`}
          </p>
        </div>
      </div>
      {citation ? (
        <blockquote className="max-h-56 overflow-y-auto border-l-2 border-brand-from/60 pl-3 text-xs leading-relaxed text-muted-foreground">
          {citation.snippet}
        </blockquote>
      ) : (
        <p className="text-xs text-muted-foreground">The passage appears when the answer finishes.</p>
      )}
    </div>
  );
}

const CHIP =
  "inline-flex h-[1.15rem] min-w-[1.15rem] items-center justify-center rounded-md bg-brand-from/15 px-1 align-[0.1em] text-[0.68rem] font-semibold text-brand-from tabular-nums transition-colors hover:bg-brand-from/25 focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none dark:text-brand-to";

/** Numbered superscript-style chip in the answer text; opens the cited passage. */
export function CitationChip({
  n,
  source,
  citation,
}: {
  n: number;
  source: CitationRef | undefined;
  citation: Citation | undefined;
}) {
  if (!source) return <span className={CHIP}>{n}</span>;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" className={cn(CHIP, "ml-0.5 cursor-pointer")} aria-label={`Source ${n}: ${source.filename}, page ${source.page}`}>
          {n}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 max-w-[calc(100vw-2rem)]" align="start">
        <SourceDetails source={source} citation={citation} />
      </PopoverContent>
    </Popover>
  );
}

interface SourceCardsProps {
  citations: readonly Citation[];
  /** Chip number for a citation, so cards and chips agree. */
  numberOf: (citation: Citation) => number | undefined;
}

/** The sources the answer cited, with the matching passage in a popover. */
export function SourceCards({ citations, numberOf }: SourceCardsProps) {
  if (citations.length === 0) return null;
  return (
    <div className="@container mt-4">
      <p className="mb-2 text-xs font-medium text-muted-foreground">Sources</p>
      <ul className="grid gap-2 @lg:grid-cols-2">
        {citations.map((citation, index) => (
          <li key={`${citation.filename}|${citation.page}`} className="min-w-0">
            <SourceCard n={numberOf(citation) ?? index + 1} citation={citation} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function SourceCard({ n, citation }: { n: number; citation: Citation }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="flex w-full min-w-0 items-center gap-2.5 rounded-xl border border-border/60 bg-background/50 px-3 py-2 text-left transition-colors hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          <span className={CHIP}>{n}</span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-xs font-medium" title={citation.filename}>
              {citation.filename}
            </span>
            <span className="block text-[11px] text-muted-foreground">
              Page {citation.page} · {formatMatch(citation.similarity)}
            </span>
          </span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 max-w-[calc(100vw-2rem)]" align="start">
        <SourceDetails source={citation} citation={citation} />
      </PopoverContent>
    </Popover>
  );
}
