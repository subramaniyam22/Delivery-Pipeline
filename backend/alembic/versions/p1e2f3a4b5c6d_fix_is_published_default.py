"""Fix is_published default: drafts show Publish, only published show Unpublish.

Revision ID: p1e2f3a4b5c6d
Revises: o2c3d4e5f6a7
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa


revision = "p1e2f3a4b5c6d"
down_revision = "o2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Set is_published = false for any template that is not actually published (status != 'published').
    op.execute("""
        UPDATE templates
        SET is_published = false
        WHERE status IS NULL OR status <> 'published'
    """)
    # Change column default so new templates are created as draft (is_published false).
    op.alter_column(
        "templates",
        "is_published",
        server_default=sa.text("false"),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "templates",
        "is_published",
        server_default=sa.text("true"),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
