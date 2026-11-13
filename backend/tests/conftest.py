"""Shared fixtures. Tests never read the developer's backend/.env API keys or hit a provider."""

import os

# Environment variables take precedence over backend/.env in pydantic-settings, so these make
# the test run deterministic: Groq "configured" with a dummy key, the others not configured.
os.environ.update(
    {
        "GROQ_API_KEY": "test-groq-key",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "DEFAULT_PROVIDER": "groq",
        "GROQ_MODEL": "openai/gpt-oss-120b",
        "COPILOT_WARMUP": "false",
        "SEED_DEMO_DATA": "false",
        # Existing API tests make many calls; test_rate_limit.py covers the limiter itself.
        "RATE_LIMIT_PER_MINUTE": "100000",
        "COPILOT_MIN_SIMILARITY": "0.5",
    }
)

import pytest  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services import llm  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
def usage_rows(monkeypatch: pytest.MonkeyPatch) -> list[llm.UsageRecord]:
    """Capture llm_usage writes in memory instead of hitting Postgres."""
    rows: list[llm.UsageRecord] = []
    monkeypatch.setattr(llm, "write_usage", rows.append)
    return rows


@pytest.fixture(autouse=True)
def no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr(llm, "_sleep", instant)
