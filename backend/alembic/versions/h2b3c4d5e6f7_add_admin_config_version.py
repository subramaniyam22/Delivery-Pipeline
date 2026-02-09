"""add admin config version

Revision ID: h2b3c4d5e6f7
Revises: e5f6a7b8c9d0
Create Date: 2026-02-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "h2b3c4d5e6f7"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "admin_configs",
        sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade():
    op.drop_column("admin_configs", "config_version")
