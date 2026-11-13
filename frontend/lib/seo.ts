import { ApiError } from "@/lib/api";
import type { CheckStatus, FixPriority } from "@/lib/types";

/** Ranges the backend checks use (backend/app/services/seo/checks.py). */
export const TITLE_RANGE = { min: 30, max: 60 } as const;
export const META_RANGE = { min: 70, max: 160 } as const;

export const EXAMPLE_URLS = [
  "https://www.python.org",
  "https://developer.mozilla.org/en-US/",
  "https://react.dev",
] as const;

export type ScoreBand = "poor" | "fair" | "good";

export function scoreBand(score: number): ScoreBand {
  if (score < 50) return "poor";
  if (score < 80) return "fair";
  return "good";
}

export const SCORE_BAND_LABEL: Record<ScoreBand, string> = {
  poor: "Needs work",
  fair: "Fair",
  good: "Good",
};

export const STATUS_ORDER: readonly CheckStatus[] = ["fail", "warn", "pass"];

export const STATUS_LABEL: Record<CheckStatus, string> = {
  fail: "Failed",
  warn: "Warnings",
  pass: "Passed",
};

export const PRIORITY_ORDER: Record<FixPriority, number> = { High: 0, Medium: 1, Low: 2 };

export function isInRange(length: number, range: { min: number; max: number }): boolean {
  return length >= range.min && length <= range.max;
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatRelativeTime(iso: string, now: number = Date.now()): string {
  const minutes = Math.round((now - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export type AuditErrorKind =
  | "offline"
  | "invalid"
  | "too-large"
  | "blocked-address"
  | "not-html"
  | "timeout"
  | "bot-blocked"
  | "unreachable"
  | "not-found"
  | "unknown";

export interface AuditErrorInfo {
  kind: AuditErrorKind;
  title: string;
  hint: string;
}

const ERROR_COPY: Record<AuditErrorKind, Omit<AuditErrorInfo, "kind">> = {
  offline: { title: "Can't reach the API", hint: "Check that the backend is running on port 8000." },
  invalid: { title: "That URL isn't valid", hint: "Use a full web address like https://example.com." },
  "too-large": { title: "The page is too large", hint: "Audits are limited to pages under 2 MB." },
  "blocked-address": {
    title: "This address can't be audited",
    hint: "For safety, only public websites can be audited, not private or internal addresses.",
  },
  "not-html": { title: "Not a web page", hint: "Enter the URL of an HTML page rather than a file or image." },
  timeout: { title: "The site took too long", hint: "It didn't respond within 10 seconds. Try again later." },
  "bot-blocked": {
    title: "The site blocked our auditor",
    hint: "Some sites refuse automated requests. Try another page on the site.",
  },
  unreachable: { title: "Couldn't load the site", hint: "Check the address, or try again in a moment." },
  "not-found": { title: "Audit not found", hint: "It may have been removed. Run a new audit." },
  unknown: { title: "The audit failed", hint: "Please try again." },
};

function errorKind(error: ApiError): AuditErrorKind {
  const detail = error.message.toLowerCase();
  switch (error.status) {
    case null:
      return detail.includes("too long") ? "timeout" : "offline";
    case 400:
      return "blocked-address";
    case 404:
      return "not-found";
    case 415:
      return "not-html";
    case 422:
      return detail.includes("2 mb") ? "too-large" : "invalid";
    case 502:
      return detail.includes("automated") || detail.includes("refused") ? "bot-blocked" : "unreachable";
    case 504:
      return "timeout";
    default:
      return "unknown";
  }
}

export function describeAuditError(error: ApiError): AuditErrorInfo {
  const kind = errorKind(error);
  return { kind, ...ERROR_COPY[kind] };
}
