import { toast } from "sonner";

import { DEFAULT_PROVIDER, isProvider } from "@/lib/providers";
import { readStorage } from "@/lib/storage";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import type {
  AskResponse,
  DatasetUploadResponse,
  Days,
  HealthResponse,
  InsightsDashboard,
  InsightSummary,
  LlmProvider,
  OverviewResponse,
  SampleLoadResponse,
  SeoAuditRequest,
  SeoAuditResponse,
  SeoAuditSummary,
} from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);
export const PROVIDER_HEADER = "X-LLM-Provider";
const DEFAULT_TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  constructor(
    message: string,
    /** HTTP status, or null for network errors / timeouts. */
    readonly status: number | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiOptions extends RequestInit {
  /** Don't show a toast on failure (e.g. background polling). */
  silent?: boolean;
  timeoutMs?: number;
}

/** The provider chosen in the model switcher, readable outside React. */
export function getSelectedProvider(): LlmProvider {
  const stored = readStorage(STORAGE_KEYS.provider);
  return isProvider(stored) ? stored : DEFAULT_PROVIDER;
}

function buildHeaders(init: RequestInit): Headers {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set(PROVIDER_HEADER, getSelectedProvider());
  const isJsonBody = init.body !== undefined && !(init.body instanceof FormData);
  if (isJsonBody && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return headers;
}

/** FastAPI errors look like {"detail": "..."} or {"detail": [{msg: "..."}]}. */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const { detail } = body as { detail: unknown };
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
    }
  } catch {
    // Non-JSON error body; fall through to the status text.
  }
  return response.statusText || `Request failed with status ${response.status}`;
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return new ApiError("The API took too long to respond.", null);
  }
  return new ApiError("Can't reach the API. Is the backend running?", null);
}

/** True when the caller cancelled the request (not a timeout): never worth a toast. */
export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { silent = false, timeoutMs = DEFAULT_TIMEOUT_MS, ...init } = options;
  const timeout = AbortSignal.timeout(timeoutMs);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: buildHeaders(init),
      signal: init.signal ? AbortSignal.any([init.signal, timeout]) : timeout,
    });
    if (!response.ok) throw new ApiError(await readErrorMessage(response), response.status);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (isAbortError(error)) throw error;
    const apiError = toApiError(error);
    if (!silent) toast.error("Request failed", { description: apiError.message });
    throw apiError;
  }
}

export function getHealth(options: ApiOptions = {}): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", { timeoutMs: 5_000, ...options });
}

/* ---- Insights ---- */

/** LLM calls can take a while (reasoning models, retries with backoff). */
const LLM_TIMEOUT_MS = 90_000;

export function getInsightsDashboard(
  clientId: string,
  days: Days,
  options: ApiOptions = {},
): Promise<InsightsDashboard> {
  return apiFetch(`/api/insights/${clientId}/summary?days=${days}`, options);
}

export function getInsightsOverview(days: Days, options: ApiOptions = {}): Promise<OverviewResponse> {
  return apiFetch(`/api/insights/overview?days=${days}`, options);
}

export function generateAiSummary(clientId: string, days: Days): Promise<InsightSummary> {
  return apiFetch(`/api/insights/${clientId}/ai-summary`, {
    method: "POST",
    body: JSON.stringify({ days }),
    timeoutMs: LLM_TIMEOUT_MS,
  });
}

export function askInsights(clientId: string, days: Days, question: string): Promise<AskResponse> {
  return apiFetch(`/api/insights/${clientId}/ask`, {
    method: "POST",
    body: JSON.stringify({ days, question }),
    timeoutMs: LLM_TIMEOUT_MS,
  });
}

export function uploadInsightsCsv(
  clientId: string,
  clientName: string,
  file: File,
): Promise<DatasetUploadResponse> {
  const body = new FormData();
  body.append("file", file);
  body.append("client_name", clientName);
  return apiFetch(`/api/insights/${clientId}/upload`, {
    method: "POST",
    body,
    timeoutMs: 60_000,
    silent: true, // the upload dialog shows the validation message inline
  });
}

/* ---- SEO Audit ---- */

/** Fetch (≤10 s) + checks + LLM report; cached audits return in milliseconds. */
const SEO_AUDIT_TIMEOUT_MS = 120_000;

export function runSeoAudit(request: SeoAuditRequest): Promise<SeoAuditResponse> {
  return apiFetch("/api/seo/audit", {
    method: "POST",
    body: JSON.stringify(request),
    timeoutMs: SEO_AUDIT_TIMEOUT_MS,
    silent: true, // the page shows a friendly error card instead of a toast
  });
}

export function getSeoAudit(id: string, options: ApiOptions = {}): Promise<SeoAuditResponse> {
  return apiFetch(`/api/seo/audits/${encodeURIComponent(id)}`, options);
}

export function getSeoHistory(
  clientId: string | null,
  options: ApiOptions = {},
): Promise<SeoAuditSummary[]> {
  const query = clientId ? `?client=${encodeURIComponent(clientId)}` : "";
  return apiFetch(`/api/seo/history${query}`, options);
}

export function loadSampleData(): Promise<SampleLoadResponse> {
  return apiFetch("/api/insights/sample", { method: "POST", timeoutMs: 60_000 });
}
