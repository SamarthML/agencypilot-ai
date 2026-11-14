import { toast } from "sonner";

import { DEFAULT_PROVIDER, isProvider } from "@/lib/providers";
import { readStorage } from "@/lib/storage";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import { parseSseChunk } from "@/lib/sse";
import { createWarmup } from "@/lib/warmup";
import type {
  AskResponse,
  ChatRequest,
  CopilotDocument,
  CopilotStreamEvent,
  FeedbackRequest,
  FeedbackResponse,
  DatasetUploadResponse,
  Days,
  HealthResponse,
  InsightsDashboard,
  InsightSummary,
  LlmProvider,
  ModelsResponse,
  OverviewResponse,
  Report,
  ReportGenerateRequest,
  ReportMonth,
  ReportSummary,
  ReportUpdate,
  SampleLoadResponse,
  SeoAuditRequest,
  SeoAuditResponse,
  SeoAuditSummary,
  AppSettings,
  UsageCall,
  UsageDays,
  UsageSummary,
} from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);
export const PROVIDER_HEADER = "X-LLM-Provider";

/** Cold-start gate: every request waits for the first /health answer (see lib/warmup.ts). */
export const serverWarmup = createWarmup(async (timeoutMs) => {
  try {
    const response = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(timeoutMs) });
    return response.ok;
  } catch {
    return false;
  }
});
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
function parseErrorDetail(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const { detail } = body as { detail: unknown };
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  return null;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const detail = parseErrorDetail(await response.json());
    if (detail) return detail;
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

/** HTTP 429 from the per-client LLM rate limit. */
export function isRateLimited(error: unknown): boolean {
  return error instanceof ApiError && error.status === 429;
}

/** Shown even for silent requests: the user needs to know why nothing happened. One at a time. */
function toastRateLimit(error: ApiError): void {
  toast.warning("Slow down a little", { id: "rate-limit", description: error.message });
}

/** True when the caller cancelled the request (not a timeout): never worth a toast. */
export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { silent = false, timeoutMs = DEFAULT_TIMEOUT_MS, ...init } = options;
  await serverWarmup.ready();
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
    if (isRateLimited(apiError)) toastRateLimit(apiError);
    else if (!silent) toast.error("Request failed", { description: apiError.message });
    throw apiError;
  }
}

export function getHealth(options: ApiOptions = {}): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", { timeoutMs: 5_000, ...options });
}

export function getModels(options: ApiOptions = {}): Promise<ModelsResponse> {
  return apiFetch<ModelsResponse>("/api/models", { silent: true, ...options });
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

/* ---- Client Copilot ---- */

export function getCopilotDocuments(
  clientId: string,
  options: ApiOptions = {},
): Promise<CopilotDocument[]> {
  return apiFetch(`/api/copilot/documents?client=${encodeURIComponent(clientId)}`, options);
}

export function deleteCopilotDocument(id: string): Promise<void> {
  return apiFetch(`/api/copilot/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function sendCopilotFeedback(body: FeedbackRequest): Promise<FeedbackResponse> {
  return apiFetch("/api/copilot/feedback", { method: "POST", body: JSON.stringify(body) });
}

function xhrError(xhr: XMLHttpRequest): ApiError {
  let detail: string | null = null;
  try {
    detail = parseErrorDetail(JSON.parse(xhr.responseText));
  } catch {
    // Non-JSON error body.
  }
  return new ApiError(detail ?? (xhr.statusText || `Upload failed with status ${xhr.status}`), xhr.status);
}

/**
 * Upload a document for ingestion. Uses XMLHttpRequest because fetch can't report upload
 * progress. Silent: the dropzone shows failures inline.
 */
export function uploadCopilotDocument(
  clientId: string,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<CopilotDocument> {
  const body = new FormData();
  body.append("client", clientId);
  body.append("file", file);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/copilot/upload`);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.setRequestHeader(PROVIDER_HEADER, getSelectedProvider());
    xhr.timeout = 120_000;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve(JSON.parse(xhr.responseText) as CopilotDocument)
        : reject(xhrError(xhr));
    xhr.onerror = () => reject(new ApiError("Can't reach the API. Is the backend running?", null));
    xhr.ontimeout = () => reject(new ApiError("The upload took too long.", null));
    xhr.send(body);
  });
}

async function openChatStream(
  request: ChatRequest,
  signal: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  await serverWarmup.ready();
  const body = JSON.stringify(request);
  const headers = buildHeaders({ body });
  headers.set("Accept", "text/event-stream");
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/copilot/chat/stream`, {
      method: "POST",
      headers,
      body,
      signal,
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw toApiError(error);
  }
  if (!response.ok) {
    const error = new ApiError(await readErrorMessage(response), response.status);
    if (isRateLimited(error)) toastRateLimit(error);
    throw error;
  }
  if (!response.body) throw new ApiError("The API returned an empty stream.", null);
  return response.body;
}

/**
 * POST a question and yield its Server-Sent Events as they arrive (`token`* → `citations` →
 * `done`, or `error`). EventSource can't POST, so this reads the fetch body stream directly.
 * Throws ApiError on HTTP/network failure (including a drop mid-stream); rethrows aborts.
 */
export async function* streamCopilotChat(
  request: ChatRequest,
  signal: AbortSignal,
): AsyncGenerator<CopilotStreamEvent> {
  const stream = await openChatStream(request, signal);
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const parsed = parseSseChunk(buffer + decoder.decode(value, { stream: true }));
      buffer = parsed.rest;
      yield* parsed.events;
    }
  } catch (error) {
    if (isAbortError(error) || signal.aborted) throw new DOMException("Aborted", "AbortError");
    throw new ApiError("Connection lost mid-answer.", null);
  } finally {
    // Also runs when the consumer stops early: free the connection.
    reader.cancel().catch(() => undefined);
  }
  // The final event may arrive without its terminating blank line.
  yield* parseSseChunk(`${buffer}\n\n`).events;
}

/* ---- Report Generator ---- */

/** Metrics + a full structured report from a reasoning model can take a while. */
const REPORT_TIMEOUT_MS = 120_000;

export function getReportMonths(clientId: string, options: ApiOptions = {}): Promise<ReportMonth[]> {
  return apiFetch(`/api/reports/months?client=${encodeURIComponent(clientId)}`, options);
}

export function listReports(clientId: string | null, options: ApiOptions = {}): Promise<ReportSummary[]> {
  const query = clientId ? `?client=${encodeURIComponent(clientId)}` : "";
  return apiFetch(`/api/reports${query}`, options);
}

export function getReport(id: string, options: ApiOptions = {}): Promise<Report> {
  return apiFetch(`/api/reports/${encodeURIComponent(id)}`, options);
}

export function generateReport(request: ReportGenerateRequest, signal?: AbortSignal): Promise<Report> {
  return apiFetch("/api/reports/generate", {
    method: "POST",
    body: JSON.stringify(request),
    timeoutMs: REPORT_TIMEOUT_MS,
    signal,
    silent: true, // the dialog shows the error inline with a retry
  });
}

export function updateReport(id: string, update: ReportUpdate): Promise<Report> {
  return apiFetch(`/api/reports/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(update),
  });
}

export function deleteReport(id: string): Promise<void> {
  return apiFetch(`/api/reports/${encodeURIComponent(id)}`, { method: "DELETE" });
}

function filenameFrom(disposition: string | null, fallback: string): string {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] ?? fallback;
}

/** Fetch the server-rendered PDF and hand it to the browser as a download. */
export async function downloadReportPdf(id: string, fallbackName: string): Promise<void> {
  await serverWarmup.ready();
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/reports/${encodeURIComponent(id)}/pdf`, {
      signal: AbortSignal.timeout(30_000),
    });
  } catch (error) {
    const apiError = toApiError(error);
    toast.error("Couldn't download the PDF", { description: apiError.message });
    throw apiError;
  }
  if (!response.ok) {
    const apiError = new ApiError(await readErrorMessage(response), response.status);
    toast.error("Couldn't download the PDF", { description: apiError.message });
    throw apiError;
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameFrom(response.headers.get("Content-Disposition"), fallbackName);
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/* ---- Usage & cost / Settings ---- */

export function getUsageSummary(days: UsageDays, options: ApiOptions = {}): Promise<UsageSummary> {
  return apiFetch(`/api/usage/summary?days=${days}`, options);
}

export function getRecentUsage(limit = 50, options: ApiOptions = {}): Promise<UsageCall[]> {
  return apiFetch(`/api/usage/recent?limit=${limit}`, options);
}

export function getAppSettings(options: ApiOptions = {}): Promise<AppSettings> {
  return apiFetch("/api/settings", options);
}
