"""Add artifact storage fields

Revision ID: g1f2a3b4c5d6
Revises: f2a9c4d7b8e1
Create Date: 2026-02-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "g1f2a3b4c5d6"
down_revision = "f2a9c4d7b8e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("artifacts", sa.Column("storage_key", sa.String(length=1000), nullable=True))
    op.add_column("artifacts", sa.Column("content_type", sa.String(length=255), nullable=True))
    op.add_column("artifacts", sa.Column("size_bytes", sa.Integer(), nullable=True))
    op.add_column("artifacts", sa.Column("checksum", sa.String(length=128), nullable=True))

    # Backfill storage_key from url when possible
    op.execute("UPDATE artifacts SET storage_key = url WHERE storage_key IS NULL AND url IS NOT NULL")


def downgrade():
    op.drop_column("artifacts", "checksum")
    op.drop_column("artifacts", "size_bytes")
    op.drop_column("artifacts", "content_type")
    op.drop_column("artifacts", "storage_key")
