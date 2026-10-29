"""Application-owned agent ledgers; no provider activation or history replay.

Revision ID: a7d30f26b8e1
Revises: 4e51456ea4db
"""

import sqlalchemy as sa
from alembic import op

revision = "a7d30f26b8e1"
down_revision = "4e51456ea4db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_agent_run",
        sa.Column("agent_run_id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("client_request_id", sa.String(36), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("active_session", sa.String(64), unique=True, nullable=True),
        sa.Column("owner_token", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("protocol_version", sa.Integer(), nullable=False),
        sa.Column("skill_versions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("actor_id", "session_id", "client_request_id", name="uq_ai_agent_request"),
    )
    op.create_table(
        "ai_agent_tool_operation",
        sa.Column("operation_id", sa.String(36), primary_key=True),
        sa.Column("agent_run_id", sa.String(36), sa.ForeignKey("ai_agent_run.agent_run_id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("logical_key", sa.String(64), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("target_quote_run_id", sa.String(36), nullable=True),
        sa.Column("active_target", sa.String(64), unique=True, nullable=True),
        sa.Column("request_id", sa.String(36), unique=True, nullable=False),
        sa.Column("quote_run_id", sa.String(36), nullable=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_run_id", "logical_key", name="uq_ai_agent_operation"),
    )


def downgrade() -> None:
    op.drop_table("ai_agent_tool_operation")
    op.drop_table("ai_agent_run")
