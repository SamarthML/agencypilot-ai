"""usage + demo: llm_usage.skipped / saved_cost_usd, seo_audits.is_demo

Revision ID: 0006_usage_and_demo
Revises: 0005_reports
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_usage_and_demo"
down_revision: str | None = "0005_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "llm_usage",
        sa.Column("skipped", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("llm_usage", sa.Column("saved_cost_usd", sa.Numeric(12, 6), nullable=True))
    op.add_column(
        "seo_audits",
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("seo_audits", "is_demo")
    op.drop_column("llm_usage", "saved_cost_usd")
    op.drop_column("llm_usage", "skipped")
