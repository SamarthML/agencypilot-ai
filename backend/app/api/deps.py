"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import LlmProvider, get_settings
from app.services.llm import PROVIDER_IDS


def get_llm_provider(
    x_llm_provider: Annotated[str | None, Header(alias="X-LLM-Provider")] = None,
) -> LlmProvider:
    """The provider chosen in the UI's model switcher, or DEFAULT_PROVIDER when absent."""
    if x_llm_provider is None or not x_llm_provider.strip():
        return get_settings().default_provider
    value = x_llm_provider.strip().lower()
    for provider in PROVIDER_IDS:
        if provider == value:
            return provider
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown LLM provider '{x_llm_provider}'. Use one of: {', '.join(PROVIDER_IDS)}.",
    )


LlmProviderDep = Annotated[LlmProvider, Depends(get_llm_provider)]
