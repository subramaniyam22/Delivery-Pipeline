"""Add slug and generator_prompt to templates.

Revision ID: l6f7a8b9c0d1
Revises: k5e6f7a8b9c0
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = "l6f7a8b9c0d1"
down_revision = "k5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE templates ADD COLUMN IF NOT EXISTS slug VARCHAR(255)"))
    conn.execute(sa.text("ALTER TABLE templates ADD COLUMN IF NOT EXISTS generator_prompt TEXT"))
    op.create_index("ix_templates_slug", "templates", ["slug"], unique=False)
    # Unique on (slug, version) - only one row per slug+version when slug is set
    try:
        op.create_unique_constraint("uq_templates_slug_version", "templates", ["slug", "version"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_constraint("uq_templates_slug_version", "templates", type_="unique")
    except Exception:
        pass
    op.drop_index("ix_templates_slug", table_name="templates")
    op.drop_column("templates", "generator_prompt")
    op.drop_column("templates", "slug")
