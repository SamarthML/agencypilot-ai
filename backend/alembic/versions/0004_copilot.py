"""copilot: documents, chunks (pgvector + HNSW cosine index), feedback

Revision ID: 0004_copilot
Revises: 0003_seo_audits
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_copilot"
down_revision: str | None = "0003_seo_audits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client", sa.String(50), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("pages", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "status IN ('processing', 'ready', 'failed')", name="ck_documents_status"
        ),
    )
    op.create_index("ix_documents_client", "documents", ["client"])

    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client", sa.String(50), nullable=False),
        sa.Column("page", sa.Integer, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_client", "chunks", ["client"])
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "copilot_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client", sa.String(50), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question", sa.Text, nullable=True),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("rating", sa.String(4), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        _created_at(),
        sa.CheckConstraint("rating IN ('up', 'down')", name="ck_copilot_feedback_rating"),
    )
    op.create_index("ix_copilot_feedback_client", "copilot_feedback", ["client"])


def downgrade() -> None:
    op.drop_index("ix_copilot_feedback_client", table_name="copilot_feedback")
    op.drop_table("copilot_feedback")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_client", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_documents_client", table_name="documents")
    op.drop_table("documents")
