/** Types mirroring backend Pydantic schemas (backend/app/schemas). Keep names identical. */

export type LlmProvider = "groq" | "openai" | "claude";

export interface HealthResponse {
  status: "ok" | "degraded";
  db: "ok" | "down";
  version: string;
}

/** Frontend-only demo data until clients are stored in the backend. */
export interface DemoClient {
  id: string;
  name: string;
  industry: string;
  initials: string;
}
