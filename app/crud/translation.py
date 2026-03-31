"""CRUD operations for translation management."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.encryption import EncryptionService
from app.models.translation import Language, Translation, TranslationProvider
from app.schemas.translation import (
    LanguageCreate,
    LanguageUpdate,
    TranslationCreate,
    TranslationProviderCreate,
    TranslationProviderUpdate,
)


# ----------------------------- Provider CRUD ----------------------------- #

async def create_provider(
    db: AsyncSession,
    provider: TranslationProviderCreate
) -> TranslationProvider:
    """Create a translation provider with encrypted API key."""
    encryption = EncryptionService(settings.encryption_key.get_secret_value())
    encrypted_key = encryption.encrypt(provider.api_key.get_secret_value())

    if provider.is_default:
        # Ensure only one default provider exists
        await db.execute(update(TranslationProvider).values(is_default=False))

    provider_data = provider.model_dump(exclude={'api_key'})
    db_provider = TranslationProvider(
        **provider_data,
        encrypted_api_key=encrypted_key
    )

    db.add(db_provider)
    await db.commit()
    await db.refresh(db_provider)
    return db_provider


async def get_provider(db: AsyncSession, provider_id: int) -> TranslationProvider | None:
    """Get provider by ID."""
    result = await db.execute(
        select(TranslationProvider).where(TranslationProvider.id == provider_id)
    )
    return result.scalar_one_or_none()


async def get_providers(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    only_active: bool = False
) -> list[TranslationProvider]:
    """Get providers with optional active filter."""
    query = select(TranslationProvider)
    if only_active:
        query = query.where(TranslationProvider.is_active == True)  # noqa: E712
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_default_provider(db: AsyncSession) -> TranslationProvider | None:
    """Get the default active provider."""
    result = await db.execute(
        select(TranslationProvider)
        .where(TranslationProvider.is_default == True)  # noqa: E712
        .where(TranslationProvider.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def update_provider(
    db: AsyncSession,
    provider_id: int,
    provider_update: TranslationProviderUpdate
) -> TranslationProvider | None:
    """Update provider, re-encrypting API key if changed."""
    provider = await get_provider(db, provider_id)
    if not provider:
        return None

    update_data = provider_update.model_dump(exclude_unset=True)

    # If making this provider default, clear the flag on all others first
    if update_data.get("is_default"):
        await db.execute(update(TranslationProvider).values(is_default=False))

    if "api_key" in update_data and update_data["api_key"] is not None:
        encryption = EncryptionService(settings.encryption_key.get_secret_value())
        encrypted_key = encryption.encrypt(update_data.pop("api_key").get_secret_value())
        update_data["encrypted_api_key"] = encrypted_key

    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


async def delete_provider(db: AsyncSession, provider_id: int) -> bool:
    """Delete a provider."""
    provider = await get_provider(db, provider_id)
    if not provider:
        return False
    await db.delete(provider)
    await db.commit()
    return True


async def set_default_provider(db: AsyncSession, provider_id: int) -> TranslationProvider | None:
    """Set provider as default, removing default from others."""
    await db.execute(
        update(TranslationProvider).values(is_default=False)
    )

    provider = await get_provider(db, provider_id)
    if not provider:
        return None

    provider.is_default = True
    await db.commit()
    await db.refresh(provider)
    return provider


async def get_decrypted_api_key(db: AsyncSession, provider_id: int) -> str:
    """Get decrypted API key (internal use only)."""
    provider = await get_provider(db, provider_id)
    if not provider:
        raise ValueError("Provider not found")

    encryption = EncryptionService(settings.encryption_key.get_secret_value())
    return encryption.decrypt(provider.encrypted_api_key)


# ----------------------------- Language CRUD ----------------------------- #

async def create_language(db: AsyncSession, language: LanguageCreate) -> Language:
    """Create a new language."""
    db_language = Language(**language.model_dump())
    db.add(db_language)
    await db.commit()
    await db.refresh(db_language)
    return db_language


async def get_language(db: AsyncSession, language_id: int) -> Language | None:
    """Get language by ID."""
    result = await db.execute(
        select(Language).where(Language.id == language_id)
    )
    return result.scalar_one_or_none()


async def get_language_by_code(db: AsyncSession, code: str) -> Language | None:
    """Get language by code."""
    result = await db.execute(
        select(Language).where(Language.code == code)
    )
    return result.scalar_one_or_none()


async def get_languages_by_ids(db: AsyncSession, language_ids: list[int]) -> list[Language]:
    """Get multiple languages by their IDs."""
    if not language_ids:
        return []
    result = await db.execute(
        select(Language).where(Language.id.in_(language_ids))
    )
    return list(result.scalars().all())


async def get_languages(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    only_active: bool = False
) -> list[Language]:
    """Get languages with optional active filter."""
    query = select(Language).order_by(Language.sort_order, Language.name)
    if only_active:
        query = query.where(Language.is_active == True)  # noqa: E712
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_language(
    db: AsyncSession,
    language_id: int,
    language_update: LanguageUpdate
) -> Language | None:
    """Update a language."""
    language = await get_language(db, language_id)
    if not language:
        return None

    update_data = language_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(language, field, value)

    await db.commit()
    await db.refresh(language)
    return language


async def delete_language(db: AsyncSession, language_id: int) -> bool:
    """Delete a language."""
    language = await get_language(db, language_id)
    if not language:
        return False
    await db.delete(language)
    await db.commit()
    return True


async def activate_language(db: AsyncSession, language_id: int, is_active: bool) -> Language | None:
    """Activate or deactivate a language."""
    language = await get_language(db, language_id)
    if not language:
        return None

    language.is_active = is_active
    await db.commit()
    await db.refresh(language)
    return language


# ----------------------------- Translation CRUD ----------------------------- #

async def create_translation(
    db: AsyncSession,
    translation_data: TranslationCreate
) -> Translation:
    """Create a translation record."""
    db_translation = Translation(**translation_data.model_dump())
    db.add(db_translation)
    await db.commit()
    await db.refresh(
        db_translation,
        ["source_language", "target_language", "provider", "user"]
    )
    return db_translation


async def get_translation(db: AsyncSession, translation_id: int) -> Translation | None:
    """Get translation by ID."""
    result = await db.execute(
        select(Translation)
        .where(Translation.id == translation_id)
        .options(
            selectinload(Translation.source_language),
            selectinload(Translation.target_language),
            selectinload(Translation.provider),
            selectinload(Translation.user)
        )
    )
    return result.scalar_one_or_none()


async def get_translations(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = None,
    source_language_id: int | None = None,
    target_language_id: int | None = None
) -> list[Translation]:
    """Get translations with filters."""
    query = select(Translation).options(
        selectinload(Translation.source_language),
        selectinload(Translation.target_language),
        selectinload(Translation.provider)
    ).order_by(Translation.created_at.desc())

    if user_id:
        query = query.where(Translation.user_id == user_id)
    if source_language_id:
        query = query.where(Translation.source_language_id == source_language_id)
    if target_language_id:
        query = query.where(Translation.target_language_id == target_language_id)

    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_user_translations(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> list[Translation]:
    """Get all translations for a specific user."""
    return await get_translations(db, skip=skip, limit=limit, user_id=user_id)
