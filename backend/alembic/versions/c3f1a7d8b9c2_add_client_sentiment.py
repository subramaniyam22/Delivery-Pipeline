"""add client sentiment table

Revision ID: c3f1a7d8b9c2
Revises: f2a9c4d7b8e1
Create Date: 2026-02-07 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c3f1a7d8b9c2"
down_revision = "f2a9c4d7b8e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_sentiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_client_sentiments_project_id", "client_sentiments", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_client_sentiments_project_id", table_name="client_sentiments")
    op.drop_table("client_sentiments")
