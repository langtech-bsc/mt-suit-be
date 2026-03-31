"""Post-editing service using Hugging Face Inference Endpoints."""

import asyncio
from typing import Any

import httpx
from fastapi import HTTPException
from huggingface_hub import InferenceClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import translation as crud_translation


class HuggingFacePostEditingService:
    """Hugging Face Inference Endpoint post-editing service."""

    # Constants for repeated strings
    EMPTY_RESPONSE_ERROR = "Empty response from post-editing service"
    CORRECTED_LABEL = "corrected:"

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None
    ):
        """Initialize Hugging Face Post-Editing Service using InferenceClient."""
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model or "BSC-LT/salamandraTA-2b-instruct"
        self.parameters = {
            "max_new_tokens": 512,
            "do_sample": False,  # Greedy decoding as recommended by the manual
        }
        # Default chunk size to avoid overwhelming the endpoint
        self.chunk_chars = 800
        if parameters:
            safe_params = dict(parameters)
            # Allow overriding chunk size without sending it to the endpoint
            self.chunk_chars = safe_params.pop("chunk_chars", self.chunk_chars)
            safe_params.pop("stop_sequences", None)
            self.parameters.update(safe_params)

        self._auth_headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        self.client = InferenceClient(model=self.endpoint, token=api_key)

    def _clean_generation_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Remove unsupported or empty parameters before calling HF."""
        unsupported_params = {'stop_sequences', 'details', 'return_full_text', 'stop'}
        return {
            k: v for k, v in params.items()
            if v is not None and k not in unsupported_params
        }

    def _extract_generated_text(self, data: Any) -> str:
        """Normalize HF responses into a plain string."""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            data = data[0]
        if isinstance(data, dict):
            for key in ("generated_text", "translation_text"):
                if key in data:
                    return str(data[key])
        if isinstance(data, str):
            return data
        return ""

    def _generate_via_http(self, prompt: str, params: dict[str, Any]) -> str:
        """Call the HF endpoint via raw HTTP to handle varied payloads."""
        payload: dict[str, Any] = {"inputs": prompt}
        clean_params = self._clean_generation_params(params)
        if clean_params:
            payload["parameters"] = clean_params

        response = httpx.post(
            self.endpoint,
            json=payload,
            headers=self._auth_headers,
            timeout=60,
        )
        response.raise_for_status()

        text = self._extract_generated_text(response.json())
        if not text:
            raise ValueError(self.EMPTY_RESPONSE_ERROR)
        return text

    @staticmethod
    def _remove_markers(text: str) -> str:
        """Remove stray markers and labels."""
        markers = (
            "<START_OF_EDIT>",
            "</START_OF_EDIT>",
            "<START_OF_CORRECTION>",
            "</START_OF_CORRECTION>",
            "```",
        )
        for marker in markers:
            text = text.replace(marker, "")
        if "<|im_end|>" in text:
            text = text.split("<|im_end|>", 1)[0]
        text = text.replace("<|im_start|>", "").replace("<|im_end|>", "")
        return text

    @classmethod
    def _extract_corrected_portion(cls, text: str) -> str:
        """Extract text after the last 'Corrected:' marker if present."""
        lower_text = text.lower()
        if cls.CORRECTED_LABEL in lower_text:
            idx = lower_text.rfind(cls.CORRECTED_LABEL) + len(cls.CORRECTED_LABEL)
            return text[idx:]
        return text

    @classmethod
    def _is_prompt_echo(cls, line: str) -> bool:
        """Check if line is an echoed prompt instruction."""
        prompt_phrases = (
            "please fix any mistakes",
            "or keep it unedited if it's correct",
            "machine translation",
        )
        lower = line.lower().strip()
        return (
            any(phrase in lower for phrase in prompt_phrases)
            or lower.startswith(("source:", "mt:", cls.CORRECTED_LABEL))
        )

    @classmethod
    def _clean_output(cls, text: str, original: str | None = None) -> str:
        """Remove any stray markers or labels and trim."""
        text = cls._remove_markers(text)
        text = cls._extract_corrected_portion(text)

        lines = text.splitlines()
        cleaned_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if cls._is_prompt_echo(stripped):
                continue
            if original and stripped.strip() == original.strip():
                continue

            # Remove role labels
            lower = stripped.lower()
            for role in ("user:", "assistant:", "system:"):
                if lower.startswith(role):
                    stripped = stripped[len(role):].strip()
                    break
            if stripped:
                cleaned_lines.append(stripped)

        return "\n".join(cleaned_lines).strip()

    def _chunk_text(self, text: str) -> list[str]:
        """Split long text into manageable chunks while preserving paragraphs."""
        chunks: list[str] = []
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                chunks.append("")
                continue

            current = para
            while len(current) > self.chunk_chars:
                break_idx = current.rfind(" ", 0, self.chunk_chars)
                if break_idx == -1:
                    break_idx = self.chunk_chars
                chunks.append(current[:break_idx].strip())
                current = current[break_idx:].strip()
            if current:
                chunks.append(current)
        return chunks

    @staticmethod
    def _wrap_chatml(content: str) -> str:
        """Wrap prompt content in ChatML format."""
        content = content.rstrip()
        return f"<|im_start|>user\n{content}\n<|im_end|>\n<|im_start|>assistant\n"

    def _build_prompt(
        self,
        source_chunk: str,
        mt_chunk: str,
        source_language_name: str,
        target_language_name: str,
    ) -> str:
        """Build MT post-editing prompt using SalamandraTA recommended format.

        From the manual:
            Please fix any mistakes in the following {source}-{target} machine translation
            or keep it unedited if it's correct.
            Source: {source_sentence}
            MT: {machine_translation}
            Corrected:
        """
        base_prompt = (
            f"Please fix any mistakes in the following {source_language_name}-{target_language_name} "
            f"machine translation or keep it unedited if it's correct.\n"
            f"Source: {source_chunk}\n"
            f"MT: {mt_chunk}\n"
            "Corrected:"
        )
        return self._wrap_chatml(base_prompt)

    def _build_params(self, chunk: str) -> dict[str, Any]:
        """Build generation parameters."""
        params = dict(self.parameters)
        configured_max = params.get("max_new_tokens", 512)
        max_new = max(80, min(configured_max, int(len(chunk) * 1.1) + 80))
        params["max_new_tokens"] = max_new
        return params

    def _call_hf_with_fallback(self, prompt: str, params: dict[str, Any]) -> str:
        """Call HF endpoint with HTTP fallback to client library."""
        clean_params = self._clean_generation_params(params)
        try:
            return self._generate_via_http(prompt, clean_params)
        except Exception as http_exc:
            try:
                result = self.client.text_generation(prompt, **clean_params)
                extracted = self._extract_generated_text(result)
                if not extracted:
                    raise ValueError(self.EMPTY_RESPONSE_ERROR) from http_exc
                return extracted
            except KeyError as key_exc:
                raise ValueError(
                    "Unexpected response format from post-editing service"
                ) from key_exc

    async def _process_chunk(
        self,
        source_chunk: str,
        mt_chunk: str,
        source_language_name: str,
        target_language_name: str,
    ) -> str:
        """Process a single paired source/MT chunk."""
        if mt_chunk == "":
            return ""

        prompt = self._build_prompt(source_chunk, mt_chunk, source_language_name, target_language_name)
        params = self._build_params(mt_chunk)

        response = await asyncio.to_thread(
            self._call_hf_with_fallback, prompt, params
        )

        if not response:
            raise HTTPException(
                status_code=500,
                detail=self.EMPTY_RESPONSE_ERROR
            )

        cleaned = self._clean_output(response, original=mt_chunk)
        return cleaned or mt_chunk

    async def post_edit(
        self,
        source_text: str,
        mt_text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Post-edit machine translation using Hugging Face Inference Endpoint.

        Args:
            source_text: Original source sentence/text
            mt_text: Machine translation to be post-edited
            source_language: Source language code
            target_language: Target language code
        """
        language_names = {
            "en": "English", "es": "Spanish", "ca": "Catalan", "gl": "Galician",
            "pt": "Portuguese", "fr": "French", "de": "German", "it": "Italian",
            "eu": "Basque", "an": "Aragonese", "ast": "Asturian", "bg": "Bulgarian",
            "hr": "Croatian", "cs": "Czech", "da": "Danish", "nl": "Dutch",
            "et": "Estonian", "fi": "Finnish", "el": "Greek", "hu": "Hungarian",
            "ga": "Irish", "lv": "Latvian", "lt": "Lithuanian", "mt": "Maltese",
            "nb": "Norwegian Bokmål", "nn": "Norwegian Nynorsk", "oc": "Occitan",
            "pl": "Polish", "ro": "Romanian", "ru": "Russian", "sr": "Serbian",
            "sk": "Slovak", "sl": "Slovenian", "sv": "Swedish", "uk": "Ukrainian",
            "cy": "Welsh",
        }

        source_language_name = language_names.get(source_language.lower(), source_language)
        target_language_name = language_names.get(target_language.lower(), target_language)

        try:
            source_chunks = self._chunk_text(source_text.strip())
            mt_chunks = self._chunk_text(mt_text.strip())

            # Pair source and MT chunks; pad with empty string if lengths differ
            max_len = max(len(source_chunks), len(mt_chunks))
            edited_parts: list[str] = []
            for i in range(max_len):
                s_chunk = source_chunks[i] if i < len(source_chunks) else ""
                m_chunk = mt_chunks[i] if i < len(mt_chunks) else ""
                processed = await self._process_chunk(
                    s_chunk, m_chunk, source_language_name, target_language_name
                )
                edited_parts.append(processed)

            return "\n\n".join(edited_parts).strip()

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Post-editing failed: {str(e)}"
            ) from e


class PostEditingServiceFactory:
    """Factory for creating post-editing service instances."""

    @staticmethod
    async def get_service(
        db: AsyncSession,
        provider_id: int | None = None
    ) -> HuggingFacePostEditingService:
        """Get post-editing service instance (Hugging Face only)."""
        if provider_id:
            provider = await crud_translation.get_provider(db, provider_id)
            if not provider:
                raise HTTPException(
                    status_code=404,
                    detail="Translation provider not found"
                )
        else:
            provider = await crud_translation.get_default_provider(db)
            if not provider:
                raise HTTPException(
                    status_code=500,
                    detail="No default translation provider configured"
                )

        if not provider.is_active:
            raise HTTPException(
                status_code=400,
                detail="Translation provider is not active"
            )

        api_key = await crud_translation.get_decrypted_api_key(db, provider.id)

        if provider.provider_type != "huggingface":
            raise HTTPException(
                status_code=400,
                detail="Only Hugging Face provider is supported for post-editing"
            )

        config = provider.configuration or {}
        model = config.get("model")
        parameters = config.get("parameters") if isinstance(config.get("parameters"), dict) else None

        if not provider.endpoint:
            raise HTTPException(
                status_code=500,
                detail="Hugging Face provider requires an endpoint URL"
            )

        return HuggingFacePostEditingService(
            api_key=api_key,
            endpoint=provider.endpoint,
            model=model,
            parameters=parameters
        )
