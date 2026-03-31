"""007_populate_provider_language_ids

Revision ID: a1b2c3d4e5f6
Revises: 9d5a9d7b12b0
Create Date: 2025-12-12 18:20:00.000000

Populate existing providers with all available languages as both input and output.
"""
from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9d5a9d7b12b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set input/output languages for existing providers to all active languages."""
    conn = op.get_bind()
    lang_rows = conn.execute(
        sa.text("SELECT id FROM languages WHERE is_active = true ORDER BY sort_order, name")
    ).fetchall()

    language_ids = [row[0] for row in lang_rows]
    languages_json = json.dumps(language_ids)

    conn.execute(
        sa.text(
            "UPDATE translation_providers "
            "SET input_language_ids = :langs, output_language_ids = :langs"
        ),
        {"langs": languages_json},
    )


def downgrade() -> None:
    """Clear input/output language lists on downgrade."""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE translation_providers "
            "SET input_language_ids = '[]', output_language_ids = '[]'"
        )
    )
