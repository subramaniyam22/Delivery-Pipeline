"""Sentiment enrichment, delivery_outcomes, template performance_metrics, evolution_proposals.

Revision ID: t4b6c8d0e1f2a
Revises: s3a5b6c7d8e9f
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "t4b6c8d0e1f2a"
down_revision = "s3a5b6c7d8e9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ClientSentiment enrichment
    op.add_column("client_sentiments", sa.Column("overall_score", sa.Float(), nullable=True))
    op.add_column("client_sentiments", sa.Column("nps_score", sa.Integer(), nullable=True))
    op.add_column("client_sentiments", sa.Column("tags_json", JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"))
    op.add_column("client_sentiments", sa.Column("free_text_feedback", sa.Text(), nullable=True))
    op.add_column("client_sentiments", sa.Column("template_registry_id", UUID(as_uuid=True), nullable=True))
    op.add_column("client_sentiments", sa.Column("template_version", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_client_sentiments_template_registry", "client_sentiments", "templates", ["template_registry_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_client_sentiments_template_registry_id", "client_sentiments", ["template_registry_id"])

    # delivery_outcomes table
    op.create_table(
        "delivery_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("template_registry_id", UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cycle_time_days", sa.Integer(), nullable=True),
        sa.Column("defect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reopened_defects_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("on_time_delivery", sa.Boolean(), nullable=True),
        sa.Column("final_quality_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_delivery_outcomes_project_id", "delivery_outcomes", ["project_id"])
    op.create_index("ix_delivery_outcomes_template_registry_id", "delivery_outcomes", ["template_registry_id"])

    # TemplateRegistry performance_metrics_json + is_deprecated
    op.add_column("templates", sa.Column("performance_metrics_json", JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"))
    op.add_column("templates", sa.Column("is_deprecated", sa.Boolean(), nullable=False, server_default="false"))

    # template_evolution_proposals table
    op.create_table(
        "template_evolution_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposal_json", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_template_evolution_proposals_template_id", "template_evolution_proposals", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_template_evolution_proposals_template_id", table_name="template_evolution_proposals")
    op.drop_table("template_evolution_proposals")
    op.drop_column("templates", "is_deprecated")
    op.drop_column("templates", "performance_metrics_json")
    op.drop_index("ix_delivery_outcomes_template_registry_id", table_name="delivery_outcomes")
    op.drop_index("ix_delivery_outcomes_project_id", table_name="delivery_outcomes")
    op.drop_table("delivery_outcomes")
    op.drop_index("ix_client_sentiments_template_registry_id", table_name="client_sentiments")
    op.drop_constraint("fk_client_sentiments_template_registry", "client_sentiments", type_="foreignkey")
    op.drop_column("client_sentiments", "template_version")
    op.drop_column("client_sentiments", "template_registry_id")
    op.drop_column("client_sentiments", "free_text_feedback")
    op.drop_column("client_sentiments", "tags_json")
    op.drop_column("client_sentiments", "nps_score")
    op.drop_column("client_sentiments", "overall_score")
