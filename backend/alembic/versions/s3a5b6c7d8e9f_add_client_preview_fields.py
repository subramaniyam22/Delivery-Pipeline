"""Add Project client preview fields (url, thumbnail, status, hash, error).

Revision ID: s3a5b6c7d8e9f
Revises: r2f3a4b5c6d7
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = "s3a5b6c7d8e9f"
down_revision = "r2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("client_preview_url", sa.String(1000), nullable=True))
    op.add_column("projects", sa.Column("client_preview_thumbnail_url", sa.String(1000), nullable=True))
    op.add_column("projects", sa.Column("client_preview_status", sa.String(30), nullable=False, server_default="not_generated"))
    op.add_column("projects", sa.Column("client_preview_last_generated_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("client_preview_hash", sa.String(64), nullable=True))
    op.add_column("projects", sa.Column("client_preview_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "client_preview_error")
    op.drop_column("projects", "client_preview_hash")
    op.drop_column("projects", "client_preview_last_generated_at")
    op.drop_column("projects", "client_preview_status")
    op.drop_column("projects", "client_preview_thumbnail_url")
    op.drop_column("projects", "client_preview_url")
