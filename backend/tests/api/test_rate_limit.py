"""Per-client LLM rate limiting: the sliding window and the 429 contract."""

from collections.abc import Iterator

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.api import rate_limit
from app.core.config import Settings, get_settings
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


# --- Client IP behind a proxy -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "hops", "expected"),
    [
        ("203.0.113.7", 1, "203.0.113.7"),
        ("6.6.6.6, 203.0.113.7", 1, "203.0.113.7"),  # left entry was sent by the client
        ("6.6.6.6, 203.0.113.7, 10.0.0.2", 2, "203.0.113.7"),
        ("203.0.113.7", 3, "203.0.113.7"),  # fewer entries than hops: left-most
        (" 203.0.113.7 , ,", 1, "203.0.113.7"),
        (" , ", 1, None),
    ],
)
def test_forwarded_client_takes_the_trusted_hop(header: str, hops: int, expected: str) -> None:
    assert rate_limit.forwarded_client(header, hops) == expected


def build_request(headers: dict[str, str], peer: str = "10.1.1.1") -> Request:
    raw = [(name.lower().encode(), value.encode()) for name, value in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (peer, 1234)})


def test_client_ip_ignores_forwarded_header_unless_proxy_is_trusted() -> None:
    request = build_request({"X-Forwarded-For": "6.6.6.6"})

    assert rate_limit.client_ip(request, Settings(trust_proxy=False)) == "10.1.1.1"
    assert rate_limit.client_ip(request, Settings(trust_proxy=True)) == "6.6.6.6"


def test_client_ip_falls_back_to_socket_without_header() -> None:
    request = build_request({})
    assert rate_limit.client_ip(request, Settings(trust_proxy=True)) == "10.1.1.1"


def ask_from(client: TestClient, forwarded_for: str) -> int:
    response = client.post(
        "/api/insights/apex-fitness/ask",
        json={"question": "Why?", "days": 30},
        headers={"X-Forwarded-For": forwarded_for},
    )
    return response.status_code


def test_spoofed_forwarded_for_cannot_dodge_the_limit(limited_client: TestClient) -> None:
    # TRUST_PROXY is off: a client rotating fake X-Forwarded-For values is still one socket IP.
    statuses = [ask_from(limited_client, f"198.51.100.{n}") for n in range(3)]
    assert statuses == [200, 200, 429]


def test_trusted_proxy_limits_each_forwarded_client(
    limited_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRUST_PROXY", "true")
    get_settings.cache_clear()

    assert [ask_from(limited_client, "198.51.100.1") for _ in range(3)] == [200, 200, 429]
    assert ask_from(limited_client, "198.51.100.2") == 200
    # A forged left-most entry doesn't help: the proxy-appended right-most entry is the key.
    assert ask_from(limited_client, "1.2.3.4, 198.51.100.1") == 429
