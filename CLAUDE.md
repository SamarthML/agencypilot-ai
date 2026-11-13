# CLAUDE.md — AgencyPilot AI

Guidance for Claude Code (and humans) working in this repo. Read this before writing code.

## Project goal

AgencyPilot AI is an AI workspace for digital agencies. It is a portfolio project for an
AI/ML Engineer role, so it must show **production-minded, full-stack AI engineering**:
clean typed code, real LLM integration, RAG, and cost/latency awareness. It is not a toy demo.

Four micro apps + two platform features:

| # | Micro app | What it does |
|---|-----------|--------------|
| 1 | **Client Insights Dashboard** | CSV upload → Pandas KPIs + Recharts charts → LLM summary written **only from computed numbers** (the raw CSV never goes to the LLM) |
| 2 | **SEO Audit** | URL → httpx + BeautifulSoup scrape → 10 rule-based checks + 0–100 score → LLM fix suggestions for failed checks |
| 3 | **Client Copilot** | RAG over uploaded PDFs (pgvector + bge-small) → streaming chat with page-level citations |
| 4 | **Report Generator** | Monthly client report built from dashboard data → editable in the browser → PDF export |
| — | **Model switcher** | Groq (default), OpenAI, Claude — selectable per request from the UI |
| — | **Usage page** | Every LLM call: provider, model, feature, tokens in/out, latency, estimated cost |

## Stack

**Frontend** (`frontend/`): Next.js (App Router) · TypeScript (strict) · Tailwind CSS · shadcn/ui ·
Recharts · Framer Motion · lucide-react

**Backend** (`backend/`): Python 3.12 · FastAPI · Pydantic v2 (+ pydantic-settings) · SQLAlchemy 2.x ·
Alembic · PostgreSQL 16 + pgvector · Pandas · httpx · BeautifulSoup4 · sentence-transformers
(`BAAI/bge-small-en-v1.5`, 384-dim) · pypdf · pytest

**LLM providers**: Groq (default), OpenAI, Anthropic Claude. All behind one service layer.

**Infra**: Docker Compose (Postgres + pgvector) · GitHub Actions CI

## Folder structure

```
AgencyPilot/
├── CLAUDE.md
├── PLAN.md
├── README.md
├── docker-compose.yml          # postgres (pgvector/pgvector:pg16)
├── .github/workflows/ci.yml
├── backend/
│   ├── .env.example            # every backend env var, no real values (copy to .env)
│   ├── requirements.txt        # major versions pinned
│   ├── pyproject.toml          # ruff + pytest config
│   ├── alembic.ini
│   ├── alembic/                # migrations: 0001 pgvector + llm_usage, 0002 insights, 0003 seo_audits,
│   │                           #   0004 copilot (documents, chunks + HNSW, copilot_feedback)
│   ├── scripts/                # generate_demo_data.py (marketing_demo.csv),
│   │                           #   generate_sample_brief.py (bloom_bakery_brief.pdf)
│   ├── sample_data/            # demo CSV (auto-loaded on first Insights request) and Bloom Bakery
│   │                           #   brief PDF (ingested at startup if that client has no documents)
│   ├── app/
│   │   ├── main.py             # FastAPI app factory, CORS, router registration
│   │   ├── core/
│   │   │   ├── config.py       # pydantic-settings Settings, reads .env
│   │   │   └── db.py           # engine, SessionLocal, get_db dependency
│   │   ├── models/             # SQLAlchemy ORM models (one file per table group)
│   │   ├── schemas/            # Pydantic request/response models (one file per feature)
│   │   ├── api/routes/         # thin routers; /health at root, features under /api/<feature>
│   │   └── services/
│   │       ├── llm.py          # THE ONLY place that calls an LLM provider
│   │       ├── llm_meta.py     # LLMResult -> LlmCallMeta; cache-hit logging helper
│   │       ├── cache.py        # shared in-process TtlCache for LLM results
│   │       ├── pricing.py      # per-model token prices for cost estimation
│   │       ├── analytics.py    # pure Pandas: CSV validation, KPIs, breakdowns, signals
│   │       ├── insights.py     # insights datasets: Postgres storage + dashboard assembly
│   │       ├── insights_ai.py  # grounded AI summary (TTL-cached) + Q&A prompts
│   │       ├── seo_audit.py    # SEO orchestration: fetch → checks → score → AI (cached) → save
│   │       ├── seo/            # fetcher.py (SSRF guard), checks.py (10 checks), scoring.py
│   │       ├── rag.py          # extract (pypdf) → token-aware chunking → BGE embeddings → pgvector
│   │       │                   #   retrieval + similarity threshold
│   │       ├── copilot.py      # ingest background task, SSE chat (rewrite → retrieve → guardrail →
│   │       │                   #   stream), citation parsing, feedback, demo seed + startup warm-up
│   │       └── reports.py      # report assembly + PDF rendering
│   └── tests/                  # pytest; mirrors app/ layout; fixtures in tests/fixtures/,
│                               #   fake LLM provider in tests/fakes.py
└── frontend/
    ├── .env.local.example      # NEXT_PUBLIC_API_URL (copy to .env.local)
    ├── package.json
    ├── app/                    # App Router; (app)/ route group holds the sidebar+topbar shell
    ├── components/
    │   ├── ui/                 # shadcn/ui (radix-nova); only card.tsx is restyled (rounded-2xl)
    │   ├── sidebar.tsx, topbar.tsx, page-header.tsx, empty-state.tsx, kpi-card.tsx, motion.tsx,
    │   │   llm-meta.tsx        # provider/model/tokens/latency/cost line under AI output
    │   ├── copy-button.tsx     # shared copy-to-clipboard icon button
    │   └── <feature>/          # feature components (home/, insights/, seo/, copilot/); container queries
    │                           #   (@container / @xl:) where a card's width, not the viewport, matters
    ├── lib/
    │   ├── api.ts              # typed fetch client: X-LLM-Provider header, ApiError, toasts
    │   ├── types.ts            # TS types mirroring backend Pydantic schemas
    │   ├── nav.ts              # single nav config (sidebar, titles, empty states)
    │   ├── seo.ts, channels.ts, format.ts   # feature helpers: score bands/error copy, chart colours, formatters
    │   ├── sse.ts              # pure Server-Sent Events parser for the Copilot chat stream
    │   ├── citations.ts        # [file p.N] / 【file p.N】 markers -> numbered chips (mirrors backend)
    │   ├── providers.ts        # LLM provider display metadata
    │   └── model-context.tsx, client-context.tsx   # persisted UI state
    └── hooks/
        ├── use-local-storage.ts     # useSyncExternalStore-backed, hydration-safe
        ├── use-api.ts               # abortable data fetching; loading derived, no setState in effects
        ├── use-copilot-documents.ts # document list that polls while any doc is processing
        └── use-copilot-chat.ts      # per-client chat threads, SSE streaming, stop/retry
```

## Coding rules

### General
- **Typed code everywhere.** Python: full type hints on every function signature, no bare `dict`/`Any`
  where a model fits. TypeScript: `strict: true`, no `any`.
- **Small functions.** One job per function; aim for < 30 lines. Pull out a helper instead of nesting.
- **Thin routes, fat services.** Routers validate, call one service, and return a schema. Business logic
  lives in `services/` so it can be unit-tested without HTTP.
- Prefer clear names over comments; comment the *why*, not the *what*.
- No dead code, no commented-out blocks, no `print()` (use `logging`).

### API contracts
- **Every request and response body is a Pydantic v2 model** in `backend/app/schemas/`. Routes declare
  `response_model=`. Never return raw dicts or ORM objects.
- Mirror each response schema as a TS type in `frontend/lib/types.ts`. Keep the names identical.
- Errors: raise `HTTPException` with a clear `detail`; validation is Pydantic's job.

### LLM calls (non-negotiable)
- **All LLM calls go through `backend/app/services/llm.py`.** No other module imports `openai`,
  `anthropic`, `groq`, or calls a provider URL. Features call e.g. `llm.complete(...)` / `llm.stream(...)`
  with a `provider`, `model`, `feature` tag, and messages.
- **Every LLM call is logged to the `llm_usage` table**: id, timestamp, feature, provider, model,
  input_tokens, output_tokens, latency_ms, cost_usd, success/error. This includes streaming calls
  (log on stream completion) and failed calls.
- Cost is computed from `services/pricing.py` (a per-model price table), not hardcoded at call sites.
- Default provider is **Groq**; the provider/model can be overridden per request.
- **Ground the LLM in data we computed.** Insights summaries get KPI numbers, not the raw CSV. SEO
  suggestions get the failed check results. Copilot answers only from retrieved chunks and must cite pages.
- Keep prompts as module-level constants or small builder functions, not inline f-strings scattered in routes.

### Secrets & config
- **Secrets only come from `backend/.env`**, loaded via `app/core/config.py` (pydantic-settings).
- **Never hardcode API keys**, DB passwords, or tokens. Not in code, tests, fixtures, or docs.
- `.env` is gitignored. `backend/.env.example` lists every variable with an empty or dummy value and
  must be updated whenever a new setting is added.
- Frontend only sees `NEXT_PUBLIC_API_URL` (`frontend/.env.local`). Provider keys never reach the browser.
- The frontend sends the selected provider as the `X-LLM-Provider` header; the backend validates it.

### Database
- Schema changes go through **Alembic migrations**, never `create_all()` in app code.
- pgvector: `CREATE EXTENSION IF NOT EXISTS vector` in the first migration; embeddings are `Vector(384)`.

### Testing
- Every service gets pytest unit tests. LLM calls are **mocked** in tests (patch `llm.py`); tests must
  never hit a real provider or need a real API key.
- SEO checks are tested against saved HTML fixtures, not live sites.
- Run `pytest` and `ruff` (backend) and `npm run lint` + `npm run build` (frontend) before calling a task done.

### Frontend
- **Next.js 16 + React 19.** APIs differ from older versions: check `frontend/node_modules/next/dist/docs/`
  before using an unfamiliar Next API (see `frontend/AGENTS.md`).
- Design: zinc neutrals; the brand gradient (`bg-brand-gradient` / `text-brand-gradient`) is used
  sparingly (logo, active nav bar, hero accent, primary CTA). Cards are `rounded-2xl` with a subtle
  border and `shadow-card`. Check 375 / 768 / 1440 px before calling UI work done.
- Persisted UI state goes through `useLocalStorage` (no `setState` in effects, no hydration mismatch).
- Server Components by default; add `"use client"` only where state/effects/streaming are needed.
- All backend calls go through `lib/api.ts`.
- UI built from shadcn/ui primitives; icons from lucide-react; motion is subtle (Framer Motion for
  page/card transitions only).

## Run commands (Windows PowerShell)

Prerequisites: Python 3.12, Node.js 20+ LTS, Docker Desktop, Git.

> **Windows Smart App Control is ON on the dev machine.** It blocks the `.exe` launchers that pip
> creates in `.venv\Scripts\` (pip.exe, pytest.exe, uvicorn.exe, ...). Always invoke tools as
> `.\.venv\Scripts\python.exe -m <tool>`. It also blocks SQLAlchemy 2.1's Cython modules, which is
> why `sqlalchemy` is pinned `<2.1` (2.0 falls back to pure Python). Files written with PowerShell 5.1
> `Set-Content -Encoding utf8` get a BOM, which breaks `alembic.ini`/`.env`; write them without a BOM.

```powershell
# 1. Database (Postgres 16 + pgvector), from repo root
docker compose up -d --wait

# 2. Backend (terminal 1)
cd backend
python -m venv .venv                                   # one-time
# CPU-only torch first (no CUDA; <2.15 because Smart App Control blocks 2.15's DLLs)
.\.venv\Scripts\python.exe -m pip install "torch>=2.4,<2.15" --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env                            # one-time, then fill in keys + HF_HOME
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs   Health: http://localhost:8000/health

# 3. Frontend (terminal 2)
cd frontend
Copy-Item .env.local.example .env.local                # one-time
npm install
npm run dev
# App: http://localhost:3000
```

### Tests & checks

```powershell
# Backend (from backend/)
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m alembic check            # models match migrations

# Frontend (from frontend/)
npm run lint
npx tsc --noEmit
npm run build
```

### Useful

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
docker compose down                                    # stop DB (keeps data)
docker compose down -v                                 # stop DB and wipe data
```

## Environment variables

`backend/.env` (see `backend/.env.example`):

```
DATABASE_URL=postgresql+psycopg://agencypilot:agencypilot@localhost:5432/agencypilot
GROQ_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEFAULT_PROVIDER=groq
GROQ_MODEL=openai/gpt-oss-120b
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-haiku-5-5
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
COPILOT_MAX_UPLOAD_MB=10
COPILOT_TOP_K=5
COPILOT_MIN_SIMILARITY=0.5                             # below this: "not found", no LLM call
COPILOT_WARMUP=true                                    # load model + seed brief at startup
CORS_ORIGINS=http://localhost:3000
HF_HOME=C:/Users/<you>/.cache/agencypilot-hf          # model cache outside the repo/OneDrive
```

`frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Working agreement for Claude Code
- Follow `PLAN.md` phase by phase; tick checklist items as they land.
- Don't add dependencies outside the stack above without saying why.
- Keep commits small and scoped to one checklist item where practical.
