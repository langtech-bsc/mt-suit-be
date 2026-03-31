"""Translation models definition."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class TranslationProvider(Base):
    """Translation provider model (e.g., Azure Translator, Google Translate, Hugging Face)."""

    __tablename__ = "translation_providers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    provider_type = Column(String(50), nullable=False)  # azure, google, deepl, openai, huggingface
    endpoint = Column(String(500), nullable=True)  # Optional for OpenAI
    encrypted_api_key = Column(Text, nullable=False)  # Encrypted API key
    region = Column(String(50), nullable=True)  # Optional for OpenAI
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    configuration = Column(JSON, nullable=True)  # Additional configuration
    input_language_ids = Column(JSON, default=list, nullable=False)  # Allowed source language IDs
    output_language_ids = Column(JSON, default=list, nullable=False)  # Allowed target language IDs
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    translations = relationship("Translation", back_populates="provider")

    def __repr__(self) -> str:
        return f"<TranslationProvider(id={self.id}, name={self.name}, type={self.provider_type}, active={self.is_active})>"


class Language(Base):
    """Language model for translation."""

    __tablename__ = "languages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # ISO 639-1 code (en, es, etc.)
    name = Column(String(100), nullable=False)  # English name
    native_name = Column(String(100), nullable=False)  # Native name (e.g., "Español")
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    source_translations = relationship(
        "Translation",
        foreign_keys="Translation.source_language_id",
        back_populates="source_language"
    )
    target_translations = relationship(
        "Translation",
        foreign_keys="Translation.target_language_id",
        back_populates="target_language"
    )

    def __repr__(self) -> str:
        return f"<Language(id={self.id}, code={self.code}, name={self.name}, active={self.is_active})>"


class Translation(Base):
    """Translation history model."""

    __tablename__ = "translations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    provider_id = Column(BigInteger, ForeignKey("translation_providers.id", ondelete="CASCADE"), nullable=False)
    source_language_id = Column(BigInteger, ForeignKey("languages.id", ondelete="CASCADE"), nullable=False)
    target_language_id = Column(BigInteger, ForeignKey("languages.id", ondelete="CASCADE"), nullable=False)
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    character_count = Column(Integer, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    provider = relationship("TranslationProvider", back_populates="translations")
    source_language = relationship("Language", foreign_keys=[source_language_id], back_populates="source_translations")
    target_language = relationship("Language", foreign_keys=[target_language_id], back_populates="target_translations")
    user = relationship("User", back_populates="translations")

    def __repr__(self) -> str:
        return f"<Translation(id={self.id}, from={self.source_language.code if self.source_language else 'N/A'}, to={self.target_language.code if self.target_language else 'N/A'}, chars={self.character_count})>"
