# AgencyPilot API: FastAPI + fastembed (ONNX, no torch) so it fits a 512 MB free instance.
# EMBEDDING_THREADS=2: ONNX Runtime would otherwise start one thread per host core it can see,
# which on a shared cloud host is far more than the instance's small CPU share.
# Build context: backend/.  Run: docker build -t agencypilot-api backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    EMBEDDING_BACKEND=fastembed \
    EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
    FASTEMBED_CACHE_PATH=/opt/fastembed \
    HF_HUB_DISABLE_TELEMETRY=1 \
    PORT=8000

WORKDIR /app

COPY requirements-deploy.txt .
RUN python -m pip install -r requirements-deploy.txt

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin app

# Bake the ONNX model into the image so a cold start never waits on a Hugging Face download,
# then stay offline at runtime (no Hub round trip on startup). The app user owns the cache.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"     && chown -R app:app /opt/fastembed
ENV HF_HUB_OFFLINE=1

COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
COPY --chown=app:app sample_data ./sample_data

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=4)"

# Migrate, then serve. --proxy-headers makes uvicorn honour X-Forwarded-Proto/For, but only from
# peers in FORWARDED_ALLOW_IPS (default: loopback only). The rate limiter reads X-Forwarded-For
# itself (TRUST_PROXY / TRUSTED_PROXY_COUNT), so it never trusts a client-supplied left-most IP.
CMD ["sh", "-c", "python -m alembic upgrade head && exec python -m uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]
