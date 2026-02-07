"""merge alembic heads

Revision ID: b206386a8ce2
Revises: add_desc_col, c1a4e77d9f3b
Create Date: 2026-02-07 18:48:19.842977

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b206386a8ce2'
down_revision = ('add_desc_col', 'c1a4e77d9f3b')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
