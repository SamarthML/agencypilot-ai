# PLAN.md — AgencyPilot AI build plan

Six phases. Each phase ends in a working, demoable state with passing tests and CI.
Tick items (`[x]`) as they land.

---

## Phase 1 — Foundation

Goal: both apps boot, talk to each other, talk to Postgres, and can make one logged LLM call.

- [x] `docker-compose.yml` with `pgvector/pgvector:pg16`, named volume, healthcheck
- [x] `backend/.env.example` + `frontend/.env.local.example` with every variable from CLAUDE.md
- [x] Backend skeleton: `app/main.py`, `core/config.py` (pydantic-settings), `core/db.py`
- [x] Empty feature routers mounted under `/api/{insights,seo,copilot,reports,usage}`
- [x] CORS configured from `CORS_ORIGINS` (allows `X-LLM-Provider`)
- [x] `GET /health` returns a schema (`status`, `db`, `version`) and checks the DB
- [x] Alembic initialised; first migration enables `vector` extension + creates `llm_usage` table
- [x] pytest + ruff setup; tests for `/health` and CORS
- [x] `services/pricing.py` with per-model input/output prices for the default models
- [x] `services/llm.py`: provider abstraction (Groq, OpenAI, Anthropic), `complete()` and `stream()`,
      usage logging (tokens, latency, cost, success/error, cached) to `llm_usage`
- [x] Backend reads `X-LLM-Provider` (validated) with fallback to `DEFAULT_PROVIDER`
- [x] `GET /api/models` lists providers/models with an `available` flag (true when a key is configured)
- [x] Tests for `pricing.py` and `llm.py` (providers mocked)
- [x] Frontend: Next.js App Router + TS strict + Tailwind + shadcn/ui init
- [x] Design system: zinc tokens, indigo→violet brand accent, Inter, dark default + light toggle
- [x] App shell: collapsible sidebar (Sheet drawer on mobile), top bar with client selector,
      model switcher, theme toggle and API status dot (polls `/health` every 30s)
- [x] Home page (hero, KPI cards, micro-app cards) + empty-state placeholder pages for every route
- [x] `lib/api.ts` typed client (sends `X-LLM-Provider`, toasts on failure) + `lib/types.ts`;
      model choice stored in React context + localStorage
- [ ] GitHub Actions CI: backend (ruff + pytest), frontend (lint + tsc + build)
- [ ] README: setup steps verified on a clean Windows checkout

**Done when:** `docker compose up`, backend, and frontend all run; `/health` is green in the UI; a test LLM call shows up in `llm_usage`.

---

## Phase 2 — Client Insights Dashboard

Goal: upload a marketing CSV, see KPIs + charts + a grounded AI summary.

- [x] Demo data: `scripts/generate_demo_data.py` → `sample_data/marketing_demo.csv` (3 clients × 6 channels
      × 180 days, seeded; Apex Fitness has a scripted Organic drop); small fixture in `tests/fixtures/`;
      auto-loaded on first use + "Reset all to sample data" button
- [x] Schemas: `DatasetUploadResponse`, `Kpi`, `TimeSeriesPoint`, `ChannelBreakdown`, `Signal`,
      `InsightsDashboard`, `InsightSummary`, `AskResponse`, `OverviewResponse`
- [x] `POST /api/insights/{client_id}/upload`: validate columns/types, store in `insight_datasets` +
      `insight_rows` (migration 0002), one active dataset per client
- [x] `services/analytics.py`: Pandas KPIs (sessions, conversions, CVR, revenue, spend, ROAS, CPA, AOV,
      period-over-period deltas, channel breakdown, notable-change signals)
- [x] Clear errors for missing columns / bad dates / bad numbers / empty files / oversize uploads (422/413)
- [x] `GET /api/insights/{client_id}/summary?days=7|30|90` (KPIs + timeseries + channels + signals) and
      `GET /api/insights/overview` (agency-wide KPIs for Home)
- [x] `POST /api/insights/{client_id}/ai-summary`: LLM gets **only the computed KPI JSON**; prompt forbids
      inventing numbers; TTL-cached per dataset/period/provider/model, cache hits logged at $0
- [x] `POST /api/insights/{client_id}/ask`: Q&A grounded in the same KPI JSON
- [x] Frontend: drag-and-drop upload dialog, KPI cards with delta badges, Recharts line + bar + donut,
      channel table, notable changes, period tabs; Home KPIs use real data
- [x] Summary panel with provider/model/tokens/latency/cost (and "Cached") shown under it
- [x] Tests: KPI math on fixtures, column validation, summary prompt contains no raw rows, cache, routes,
      DB round trip (skipped without Postgres)

**Done when:** uploading the sample CSV renders a full dashboard and a summary whose numbers match the KPI cards.

---

## Phase 3 — SEO Audit

Goal: enter a URL, get a scored audit with rule results and AI fix suggestions.

- [x] `services/seo/fetcher.py`: httpx fetch (10 s, 2 MB, browser UA, ≤5 redirects followed manually),
      load time / final URL / status / size recorded; BeautifulSoup (stdlib html.parser) parse
- [x] URL validation + SSRF guard: http/https on default ports only, every resolved IP must be public
      (private, loopback, link-local, reserved, CGNAT, multicast, IPv4-mapped blocked), re-checked on
      every redirect, connection pinned to the validated IP (Host header + TLS SNI) against DNS rebinding
- [x] `services/seo/checks.py`: 10 pure-function checks, each returning
      `SeoCheck(id, name, status: pass|warn|fail, value, recommendation, weight)`:
  - [x] title present & 30–60 chars
  - [x] meta description present & 70–160 chars
  - [x] exactly one H1
  - [x] heading hierarchy (no skipped levels)
  - [x] images have alt text
  - [x] canonical link present
  - [x] viewport meta (mobile-friendly)
  - [x] HTTPS
  - [x] Open Graph tags
  - [x] content length / word count threshold
- [x] `services/seo/scoring.py`: weighted 0–100 score (pass 1, warn 0.5, fail 0), computed in code
- [x] `POST /api/seo/audit` → `SeoAuditResponse`; every audit saved to `seo_audits` (migration 0003);
      `GET /api/seo/history?client=` (last 10) and `GET /api/seo/audits/{id}`
- [x] AI report in the same call (`services/seo_audit.py`, feature `seo_audit`): LLM gets check results +
      title, meta description, H1 and first 1500 chars of visible text; Pydantic-validated JSON (5 fixes,
      rewritten title/meta, 8 keywords, 3 content ideas), one repair retry; audit still returns score +
      checks with `ai: null` if the LLM fails; cached 1 h per (normalised URL, provider), hits logged at $0
- [x] Friendly errors: invalid URL 422, blocked address 400, timeout 504, non-HTML 415, too large 422,
      bot-blocked (401/403/429) / unreachable 502
- [ ] Frontend: URL form, score gauge, pass/fail checklist, suggestions accordion, recent audits list
- [x] Tests: every check against saved HTML fixtures (pass + warn + fail cases), scoring, SSRF guard,
      redirects/limits via `httpx.MockTransport`, orchestration + cache, routes, DB round trip

**Done when:** auditing a real site gives a believable score and specific, actionable suggestions.

---

## Phase 4 — Client Copilot (RAG)

Goal: upload PDFs, ask questions, get streamed answers with page citations.

- [ ] Migrations: `documents` and `chunks` (text, page, doc_id, `embedding Vector(384)`) + HNSW/IVFFlat index
- [ ] `rag/pdf_loader.py`: pypdf text per page
- [ ] `rag/chunker.py`: token/char-window chunking with overlap, page number preserved
- [ ] `rag/embedder.py`: bge-small-en-v1.5 loaded once (singleton), batch encode, normalised vectors,
      query prefix for bge
- [ ] `POST /copilot/documents`: upload + ingest; `GET`/`DELETE` documents
- [ ] `rag/retriever.py`: cosine top-k via pgvector, optional doc filter, min-score cutoff
- [ ] `POST /copilot/chat` streaming (SSE): retrieve → prompt with numbered sources → stream via `llm.stream()`
- [ ] Answers cite `[doc, p. N]`; "I don't know from the documents" when retrieval is empty/weak
- [ ] Citations returned as structured data alongside the stream
- [ ] Frontend: document manager, chat UI with token streaming, clickable citation chips
- [ ] Tests: chunker boundaries + page tracking, retriever on seeded vectors, prompt includes sources, stream logs usage

**Done when:** asking a question about an uploaded PDF streams a correct answer with accurate page citations.

---

## Phase 5 — Report Generator + Usage/Cost

Goal: one-click monthly client report, and full visibility into LLM spend.

### Reports
- [ ] Schemas: `ReportSection`, `ReportDraft`, `ReportUpdate`
- [ ] `POST /reports/generate` from an insights dataset: KPI tables + LLM narrative sections
      (exec summary, wins, issues, next-month plan)
- [ ] Persist drafts; `GET` / `PUT /reports/{id}` for edits
- [ ] Frontend: section-by-section editor, regenerate a single section, charts embedded
- [ ] PDF export (backend-rendered, consistent layout) via `GET /reports/{id}/pdf`
- [ ] Tests: report assembly, update round-trip, PDF endpoint returns valid PDF bytes

### Usage & cost
- [ ] `GET /usage/summary` (totals, by provider, by feature, by day) and `GET /usage/calls` (paginated)
- [ ] Usage page: KPI cards (calls, tokens, $ spent, p50/p95 latency), cost-by-model chart, call log table
- [ ] Side-by-side provider comparison (same prompt → latency/cost/output across Groq/OpenAI/Claude)
- [ ] Cost optimisations documented and implemented where cheap: response caching for identical prompts,
      `max_tokens` caps per feature, smaller default models, embedding batching
- [ ] Tests: aggregation queries, cost calculation

**Done when:** a report can be generated, edited, and downloaded as PDF; the Usage page shows every call made during the demo.

---

## Phase 6 — Polish, tests, deploy

Goal: interview-ready.

- [ ] Loading, empty, and error states on every page; toasts for failures
- [ ] Dark mode, responsive layout, Framer Motion page transitions
- [ ] Rate limiting / request size limits on upload + LLM endpoints
- [ ] Structured logging with request ids
- [ ] Backend test coverage ≥ 80% on `services/`; coverage report in CI
- [ ] A few frontend component tests (optional) or Playwright smoke test
- [ ] Seed script for a full demo (sample CSV, sample PDF, a few audits)
- [ ] Deploy: frontend → Vercel; backend → Render/Railway (Dockerfile); DB → Neon/Supabase with pgvector
- [ ] README: architecture diagram, screenshots/GIF, design decisions, cost numbers, "what I'd do next"
- [ ] 3-minute demo script for the interview

**Done when:** a live URL works end-to-end and the README tells the story without me in the room.
