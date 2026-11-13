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

/** Frontend-only demo data until clients are stored in the backend. */
export interface DemoClient {
  id: string;
  name: string;
  industry: string;
  initials: string;
}
