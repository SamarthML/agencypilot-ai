import type { ReportContent } from "@/lib/types";

/** Mirrors the backend's ReportContent limits so edits are validated before saving. */
export const TEXT_LIMITS = {
  title: 120,
  executive_summary: 2000,
  channel_commentary: 2500,
  seo_highlights: 1500,
  closing_note: 800,
} as const;

export const ITEM_MAX = 500;

export const LIST_LIMITS = {
  wins: { min: 2, max: 5 },
  challenges: { min: 1, max: 4 },
  next_month_plan: { min: 3, max: 5 },
} as const;

export type TextKey = keyof typeof TEXT_LIMITS;
export type ListKey = keyof typeof LIST_LIMITS;

const LABELS: Record<TextKey | ListKey, string> = {
  title: "Title",
  executive_summary: "Executive summary",
  channel_commentary: "Channel performance",
  seo_highlights: "SEO highlights",
  closing_note: "Closing note",
  wins: "Wins",
  challenges: "Challenges",
  next_month_plan: "Plan for next month",
};

export function sectionLabel(key: TextKey | ListKey): string {
  return LABELS[key];
}

function textProblem(key: TextKey, value: string | null): string | null {
  if (value === null) return key === "seo_highlights" ? null : `${LABELS[key]} is required.`;
  if (!value.trim()) return key === "seo_highlights" ? null : `${LABELS[key]} can't be empty.`;
  if (value.length > TEXT_LIMITS[key]) return `${LABELS[key]} is over ${TEXT_LIMITS[key]} characters.`;
  return null;
}

function listProblem(key: ListKey, items: string[]): string | null {
  const { min, max } = LIST_LIMITS[key];
  if (items.length < min || items.length > max) return `${LABELS[key]} needs ${min}-${max} items.`;
  if (items.some((item) => !item.trim())) return `${LABELS[key]} has an empty item.`;
  if (items.some((item) => item.length > ITEM_MAX)) return `A ${LABELS[key]} item is over ${ITEM_MAX} characters.`;
  return null;
}

/** First problem that would make the backend reject the edit, or null when it is valid. */
export function validateContent(content: ReportContent): string | null {
  for (const key of Object.keys(TEXT_LIMITS) as TextKey[]) {
    const problem = textProblem(key, content[key]);
    if (problem) return problem;
  }
  for (const key of Object.keys(LIST_LIMITS) as ListKey[]) {
    const problem = listProblem(key, content[key]);
    if (problem) return problem;
  }
  return null;
}

/** Trim whitespace and turn an empty SEO section into null before saving. */
export function normalizeContent(content: ReportContent): ReportContent {
  const seo = content.seo_highlights?.trim();
  return {
    ...content,
    title: content.title.trim(),
    executive_summary: content.executive_summary.trim(),
    channel_commentary: content.channel_commentary.trim(),
    closing_note: content.closing_note.trim(),
    seo_highlights: seo ? seo : null,
    wins: content.wins.map((s) => s.trim()),
    challenges: content.challenges.map((s) => s.trim()),
    next_month_plan: content.next_month_plan.map((s) => s.trim()),
  };
}
