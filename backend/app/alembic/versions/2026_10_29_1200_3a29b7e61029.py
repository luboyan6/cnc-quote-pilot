"""Add numeric-owner source chat metadata and visible message projection.

Revision ID: 3a29b7e61029
Revises: f6b3e1c91028
"""

import sqlalchemy as sa
from alembic import op

revision = "3a29b7e61029"
down_revision = "f6b3e1c91028"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_source_chat_session",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_source_chat_session_owner_updated", "ai_source_chat_session", ["owner_id", "updated_at"])
    op.create_table(
        "ai_source_chat_message",
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["ai_source_chat_session.session_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "source_id"),
        sa.UniqueConstraint("session_id", "position", name="uq_ai_source_chat_message_position"),
    )


def downgrade():
    op.drop_table("ai_source_chat_message")
    op.drop_index("ix_ai_source_chat_session_owner_updated", table_name="ai_source_chat_session")
    op.drop_table("ai_source_chat_session")
