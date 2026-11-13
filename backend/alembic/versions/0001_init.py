"""init: enable pgvector, create llm_usage

Revision ID: 0001_init
Revises:
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "llm_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("feature", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("cached", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    for column in ("created_at", "feature", "provider", "model"):
        op.create_index(f"ix_llm_usage_{column}", "llm_usage", [column])


def downgrade() -> None:
    for column in ("created_at", "feature", "provider", "model"):
        op.drop_index(f"ix_llm_usage_{column}", table_name="llm_usage")
    op.drop_table("llm_usage")
    op.execute("DROP EXTENSION IF EXISTS vector")
