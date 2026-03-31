"""006_add_provider_language_ids

Revision ID: 9d5a9d7b12b0
Revises: 5dca7faa294c
Create Date: 2025-12-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d5a9d7b12b0'
down_revision: Union[str, None] = '5dca7faa294c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add input/output language lists to translation providers."""
    from sqlalchemy.dialects import postgresql

    op.add_column(
        'translation_providers',
        sa.Column(
            'input_language_ids',
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default='[]'
        )
    )
    op.add_column(
        'translation_providers',
        sa.Column(
            'output_language_ids',
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default='[]'
        )
    )


def downgrade() -> None:
    """Remove input/output language lists from translation providers."""
    op.drop_column('translation_providers', 'output_language_ids')
    op.drop_column('translation_providers', 'input_language_ids')
