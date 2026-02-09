"""Merge multiple alembic heads (template_ai, admin_config, artifact_storage)

Revision ID: i3c4d5e6f7a8
Revises: c9d8e7f6a5b4, h2b3c4d5e6f7, g1f2a3b4c5d6
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = "i3c4d5e6f7a8"
down_revision = ("c9d8e7f6a5b4", "h2b3c4d5e6f7", "g1f2a3b4c5d6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
