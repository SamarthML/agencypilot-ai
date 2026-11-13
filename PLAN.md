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
- [ ] `services/pricing.py` with per-model input/output prices for the default models
- [ ] `services/llm.py`: provider abstraction (Groq, OpenAI, Anthropic), `complete()` and `stream()`,
      usage logging (tokens, latency, cost, success/error, cached) to `llm_usage`
- [ ] Backend reads `X-LLM-Provider` (validated) with fallback to `DEFAULT_PROVIDER`
- [ ] `GET /models` lists available providers/models (only those with a key configured)
- [ ] Tests for `pricing.py` and `llm.py` (providers mocked)
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

- [ ] Sample CSV(s) in `backend/tests/fixtures/` and a "load sample data" button
- [ ] Schemas: `DatasetUploadResponse`, `KpiSet`, `TimeSeriesPoint`, `ChannelBreakdown`, `InsightSummary`
- [ ] `POST /insights/upload`: validate columns/types, store dataset (table or JSON), return id
- [ ] `services/insights.py`: Pandas KPIs (sessions, conversions, CVR, spend, CPA, ROAS, MoM deltas, top channels)
- [ ] Clear errors for missing columns / bad dates / empty files
- [ ] `GET /insights/{id}/kpis` and `/timeseries`
- [ ] `POST /insights/{id}/summary`: LLM gets **only the computed KPI JSON**; prompt forbids inventing numbers
- [ ] Frontend: drag-and-drop upload, KPI cards with delta badges, Recharts line + bar + pie
- [ ] Summary panel with provider/model/cost shown under it
- [ ] Tests: KPI math on fixtures, column validation, summary prompt contains no raw rows

**Done when:** uploading the sample CSV renders a full dashboard and a summary whose numbers match the KPI cards.

---

## Phase 3 — SEO Audit

Goal: enter a URL, get a scored audit with rule results and AI fix suggestions.

- [ ] `services/seo/scraper.py`: httpx fetch (timeout, size limit, user-agent, redirects), BeautifulSoup parse
- [ ] URL validation + SSRF guard (block private/loopback IPs)
- [ ] `services/seo/checks.py`: 10 pure-function checks, each returning `CheckResult(id, passed, severity, detail)`:
  - [ ] title present & 30–60 chars
  - [ ] meta description present & 70–160 chars
  - [ ] exactly one H1
  - [ ] heading hierarchy (no skipped levels)
  - [ ] images have alt text
  - [ ] canonical link present
  - [ ] viewport meta (mobile-friendly)
  - [ ] HTTPS
  - [ ] Open Graph tags
  - [ ] content length / word count threshold
- [ ] `services/seo/scoring.py`: severity-weighted 0–100 score
- [ ] `POST /seo/audit` → `SeoAuditResponse`; audits persisted for history
- [ ] `POST /seo/audit/{id}/suggestions`: LLM gets failed checks + relevant page snippets only
- [ ] Frontend: URL form, score gauge, pass/fail checklist, suggestions accordion, recent audits list
- [ ] Tests: every check against saved HTML fixtures (pass + fail cases), scoring, SSRF guard

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
