"""Document translation service for TXT and DOCX files."""

import base64
import io
import logging
from typing import BinaryIO

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.translation_service import TranslationServiceFactory

logger = logging.getLogger(__name__)

# File type constants
EXT_TXT = ".txt"
EXT_DOCX = ".docx"

# Supported file extensions
SUPPORTED_EXTENSIONS = {EXT_TXT, EXT_DOCX}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class DocumentTranslationService:
    """Service for translating documents while preserving format."""

    def __init__(self, session: AsyncSession, provider_id: int | None = None):
        """Initialize the document translation service.

        Args:
            session: Database session for provider lookup
            provider_id: Optional specific provider to use
        """
        self.session = session
        self.provider_id = provider_id

    async def translate_document(
        self,
        file: UploadFile,
        source_language_code: str,
        target_language_code: str,
    ) -> tuple[str, int]:
        """Translate a document and return it as base64.

        Args:
            file: The uploaded file
            source_language_code: Source language ISO code
            target_language_code: Target language ISO code

        Returns:
            Tuple of (base64 encoded translated document, character count)

        Raises:
            HTTPException: If file type is unsupported or processing fails
        """
        # Validate file extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        file_ext = self._get_file_extension(file.filename)
        if file_ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # Read file content
        try:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024} MB"
                )
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise HTTPException(status_code=400, detail="Error reading file")

        # Extract text based on file type
        try:
            if file_ext == EXT_TXT:
                text = self._extract_text_from_txt(content)
            elif file_ext == EXT_DOCX:
                text = self._extract_text_from_docx(content)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")

            logger.info(f"Extracted text length: {len(text)} characters")
            logger.debug(f"First 100 chars of extracted text: {text[:100]}")
        except Exception as e:
            logger.error(f"Error extracting text from {file_ext}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Error extracting text from document: {str(e)}"
            )

        if not text.strip():
            raise HTTPException(status_code=400, detail="Document contains no text to translate")

        # Store original character count for accurate reporting
        original_char_count = len(text)

        # Get translation service
        try:
            translation_service = await TranslationServiceFactory.get_service(
                db=self.session,
                provider_id=self.provider_id
            )
        except Exception as e:
            logger.error(f"Error creating translation service: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Translate the text
        try:
            logger.info(f"Starting translation from {source_language_code} to {target_language_code}")
            translated_text = await translation_service.translate(
                text=text,
                source_language=source_language_code,
                target_language=target_language_code
            )
            logger.info(f"Translation completed. Result length: {len(translated_text)} characters")
            logger.debug(f"First 100 chars of translation: {translated_text[:100]}")
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

        # Reconstruct document with translated text
        try:
            if file_ext == EXT_TXT:
                translated_content = self._create_txt(translated_text)
            elif file_ext == EXT_DOCX:
                translated_content = self._create_docx(translated_text)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
        except Exception as e:
            logger.error(f"Error creating translated document: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creating translated document: {str(e)}"
            )

        # Encode to base64
        base64_content = base64.b64encode(translated_content).decode('utf-8')
        return base64_content, original_char_count

    def _get_file_extension(self, filename: str) -> str:
        """Get lowercase file extension with leading dot."""
        if "." not in filename:
            return ""
        ext = filename.lower().rsplit(".", 1)[-1]
        return f".{ext}"

    def _extract_text_from_txt(self, content: bytes) -> str:
        """Extract text from TXT file."""
        try:
            # Try UTF-8 first, then fallback to latin-1
            return content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return content.decode('latin-1')
            except Exception as e:
                raise ValueError(f"Unable to decode text file: {e}")

    def _extract_text_from_docx(self, content: bytes) -> str:
        """Extract text from DOCX file."""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("python-docx is required for DOCX support. Install it with: poetry add python-docx")

        try:
            doc = Document(io.BytesIO(content))
            # Extract text from all paragraphs
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise ValueError(f"Error reading DOCX file: {e}")

    def _create_txt(self, text: str) -> bytes:
        """Create TXT file from text."""
        return text.encode('utf-8')

    def _create_docx(self, text: str) -> bytes:
        """Create DOCX file from text."""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("python-docx is required for DOCX support")

        doc = Document()
        # Split text into paragraphs and add them to the document
        paragraphs = text.split("\n\n")
        for para_text in paragraphs:
            if para_text.strip():
                doc.add_paragraph(para_text.strip())

        # Save to bytes
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream.read()
