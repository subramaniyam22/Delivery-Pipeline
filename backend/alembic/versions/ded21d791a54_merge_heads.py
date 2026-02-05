"""merge_heads

Revision ID: ded21d791a54
Revises: 8cf57896ef1a, add_indexes_soft_delete
Create Date: 2026-02-04 23:54:22.616377

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ded21d791a54'
down_revision = ('8cf57896ef1a', 'add_indexes_soft_delete')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
