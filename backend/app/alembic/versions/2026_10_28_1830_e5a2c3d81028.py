"""CNC quote schedules and rounds."""

import sqlalchemy as sa
from alembic import op

revision = "e5a2c3d81028"
down_revision = "d4b9a2f61028"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cnc_quote_schedule",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("actor_id", sa.Integer, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("interval_minutes", sa.Integer, nullable=False),
        sa.Column("timezone", sa.String(40), nullable=False),
        sa.Column("anchor_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("target_snapshot", sa.JSON, nullable=False),
        sa.Column("target_fingerprint", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("last_round_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_reason", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cnc_quote_schedule_actor_id", "cnc_quote_schedule", ["actor_id"])
    op.create_index("ix_cnc_quote_schedule_next_run_at", "cnc_quote_schedule", ["next_run_at"])
    op.create_index("ix_cnc_quote_schedule_status", "cnc_quote_schedule", ["status"])

    op.create_table(
        "cnc_quote_schedule_round",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("schedule_id", sa.String(36), sa.ForeignKey("cnc_quote_schedule.id"), nullable=False),
        sa.Column("round_no", sa.Integer, nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("cnc_quote_batch.id"), nullable=True),
        sa.Column("schedule_revision", sa.Integer, nullable=False),
        sa.Column("skip_reason", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("schedule_id", "scheduled_for", name="uq_cnc_schedule_slot"),
    )
    op.create_index("ix_cnc_quote_schedule_round_schedule_id", "cnc_quote_schedule_round", ["schedule_id"])
    op.create_index("ix_cnc_quote_schedule_round_scheduled_for", "cnc_quote_schedule_round", ["scheduled_for"])
    op.create_index("ix_cnc_quote_schedule_round_status", "cnc_quote_schedule_round", ["status"])
    op.create_index("ix_cnc_quote_schedule_round_batch_id", "cnc_quote_schedule_round", ["batch_id"])


def downgrade():
    connection = op.get_bind()
    has_data = connection.execute(sa.text("SELECT COUNT(*) FROM cnc_quote_schedule")).scalar()
    if has_data:
        raise RuntimeError("Refusing destructive downgrade: cnc_quote_schedule has data")
    op.drop_table("cnc_quote_schedule_round")
    op.drop_table("cnc_quote_schedule")
