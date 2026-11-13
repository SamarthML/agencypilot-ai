"""Application settings loaded from backend/.env via pydantic-settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

LlmProvider = Literal["groq", "openai", "claude"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AgencyPilot AI"
    version: str = "0.1.0"

    database_url: str = "postgresql+psycopg://agencypilot:agencypilot@localhost:5432/agencypilot"

    groq_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    default_provider: LlmProvider = "groq"
    groq_model: str = "llama-3.3-70b-versatile"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-haiku-5-5"

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    hf_home: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("groq_api_key", "openai_api_key", "anthropic_api_key", mode="before")
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
