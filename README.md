# AgencyPilot AI

> An AI workspace for digital agencies: client insights, SEO audits, a RAG copilot over client documents, and automated monthly reports, with per-call LLM cost tracking.

🚧 **Work in progress.** See [PLAN.md](PLAN.md) for the build roadmap.

## Micro apps

- **Client Insights Dashboard**: upload a CSV to get KPIs, charts, and an AI summary grounded in computed numbers
- **SEO Audit**: enter a URL to get 10 rule-based checks, a score, and AI fix suggestions
- **Client Copilot**: chat with uploaded PDFs, with streamed answers and page citations
- **Report Generator**: an editable monthly client report with PDF export
- **Model switcher + Usage**: Groq / OpenAI / Claude, with tokens, latency, and cost for every call

## Stack

Next.js · TypeScript · Tailwind · shadcn/ui · Recharts · FastAPI · Pydantic v2 · SQLAlchemy · PostgreSQL + pgvector · sentence-transformers / fastembed (ONNX) · Docker · GitHub Actions

## Quick start

Full stack in Docker (put a `GROQ_API_KEY` in `backend/.env` first):

```bash
docker compose up --build   # http://localhost:3000 · API docs at http://localhost:8000/docs
```

For local development (DB in Docker, backend and frontend native), see
[CLAUDE.md](CLAUDE.md#run-commands-windows-powershell). To deploy for free (Neon + Render + Vercel),
see [DEPLOY.md](DEPLOY.md).

## Architecture

_Coming in Phase 6._

## Screenshots

_Coming in Phase 6._
