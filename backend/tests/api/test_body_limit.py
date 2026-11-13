"""Request-wide body cap (BodySizeLimitMiddleware) and the tightened CORS policy."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.body_limit import MB, BodySizeLimitMiddleware
from app.core.config import Settings
from app.main import create_app, max_request_bytes

LIMIT = 1000


def echo_app() -> FastAPI:
    app = FastAPI()

    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    app.add_middleware(BodySizeLimitMiddleware, max_bytes=LIMIT)
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(echo_app())


def chunks(total: int, size: int = 100) -> Iterator[bytes]:
    sent = 0
    while sent < total:
        yield b"x" * min(size, total - sent)
        sent += size


def test_body_at_the_limit_is_accepted(client: TestClient) -> None:
    response = client.post("/echo", content=b"x" * LIMIT)

    assert response.status_code == 200
    assert response.json() == {"size": LIMIT}


def test_oversized_content_length_is_refused_up_front(client: TestClient) -> None:
    response = client.post("/echo", content=b"x" * (LIMIT + 1))

    assert response.status_code == 413
    assert "larger than" in response.json()["detail"]


def test_streamed_body_without_length_is_cut_off_at_the_limit(client: TestClient) -> None:
    response = client.post("/echo", content=chunks(LIMIT * 3))

    assert response.status_code == 413


def test_streamed_body_under_the_limit_passes(client: TestClient) -> None:
    response = client.post("/echo", content=chunks(LIMIT - 1))

    assert response.json() == {"size": LIMIT - 1}


def test_cap_leaves_room_for_the_largest_upload() -> None:
    settings = Settings(max_upload_mb=5, copilot_max_upload_mb=10)

    assert max_request_bytes(settings) == 11 * MB


def test_real_app_rejects_oversized_upload_with_cors_headers() -> None:
    app_client = TestClient(create_app())
    too_big = max_request_bytes(Settings()) + 1

    response = app_client.post(
        "/api/copilot/upload",
        headers={"Origin": "http://localhost:3000", "Content-Length": str(too_big)},
        content=b"",
    )

    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_does_not_allow_credentials() -> None:
    response = TestClient(create_app()).options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-credentials" not in response.headers
