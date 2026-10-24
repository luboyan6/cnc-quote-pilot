"""Durable controlled quote runs and mutation intents.

Revision ID: c9e3a6b72f14
Revises: 0ce906be2d99
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9e3a6b72f14"
down_revision: str | None = "0ce906be2d99"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cnc_quote_run",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.BigInteger(), nullable=False),
        sa.Column("active_config_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("part_id", sa.Integer(), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("frozen", sa.JSON(), nullable=False),
        sa.Column("public_view", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("actor_id", "config_id", "request_id", name="uq_cnc_quote_request"),
    )
    op.create_index("ix_cnc_quote_run_actor_id", "cnc_quote_run", ["actor_id"])
    op.create_index("ix_cnc_quote_run_config_id", "cnc_quote_run", ["config_id"])
    op.create_table(
        "cnc_quote_intent",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("cnc_quote_run.run_id", name="fk_cnc_quote_intent_run_id_cnc_quote_run"), nullable=False),
        sa.Column("generation", sa.String(64), nullable=False),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("receipt", sa.JSON(), nullable=True),
        sa.UniqueConstraint("run_id", "generation", "operation", name="uq_cnc_quote_intent"),
    )
    op.create_index("ix_cnc_quote_intent_run_id", "cnc_quote_intent", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_cnc_quote_intent_run_id", table_name="cnc_quote_intent")
    op.drop_table("cnc_quote_intent")
    op.drop_index("ix_cnc_quote_run_config_id", table_name="cnc_quote_run")
    op.drop_index("ix_cnc_quote_run_actor_id", table_name="cnc_quote_run")
    op.drop_table("cnc_quote_run")
