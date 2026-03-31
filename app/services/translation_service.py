"""Translation service using Hugging Face Inference Endpoints only."""

import asyncio
import logging
import re
import threading
from typing import Any, AsyncGenerator

import httpx
from fastapi import HTTPException
from huggingface_hub import InferenceClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import translation as crud_translation

logger = logging.getLogger(__name__)


class StreamingNotSupportedError(RuntimeError):
    """Raised when the configured HF endpoint does not support streaming."""


class HuggingFaceTranslationService:
    """Hugging Face Inference Endpoint translation service."""

    # Constants for repeated strings
    OUTPUT_LABEL = "output:"
    LANGUAGE_THAT = "language that"
    SPOKEN_BY = "spoken by"

    # Educational content markers
    THE_VERB = "the verb"
    IN_THIS_LESSON = "in this lesson"
    WE_WILL_LOOK_AT = "we will look at"
    LETS_GET_STARTED = "let's get started"
    WELL_ALSO_LEARN = "we'll also learn"
    DEPENDING_ON_HOW = "depending on how you use"
    MANY_MEANINGS = "it can have many meanings"
    PAST_TENSE_FORM = "past tense form"
    USED_IN_A_LOT = "is used in a lot of"

    # Metadata labels
    TAGS_LABEL = "tags:"
    TRANSLATE_FROM = "translate from"
    USING_OUR = "using our"
    ONLINE_TRANSLATOR = "online translator"
    LINGUA_FRANCA = "lingua franca"
    GERMANIC_LANGUAGE = "germanic language"
    ROMANCE_LANGUAGE = "romance language"
    FIRST_SPOKEN = "first spoken"

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None
    ):
        """Initialize Hugging Face Translation Service using InferenceClient."""
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model or "BSC-LT/salamandraTA-2b-instruct"
        self.parameters = {
            # Optimized for maximum speed and low latency
            # Only using parameters that are universally supported
            # Keep generation short to avoid HF endpoint disconnects on long requests
            "max_new_tokens": 512,
            "do_sample": False,  # Greedy decoding is fastest
        }
        # SalamandraTA supports 8192 tokens, but HF endpoints have time limits
        # Use smaller chunks to reduce request time and avoid disconnects
        self.chunk_chars = 1000
        # Cache the last known streaming capability to avoid repeated 400s
        self.streaming_available: bool | None = None
        self._auth_headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        if parameters:
            safe_params = dict(parameters)
            # Allow overriding chunk size without sending it to the endpoint
            self.chunk_chars = safe_params.pop("chunk_chars", self.chunk_chars)
            self.parameters.update(safe_params)
        # InferenceClient accepts an endpoint URL as the "model" argument
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
        """Call the HF endpoint without the hub client's default extras."""
        payload: dict[str, Any] = {"inputs": prompt}
        clean_params = self._clean_generation_params(params)
        if clean_params:
            payload["parameters"] = clean_params

        response = httpx.post(
            self.endpoint,
            json=payload,
            headers=self._auth_headers,
            timeout=180,  # 3 minutes for longer texts
        )
        response.raise_for_status()
        text = self._extract_generated_text(response.json())
        if not text:
            raise ValueError("Empty response from Hugging Face translation service")
        return text

    @staticmethod
    def _remove_translation_markers(text: str) -> str:
        """Remove translation markers and code fences."""
        markers = (
            "<START_OF_TRANSLATION>",
            "</START_OF_TRANSLATION>",
            "START_OF_TRANSLATION",
        )
        for marker in markers:
            text = text.replace(marker, "")
        text = text.replace("```", "")
        return text

    @staticmethod
    def _strip_chatml(text: str) -> str:
        """Remove ChatML markers and role labels from output."""
        if "<|im_end|>" in text:
            text = text.split("<|im_end|>", 1)[0]
        text = text.replace("<|im_start|>", "").replace("<|im_end|>", "")

        cleaned_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if lower in {"user", "assistant", "system"}:
                continue
            for role in ("user:", "assistant:", "system:"):
                if lower.startswith(role):
                    stripped = stripped[len(role):].strip()
                    break
            if stripped:
                cleaned_lines.append(stripped)
        return "\n".join(cleaned_lines).strip()

    @staticmethod
    def _wrap_chatml(content: str) -> str:
        """Wrap prompt content in ChatML format."""
        content = content.rstrip()
        return f"<|im_start|>user\n{content}\n<|im_end|>\n<|im_start|>assistant\n"

    @staticmethod
    def _extract_target_language_section(
        text: str,
        target_lower: str,
        source_lower: str
    ) -> str:
        """Extract only the target language section from multi-language output."""
        if target_lower:
            target_markers = [
                rf"###\s*{re.escape(target_lower)}\b",
                rf"{re.escape(target_lower)} translation:",
                rf"{re.escape(target_lower)}:",
            ]
            for pattern in target_markers:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    text = re.split(pattern, text, flags=re.IGNORECASE)[-1].strip()
                    break

        if source_lower and re.search(rf"###\s*{re.escape(source_lower)}\b", text, flags=re.IGNORECASE):
            parts = re.split(rf"###\s*{re.escape(source_lower)}\b", text, flags=re.IGNORECASE)
            if len(parts) > 1 and not target_lower:
                text = parts[-1].strip()

        return text

    @staticmethod
    def _remove_prompt_echoes(text: str) -> str:
        """Remove echoed prompt patterns."""
        # First, try to extract content after "X translation:" pattern (e.g., "English translation:")
        # This handles cases where the model echoes the entire prompt
        translation_label_match = re.search(
            r'\b(english|spanish|french|german|catalan|portuguese|italian|galician|basque)\s+translation\s*:',
            text,
            re.IGNORECASE
        )
        if translation_label_match:
            # Extract everything after the translation label
            after_label = text[translation_label_match.end():].strip()
            if after_label:
                text = after_label

        # Handle simple prompt format: "English:" or "Spanish:" at start of line
        simple_label_match = re.search(
            r'^(english|spanish|french|german|catalan|portuguese|italian|galician|basque)\s*:',
            text,
            re.IGNORECASE | re.MULTILINE
        )
        if simple_label_match:
            after_label = text[simple_label_match.end():].strip()
            if after_label:
                # Check if there's another language label (echoed source)
                # e.g., "Spanish: hola\nEnglish: hello" -> extract "hello"
                lines = after_label.split('\n')
                for i, line in enumerate(lines):
                    target_match = re.match(
                        r'^(english|spanish|french|german|catalan|portuguese|italian|galician|basque)\s*:\s*(.+)',
                        line.strip(),
                        re.IGNORECASE
                    )
                    if target_match:
                        # Found target language line, extract the translation
                        translation = target_match.group(2).strip()
                        if translation:
                            return translation
                # No nested language label found, use the content after the first label
                text = after_label

        prompt_patterns = [
            "Text to translate:",
            "Translate only the text",
            "Provide ONLY the translation",
            "Translate the following",
            "Do NOT copy the original text",
            "Return only the full translation",
            "with no labels or explanations",
            "Preserve meaning, tone, names",
        ]
        for pattern in prompt_patterns:
            if pattern in text:
                parts = text.split(pattern)
                if len(parts) > 1:
                    text = parts[-1].strip()
        return text

    @staticmethod
    def _get_language_prefixes() -> list[str]:
        """Get list of language prefix patterns."""
        return [
            "spanish:", "english:", "french:", "german:", "italian:", "portuguese:",
            "catalan:", "galician:", "basque:", "russian:", "chinese:", "japanese:",
            "arabic:", "hindi:", "korean:", "dutch:", "polish:", "swedish:",
            "norwegian:", "danish:", "finnish:", "greek:", "czech:", "romanian:",
            "hungarian:", "turkish:", "ukrainian:", "croatian:", "serbian:",
            "bulgarian:", "slovak:", "slovenian:", "estonian:", "latvian:",
            "lithuanian:", "maltese:", "irish:", "welsh:", "occitan:",
        ]

    @staticmethod
    def _is_prompt_repetition(normalized_lower: str) -> bool:
        """Check if line is a prompt repetition."""
        return any(prompt in normalized_lower for prompt in [
            "translate the following", "translate this text", "translate to",
            "text into english", "text into spanish", "do not copy", "provide only the",
        ])

    @staticmethod
    def _extract_text_after_prefix(line_stripped: str, prefix: str, normalized_lower: str) -> str | None:
        """Extract text after a language prefix if present."""
        if normalized_lower.startswith(prefix):
            after_prefix_raw = re.sub(r"^[#*\-\s]+", "", line_stripped)
            after_prefix = after_prefix_raw[len(prefix):].strip()
            return after_prefix if after_prefix else None
        return None

    @staticmethod
    def _clean_language_prefix_lines(lines: list[str]) -> list[str]:
        """Remove language prefix labels from lines."""
        language_prefixes = HuggingFaceTranslationService._get_language_prefixes()
        cleaned = []

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            normalized_lower = re.sub(r"^[#*\-\s]+", "", line_lower)

            if any(normalized_lower == prefix or normalized_lower.startswith(prefix + " ") for prefix in language_prefixes):
                for prefix in language_prefixes:
                    extracted = HuggingFaceTranslationService._extract_text_after_prefix(
                        line_stripped, prefix, normalized_lower
                    )
                    if extracted:
                        cleaned.append(extracted)
                        break
                continue

            if HuggingFaceTranslationService._is_prompt_repetition(normalized_lower):
                continue

            if line_stripped:
                cleaned.append(line_stripped)

        return cleaned

    def _remove_educational_content(self, text: str) -> str:
        """Remove educational content that appears after translation."""
        educational_patterns = [
            self.THE_VERB, self.IN_THIS_LESSON, self.WE_WILL_LOOK_AT, self.LETS_GET_STARTED,
            self.WELL_ALSO_LEARN, self.DEPENDING_ON_HOW, self.MANY_MEANINGS,
            self.PAST_TENSE_FORM, self.USED_IN_A_LOT, 'grammar', 'vocabulary',
            'lesson', 'tutorial', 'example:', 'note:', 'remember:'
        ]

        text_lower = text.lower()
        for pattern in educational_patterns:
            if pattern in text_lower:
                idx = text_lower.index(pattern)
                text = text[:idx].strip()
                break
        return text

    def _get_metadata_labels(self) -> list[str]:
        """Get list of metadata labels to filter."""
        return [
            self.OUTPUT_LABEL, 'translation:', self.TAGS_LABEL, self.TRANSLATE_FROM,
            self.USING_OUR, self.ONLINE_TRANSLATOR, '[en]', '[es]', '[ca]',
            '[pt]', '[fr]', '[de]', '[it]', '[gl]', '[eu]',
            # Note: 'is a' removed - too generic, causes false positives
            self.LANGUAGE_THAT, self.SPOKEN_BY, self.LINGUA_FRANCA,
            self.GERMANIC_LANGUAGE, self.ROMANCE_LANGUAGE, self.FIRST_SPOKEN
        ]

    def _handle_inline_translation(
        self,
        line_stripped: str,
        line_lower: str
    ) -> str | None:
        """Extract inline translation content if present."""
        for prefix in ('translation:', self.OUTPUT_LABEL):
            if line_lower.startswith(prefix):
                content = line_stripped[len(prefix):].strip(" -:")
                return content if content else None
        return None

    def _filter_metadata_lines(self, lines: list[str]) -> list[str]:
        """Filter out metadata and label lines, keeping only translation content."""
        cleaned_lines = []
        skip_after_translation = False
        translation_started = False
        metadata_labels = self._get_metadata_labels()

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or skip_after_translation:
                if skip_after_translation:
                    break
                continue

            line_lower = line_stripped.lower()

            if any(label in line_lower for label in metadata_labels):
                if translation_started:
                    skip_after_translation = True
                    continue

                content = self._handle_inline_translation(line_stripped, line_lower)
                if content:
                    cleaned_lines.append(content)
                    translation_started = True
                continue

            cleaned_lines.append(line_stripped)
            translation_started = True

        return cleaned_lines

    @staticmethod
    def _remove_trailing_separators(result: str) -> str:
        """Remove content after common separators."""
        for separator in ['Output:', 'Tags:', 'Translate from', '\n\n']:
            if separator in result:
                result = result.split(separator)[0].strip()
        return result

    def _extract_first_valid_sentence(self, result: str) -> str | None:
        """Extract first sentence if result contains language descriptions."""
        language_desc_phrases = ['is a', self.LANGUAGE_THAT, self.SPOKEN_BY]
        if not any(phrase in result.lower() for phrase in language_desc_phrases):
            return None

        for ending in ['. ', '! ', '? ']:
            if ending in result:
                first_sentence = result.split(ending)[0] + ending.strip()
                if not any(phrase in first_sentence.lower() for phrase in language_desc_phrases):
                    return first_sentence
                break
        return None

    @staticmethod
    def _truncate_excessive_output(result: str, original_chunk: str) -> str:
        """Truncate result if it's suspiciously long."""
        if len(result) > len(original_chunk) * 3 and len(result) > 500:
            sentences = result.replace('! ', '.|').replace('? ', '.|').split('. ')
            if len(sentences) > 1:
                first_few = '. '.join(sentences[:3]).replace('|', '. ').strip()
                if not first_few.endswith(('.', '!', '?')):
                    first_few += '.'
                return first_few
        return result

    @staticmethod
    def _remove_consecutive_duplicate_sentences(text: str) -> str:
        """Remove consecutive duplicate sentences in model output."""
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        if len(sentences) < 2:
            return text
        cleaned: list[str] = []
        for sentence in sentences:
            if cleaned and sentence == cleaned[-1]:
                continue
            cleaned.append(sentence)
        return " ".join(cleaned)

    @staticmethod
    def _truncate_on_repetition(text: str) -> str:
        """Truncate output when the model starts looping on repeated content."""
        cleaned = text.strip()
        if len(cleaned) < 300:
            return cleaned

        word_matches = list(re.finditer(r"\b\w+\b", cleaned))
        if len(word_matches) < 60:
            return cleaned

        ngram_size = 12
        seen: dict[tuple[str, ...], int] = {}
        for idx in range(len(word_matches) - ngram_size + 1):
            key = tuple(m.group(0).lower() for m in word_matches[idx:idx + ngram_size])
            prev_idx = seen.get(key)
            if prev_idx is not None and idx - prev_idx >= ngram_size:
                cut_pos = word_matches[idx].start()
                if cut_pos > 200:
                    truncated = cleaned[:cut_pos].rstrip()
                    if len(truncated) < len(cleaned) * 0.85:
                        return truncated
            else:
                seen[key] = idx
        return cleaned

    def _post_process_result(self, result: str, original_chunk: str) -> str:
        """Apply final cleanup and validation to the result."""
        result = self._remove_trailing_separators(result)

        first_sentence = self._extract_first_valid_sentence(result)
        if first_sentence:
            return first_sentence

        result = self._truncate_on_repetition(result)
        result = self._remove_consecutive_duplicate_sentences(result)
        result = self._truncate_excessive_output(result, original_chunk)

        return result

    def _clean_output(
        self,
        text: str,
        original_chunk: str = "",
        target_language: str | None = None,
        source_language: str | None = None
    ) -> str:
        """Remove any stray markers, fences, labels, and extra content while keeping only the target language."""
        text = self._remove_translation_markers(text)
        text = self._strip_chatml(text)

        target_lower = target_language.lower() if target_language else ""
        source_lower = source_language.lower() if source_language else ""

        text = self._extract_target_language_section(text, target_lower, source_lower)
        text = self._remove_prompt_echoes(text)

        # Save text after prompt echo removal for potential fallback
        after_prompt_removal = text

        lines = text.split('\n')
        cleaned = self._clean_language_prefix_lines(lines)
        text = '\n'.join(cleaned)

        text = self._remove_educational_content(text)

        if original_chunk and text.strip() == original_chunk.strip():
            logger.warning("Model returned identical text to input, possible translation failure")
            return ""

        lines = text.split('\n')
        cleaned_lines = self._filter_metadata_lines(lines)
        result = ' '.join(cleaned_lines).strip()

        result = self._post_process_result(result, original_chunk)

        # Fallback: if cleaning was too aggressive, use content after prompt removal
        if not result and after_prompt_removal:
            # Try a minimal cleanup - just get the first sentence or line
            fallback = after_prompt_removal.strip().split('\n')[0].strip()
            # Truncate if too long (likely hallucination)
            if fallback and len(fallback) > len(original_chunk) * 3:
                # Get first sentence only
                for ending in ['. ', '! ', '? ']:
                    if ending in fallback:
                        fallback = fallback.split(ending)[0] + ending.strip()
                        break
            if fallback and fallback != original_chunk.strip():
                logger.warning(f"Using fallback after aggressive cleaning: {fallback[:100]}...")
                return fallback

        # Final fallback: if model returned nothing useful (e.g., "English translation:" with no content),
        # return original chunk for short texts (likely headers/labels that don't need translation)
        if not result and original_chunk:
            chunk_stripped = original_chunk.strip()
            # For very short texts (< 50 chars), use original as fallback
            # These are typically headers, labels, or technical terms
            if len(chunk_stripped) < 50:
                logger.warning(f"Model failed to translate short text, using original: {chunk_stripped}")
                return chunk_stripped

        return result

    def _build_params(self, chunk: str) -> dict[str, Any]:
        """Build generation parameters tuned for maximum speed."""
        params = dict(self.parameters)

        # Calculate appropriate max_new_tokens based on input length
        # Translation output is typically similar length to input
        # Use 1.5x multiplier to ensure complete translation without truncation
        input_length = len(chunk)
        max_new = max(100, int(input_length * 1.5))
        params["max_new_tokens"] = min(max_new, params.get("max_new_tokens", 2048))

        # Add stopping criteria to prevent run-on generation
        # Note: Not all endpoints support these, they'll be filtered by _clean_generation_params
        params["stop_sequences"] = ["\n\nText to translate:", "\n\nTranslation:", "###"]

        return params

    def _chunk_text(self, text: str) -> list[str]:
        """Split long text into manageable chunks preserving paragraph boundaries."""
        chunks: list[str] = []
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                chunks.append("")
                continue

            current = para
            # Further split paragraphs that exceed chunk size
            while len(current) > self.chunk_chars:
                # Find a break point before the limit
                break_idx = current.rfind(" ", 0, self.chunk_chars)
                if break_idx == -1:
                    break_idx = self.chunk_chars
                chunks.append(current[:break_idx].strip())
                current = current[break_idx:].strip()
            if current:
                chunks.append(current)
        return chunks

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        """Translate text using Hugging Face Inference Endpoint."""
        language_names = self._get_language_name_mapping()
        source_name = language_names.get(source_language.lower(), source_language)
        target_name = language_names.get(target_language.lower(), target_language)

        try:
            translations: list[str] = []
            for chunk in self._chunk_text(text.strip()):
                if not chunk:
                    translations.append("")  # preserve blank paragraphs
                    continue

                # Use the SalamandraTA recommended prompt format for all texts
                # See DOCUMENTATION.md - the model expects this specific structure
                prompt = self._build_translation_prompt(chunk, source_name, target_name)

                # huggingface_hub client is synchronous; run in thread to avoid blocking
                def _call_hf(p: str = prompt, c: str = chunk) -> str:
                    params = self._build_params(c)
                    return self._generate_via_http(p, params)

                translated_text = await asyncio.to_thread(_call_hf)
                if not translated_text:
                    raise HTTPException(
                        status_code=500,
                        detail="Empty response from Hugging Face translation service"
                    )

                # Log raw output before cleaning for debugging
                logger.debug(f"Raw model output (first 300 chars): {translated_text[:300]}")

                cleaned_text = self._clean_output(
                    translated_text,
                    chunk,
                    target_language=target_name,
                    source_language=source_name
                )

                # Log cleaned output
                logger.debug(f"Cleaned output (first 300 chars): {cleaned_text[:300] if cleaned_text else 'EMPTY'}")

                if not cleaned_text:
                    # Model failed to translate (copied input or returned empty)
                    logger.error(f"Translation failed for chunk: {chunk[:100]}...")
                    logger.error(f"Raw model output before cleaning: {translated_text[:500]}")
                    logger.error("Raw model output was cleaned to empty. This indicates over-aggressive cleaning.")
                    raise HTTPException(
                        status_code=500,
                        detail="Translation service failed to translate part of the text. Please try again or contact support."
                    )
                translations.append(cleaned_text)

            return "\n\n".join(translations).strip()

        except HTTPException:
            raise
        except Exception as e:
            # huggingface_hub wraps HTTP errors; surface message
            raise HTTPException(
                status_code=502,
                detail=f"Hugging Face translation failed: {str(e)}"
            )

    @staticmethod
    def _is_streaming_not_supported_error(exc: Exception) -> bool:
        """Check if exception indicates streaming is not supported."""
        message = str(exc).lower()
        return (
            "not served via tgi" in message
            or "cannot return output as a stream" in message
            or "model_kwargs" in message
        )

    def _process_streaming_events(
        self,
        prompt: str,
        params: dict[str, Any],
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[str | Exception | None]
    ) -> None:
        """Process streaming events from HF client."""
        token_sent = False
        last_generated: str | None = None
        stream_params = self._clean_generation_params(params)
        stream_params["stream"] = True

        try:
            for event in self.client.text_generation(prompt, **stream_params):
                if getattr(event, "generated_text", None):
                    last_generated = event.generated_text
                token = getattr(event, "token", None)
                token_text = getattr(token, "text", None) if token else None
                if token_text:
                    token_sent = True
                    loop.call_soon_threadsafe(queue.put_nowait, token_text)
            if not token_sent and last_generated:
                loop.call_soon_threadsafe(queue.put_nowait, last_generated)
        except Exception as exc:  # noqa: BLE001
            if self._is_streaming_not_supported_error(exc):
                self.streaming_available = False
                exc = StreamingNotSupportedError(str(exc))
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    async def _stream_hf_tokens(self, prompt: str, params: dict[str, Any]) -> AsyncGenerator[str, None]:
        """Stream tokens from Hugging Face without blocking the event loop."""
        if self.streaming_available is False:
            raise StreamingNotSupportedError("HF endpoint does not support streaming")

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str | Exception | None] = asyncio.Queue()

        def _worker() -> None:
            self._process_streaming_events(prompt, params, loop, queue)

        threading.Thread(target=_worker, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    def _get_stop_words(self) -> list[str]:
        """Get list of stop words for streaming translation."""
        return [
            self.OUTPUT_LABEL, self.TAGS_LABEL, self.TRANSLATE_FROM, self.USING_OUR, self.ONLINE_TRANSLATOR,
            'is a', self.LANGUAGE_THAT, self.SPOKEN_BY, self.LINGUA_FRANCA, self.GERMANIC_LANGUAGE,
            self.ROMANCE_LANGUAGE, self.FIRST_SPOKEN, 'medieval', 'eventually became',
            self.THE_VERB, self.IN_THIS_LESSON, self.WE_WILL_LOOK_AT, self.LETS_GET_STARTED,
            self.WELL_ALSO_LEARN, self.DEPENDING_ON_HOW, self.MANY_MEANINGS,
            self.PAST_TENSE_FORM, self.USED_IN_A_LOT, 'grammar', 'vocabulary',
            'lesson', 'tutorial'
        ]

    @staticmethod
    def _build_translation_prompt(
        chunk: str,
        source_name: str,
        target_name: str
    ) -> str:
        """Build translation prompt using SalamandraTA recommended format."""
        base_prompt = (
            f"Translate the following text from {source_name} into {target_name}.\n"
            f"{source_name}: {chunk}\n"
            f"{target_name}:"
        )
        return HuggingFaceTranslationService._wrap_chatml(base_prompt)

    async def _translate_chunk_non_streaming(
        self,
        prompt: str,
        params: dict[str, Any],
        chunk: str,
        target_name: str,
        source_name: str
    ) -> str:
        """Translate a chunk without streaming."""
        translated_text = await asyncio.to_thread(
            self._generate_via_http,
            prompt,
            params
        )
        if translated_text.startswith(prompt):
            translated_text = translated_text[len(prompt):].lstrip()
        translated_text = self._clean_output(
            translated_text,
            chunk,
            target_language=target_name,
            source_language=source_name
        )
        if not translated_text:
            logger.warning(f"Streaming translation failed for chunk: {chunk[:50]}...")
            translated_text = chunk
        return translated_text

    async def _process_streaming_chunk(
        self,
        prompt: str,
        params: dict[str, Any],
        chunk: str,
        target_name: str,
        source_name: str,
        stop_words: list[str]
    ) -> tuple[bool, bool, list[str]]:
        """Process a chunk with streaming. Returns (chunk_sent_any, started, tokens)."""
        chunk_sent_any = False
        started = False
        accumulated_text = ""
        tokens: list[str] = []

        async for token_text in self._stream_hf_tokens(prompt, params):
            accumulated_text += token_text.lower()

            if any(stop_word in accumulated_text for stop_word in stop_words):
                break

            cleaned = self._clean_output(
                token_text,
                target_language=target_name,
                source_language=source_name
            )
            if not started and not cleaned:
                continue
            started = True
            chunk_sent_any = True
            if cleaned:
                tokens.append(cleaned)

        return chunk_sent_any, started, tokens

    async def _handle_streaming_fallback(
        self,
        prompt: str,
        params: dict[str, Any],
        chunk: str,
        target_name: str,
        source_name: str
    ) -> str:
        """Handle fallback when streaming fails or returns nothing."""
        translated_text = await asyncio.to_thread(
            self._generate_via_http,
            prompt,
            params
        )
        if translated_text.startswith(prompt):
            translated_text = translated_text[len(prompt):].lstrip()
        translated_text = self._clean_output(
            translated_text,
            chunk,
            target_language=target_name,
            source_language=source_name
        )
        if not translated_text:
            logger.warning(f"Streaming fallback for chunk: {chunk[:50]}...")
            translated_text = chunk
        return translated_text

    async def _try_stream_chunk(
        self,
        prompt: str,
        params: dict[str, Any],
        chunk: str,
        target_name: str,
        source_name: str,
        stop_words: list[str],
        translated_any: bool,
        idx: int,
        total_chunks: int
    ) -> AsyncGenerator[str, None]:
        """Try to stream a chunk, with fallback on failure."""
        chunk_sent_any = False

        try:
            chunk_sent_any, _, tokens = await self._process_streaming_chunk(
                prompt, params, chunk, target_name, source_name, stop_words
            )

            for token in tokens:
                yield token

            if not chunk_sent_any:
                fallback_text = await self._handle_streaming_fallback(
                    prompt, params, chunk, target_name, source_name
                )
                yield fallback_text
                chunk_sent_any = True

        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, StreamingNotSupportedError):
                self.streaming_available = False

            if not chunk_sent_any:
                try:
                    fallback_text = await self._handle_streaming_fallback(
                        prompt, params, chunk, target_name, source_name
                    )
                    yield fallback_text
                except Exception as inner_exc:  # noqa: BLE001
                    if not translated_any:
                        raise HTTPException(
                            status_code=502,
                            detail=f"Hugging Face translation failed: {inner_exc}"
                        ) from inner_exc
                    logger.error(
                        "Translation failed for chunk %d/%d after response started: %s",
                        idx + 1, total_chunks, inner_exc
                    )

    async def translate_stream(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> AsyncGenerator[str, None]:
        """Stream translation with token-level updates from HF endpoints."""
        language_names = self._get_language_name_mapping()
        source_name = language_names.get(source_language.lower(), source_language)
        target_name = language_names.get(target_language.lower(), target_language)

        chunks = self._chunk_text(text.strip())
        total_chunks = len(chunks)
        translated_any = False
        stop_words = self._get_stop_words()

        for idx, chunk in enumerate(chunks):
            if chunk == "":
                yield "\n\n"
                translated_any = True
                continue

            params = self._build_params(chunk)
            prompt = self._build_translation_prompt(chunk, source_name, target_name)

            if self.streaming_available is False:
                translated_text = await self._translate_chunk_non_streaming(
                    prompt, params, chunk, target_name, source_name
                )
                yield translated_text
                translated_any = True
            else:
                async for token in self._try_stream_chunk(
                    prompt, params, chunk, target_name, source_name,
                    stop_words, translated_any, idx, total_chunks
                ):
                    yield token
                    translated_any = True

            if idx < total_chunks - 1:
                yield "\n\n"

    @staticmethod
    def _get_language_name_mapping() -> dict[str, str]:
        """Get mapping of language codes to full names."""
        return {
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


class TranslationServiceFactory:
    """Factory for creating translation service instances."""

    @staticmethod
    async def get_service(
        db: AsyncSession,
        provider_id: int | None = None
    ) -> HuggingFaceTranslationService:
        """Get translation service instance (Hugging Face only).

        Args:
            db: Database session
            provider_id: Optional provider ID (uses default if not provided)

        Returns:
            Translation service instance

        Raises:
            HTTPException: If provider not found or not configured
        """
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

        # Decrypt API key
        api_key = await crud_translation.get_decrypted_api_key(db, provider.id)

        if provider.provider_type != "huggingface":
            raise HTTPException(
                status_code=400,
                detail="Only Hugging Face translation provider is supported"
            )

        config = provider.configuration or {}
        model = config.get("model")
        parameters = config.get("parameters") if isinstance(config.get("parameters"), dict) else None
        if not provider.endpoint:
            raise HTTPException(
                status_code=500,
                detail="Hugging Face provider requires an endpoint URL"
            )
        return HuggingFaceTranslationService(
            api_key=api_key,
            endpoint=provider.endpoint,
            model=model,
            parameters=parameters
        )
