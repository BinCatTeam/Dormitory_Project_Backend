"""add deleted column to Bill

Revision ID: 191b12ff6a94
Revises: 
Create Date: 2026-01-10 22:49:05.168847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '191b12ff6a94'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bill', sa.Column(
        'deleted',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('false')
    ), schema='bill')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bill', 'deleted', schema='bill')
