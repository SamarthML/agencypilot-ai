"""Settings: DEMO_MODE overrides and the per-provider allow list."""

from collections.abc import Iterator

import pytest
from fastapi import HTTPException

from app.api.deps import get_llm_provider
from app.core.config import DEMO_RATE_LIMIT_PER_MINUTE, Settings, get_settings
from app.services.llm import available_providers


def test_demo_mode_forces_the_hosted_demo_profile() -> None:
    settings = Settings(
        demo_mode=True,
        default_provider="openai",
        seed_demo_data=False,
        trust_proxy=False,
        rate_limit_enabled=False,
        rate_limit_per_minute=50,
        openai_api_key="sk-test",
    )

    assert settings.default_provider == "groq"
    assert settings.seed_demo_data is True
    assert settings.trust_proxy is True
    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_per_minute == DEMO_RATE_LIMIT_PER_MINUTE
    assert available_providers(settings) == {"groq": True, "openai": False, "claude": False}


def test_demo_mode_keeps_an_even_stricter_limit() -> None:
    assert Settings(demo_mode=True, rate_limit_per_minute=3).rate_limit_per_minute == 3


def test_without_demo_mode_settings_are_untouched() -> None:
    settings = Settings(default_provider="claude", rate_limit_per_minute=50)

    assert settings.default_provider == "claude"
    assert settings.rate_limit_per_minute == 50
    assert settings.trust_proxy is False
    assert all(settings.provider_allowed(p) for p in ("groq", "openai", "claude"))


@pytest.fixture
def demo_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("DEMO_MODE")
    get_settings.cache_clear()


@pytest.mark.usefixtures("demo_mode")
def test_demo_mode_rejects_other_providers() -> None:
    assert get_llm_provider(None) == "groq"
    assert get_llm_provider("groq") == "groq"
    with pytest.raises(HTTPException) as exc_info:
        get_llm_provider("claude")

    assert exc_info.value.status_code == 400
    assert "Groq only" in str(exc_info.value.detail)


def test_empty_embedding_threads_means_all_cores() -> None:
    assert Settings(embedding_threads="").embedding_threads is None
    assert Settings(embedding_threads="2").embedding_threads == 2
