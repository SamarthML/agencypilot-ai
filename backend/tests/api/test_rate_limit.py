"""Per-client LLM rate limiting: the sliding window and the 429 contract."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api import rate_limit
from app.core.config import get_settings
from app.main import create_app
from app.schemas.common import LlmCallMeta
from app.schemas.insights import AskResponse
from app.services import insights_ai


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_limit_then_blocks_with_retry_after() -> None:
    clock = Clock()
    limiter = rate_limit.SlidingWindowLimiter(3, 60, clock)

    assert [limiter.hit("1.2.3.4") for _ in range(3)] == [None, None, None]
    clock.now += 10
    assert limiter.hit("1.2.3.4") == pytest.approx(50)  # oldest hit expires 60 s after it
    assert limiter.hit("5.6.7.8") is None  # other clients are unaffected


def test_window_slides() -> None:
    clock = Clock()
    limiter = rate_limit.SlidingWindowLimiter(2, 60, clock)
    limiter.hit("ip")
    clock.now += 30
    limiter.hit("ip")

    clock.now += 30  # the first hit is now exactly 60 s old and drops out
    assert limiter.hit("ip") is None
    assert limiter.hit("ip") == pytest.approx(30)


def test_blocked_hits_do_not_extend_the_window() -> None:
    clock = Clock()
    limiter = rate_limit.SlidingWindowLimiter(1, 60, clock)
    limiter.hit("ip")
    for _ in range(5):
        clock.now += 1
        assert limiter.hit("ip") is not None
    clock.now += 55
    assert limiter.hit("ip") is None


# --- HTTP contract ----------------------------------------------------------------------------


@pytest.fixture
def limited_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    rate_limit._limiter = None

    async def ask(*args: object) -> AskResponse:
        meta = LlmCallMeta(
            provider="groq", model="m", input_tokens=1, output_tokens=1, latency_ms=1,
            cost_usd=0.0, cached=False,
        )  # fmt: skip
        return AskResponse(question="q?", answer="a", meta=meta)

    monkeypatch.setattr(insights_ai, "ask", ask)
    yield TestClient(create_app())
    get_settings.cache_clear()
    rate_limit._limiter = None


def ask(client: TestClient) -> int:
    response = client.post("/api/insights/apex-fitness/ask", json={"question": "Why?", "days": 30})
    return response.status_code


def test_llm_endpoint_returns_429_with_clear_message(limited_client: TestClient) -> None:
    assert [ask(limited_client), ask(limited_client)] == [200, 200]

    blocked = limited_client.post(
        "/api/insights/apex-fitness/ask", json={"question": "Why?", "days": 30}
    )

    assert blocked.status_code == 429
    assert blocked.json()["detail"].startswith("Too many AI requests: the limit is 2 per minute.")
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60


def test_non_llm_endpoints_are_not_limited(limited_client: TestClient) -> None:
    statuses = {limited_client.get("/health").status_code for _ in range(5)}
    assert 429 not in statuses


def test_limit_can_be_disabled(limited_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    assert {ask(limited_client) for _ in range(5)} == {200}
