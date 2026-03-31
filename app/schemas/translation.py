"""Translation schemas for request/response validation."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, SecretStr, field_validator

# Field description constants
DESC_PROVIDER_OPTIONAL = "DESC_PROVIDER_OPTIONAL"


# ----------------------------- Provider Schemas ----------------------------- #

class TranslationProviderBase(BaseModel):
    """Base schema for translation provider."""

    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    provider_type: str = Field(
        ...,
        pattern="^(azure|google|deepl|openai|huggingface)$",
        description="Provider type (azure, google, deepl, openai, huggingface)"
    )
    endpoint: str | None = Field(
        None,
        max_length=500,
        description="API endpoint URL (required for Azure and Hugging Face, optional for OpenAI)"
    )
    region: str | None = Field(None, max_length=50, description="Service region (required for Azure, optional for OpenAI)")
    input_language_ids: list[int] = Field(..., description="Language IDs accepted as input/source")
    output_language_ids: list[int] = Field(..., description="Language IDs supported as output/target")


class TranslationProviderCreate(TranslationProviderBase):
    """Schema for creating a translation provider."""

    api_key: SecretStr = Field(..., description="API key (will be encrypted)")
    configuration: dict | None = Field(None, description="Additional configuration")
    is_active: bool = Field(True, description="Whether the provider is active")
    is_default: bool = Field(False, description="Whether this is the default provider")

    @field_validator("input_language_ids", "output_language_ids")
    @classmethod
    def validate_languages(cls, v: list[int]) -> list[int]:
        """Ensure at least one language ID is provided."""
        if not v:
            raise ValueError("At least one language ID is required")
        return v


class TranslationProviderUpdate(BaseModel):
    """Schema for updating a translation provider."""

    name: str | None = Field(None, min_length=1, max_length=100)
    endpoint: str | None = Field(None, max_length=500)
    api_key: SecretStr | None = Field(None, description="API key (will be re-encrypted if provided)")
    region: str | None = Field(None, max_length=50)
    configuration: dict | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    input_language_ids: list[int] | None = Field(None, description="Language IDs accepted as input/source")
    output_language_ids: list[int] | None = Field(None, description="Language IDs supported as output/target")

    @field_validator("input_language_ids", "output_language_ids")
    @classmethod
    def validate_optional_languages(cls, v: list[int] | None) -> list[int] | None:
        """Ensure provided language lists are not empty when supplied."""
        if v is not None and not v:
            raise ValueError("Language ID list cannot be empty")
        return v


class TranslationProviderResponse(TranslationProviderBase):
    """Schema for translation provider response."""

    id: int
    api_key: str | None = Field(
        None,
        description="Decrypted API key (visible only to superusers)"
    )
    is_active: bool
    is_default: bool
    configuration: dict | None
    input_languages: list[LanguageResponse] = Field(default_factory=list, description="Detailed input/source languages")
    output_languages: list[LanguageResponse] = Field(default_factory=list, description="Detailed output/target languages")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ----------------------------- Language Schemas ----------------------------- #

class LanguageBase(BaseModel):
    """Base schema for language."""

    code: str = Field(..., min_length=2, max_length=10, description="ISO 639-1 language code")
    name: str = Field(..., min_length=1, max_length=100, description="Language name in English")
    native_name: str = Field(..., min_length=1, max_length=100, description="Language name in native script")


class LanguageCreate(LanguageBase):
    """Schema for creating a language."""

    sort_order: int = Field(default=0, ge=0, description="Display sort order")


class LanguageUpdate(BaseModel):
    """Schema for updating a language."""

    name: str | None = Field(None, min_length=1, max_length=100)
    native_name: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)


class LanguageResponse(LanguageBase):
    """Schema for language response."""

    id: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ----------------------------- Translation Schemas ----------------------------- #

class TranslationRequest(BaseModel):
    """Schema for translation request."""

    source_language_code: str = Field(..., max_length=10, description="Source language code")
    target_language_code: str = Field(..., max_length=10, description="Target language code")
    text: str = Field(..., min_length=1, max_length=25000, description="Text to translate")
    provider_id: int | None = Field(None, description="DESC_PROVIDER_OPTIONAL")

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError('Text cannot be empty or whitespace only')
        return v


class TranslationCreate(BaseModel):
    """Schema for creating a translation record (internal use)."""

    provider_id: int
    source_language_id: int
    target_language_id: int
    source_text: str
    translated_text: str
    character_count: int
    user_id: int


class TranslationResponse(BaseModel):
    """Schema for translation response."""

    translated_text: str
    source_language: LanguageResponse
    target_language: LanguageResponse
    character_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TranslationHistoryResponse(TranslationResponse):
    """Schema for translation history response (includes more details)."""

    id: int
    source_text: str
    user_id: int
    provider_id: int

    model_config = {"from_attributes": True}


# ----------------------------- Grammar Checker Schemas ----------------------------- #

class GrammarCheckRequest(BaseModel):
    """Schema for grammar check request."""

    text: str = Field(..., min_length=1, max_length=25000, description="Text to check grammar")
    language_code: str = Field(..., max_length=10, description="Language code for the text")
    provider_id: int | None = Field(None, description="DESC_PROVIDER_OPTIONAL")

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError('Text cannot be empty or whitespace only')
        return v


class GrammarSuggestion(BaseModel):
    """Schema for a grammar correction suggestion."""

    original: str = Field(..., description="Original text with error")
    correction: str = Field(..., description="Suggested correction")
    explanation: str = Field(..., description="Explanation of the error")
    position: int | None = Field(None, description="Position in the text (character index)")


class GrammarCheckResponse(BaseModel):
    """Schema for grammar check response."""

    corrected_text: str = Field(..., description="Fully corrected text")
    suggestions: list[GrammarSuggestion] = Field(default_factory=list, description="List of grammar suggestions")
    has_errors: bool = Field(..., description="Whether errors were found")
    language: LanguageResponse
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}


# ----------------------------- Post-Editing Schemas ----------------------------- #

class PostEditRequest(BaseModel):
    """Schema for MT post-editing requests.

    Follows the SalamandraTA post-editing task format:
        Please fix any mistakes in the following {source}-{target} machine translation
        or keep it unedited if it's correct.
        Source: {source_sentence}
        MT: {machine_translation}
        Corrected:
    """

    source_text: str = Field(..., min_length=1, max_length=25000, description="Original source text")
    mt_text: str = Field(..., min_length=1, max_length=25000, description="Machine translation to post-edit")
    source_language_code: str = Field(..., max_length=10, description="Source language code")
    target_language_code: str = Field(..., max_length=10, description="Target language code")
    provider_id: int | None = Field(None, description="DESC_PROVIDER_OPTIONAL")

    @field_validator("source_text", "mt_text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v


class PostEditResponse(BaseModel):
    """Schema for post-editing responses."""

    edited_text: str = Field(..., description="Post-edited machine translation")
    source_language: LanguageResponse
    target_language: LanguageResponse
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}


# ----------------------------- Document Translation Schemas ----------------------------- #

class DocumentTranslationResponse(BaseModel):
    """Schema for document translation response."""

    filename: str = Field(..., description="Original filename")
    translated_filename: str = Field(..., description="Translated document filename")
    file_base64: str = Field(..., description="Translated document encoded in base64")
    source_language: LanguageResponse
    target_language: LanguageResponse
    character_count: int = Field(..., description="Total characters translated")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}
