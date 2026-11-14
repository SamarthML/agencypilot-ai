"""Copilot tables: uploaded documents, their embedded chunks, and answer feedback."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# BAAI/bge-small-en-v1.5 output size. Changing the embedding model means a new migration.
EMBEDDING_DIM = 384


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("status IN ('processing', 'ready', 'failed')", name="ck_documents_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Which backend embedded the chunks: their vectors differ slightly, so a document is
    # re-embedded when the deployment switches backend (see copilot.seed_sample_documents).
    embedding_backend: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="sentence-transformers"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        # HNSW over cosine distance: the embeddings are normalised, and retrieval orders by `<=>`.
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised from documents so retrieval filters chunks without a join.
    client: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)


class CopilotFeedback(Base):
    __tablename__ = "copilot_feedback"
    __table_args__ = (
        CheckConstraint("rating IN ('up', 'down')", name="ck_copilot_feedback_rating"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[str] = mapped_column(String(4), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
