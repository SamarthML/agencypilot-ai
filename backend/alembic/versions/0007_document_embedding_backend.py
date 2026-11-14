"""documents.embedding_backend: which embedding backend produced a document's chunks

Revision ID: 0007_document_embedding_backend
Revises: 0006_usage_and_demo
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_document_embedding_backend"
down_revision: str | None = "0006_usage_and_demo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Every existing document was embedded by sentence-transformers (the only backend so far).
    op.add_column(
        "documents",
        sa.Column(
            "embedding_backend",
            sa.String(40),
            nullable=False,
            server_default="sentence-transformers",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "embedding_backend")
