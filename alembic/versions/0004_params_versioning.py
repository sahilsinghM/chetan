"""Parameter versioning tables (Phase 5): param_versions, ab_experiments.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "param_versions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "params", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_param_version"),
    )
    # Only one active param version at a time
    op.execute(
        """
        CREATE UNIQUE INDEX uq_param_versions_active
        ON param_versions (is_active)
        WHERE is_active = TRUE
        """
    )

    op.create_table(
        "ab_experiments",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("param_ver_a", sa.String(), nullable=True),
        sa.Column("param_ver_b", sa.String(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "result_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("winner", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ab_experiments")
    op.drop_index("uq_param_versions_active", table_name="param_versions")
    op.drop_table("param_versions")
