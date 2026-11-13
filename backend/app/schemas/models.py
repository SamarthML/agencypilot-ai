from pydantic import BaseModel

from app.core.config import LlmProvider


class ProviderInfo(BaseModel):
    id: LlmProvider
    label: str
    model: str
    available: bool
    is_default: bool


class ModelsResponse(BaseModel):
    default_provider: LlmProvider
    providers: list[ProviderInfo]
