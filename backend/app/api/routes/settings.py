"""Read-only view of the backend configuration (from backend/.env). API keys are never returned."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.settings import AppSettings, ProviderSettings
from app.services.llm import PROVIDER_IDS, PROVIDER_LABELS, available_providers

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
def app_settings() -> AppSettings:
    settings = get_settings()
    configured = available_providers(settings)
    return AppSettings(
        providers=[
            ProviderSettings(
                id=provider,
                label=PROVIDER_LABELS[provider],
                configured=configured[provider],
                model=settings.model_for(provider),
                is_default=provider == settings.default_provider,
            )
            for provider in PROVIDER_IDS
        ],
        default_provider=settings.default_provider,
        embedding_model=settings.embedding_model,
        copilot_min_similarity=settings.copilot_min_similarity,
        copilot_top_k=settings.copilot_top_k,
        copilot_max_upload_mb=settings.copilot_max_upload_mb,
        insights_max_upload_mb=settings.max_upload_mb,
        insights_cache_ttl_seconds=settings.insights_cache_ttl_seconds,
        seo_cache_ttl_seconds=settings.seo_cache_ttl_seconds,
        llm_timeout_seconds=settings.llm_timeout_seconds,
        llm_max_retries=settings.llm_max_retries,
        rate_limit_enabled=settings.rate_limit_enabled,
        rate_limit_per_minute=settings.rate_limit_per_minute,
        seed_demo_data=settings.seed_demo_data,
    )
