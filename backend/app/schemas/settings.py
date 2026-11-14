"""Read-only app configuration for the Settings page (/api/settings). Never exposes keys."""

from pydantic import BaseModel, Field

from app.core.config import EmbeddingBackend, LlmProvider


class ProviderSettings(BaseModel):
    id: LlmProvider
    label: str
    configured: bool = Field(description="An API key is set. The key itself is never returned.")
    model: str
    is_default: bool


class AppSettings(BaseModel):
    providers: list[ProviderSettings]
    default_provider: LlmProvider
    embedding_model: str
    embedding_backend: EmbeddingBackend
    copilot_min_similarity: float
    copilot_top_k: int
    copilot_max_upload_mb: float
    insights_max_upload_mb: float
    insights_cache_ttl_seconds: int
    seo_cache_ttl_seconds: int
    llm_timeout_seconds: float
    llm_max_retries: int
    rate_limit_enabled: bool
    rate_limit_per_minute: int
    seed_demo_data: bool
    demo_mode: bool
