"""005_make_provider_endpoint_region_optional

Revision ID: 5dca7faa294c
Revises: 88b8e407b2c0
Create Date: 2025-12-12 15:33:47.908282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dca7faa294c'
down_revision: Union[str, None] = '88b8e407b2c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make endpoint and region columns nullable for OpenAI support."""
    # Alter endpoint column to allow NULL
    op.alter_column('translation_providers', 'endpoint',
                    existing_type=sa.String(length=500),
                    nullable=True)

    # Alter region column to allow NULL
    op.alter_column('translation_providers', 'region',
                    existing_type=sa.String(length=50),
                    nullable=True)


def downgrade() -> None:
    """Revert endpoint and region columns to NOT NULL."""
    # Revert region column to NOT NULL
    op.alter_column('translation_providers', 'region',
                    existing_type=sa.String(length=50),
                    nullable=False)

    # Revert endpoint column to NOT NULL
    op.alter_column('translation_providers', 'endpoint',
                    existing_type=sa.String(length=500),
                    nullable=False)
