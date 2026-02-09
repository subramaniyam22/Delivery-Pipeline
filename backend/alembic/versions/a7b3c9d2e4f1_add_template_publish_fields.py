"""add template publish fields

Revision ID: a7b3c9d2e4f1
Revises: d7f3a2c6b1a9
Create Date: 2026-02-08 07:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a7b3c9d2e4f1"
down_revision = "d7f3a2c6b1a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("templates", "repo_url", nullable=True)
    op.alter_column("templates", "default_branch", nullable=True)
    op.add_column("templates", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("templates", sa.Column("features_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("templates", sa.Column("preview_url", sa.String(length=1000), nullable=True))
    op.add_column("templates", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("templates", sa.Column("source_type", sa.String(length=20), nullable=False, server_default=sa.text("'ai'")))
    op.add_column("templates", sa.Column("intent", sa.Text(), nullable=True))
    op.add_column("templates", sa.Column("preview_status", sa.String(length=30), nullable=False, server_default=sa.text("'not_generated'")))
    op.add_column("templates", sa.Column("preview_last_generated_at", sa.DateTime(), nullable=True))
    op.add_column("templates", sa.Column("preview_error", sa.Text(), nullable=True))
    op.add_column("templates", sa.Column("preview_thumbnail_url", sa.String(length=1000), nullable=True))
    op.execute("UPDATE templates SET features_json = '[]'::jsonb WHERE features_json IS NULL")
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
    op.drop_column("templates", "is_published")
    op.drop_column("templates", "preview_url")
    op.drop_column("templates", "features_json")
    op.drop_column("templates", "description")
