"""003_create_translation_tables

Revision ID: ce8927b9ce10
Revises: 5b0215d4c850
Create Date: 2025-12-12 15:21:50.574604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce8927b9ce10'
down_revision: Union[str, None] = '5b0215d4c850'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Import JSON type for PostgreSQL
    from sqlalchemy.dialects import postgresql

    # Create translation_providers table
    op.create_table(
        'translation_providers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('encrypted_api_key', sa.Text(), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_translation_providers_name'), 'translation_providers', ['name'], unique=False)

    # Create languages table
    op.create_table(
        'languages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('native_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_languages_code'), 'languages', ['code'], unique=True)

    # Create translations table
    op.create_table(
        'translations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('provider_id', sa.BigInteger(), nullable=False),
        sa.Column('source_language_id', sa.BigInteger(), nullable=False),
        sa.Column('target_language_id', sa.BigInteger(), nullable=False),
        sa.Column('source_text', sa.Text(), nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=False),
        sa.Column('character_count', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['translation_providers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_language_id'], ['languages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_language_id'], ['languages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create triggers for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        CREATE TRIGGER update_translation_providers_updated_at
        BEFORE UPDATE ON translation_providers
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_languages_updated_at
        BEFORE UPDATE ON languages
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # Insert common languages
    op.execute("""
        INSERT INTO languages (code, name, native_name, is_active, sort_order) VALUES
        ('en', 'English', 'English', true, 1),
        ('es', 'Spanish', 'Español', true, 2),
        ('fr', 'French', 'Français', true, 3),
        ('de', 'German', 'Deutsch', true, 4),
        ('pt', 'Portuguese', 'Português', true, 5),
        ('it', 'Italian', 'Italiano', true, 6),
        ('ja', 'Japanese', '日本語', true, 7),
        ('zh', 'Chinese (Simplified)', '简体中文', true, 8),
        ('zh-Hant', 'Chinese (Traditional)', '繁體中文', true, 9),
        ('ko', 'Korean', '한국어', true, 10),
        ('ru', 'Russian', 'Русский', true, 11),
        ('ar', 'Arabic', 'العربية', true, 12),
        ('hi', 'Hindi', 'हिन्दी', true, 13),
        ('nl', 'Dutch', 'Nederlands', true, 14),
        ('sv', 'Swedish', 'Svenska', true, 15),
        ('no', 'Norwegian', 'Norsk', true, 16),
        ('da', 'Danish', 'Dansk', true, 17),
        ('fi', 'Finnish', 'Suomi', true, 18),
        ('pl', 'Polish', 'Polski', true, 19),
        ('tr', 'Turkish', 'Türkçe', true, 20),
        ('th', 'Thai', 'ไทย', true, 21),
        ('vi', 'Vietnamese', 'Tiếng Việt', true, 22),
        ('id', 'Indonesian', 'Bahasa Indonesia', true, 23),
        ('ms', 'Malay', 'Bahasa Melayu', true, 24),
        ('cs', 'Czech', 'Čeština', true, 25),
        ('ro', 'Romanian', 'Română', true, 26),
        ('el', 'Greek', 'Ελληνικά', true, 27),
        ('he', 'Hebrew', 'עברית', true, 28),
        ('uk', 'Ukrainian', 'Українська', true, 29),
        ('hu', 'Hungarian', 'Magyar', true, 30)
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_languages_updated_at ON languages")
    op.execute("DROP TRIGGER IF EXISTS update_translation_providers_updated_at ON translation_providers")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables in reverse order
    op.drop_table('translations')
    op.drop_index(op.f('ix_languages_code'), table_name='languages')
    op.drop_table('languages')
    op.drop_index(op.f('ix_translation_providers_name'), table_name='translation_providers')
    op.drop_table('translation_providers')
