"""CNC quote result comparable dimensions, commercial conditions, durations, and private evidence.

Revision ID: f6b3e1c91028
Revises: e5a2c3d81028
Create Date: 2026-10-28 19:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "f6b3e1c91028"
down_revision = "e5a2c3d81028"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("cnc_quote_result") as batch:
        batch.add_column(sa.Column("round_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("file_sha256", sa.String(64), nullable=True))
        batch.add_column(sa.Column("comparison_key", sa.String(64), nullable=True))
        batch.add_column(sa.Column("comparison_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("effective_snapshot", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("tax_included", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("shipping_amount", sa.Numeric(14, 4), nullable=True))
        batch.add_column(sa.Column("evidence_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("evidence_state", sa.String(32), nullable=True))
        batch.add_column(sa.Column("queue_ms", sa.BigInteger(), nullable=True, server_default="0"))
        batch.add_column(sa.Column("active_execution_ms", sa.BigInteger(), nullable=True, server_default="0"))
        batch.add_column(sa.Column("human_wait_ms", sa.BigInteger(), nullable=True, server_default="0"))
        batch.add_column(sa.Column("reconcile_ms", sa.BigInteger(), nullable=True, server_default="0"))
        batch.add_column(sa.Column("total_wall_ms", sa.BigInteger(), nullable=True, server_default="0"))
        batch.add_column(sa.Column("error_code", sa.String(80), nullable=True))

        batch.create_index("ix_cnc_quote_result_round_id", ["round_id"])
        batch.create_index("ix_cnc_quote_result_comparison_key", ["comparison_key"])
        batch.create_index("ix_cnc_quote_result_evidence_id", ["evidence_id"])


def downgrade():
    with op.batch_alter_table("cnc_quote_result") as batch:
        batch.drop_index("ix_cnc_quote_result_evidence_id")
        batch.drop_index("ix_cnc_quote_result_comparison_key")
        batch.drop_index("ix_cnc_quote_result_round_id")

        batch.drop_column("error_code")
        batch.drop_column("total_wall_ms")
        batch.drop_column("reconcile_ms")
        batch.drop_column("human_wait_ms")
        batch.drop_column("active_execution_ms")
        batch.drop_column("queue_ms")
        batch.drop_column("evidence_state")
        batch.drop_column("evidence_id")
        batch.drop_column("shipping_amount")
        batch.drop_column("tax_included")
        batch.drop_column("effective_snapshot")
        batch.drop_column("comparison_version")
        batch.drop_column("comparison_key")
        batch.drop_column("file_sha256")
        batch.drop_column("round_id")
