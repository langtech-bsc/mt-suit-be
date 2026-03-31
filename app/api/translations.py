"""Translation API endpoints."""

import base64
import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_active_user, get_session
from app.core.config import settings
from app.core.encryption import EncryptionService
from app.crud import translation as crud_translation
from app.models.translation import Language, TranslationProvider
from app.models.user import User
from app.schemas.translation import (
    DocumentTranslationResponse,
    GrammarCheckRequest,
    GrammarCheckResponse,
    LanguageCreate,
    LanguageResponse,
    LanguageUpdate,
    PostEditRequest,
    PostEditResponse,
    TranslationCreate,
    TranslationHistoryResponse,
    TranslationProviderCreate,
    TranslationProviderResponse,
    TranslationProviderUpdate,
    TranslationRequest,
    TranslationResponse,
)
from app.services.translation_service import TranslationServiceFactory
from app.services.grammar_service import GrammarServiceFactory
from app.services.post_editing_service import PostEditingServiceFactory
from app.services.document_service import DocumentTranslationService

logger = logging.getLogger(__name__)
router = APIRouter()

# Query parameter descriptions
DESC_SKIP_RECORDS = "DESC_SKIP_RECORDS"
DESC_MAX_RECORDS = "DESC_MAX_RECORDS"

# Error message constants
ERR_PROVIDER_NOT_FOUND = "ERR_PROVIDER_NOT_FOUND"
ERR_LANGUAGE_NOT_FOUND = "ERR_LANGUAGE_NOT_FOUND"


def _decrypt_provider_api_key(provider: TranslationProvider) -> str:
    """Return decrypted API key for a provider."""
    try:
        encryption = EncryptionService(settings.encryption_key.get_secret_value())
        return encryption.decrypt(provider.encrypted_api_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt provider API key"
        ) from exc


def _collect_language_ids(providers: list[TranslationProvider]) -> set[int]:
    """Gather all language IDs referenced by a list of providers."""
    ids: set[int] = set()
    for provider in providers:
        ids.update(provider.input_language_ids or [])
        ids.update(provider.output_language_ids or [])
    return ids


async def _build_language_map(db: AsyncSession, providers: list[TranslationProvider]) -> dict[int, Language]:
    """Fetch languages referenced by providers and return a map by ID."""
    lang_ids = _collect_language_ids(providers)
    languages = await crud_translation.get_languages_by_ids(db, list(lang_ids))
    return {lang.id: lang for lang in languages}


def _ordered_languages(language_ids: list[int], language_map: dict[int, Language]) -> list[Language]:
    """Return languages in the same order as the IDs list."""
    return [language_map[lang_id] for lang_id in language_ids if lang_id in language_map]


def _resolve_api_key(provider: TranslationProvider, current_user: User) -> str | None:
    """Return decrypted API key for superusers or admin role users."""
    if not (current_user.is_superuser or current_user.has_role("admin")):
        return None
    return _decrypt_provider_api_key(provider)


async def _validate_language(db: AsyncSession, language_code: str, lang_type: str) -> Language:
    """Validate that a language exists and is active."""
    language = await crud_translation.get_language_by_code(db, language_code)
    if not language or not language.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"{lang_type} language '{language_code}' not available"
        )
    return language


async def _provider_to_response(
    db: AsyncSession,
    provider: TranslationProvider,
    current_user: User,
    language_map: dict[int, Language] | None = None
) -> TranslationProviderResponse:
    """Build provider response including detailed language info."""
    lang_map = language_map or await _build_language_map(db, [provider])

    input_ids = provider.input_language_ids or []
    output_ids = provider.output_language_ids or []

    return TranslationProviderResponse(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        endpoint=provider.endpoint,
        region=provider.region,
        input_language_ids=input_ids,
        output_language_ids=output_ids,
        input_languages=_ordered_languages(input_ids, lang_map),
        output_languages=_ordered_languages(output_ids, lang_map),
        api_key=_resolve_api_key(provider, current_user),
        is_active=provider.is_active,
        is_default=provider.is_default,
        configuration=provider.configuration,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


# ----------------------------- Provider Endpoints ----------------------------- #

@router.get("/providers", response_model=list[TranslationProviderResponse], status_code=status.HTTP_200_OK)
async def list_providers(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(PermissionChecker(["translations:read", "translations:translate"]))],
    skip: int = Query(0, ge=0, description="DESC_SKIP_RECORDS"),
    limit: int = Query(100, ge=1, le=100, description="DESC_MAX_RECORDS"),
):
    """List all translation providers."""
    providers = await crud_translation.get_providers(db, skip=skip, limit=limit)
    language_map = await _build_language_map(db, providers)
    return [
        await _provider_to_response(db, provider, current_user, language_map)
        for provider in providers
    ]


@router.post("/providers", response_model=TranslationProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider: TranslationProviderCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Create a new translation provider."""
    created = await crud_translation.create_provider(db, provider)
    return await _provider_to_response(db, created, current_user)


@router.get("/providers/{provider_id}", response_model=TranslationProviderResponse, status_code=status.HTTP_200_OK)
async def get_provider(
    provider_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(PermissionChecker(["translations:read", "translations:translate"]))],
):
    """Get a translation provider by ID."""
    provider = await crud_translation.get_provider(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="ERR_PROVIDER_NOT_FOUND")
    return await _provider_to_response(db, provider, current_user)


@router.put("/providers/{provider_id}", response_model=TranslationProviderResponse, status_code=status.HTTP_200_OK)
async def update_provider(
    provider_id: int,
    provider_update: TranslationProviderUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Update a translation provider."""
    provider = await crud_translation.update_provider(db, provider_id, provider_update)
    if not provider:
        raise HTTPException(status_code=404, detail="ERR_PROVIDER_NOT_FOUND")
    return await _provider_to_response(db, provider, current_user)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Delete a translation provider."""
    success = await crud_translation.delete_provider(db, provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="ERR_PROVIDER_NOT_FOUND")


@router.post("/providers/{provider_id}/default", response_model=TranslationProviderResponse, status_code=status.HTTP_200_OK)
async def set_default_provider(
    provider_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Set a provider as the default."""
    provider = await crud_translation.set_default_provider(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="ERR_PROVIDER_NOT_FOUND")
    return await _provider_to_response(db, provider, current_user)


# ----------------------------- Language Endpoints ----------------------------- #

@router.get("/languages", response_model=list[LanguageResponse], status_code=status.HTTP_200_OK)
async def list_languages(
    db: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(0, ge=0, description="DESC_SKIP_RECORDS"),
    limit: int = Query(100, ge=1, le=100, description="DESC_MAX_RECORDS"),
    only_active: bool = Query(True, description="Show only active languages"),
):
    """List all languages (public endpoint)."""
    languages = await crud_translation.get_languages(db, skip=skip, limit=limit, only_active=only_active)
    return languages


@router.post("/languages", response_model=LanguageResponse, status_code=status.HTTP_201_CREATED)
async def create_language(
    language: LanguageCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Create a new language."""
    existing = await crud_translation.get_language_by_code(db, language.code)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Language with code '{language.code}' already exists"
        )
    return await crud_translation.create_language(db, language)


@router.get("/languages/{language_id}", response_model=LanguageResponse, status_code=status.HTTP_200_OK)
async def get_language(
    language_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Get a language by ID (public endpoint)."""
    language = await crud_translation.get_language(db, language_id)
    if not language:
        raise HTTPException(status_code=404, detail="ERR_LANGUAGE_NOT_FOUND")
    return language


@router.put("/languages/{language_id}", response_model=LanguageResponse, status_code=status.HTTP_200_OK)
async def update_language(
    language_id: int,
    language_update: LanguageUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Update a language."""
    language = await crud_translation.update_language(db, language_id, language_update)
    if not language:
        raise HTTPException(status_code=404, detail="ERR_LANGUAGE_NOT_FOUND")
    return language


@router.delete("/languages/{language_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_language(
    language_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Delete a language."""
    success = await crud_translation.delete_language(db, language_id)
    if not success:
        raise HTTPException(status_code=404, detail="ERR_LANGUAGE_NOT_FOUND")


@router.patch("/languages/{language_id}/toggle", response_model=LanguageResponse, status_code=status.HTTP_200_OK)
async def toggle_language(
    language_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
    is_active: bool = Query(..., description="Set language active status"),
):
    """Toggle language active status."""
    language = await crud_translation.activate_language(db, language_id, is_active)
    if not language:
        raise HTTPException(status_code=404, detail="ERR_LANGUAGE_NOT_FOUND")
    return language


# ----------------------------- Translation Endpoints ----------------------------- #

@router.post("/translate", response_model=TranslationResponse, status_code=status.HTTP_200_OK)
async def translate_text(
    request: TranslationRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[User, Depends(PermissionChecker(["translations:translate"]))],
):
    """Translate text using the configured provider."""
    # Validate languages
    source_lang = await _validate_language(db, request.source_language_code, "Source")
    target_lang = await _validate_language(db, request.target_language_code, "Target")

    # Get translation service
    service = await TranslationServiceFactory.get_service(db, request.provider_id)

    # Translate
    translated_text = await service.translate(
        text=request.text,
        source_language=request.source_language_code,
        target_language=request.target_language_code
    )

    # Get provider for saving to history
    provider = await crud_translation.get_default_provider(db) if not request.provider_id else await crud_translation.get_provider(db, request.provider_id)

    # Save to history
    translation_record = await crud_translation.create_translation(
        db,
        TranslationCreate(
            provider_id=provider.id,
            source_language_id=source_lang.id,
            target_language_id=target_lang.id,
            source_text=request.text,
            translated_text=translated_text,
            character_count=len(request.text),
            user_id=current_user.id
        )
    )

    return translation_record


@router.post("/translate/stream", status_code=status.HTTP_200_OK)
async def translate_text_stream(
    request: TranslationRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[User, Depends(PermissionChecker(["translations:translate"]))],
):
    """Translate text using the configured provider (streaming response)."""
    # Validate languages
    source_lang = await _validate_language(db, request.source_language_code, "Source")
    target_lang = await _validate_language(db, request.target_language_code, "Target")

    # Get translation service
    service = await TranslationServiceFactory.get_service(db, request.provider_id)
    provider = (
        await crud_translation.get_provider(db, request.provider_id)
        if request.provider_id
        else await crud_translation.get_default_provider(db)
    )

    translation_gen = service.translate_stream(
        text=request.text,
        source_language=request.source_language_code,
        target_language=request.target_language_code
    )

    try:
        first_chunk = await anext(translation_gen)
    except StopAsyncIteration:
        raise HTTPException(
            status_code=502,
            detail="Hugging Face translation failed: empty response"
        )
    except HTTPException:
        # Surface provider errors before the response starts streaming
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Hugging Face translation failed: {exc}"
        ) from exc

    async def streamer():
        translated_parts: list[str] = [first_chunk]
        success = False
        try:
            yield first_chunk
            async for chunk in translation_gen:
                translated_parts.append(chunk)
                yield chunk
            success = True
        except Exception as exc:  # noqa: BLE001
            logger.error("Streaming translation failed after start: %s", exc)
        finally:
            # Persist translation history after streaming finishes
            if success and provider:
                full_translation = "".join(translated_parts).strip()
                if full_translation:
                    await crud_translation.create_translation(
                        db,
                        TranslationCreate(
                            provider_id=provider.id,
                            source_language_id=source_lang.id,
                            target_language_id=target_lang.id,
                            source_text=request.text,
                            translated_text=full_translation,
                            character_count=len(request.text),
                            user_id=current_user.id
                        )
                    )

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")


@router.get("/history", response_model=list[TranslationHistoryResponse], status_code=status.HTTP_200_OK)
async def get_my_translation_history(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = Query(0, ge=0, description="DESC_SKIP_RECORDS"),
    limit: int = Query(100, ge=1, le=100, description="DESC_MAX_RECORDS"),
):
    """Get translation history for the current user."""
    translations = await crud_translation.get_user_translations(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return translations


@router.get("/history/all", response_model=list[TranslationHistoryResponse], status_code=status.HTTP_200_OK)
async def get_all_translation_history(
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["translations:read"]))],
    skip: int = Query(0, ge=0, description="DESC_SKIP_RECORDS"),
    limit: int = Query(100, ge=1, le=100, description="DESC_MAX_RECORDS"),
):
    """Get all translation history (admin only)."""
    translations = await crud_translation.get_translations(db, skip=skip, limit=limit)
    return translations


@router.post("/translate/document", response_model=DocumentTranslationResponse, status_code=status.HTTP_200_OK)
async def translate_document(
    file: Annotated[UploadFile, File(description="Document file to translate (TXT or DOCX)")],
    source_language_code: Annotated[str, Query(description="Source language ISO code")],
    target_language_code: Annotated[str, Query(description="Target language ISO code")],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[User, Depends(PermissionChecker(["translations:translate"]))],
    provider_id: Annotated[int | None, Query(description="Optional provider ID")] = None,
    download: Annotated[bool, Query(description="Return translated file for download instead of base64", alias="as_file")] = False,
):
    """Translate a document file and return it in base64 format.

    Supports TXT and DOCX files. The document content is extracted, translated,
    and returned as a base64-encoded file maintaining the original format.
    """
    # Validate languages
    source_lang = await _validate_language(db, source_language_code, "Source")
    target_lang = await _validate_language(db, target_language_code, "Target")

    # Create document service
    document_service = DocumentTranslationService(session=db, provider_id=provider_id)

    # Translate document
    try:
        translated_base64, character_count = await document_service.translate_document(
            file=file,
            source_language_code=source_language_code,
            target_language_code=target_language_code
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error translating document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during translation")

    # Generate translated filename
    original_filename = file.filename or "document"
    name_parts = original_filename.rsplit(".", 1)
    if len(name_parts) == 2:
        translated_filename = f"{name_parts[0]}_translated.{name_parts[1]}"
    else:
        translated_filename = f"{original_filename}_translated"

    if download:
        try:
            decoded_content = base64.b64decode(translated_base64)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error decoding translated document base64: {e}")
            raise HTTPException(status_code=500, detail="Failed to decode translated document")

        media_type = "text/plain"
        if original_filename.lower().endswith(".docx"):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        return StreamingResponse(
            io.BytesIO(decoded_content),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{translated_filename}"'}
        )

    return DocumentTranslationResponse(
        filename=original_filename,
        translated_filename=translated_filename,
        file_base64=translated_base64,
        source_language=source_lang,
        target_language=target_lang,
        character_count=character_count
    )


# ----------------------------- Grammar Checker Endpoints ----------------------------- #

@router.post("/grammar-check", response_model=GrammarCheckResponse, status_code=status.HTTP_200_OK)
async def check_grammar(
    request: GrammarCheckRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[User, Depends(PermissionChecker(["translations:translate"]))],
):
    """Check grammar and spelling in text using the configured provider."""
    # Validate language
    language = await _validate_language(db, request.language_code, "Language")

    # Get grammar service
    service = await GrammarServiceFactory.get_service(db, request.provider_id)

    # Check grammar
    corrected_text, suggestions, has_errors = await service.check_grammar(
        text=request.text,
        language=request.language_code
    )

    return GrammarCheckResponse(
        corrected_text=corrected_text,
        suggestions=suggestions,
        has_errors=has_errors,
        language=language
    )


# ----------------------------- Post-Editing Endpoints ----------------------------- #

@router.post("/post-edit", response_model=PostEditResponse, status_code=status.HTTP_200_OK)
async def post_edit_text(
    request: PostEditRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[User, Depends(PermissionChecker(["translations:translate"]))],
):
    """Post-edit machine translation using SalamandraTA."""
    source_lang = await _validate_language(db, request.source_language_code, "Source")
    target_lang = await _validate_language(db, request.target_language_code, "Target")

    service = await PostEditingServiceFactory.get_service(db, request.provider_id)

    edited_text = await service.post_edit(
        source_text=request.source_text,
        mt_text=request.mt_text,
        source_language=request.source_language_code,
        target_language=request.target_language_code,
    )

    return PostEditResponse(
        edited_text=edited_text,
        source_language=source_lang,
        target_language=target_lang,
    )
