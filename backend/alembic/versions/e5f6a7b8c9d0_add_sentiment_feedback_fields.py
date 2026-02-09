"""add sentiment feedback fields

Revision ID: e5f6a7b8c9d0
Revises: c3f1a7d8b9c2
Create Date: 2026-02-08 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "c3f1a7d8b9c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("client_sentiments", sa.Column("template_id", sa.String(length=100), nullable=True))
    op.add_column("client_sentiments", sa.Column("template_name", sa.String(length=255), nullable=True))
    op.add_column("client_sentiments", sa.Column("stage_at_delivery", sa.String(length=50), nullable=True))
    op.add_column("client_sentiments", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("client_sentiments", sa.Column("created_by_type", sa.String(length=50), nullable=True))
    op.create_foreign_key(
        "fk_client_sentiments_created_by_user",
        "client_sentiments",
        "users",
        ["created_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_client_sentiments_created_by_user", "client_sentiments", type_="foreignkey")
    op.drop_column("client_sentiments", "created_by_type")
    op.drop_column("client_sentiments", "created_by_user_id")
    op.drop_column("client_sentiments", "stage_at_delivery")
    op.drop_column("client_sentiments", "template_name")
    op.drop_column("client_sentiments", "template_id")
