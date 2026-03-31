"""009_add_salamandra_default_provider

Revision ID: d8e9f0a1b2c3
Revises: c7e8f9a0b1c2
Create Date: 2026-01-21 12:00:00.000000

"""
from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, None] = "c7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add salamandra-2b-instruct-yfm as the default translation provider."""
    connection = op.get_bind()

    # Clear existing default provider flag
    connection.execute(
        sa.text("UPDATE translation_providers SET is_default = false WHERE is_default = true")
    )

    # Get language IDs for Spanish and English
    result = connection.execute(
        sa.text("SELECT id FROM languages WHERE code IN ('es', 'en') ORDER BY code")
    )
    language_ids = [row[0] for row in result.fetchall()]
    language_ids_json = json.dumps(language_ids)

    # Insert the Salamandra provider as default
    connection.execute(
        sa.text(
            """
            INSERT INTO translation_providers (
                name,
                provider_type,
                endpoint,
                encrypted_api_key,
                region,
                is_active,
                is_default,
                configuration,
                input_language_ids,
                output_language_ids
            ) VALUES (
                :name,
                :provider_type,
                :endpoint,
                :encrypted_api_key,
                :region,
                :is_active,
                :is_default,
                :configuration,
                :input_language_ids,
                :output_language_ids
            )
            """
        ),
        {
            "name": "salamandra-2b-instruct-yfm",
            "provider_type": "huggingface",
            "endpoint": "https://tb3aka8w0o52ns2f.us-east-1.aws.endpoints.huggingface.cloud",
            "encrypted_api_key": "gAAAAABpRWT8hrjj3BWzkA8ZzeWPR06wtT161nfXoaUJesXEdchuXy2QJDanN_-r5vZx2iI4n7J7v0mdpmSqbuLrqJnyply0Kk_t9DyP4yeiW1dPtiT3f07uUFHBR9sSJZmd8-l-MoFX",
            "region": None,
            "is_active": True,
            "is_default": True,
            "configuration": "{}",
            "input_language_ids": language_ids_json,
            "output_language_ids": language_ids_json,
        },
    )


def downgrade() -> None:
    """Remove the salamandra provider."""
    connection = op.get_bind()

    connection.execute(
        sa.text(
            "DELETE FROM translation_providers WHERE name = 'salamandra-2b-instruct-yfm'"
        )
    )
