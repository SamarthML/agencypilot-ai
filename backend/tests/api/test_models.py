import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_llm_provider
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_models_lists_every_provider_with_availability(client: TestClient) -> None:
    response = client.get("/api/models")

    assert response.status_code == 200
    body = response.json()
    assert body["default_provider"] == "groq"
    by_id = {p["id"]: p for p in body["providers"]}
    assert set(by_id) == {"groq", "openai", "claude"}
    assert by_id["groq"]["available"] is True
    assert by_id["groq"]["is_default"] is True
    assert by_id["openai"]["available"] is False
    assert by_id["claude"]["model"] == "claude-haiku-5-5"


def test_models_never_exposes_keys(client: TestClient) -> None:
    assert "test-groq-key" not in client.get("/api/models").text


@pytest.mark.parametrize(
    ("header", "expected"),
    [(None, "groq"), ("", "groq"), ("openai", "openai"), (" Claude ", "claude")],
)
def test_provider_header_parsing(header: str | None, expected: str) -> None:
    assert get_llm_provider(header) == expected


def test_unknown_provider_header_is_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_llm_provider("gemini")

    assert exc_info.value.status_code == 400
    assert "gemini" in str(exc_info.value.detail)
