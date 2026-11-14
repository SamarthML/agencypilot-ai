"""Application settings loaded from backend/.env via pydantic-settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

LlmProvider = Literal["groq", "openai", "claude"]
EmbeddingBackend = Literal["sentence-transformers", "fastembed"]

# Hosted demo: one cheap provider, a stricter limit, and real client IPs from the proxy.
DEMO_RATE_LIMIT_PER_MINUTE = 10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AgencyPilot AI"
    version: str = "0.1.0"

    database_url: str = "postgresql+psycopg://agencypilot:agencypilot@localhost:5432/agencypilot"
    # Serverless Postgres (Neon) can take a few seconds to wake from autosuspend.
    db_connect_timeout: int = Field(default=10, ge=1)

    groq_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    default_provider: LlmProvider = "groq"
    groq_model: str = "openai/gpt-oss-120b"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-haiku-5-5"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    hf_home: str | None = None

    max_upload_mb: float = 5.0
    insights_cache_ttl_seconds: int = 600
    seo_cache_ttl_seconds: int = 3600

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    # fastembed runs the same model on ONNX Runtime without torch (fits a 512 MB host).
    embedding_backend: EmbeddingBackend = "sentence-transformers"
    # ONNX Runtime threads for fastembed (None = all cores). Small hosts get ~1 vCPU.
    embedding_threads: int | None = Field(default=None, ge=1)
    copilot_max_upload_mb: float = 10.0
    copilot_top_k: int = 5
    # Calibrated on bge-small: in-document questions scored >= 0.52, unrelated ones 0.36-0.50.
    copilot_min_similarity: float = 0.5
    copilot_warmup: bool = True

    # Per-client (IP) limit on endpoints that call an LLM; 429 beyond it.
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = Field(default=20, ge=1)
    # Behind a reverse proxy the socket IP is the proxy's: read X-Forwarded-For instead, taking
    # the entry appended by the Nth proxy from the right (entries left of it are client-forgeable).
    trust_proxy: bool = False
    trusted_proxy_count: int = Field(default=1, ge=1)

    # Seed one fixture-based SEO audit per demo client (only for clients with no audits).
    seed_demo_data: bool = True

    # Public hosted demo: Groq only, demo data seeded, stricter rate limit, proxy IPs trusted.
    demo_mode: bool = False

    def api_key_for(self, provider: LlmProvider) -> SecretStr | None:
        return {
            "groq": self.groq_api_key,
            "openai": self.openai_api_key,
            "claude": self.anthropic_api_key,
        }[provider]

    def model_for(self, provider: LlmProvider) -> str:
        return {
            "groq": self.groq_model,
            "openai": self.openai_model,
            "claude": self.anthropic_model,
        }[provider]

    @model_validator(mode="after")
    def apply_demo_mode(self) -> "Settings":
        if self.demo_mode:
            self.default_provider = "groq"
            self.seed_demo_data = True
            self.trust_proxy = True
            self.rate_limit_enabled = True
            self.rate_limit_per_minute = min(self.rate_limit_per_minute, DEMO_RATE_LIMIT_PER_MINUTE)
        return self

    def provider_allowed(self, provider: LlmProvider) -> bool:
        """The demo only spends Groq credits; every provider is allowed otherwise."""
        return not self.demo_mode or provider == "groq"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "groq_api_key", "openai_api_key", "anthropic_api_key", "embedding_threads", mode="before"
    )
    @classmethod
    def empty_key_is_none(cls, value: object) -> object:
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def apply_runtime_env(settings: Settings) -> None:
    """Export settings that third-party libraries read from os.environ."""
    if settings.hf_home:
        os.environ.setdefault("HF_HOME", settings.hf_home)
        # fastembed keeps its own cache (default: the OS temp dir); keep it next to HF's.
        os.environ.setdefault("FASTEMBED_CACHE_PATH", f"{settings.hf_home}/fastembed")
