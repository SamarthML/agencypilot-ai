/** Types mirroring backend Pydantic schemas (backend/app/schemas). Keep names identical. */

export type LlmProvider = "groq" | "openai" | "claude";

export interface HealthResponse {
  status: "ok" | "degraded";
  db: "ok" | "down";
  version: string;
}

export interface ProviderInfo {
  id: LlmProvider;
  label: string;
  model: string;
  available: boolean;
  is_default: boolean;
}

export interface ModelsResponse {
  default_provider: LlmProvider;
  providers: ProviderInfo[];
}

/* ---- Insights (backend/app/schemas/insights.py) ---- */

export type Days = 7 | 30 | 90;
export type KpiUnit = "count" | "currency" | "percent" | "ratio";
export type GoodWhen = "up" | "down" | "neutral";

export interface DatasetInfo {
  id: string;
  client_id: string;
  client_name: string;
  filename: string;
  source: "sample" | "upload";
  row_count: number;
  channels: string[];
  start_date: string;
  end_date: string;
  created_at: string;
}

export interface DatasetUploadResponse {
  dataset: DatasetInfo;
  warnings: string[];
}

export interface SampleLoadResponse {
  datasets: DatasetInfo[];
}

export interface Period {
  days: number;
  start: string;
  end: string;
  previous_start: string;
  previous_end: string;
  has_previous: boolean;
}

export interface Kpi {
  key: string;
  label: string;
  value: number | null;
  previous: number | null;
  delta_pct: number | null;
  unit: KpiUnit;
  good_when: GoodWhen;
}

export interface TimeSeriesPoint {
  date: string;
  sessions: number;
  conversions: number;
  revenue: number;
  spend: number;
  by_channel: Record<string, number>;
}

export interface ChannelBreakdown {
  channel: string;
  sessions: number;
  previous_sessions: number;
  sessions_delta_pct: number | null;
  sessions_share_pct: number;
  conversions: number;
  revenue: number;
  revenue_delta_pct: number | null;
  spend: number;
  conversion_rate: number | null;
  roas: number | null;
}

export interface Signal {
  kind: "channel" | "kpi";
  metric: string;
  channel: string | null;
  delta_pct: number;
  current: number;
  previous: number;
  sentiment: "positive" | "negative" | "neutral";
  message: string;
}

export interface InsightsDashboard {
  dataset: DatasetInfo;
  period: Period;
  kpis: Kpi[];
  timeseries: TimeSeriesPoint[];
  channels: ChannelBreakdown[];
  signals: Signal[];
}

export interface LlmCallMeta {
  provider: LlmProvider;
  model: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  cost_usd: number;
  cached: boolean;
}

export interface AiSummaryContent {
  headline: string;
  highlights: string[];
  concerns: string[];
  recommendations: string[];
}

export interface InsightSummary {
  client_id: string;
  period: Period;
  summary: AiSummaryContent;
  meta: LlmCallMeta;
}

export interface AskResponse {
  question: string;
  answer: string;
  meta: LlmCallMeta;
}

export interface OverviewResponse {
  days: number;
  client_count: number;
  kpis: Kpi[];
}

/* ---- SEO Audit (backend/app/schemas/seo.py) ---- */

export type CheckStatus = "pass" | "warn" | "fail";
export type FixPriority = "High" | "Medium" | "Low";

export interface SeoCheck {
  id: string;
  name: string;
  status: CheckStatus;
  value: string;
  recommendation: string;
  weight: number;
}

export interface SeoPageSummary {
  title: string | null;
  meta_description: string | null;
  h1: string | null;
  word_count: number;
}

export interface SeoFix {
  title: string;
  detail: string;
  priority: FixPriority;
  impact: string;
}

export interface SeoAiReport {
  summary: string;
  top_fixes: SeoFix[];
  rewritten_title: string;
  rewritten_meta_description: string;
  suggested_keywords: string[];
  content_ideas: string[];
}

export interface SeoAuditRequest {
  url: string;
  client_id?: string | null;
}

export interface SeoAuditResponse {
  id: string;
  url: string;
  final_url: string;
  client_id: string | null;
  status_code: number;
  load_ms: number;
  html_bytes: number;
  score: number;
  checks: SeoCheck[];
  page: SeoPageSummary;
  ai: SeoAiReport | null;
  ai_error: string | null;
  meta: LlmCallMeta | null;
  cached: boolean;
  created_at: string;
}

export interface SeoAuditSummary {
  id: string;
  url: string;
  final_url: string;
  client_id: string | null;
  score: number;
  issue_count: number;
  created_at: string;
}

/** Frontend-only demo data until clients are stored in the backend. */
export interface DemoClient {
  id: string;
  name: string;
  industry: string;
  initials: string;
}

/* ---- Client Copilot ---- */

export type DocumentStatus = "processing" | "ready" | "failed";
export type Rating = "up" | "down";

export interface CopilotDocument {
  id: string;
  client: string;
  filename: string;
  pages: number;
  status: DocumentStatus;
  error: string | null;
  chunk_count: number;
  created_at: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  client: string;
  question: string;
  history: ChatTurn[];
}

export interface Citation {
  filename: string;
  page: number;
  snippet: string;
  similarity: number;
}

/** SSE `token`: a piece of answer text, in order. */
export interface TokenEvent {
  text: string;
}

/** SSE `citations`: the sources the answer actually cited, in order of first mention. */
export interface CitationsEvent {
  citations: Citation[];
}

/** SSE `done`: totals for the whole request (follow-up rewrite + answer). */
export interface DoneEvent {
  message_id: string;
  provider: LlmProvider;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  /** False when the similarity guardrail answered "not found" without calling the LLM. */
  grounded: boolean;
  rewritten_query: string | null;
}

/** SSE `error`: the request failed; no `done` event follows. */
export interface ErrorEvent {
  detail: string;
}

export type CopilotStreamEvent =
  | { event: "token"; data: TokenEvent }
  | { event: "citations"; data: CitationsEvent }
  | { event: "done"; data: DoneEvent }
  | { event: "error"; data: ErrorEvent };

export interface FeedbackRequest {
  client?: string | null;
  message_id?: string | null;
  question?: string | null;
  answer: string;
  rating: Rating;
  comment?: string | null;
}

export interface FeedbackResponse {
  id: string;
  created_at: string;
}
