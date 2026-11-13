"""Schema pieces shared by more than one feature."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.core.config import LlmProvider

ClientId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=50)]


class LlmCallMeta(BaseModel):
    """Provider, model, tokens, latency and cost of the LLM call behind a response."""

    provider: LlmProvider
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    cached: bool
