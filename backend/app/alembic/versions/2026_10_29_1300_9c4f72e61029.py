"""Add durable, actor-scoped private drawing upload requests.

Revision ID: 9c4f72e61029
Revises: 3a29b7e61029
"""

import sqlalchemy as sa
from alembic import op

revision = "9c4f72e61029"
down_revision = "3a29b7e61029"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cnc_drawing_upload",
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("part_id", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("extension", sa.String(8), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["cnc_part.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("owner_id", "request_id"),
        sa.UniqueConstraint("part_id", name="uq_cnc_drawing_upload_part"),
    )


def downgrade():
    op.drop_table("cnc_drawing_upload")
