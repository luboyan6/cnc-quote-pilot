"""Add rebuildable evidence references to source-chat visible messages.

Revision ID: a816e3b61030
Revises: 9c4f72e61029
"""

import sqlalchemy as sa
from alembic import op

revision = "a816e3b61030"
down_revision = "9c4f72e61029"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ai_source_chat_message", sa.Column("evidence_result_ids", sa.JSON(), nullable=True))


def downgrade():
    values = op.get_bind().execute(sa.text("SELECT evidence_result_ids FROM ai_source_chat_message")).scalars()
    if any(value not in (None, [], "[]", "null") for value in values):
        raise RuntimeError("SOURCE_EVIDENCE_PROJECTION_NOT_EMPTY")
    op.drop_column("ai_source_chat_message", "evidence_result_ids")
