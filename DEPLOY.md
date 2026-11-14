# Deploying AgencyPilot AI (free tier)

| Piece | Host | Free tier |
|-------|------|-----------|
| Postgres 16 + pgvector | **Neon** | 0.5 GB storage, autosuspends when idle |
| FastAPI backend (`backend/Dockerfile`) | **Render** web service | 512 MB RAM, sleeps after 15 min idle |
| Next.js frontend (`frontend/`) | **Vercel** | Hobby plan |

The deployed backend uses `EMBEDDING_BACKEND=fastembed`, which runs the same `BAAI/bge-small-en-v1.5`
model on ONNX Runtime without torch. The image has no torch / sentence-transformers
(`requirements-deploy.txt`) and the model is baked in at build time, so the container fits in 512 MB.
Measured locally under a 512 MB limit (`docker compose up --build`): ~320 MB idle after warm-up,
~400 MB peak while ingesting a 188-chunk document and running an Insights summary, an SEO audit
and a Copilot question.
`DEMO_MODE=true` sets the app up for a public demo:
- Groq only
- demo data seeded
- 10 AI requests per minute per visitor
- client IPs read from Render's proxy

Do the steps in order: **Neon → Render → Vercel → update CORS on Render.**

---

## 1. Neon: Postgres with pgvector

1. Go to <https://neon.tech> and sign up (GitHub login is fine).
2. **Create project**:
   - Name: `agencypilot`
   - Postgres version: **16** (or newer)
   - Region: the one closest to your Render region (e.g. *AWS US East (Ohio)* ↔ Render *Ohio*,
     *AWS Europe (Frankfurt)* ↔ Render *Frankfurt*). Same-region keeps query latency low.
3. Enable pgvector. In the project, open **SQL Editor**, select the `neondb` database and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   The first Alembic migration runs the same statement, so this step is just a quick check that the
   extension is available.
4. Copy the connection string:
   - Go to **Dashboard → Connect**.
   - Turn **Connection pooling OFF**: you want the *direct* host, without `-pooler` in it.
   - Copy the string. It looks like:
     ```
     postgresql://neondb_owner:AbC123xyz@ep-cool-name-a1b2c3d4.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
5. Rewrite it for SQLAlchemy + psycopg 3 by changing only the scheme to `postgresql+psycopg://`:
   ```
   postgresql+psycopg://neondb_owner:AbC123xyz@ep-cool-name-a1b2c3d4.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   - `sslmode=require` must stay (Neon only accepts TLS).
   - If Neon's string also has `&channel_binding=require`, you can keep it (psycopg 3 supports it).
   - If the password contains `@ : / ? #`, URL-encode those characters.

   This is your `DATABASE_URL`. Keep it secret.

> **Why not the pooled (`-pooler`) host?** Neon's pooler is PgBouncer in transaction mode, and
> psycopg 3 uses server-side prepared statements, which break across pooled transactions
> ("prepared statement does not exist"). A single small backend instance doesn't need a pooler.

You don't need to create any tables. The backend runs `alembic upgrade head` on every start.

---

## 2. Render: backend web service

1. Push this repo to GitHub (it already is if CI runs).
2. Go to <https://render.com> and sign up with GitHub.
3. **New → Web Service**. Connect your GitHub account if asked, then pick the `AgencyPilot` repo.
4. Fill in the form:

   | Field | Value |
   |-------|-------|
   | Name | `agencypilot-api` (becomes `https://agencypilot-api.onrender.com`) |
   | Language | **Docker** |
   | Branch | `main` |
   | Region | same as Neon |
   | Root Directory | `backend` |
   | Dockerfile Path | `./Dockerfile` (relative to the root directory) |
   | Docker build context | `.` (i.e. `backend/`) |
   | Instance Type | **Free** |

5. **Environment Variables**: click *Add Environment Variable* for each:

   | Key | Value | Notes |
   |-----|-------|-------|
   | `DATABASE_URL` | `postgresql+psycopg://…neon.tech/neondb?sslmode=require` | from step 1.5 |
   | `GROQ_API_KEY` | your key from <https://console.groq.com/keys> | the only provider the demo uses |
   | `DEMO_MODE` | `true` | Groq only, seeding on, 10/min limit, `TRUST_PROXY` on |
   | `EMBEDDING_BACKEND` | `fastembed` | already the image default; set it so it shows in the dashboard |
   | `TRUST_PROXY` | `true` | already forced by `DEMO_MODE`; set it explicitly anyway |
   | `TRUSTED_PROXY_COUNT` | `1` | Render's proxy appends one hop to `X-Forwarded-For` |
   | `FORWARDED_ALLOW_IPS` | `*` | lets uvicorn honour `X-Forwarded-Proto` from Render's proxy |
   | `CORS_ORIGINS` | `https://placeholder.vercel.app` | replaced with the real Vercel URL in step 4 |
   | `COPILOT_WARMUP` | `true` | loads the model and seeds the demo PDF at startup |
   | `SEED_DEMO_DATA` | `true` | demo SEO audits (forced by `DEMO_MODE` anyway) |
   | `GROQ_MODEL` | `openai/gpt-oss-120b` | optional; this is the default |
   | `DB_CONNECT_TIMEOUT` | `10` | optional; gives Neon time to wake from autosuspend |
   | `EMBEDDING_THREADS` | `2` | optional; already the image default (ONNX threads for a small CPU share) |
   | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | *(leave unset)* | `DEMO_MODE` rejects other providers anyway |

   Don't set `PORT`: Render injects it, and the container listens on `$PORT`.
   Don't set `HF_HOME`: the model is already in the image at `/opt/fastembed`.

6. **Advanced → Health Check Path**: `/health`.
7. Click **Deploy Web Service**. The first build takes ~5–8 min (pip install + model download).
   Watch the **Logs** tab. A healthy start looks like:
   ```
   INFO  [alembic.runtime.migration] Running upgrade  -> 0001_init ...
   INFO:     Uvicorn running on http://0.0.0.0:10000
   ... Loading embedding model BAAI/bge-small-en-v1.5 (fastembed)
   ... Seeding Copilot with bloom_bakery_brief.pdf for bloom-bakery
   ... Embedding model ready
   ```
8. Open `https://agencypilot-api.onrender.com/health`. You should see
   `{"status":"ok","db":"ok","version":"0.1.0"}`. `/docs` shows the API.

**Why `TRUST_PROXY` + `FORWARDED_ALLOW_IPS=*` is safe here.** On Render, every request reaches the
container through Render's proxy, which appends the real client IP to `X-Forwarded-For`. The rate
limiter takes the entry `TRUSTED_PROXY_COUNT` places from the right, which is the one Render wrote,
and ignores anything a client typed into the header (those values sit further left).

Optional spoof check: send 11 AI requests with a different fake header each time. The 11th should
still get HTTP 429:
```bash
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST \
    -H "Content-Type: application/json" -H "X-Forwarded-For: 10.0.0.$i" \
    -d '{"question":"Why?","days":30}' \
    https://agencypilot-api.onrender.com/api/insights/apex-fitness/ask
done
```
If every request succeeds, Render added more than one hop for your route. Raise
`TRUSTED_PROXY_COUNT` to `2` and repeat.

---

## 3. Vercel: frontend

1. Go to <https://vercel.com> and sign up with GitHub.
2. **Add New… → Project**, then **Import** the `AgencyPilot` repo.
3. Configure the project:

   | Field | Value |
   |-------|-------|
   | Framework Preset | **Next.js** (auto-detected) |
   | Root Directory | `frontend` (click *Edit* and select the folder) |
   | Build / Output / Install commands | leave the defaults |

4. **Environment Variables**:

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://agencypilot-api.onrender.com` (your Render URL, **no trailing slash**) |

   `NEXT_PUBLIC_*` values are compiled into the JavaScript bundle at build time. If you change it
   later, redeploy (**Deployments → ⋯ → Redeploy**).
5. Click **Deploy**. When it finishes, copy the production URL (e.g. `https://agencypilot.vercel.app`).

## 4. Allow the Vercel origin on Render (CORS)

1. In Render, open **agencypilot-api → Environment**.
2. Set `CORS_ORIGINS` to the exact Vercel URL: scheme included, **no trailing slash**:
   ```
   https://agencypilot.vercel.app
   ```
   If you also use a custom domain, list both, comma-separated:
   `https://agencypilot.vercel.app,https://demo.example.com`
3. **Save Changes**. Render redeploys automatically (~1 min, no rebuild).
4. Open the Vercel URL and check each feature:
   - **Insights**: *Generate summary*
   - **SEO Audit**: audit any public URL
   - **Copilot**: *Bloom Bakery* → "What is the Q3 catering goal?"

   Each AI call should then appear on the **Usage** page.

Vercel *preview* deployments get their own URLs, which aren't in `CORS_ORIGINS`, so they can't call
the API. Only the production URL is allowed.

---

## Cold starts (what visitors see)

- **Render free** stops the container after **15 minutes** without traffic. The next request starts
  it again, which takes **~30–60 s** (container boot, Alembic check, uvicorn start). The embedding
  model then warms up in the background.
- **Neon free** also suspends compute after ~5 minutes idle. Waking it takes under a second, and
  `DB_CONNECT_TIMEOUT=10` covers that.
- The frontend sends one `/health` request on first load and holds every other API call until the
  backend answers. If that takes longer than 1.5 s, a banner says **"Waking up the server (free
  hosting, ~30-60 s)…"**. If the backend hasn't answered after 2 minutes, the banner switches to an
  error with a **Retry** button.
- To avoid the wait right before a demo, open the `/health` URL a minute beforehand. Alternatively,
  have an external uptime pinger hit `/health` every 10 min. That keeps it awake, but uses your
  free instance hours.

## When something fails: where to look

| Symptom | Check |
|---------|-------|
| Render deploy fails | **Render → Logs** (build logs come first). `pip` errors mean a dependency issue. `alembic` errors usually mean a bad `DATABASE_URL`. |
| `could not translate host name` / `password authentication failed` | `DATABASE_URL`: scheme must be `postgresql+psycopg://`, host without `-pooler`, password URL-encoded |
| `SSL connection is required` / connection closed | missing `?sslmode=require` at the end of `DATABASE_URL` |
| `type "vector" does not exist` | run `CREATE EXTENSION IF NOT EXISTS vector;` in Neon's SQL Editor, then **Manual Deploy → Restart** |
| `/health` shows `"db":"down"` | Neon project suspended or deleted, or wrong credentials; check **Neon → Monitoring** |
| Browser console: *blocked by CORS policy* | `CORS_ORIGINS` on Render must equal the Vercel origin exactly (https, no trailing slash); save to redeploy |
| UI says "Can't reach the API" | `NEXT_PUBLIC_API_URL` on Vercel wrong or missing; fix it and **redeploy** (it's build-time) |
| AI calls return "Groq is not configured" | `GROQ_API_KEY` missing on Render |
| AI calls return "This live demo runs on Groq only" | expected with `DEMO_MODE=true` when another provider is selected |
| 429 "Too many AI requests" | the demo limit (10/min per visitor) is working |
| Instance restarts with *Out of memory* | **Render → Metrics → Memory**; confirm `EMBEDDING_BACKEND=fastembed` and that the logs say `(fastembed)`, not `(sentence-transformers)` |

Other places to look:
- **Render**: the **Logs** tab streams stdout live (searchable); **Events** lists deploys and restarts;
  **Metrics** shows memory and CPU.
- **Vercel**: **Deployments → (deployment) → Build Logs** for build failures; **Logs** for runtime
  requests.
- **Neon**: **Monitoring** shows connections and compute state.

## Running the production images locally

```powershell
docker compose up --build        # db + backend (fastembed) + frontend
# http://localhost:3000   (API: http://localhost:8000/docs)
docker stats agencypilot-backend # memory use; the free tier allows 512 MB
docker compose down              # stop (add -v to wipe the database)
```

The backend container reads provider keys from `backend/.env` if it exists. The compose file
overrides `DATABASE_URL`, `EMBEDDING_BACKEND` and `CORS_ORIGINS` for the container network.
