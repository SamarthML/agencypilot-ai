"""One row per SEO audit, including cache hits (so history reflects every request)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SeoAudit(Base):
    __tablename__ = "seo_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    final_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    client_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    # JSON columns hold validated Pydantic dumps (SeoCheck, SeoPageSummary, SeoAiReport, meta).
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    page: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # none_as_null: store Python None as SQL NULL (not JSON 'null') so `IS NULL` filters work.
    ai: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    llm_meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    ai_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    load_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    html_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Seeded from bundled fixture HTML (services/seo_demo.py), not fetched from the live site.
    is_demo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
