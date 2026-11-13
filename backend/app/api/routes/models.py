from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.models import ModelsResponse, ProviderInfo
from app.services.llm import PROVIDER_IDS, PROVIDER_LABELS, available_providers

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=ModelsResponse)
def list_models() -> ModelsResponse:
    """Providers and their configured model; `available` is true when an API key is set."""
    settings = get_settings()
    availability = available_providers(settings)
    return ModelsResponse(
        default_provider=settings.default_provider,
        providers=[
            ProviderInfo(
                id=provider,
                label=PROVIDER_LABELS[provider],
                model=settings.model_for(provider),
                available=availability[provider],
                is_default=provider == settings.default_provider,
            )
            for provider in PROVIDER_IDS
        ],
    )
