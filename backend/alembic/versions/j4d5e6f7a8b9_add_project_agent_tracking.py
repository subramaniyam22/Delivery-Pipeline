"""add project agent tracking

Revision ID: j4d5e6f7a8b9
Revises: i3c4d5e6f7a8
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = "j4d5e6f7a8b9"
down_revision = "i3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("created_by_agent_type", sa.String(length=100), nullable=True))
    op.add_column("projects", sa.Column("last_handled_by_agent_type", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "last_handled_by_agent_type")
    op.drop_column("projects", "created_by_agent_type")
