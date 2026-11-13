"""insights: datasets and daily per-channel rows

Revision ID: 0002_insights
Revises: 0001_init
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_insights"
down_revision: str | None = "0001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insight_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", sa.String(50), nullable=False),
        sa.Column("client_name", sa.String(100), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("row_count", sa.Integer, nullable=False),
        sa.Column("channels", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_insight_datasets_client_id", "insight_datasets", ["client_id"])

    op.create_table(
        "insight_rows",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("insight_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("sessions", sa.Integer, nullable=False),
        sa.Column("conversions", sa.Integer, nullable=False),
        sa.Column("revenue", sa.Numeric(14, 2), nullable=False),
        sa.Column("spend", sa.Numeric(14, 2), nullable=False),
    )
    op.create_index("ix_insight_rows_dataset_id", "insight_rows", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_insight_rows_dataset_id", table_name="insight_rows")
    op.drop_table("insight_rows")
    op.drop_index("ix_insight_datasets_client_id", table_name="insight_datasets")
    op.drop_table("insight_datasets")
