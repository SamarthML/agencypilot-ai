import type { Citation } from "@/lib/types";

/**
 * Mirrors the backend's `citation_refs` (services/copilot.py): `[a.pdf p.2]`, `[a.pdf p.2, p.3]`,
 * `[a.pdf p.2; b.md p.1]`, and gpt-oss's `【a.pdf p.2】`. Each page belongs to the nearest
 * filename before it inside the same brackets.
 */
const BRACKET_RE = /[[【]([^[\]【】]{1,300})[\]】]/g;
const PAGE_RE = /\bp(?:age|g)?\.?\s*(\d+)/gi;
/** Used when the document list hasn't loaded: anything that looks like a file name. */
const FILENAME_RE = /[\w\-.()]+\.(?:pdf|txt|md)\b/gi;

export const CITE_HREF_PREFIX = "#cite-";

export interface CitationRef {
  filename: string;
  page: number;
}

function sourceKey(ref: CitationRef): string {
  return `${ref.filename.toLowerCase()}|${ref.page}`;
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

interface Mark {
  position: number;
  filename: string;
}

/** Find filenames in a bracket group, longest first, masking each so shorter names can't re-match. */
function filenameMarks(group: string, filenames: readonly string[]): { masked: string; marks: Mark[] } {
  let masked = group;
  const marks: Mark[] = [];
  const patterns = filenames.length
    ? [...filenames].sort((a, b) => b.length - a.length).map((n) => new RegExp(escapeRegExp(n), "gi"))
    : [FILENAME_RE];
  for (const pattern of patterns) {
    for (const match of masked.matchAll(new RegExp(pattern.source, "gi"))) {
      marks.push({ position: match.index, filename: match[0] });
      masked = masked.slice(0, match.index) + "#".repeat(match[0].length) + masked.slice(match.index + match[0].length);
    }
  }
  return { masked, marks: marks.sort((a, b) => a.position - b.position) };
}

function refsInGroup(group: string, filenames: readonly string[]): CitationRef[] {
  const { masked, marks } = filenameMarks(group, filenames);
  const refs: CitationRef[] = [];
  for (const page of masked.matchAll(PAGE_RE)) {
    const owner = marks.filter((m) => m.position < page.index).at(-1);
    if (owner) refs.push({ filename: owner.filename, page: Number(page[1]) });
  }
  return refs;
}

/**
 * Replace citation markers with markdown links `[n](#cite-n)`, numbered by first mention —
 * the same order the backend uses for the `citations` event. Repeats reuse their number.
 */
export function numberCitations(
  text: string,
  filenames: readonly string[] = [],
): { markdown: string; refs: CitationRef[] } {
  const refs: CitationRef[] = [];
  const numbers = new Map<string, number>();
  const numberFor = (ref: CitationRef): number => {
    const key = sourceKey(ref);
    if (!numbers.has(key)) {
      refs.push(ref);
      numbers.set(key, refs.length);
    }
    return numbers.get(key) ?? refs.length;
  };
  const markdown = text.replace(BRACKET_RE, (marker, group: string) => {
    const groupRefs = refsInGroup(group, filenames);
    if (groupRefs.length === 0) return marker;
    const unique = [...new Set(groupRefs.map(numberFor))];
    return unique.map((n) => `[${n}](${CITE_HREF_PREFIX}${n})`).join("");
  });
  return { markdown, refs };
}

/** The structured citation behind a ref, matched by file + page. */
export function citationFor(ref: CitationRef | undefined, citations: readonly Citation[]): Citation | undefined {
  if (!ref) return undefined;
  const key = sourceKey(ref);
  return citations.find((c) => sourceKey(c) === key);
}

/** Answer text with citation markers stripped, for the clipboard. */
export function stripCitations(text: string, filenames: readonly string[] = []): string {
  return text
    .replace(BRACKET_RE, (marker, group: string) => (refsInGroup(group, filenames).length ? "" : marker))
    .replace(/[ \t]+([.,;:!?])/g, "$1")
    .replace(/[ \t]{2,}/g, " ");
}
