"""Client Copilot request/response bodies and the payloads of its SSE chat events."""

import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import LlmProvider
from app.schemas.common import ClientId

DocumentStatus = Literal["processing", "ready", "failed"]
Rating = Literal["up", "down"]


class CopilotDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client: str
    filename: str
    pages: int
    status: DocumentStatus
    error: str | None
    chunk_count: int = 0
    created_at: datetime


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    client: ClientId
    # ~1000 chars keeps "query prefix + question" well inside the embedder's 512-token window.
    question: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)


class Citation(BaseModel):
    filename: str
    page: int
    snippet: str
    similarity: float


# --- SSE event payloads (event name in the comment) -----------------------------------------


class TokenEvent(BaseModel):
    """`token`: a piece of answer text, in order."""

    text: str


class CitationsEvent(BaseModel):
    """`citations`: the sources the answer actually cited, in order of first mention."""

    citations: list[Citation]


class DoneEvent(BaseModel):
    """`done`: totals for the whole request (follow-up rewrite + answer)."""

    message_id: uuid.UUID
    provider: LlmProvider
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    # False when the similarity guardrail answered "not found" without calling the LLM.
    grounded: bool
    # The standalone query used for retrieval when the question was a follow-up.
    rewritten_query: str | None


class ErrorEvent(BaseModel):
    """`error`: the request failed; no `done` event follows."""

    detail: str


# --- Feedback ---------------------------------------------------------------------------------


class FeedbackRequest(BaseModel):
    client: ClientId | None = None
    message_id: uuid.UUID | None = None
    question: str | None = Field(default=None, min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=20000)
    rating: Rating
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def needs_message_or_question(self) -> Self:
        if self.message_id is None and self.question is None:
            raise ValueError("Provide message_id or question.")
        return self


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
