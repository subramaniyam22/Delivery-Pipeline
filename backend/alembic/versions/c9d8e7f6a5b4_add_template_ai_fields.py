"""add template ai fields

Revision ID: c9d8e7f6a5b4
Revises: a7b3c9d2e4f1
Create Date: 2026-02-08 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c9d8e7f6a5b4"
down_revision = "a7b3c9d2e4f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: a7b3c9d2e4f1 may have already added these columns; use IF NOT EXISTS for safe merge.
    conn = op.get_bind()
    for stmt in [
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'ai'",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS intent TEXT",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS preview_status VARCHAR(30) NOT NULL DEFAULT 'not_generated'",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS preview_last_generated_at TIMESTAMP",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS preview_error TEXT",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS preview_thumbnail_url VARCHAR(1000)",
    ]:
        conn.execute(sa.text(stmt))
    op.alter_column("templates", "repo_url", nullable=True)
    op.alter_column("templates", "default_branch", nullable=True)
    op.execute("""
        UPDATE templates
        SET source_type = CASE
            WHEN repo_url IS NULL OR repo_url = '' THEN 'ai'
            ELSE 'git'
        END
    """)
    op.execute("""
        UPDATE templates
        SET preview_status = CASE
            WHEN preview_url IS NOT NULL AND preview_url <> '' THEN 'ready'
            ELSE 'not_generated'
        END
    """)


def downgrade() -> None:
    op.alter_column("templates", "default_branch", nullable=False)
    op.alter_column("templates", "repo_url", nullable=False)
    op.drop_column("templates", "preview_thumbnail_url")
    op.drop_column("templates", "preview_error")
    op.drop_column("templates", "preview_last_generated_at")
    op.drop_column("templates", "preview_status")
    op.drop_column("templates", "intent")
    op.drop_column("templates", "source_type")
