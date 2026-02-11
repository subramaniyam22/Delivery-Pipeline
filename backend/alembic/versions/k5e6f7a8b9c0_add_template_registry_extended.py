"""Add extended TemplateRegistry fields (category, style, status, pages_json, etc.)

Revision ID: k5e6f7a8b9c0
Revises: j4d5e6f7a8b9
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "k5e6f7a8b9c0"
down_revision = "j4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Add new columns (idempotent where supported)
    for stmt in [
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS style VARCHAR(50)",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS feature_tags_json JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'draft'",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS is_recommended BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS repo_path VARCHAR(1000)",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS pages_json JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS required_inputs_json JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS optional_inputs_json JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS default_config_json JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS rules_json JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS validation_results_json JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS changelog TEXT",
        "ALTER TABLE templates ADD COLUMN IF NOT EXISTS parent_template_id UUID",
    ]:
        try:
            conn.execute(sa.text(stmt))
        except Exception:
            pass
    # Backfill existing rows: status from is_published, feature_tags_json from features_json
    op.execute("""
        UPDATE templates
        SET status = CASE WHEN is_published = true THEN 'published' ELSE 'draft' END,
            feature_tags_json = COALESCE(features_json, '[]'::jsonb)
    """)


def downgrade() -> None:
    for col in [
        "parent_template_id", "changelog", "version", "validation_results_json",
        "rules_json", "default_config_json", "optional_inputs_json",
        "required_inputs_json", "pages_json", "repo_path", "is_recommended",
        "is_default", "status", "feature_tags_json", "style", "category",
    ]:
        try:
            op.drop_column("templates", col)
        except Exception:
            pass
