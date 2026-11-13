"""Request/response models for the SEO Audit (/api/seo)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ClientId, LlmCallMeta

CheckStatus = Literal["pass", "warn", "fail"]
FixPriority = Literal["High", "Medium", "Low"]


class SeoCheck(BaseModel):
    """One rule-based check. `weight` is its share of the 0-100 score."""

    id: str
    name: str
    status: CheckStatus
    value: str
    recommendation: str
    weight: int


class SeoPageSummary(BaseModel):
    title: str | None
    meta_description: str | None
    h1: str | None
    word_count: int


class SeoFix(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1)
    priority: FixPriority
    impact: str = Field(min_length=1)


class SeoAiReport(BaseModel):
    """The structured output the LLM must return."""

    summary: str = Field(min_length=1)
    top_fixes: list[SeoFix] = Field(min_length=5, max_length=5)
    rewritten_title: str = Field(min_length=1, max_length=70)
    rewritten_meta_description: str = Field(min_length=1, max_length=180)
    suggested_keywords: list[str] = Field(min_length=8, max_length=8)
    content_ideas: list[str] = Field(min_length=3, max_length=3)


class SeoAuditRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    client_id: ClientId | None = None


class SeoAuditResponse(BaseModel):
    id: uuid.UUID
    url: str
    final_url: str
    client_id: str | None
    status_code: int
    load_ms: int
    html_bytes: int
    score: int = Field(ge=0, le=100)
    checks: list[SeoCheck]
    page: SeoPageSummary
    ai: SeoAiReport | None = Field(description="Null when the LLM call failed; see ai_error.")
    ai_error: str | None
    meta: LlmCallMeta | None
    cached: bool
    is_demo: bool = Field(
        default=False, description="Seeded from bundled HTML (demo data), not a live fetch."
    )
    created_at: datetime


class SeoAuditSummary(BaseModel):
    id: uuid.UUID
    url: str
    final_url: str
    client_id: str | None
    score: int
    issue_count: int = Field(description="Checks with status fail or warn.")
    is_demo: bool = False
    created_at: datetime
