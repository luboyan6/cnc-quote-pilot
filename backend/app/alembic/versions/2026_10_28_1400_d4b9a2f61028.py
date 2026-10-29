"""Durable quote batches. Refuse duplicate historical run results without deleting data."""

import sqlalchemy as sa
from alembic import op

revision = "d4b9a2f61028"
down_revision = "b76d50ea5d8f"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    duplicates = connection.execute(sa.text("SELECT run_id, COUNT(*) FROM cnc_quote_result WHERE run_id IS NOT NULL GROUP BY run_id HAVING COUNT(*) > 1")).fetchall()
    if duplicates:
        raise RuntimeError("Duplicate cnc_quote_result.run_id; review required: " + repr([(row[0], row[1]) for row in duplicates]))
    op.create_table(
        "cnc_quote_batch",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("actor_id", sa.Integer, nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("actor_id", "request_id", name="uq_cnc_batch_request"),
    )
    op.create_index("ix_cnc_quote_batch_actor_id", "cnc_quote_batch", ["actor_id"])
    op.create_table(
        "cnc_quote_capacity",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
    )
    op.create_table(
        "cnc_quote_batch_item",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("cnc_quote_batch.id"), nullable=False),
        sa.Column("config_id", sa.BigInteger, nullable=False),
        sa.Column("account_id", sa.Integer, nullable=False),
        sa.Column("input_snapshot", sa.JSON, nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("exec_status", sa.String(24), nullable=False),
        sa.Column("quote_kind", sa.String(24), nullable=True),
        sa.Column("run_id", sa.String(36), nullable=True),
        sa.Column("attempt_count", sa.Integer, nullable=False),
        sa.Column("max_attempts", sa.Integer, nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_owner", sa.String(64), nullable=True),
        sa.Column("claim_token", sa.Integer, nullable=False),
        sa.Column("claim_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer, nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("batch_id", "input_fingerprint", name="uq_cnc_batch_input"),
    )
    op.create_index("ix_cnc_quote_batch_item_batch_id", "cnc_quote_batch_item", ["batch_id"])
    op.create_index("ix_cnc_quote_batch_item_config_id", "cnc_quote_batch_item", ["config_id"])
    op.create_index("ix_cnc_quote_batch_item_account_id", "cnc_quote_batch_item", ["account_id"])
    op.create_index("ix_cnc_quote_batch_item_exec_status", "cnc_quote_batch_item", ["exec_status"])
    op.bulk_insert(sa.table("cnc_quote_capacity", sa.column("id", sa.Integer), sa.column("version", sa.Integer)), [{"id": 1, "version": 0}])
    with op.batch_alter_table("cnc_quote_run") as batch:
        batch.add_column(sa.Column("item_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("attempt_no", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("item_claim_owner", sa.String(64), nullable=True))
        batch.add_column(sa.Column("item_claim_token", sa.Integer(), nullable=True))
        batch.create_index("ix_cnc_quote_run_item_id", ["item_id"])
        batch.create_unique_constraint("uq_cnc_item_attempt", ["item_id", "attempt_no"])
    with op.batch_alter_table("cnc_quote_result") as batch:
        batch.alter_column("currency", existing_type=sa.String(10), nullable=True)
        batch.add_column(sa.Column("batch_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("item_id", sa.String(36), nullable=True))
        batch.create_index("ix_cnc_quote_result_batch_id", ["batch_id"])
        batch.create_index("ix_cnc_quote_result_item_id", ["item_id"])
        batch.create_unique_constraint("uq_cnc_result_run", ["run_id"])


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT COUNT(*) FROM cnc_quote_batch")):
        raise RuntimeError("Batch records exist; disable dispatch and retain data instead of destructive downgrade")
    with op.batch_alter_table("cnc_quote_result") as batch:
        batch.drop_constraint("uq_cnc_result_run", type_="unique")
        batch.drop_index("ix_cnc_quote_result_batch_id")
        batch.drop_index("ix_cnc_quote_result_item_id")
        batch.drop_column("batch_id")
        batch.drop_column("item_id")
    with op.batch_alter_table("cnc_quote_run") as batch:
        batch.drop_constraint("uq_cnc_item_attempt", type_="unique")
        batch.drop_index("ix_cnc_quote_run_item_id")
        batch.drop_column("item_id")
        batch.drop_column("attempt_no")
        batch.drop_column("item_claim_owner")
        batch.drop_column("item_claim_token")
    op.drop_table("cnc_quote_batch_item")
    op.drop_table("cnc_quote_capacity")
    op.drop_table("cnc_quote_batch")
