"""seo: audits table

Revision ID: 0003_seo_audits
Revises: 0002_insights
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_seo_audits"
down_revision: str | None = "0002_insights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEXED = ("normalized_url", "client_id", "created_at")


def upgrade() -> None:
    op.create_table(
        "seo_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("normalized_url", sa.String(2048), nullable=False),
        sa.Column("final_url", sa.String(2048), nullable=False),
        sa.Column("client_id", sa.String(50), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("checks", postgresql.JSONB, nullable=False),
        sa.Column("page", postgresql.JSONB, nullable=False),
        sa.Column("ai", postgresql.JSONB, nullable=True),
        sa.Column("llm_meta", postgresql.JSONB, nullable=True),
        sa.Column("ai_error", sa.Text, nullable=True),
        sa.Column("load_ms", sa.Integer, nullable=False),
        sa.Column("html_bytes", sa.Integer, nullable=False),
        sa.Column("cached", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    for column in INDEXED:
        op.create_index(f"ix_seo_audits_{column}", "seo_audits", [column])


def downgrade() -> None:
    for column in INDEXED:
        op.drop_index(f"ix_seo_audits_{column}", table_name="seo_audits")
    op.drop_table("seo_audits")
