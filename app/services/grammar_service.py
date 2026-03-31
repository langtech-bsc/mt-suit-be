"""Grammar checking service using Hugging Face Inference Endpoints."""

import asyncio
import re
from typing import Any

import httpx
from fastapi import HTTPException
from huggingface_hub import InferenceClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import translation as crud_translation
from app.schemas.translation import GrammarSuggestion

# Error message constants
ERR_EMPTY_GRAMMAR_RESPONSE = "Empty response from grammar checking service"

# Spanish grammar rules for common errors
# Rules are ordered by priority (more specific first)
SPANISH_GRAMMAR_RULES = [
    # Verb conjugation errors with "yo" (more specific)
    (r'\byo fue\b', 'yo fui', 'Verb conjugation: "yo fui" (preterite)'),
    (r'\byo esta\b', 'yo estoy', 'Verb conjugation: "yo estoy"'),
    (r'\byo tiene\b', 'yo tengo', 'Verb conjugation: "yo tengo"'),
    (r'\byo hace\b', 'yo hago', 'Verb conjugation: "yo hago"'),

    # Subject-verb agreement errors (more specific phrases)
    (r'\bel equipo estaban\b', 'el equipo estaba', 'Subject-verb agreement: singular subject'),
    (r'\bla empresa tienen\b', 'la empresa tiene', 'Subject-verb agreement: singular subject'),
    (r'\blos requerimientos cambia\b', 'los requerimientos cambian', 'Subject-verb agreement: plural subject'),
    (r'\bellos esta\b', 'ellos están', 'Subject-verb agreement: plural subject'),
    (r'\bnadie saben\b', 'nadie sabe', 'Subject-verb agreement: "nadie" is singular'),
    (r'\bnadie sabia\b', 'nadie sabía', 'Subject-verb agreement and accent'),
    (r'\bla gente estaban?\s+muy\s+apurado\b', 'la gente estaba muy apurada',
     'Subject-verb and gender agreement: "la gente estaba muy apurada"'),
    (r'\bla gente estaban\b(?!\s+muy\s+apurado\b)', 'la gente estaba',
     'Subject-verb agreement: "la gente" is singular'),

    # Common misspellings (check before accent rules)
    (r'\b[Oo]la\b', lambda m: 'Hola' if m.group(0)[0].isupper() else 'hola', 'Spelling: "hola" requires "h"'),
    (r'\bnonbre\b', 'nombre', 'Spelling: "nombre"'),
    (r'\bmuchas cosa\b', 'muchas cosas', 'Plural agreement: "muchas cosas"'),
    (r'\bhaci\b', 'así', 'Spelling: "así" with accent'),
    (r'\btanbien\b', 'también', 'Spelling: "también"'),
    (r'\bcomoe\b', 'como', 'Spelling: "como"'),
    (r'\bstas\b', 'estás', 'Spelling: "estás"'),

    # Missing accents on verbs (context-aware)
    (r'\besta\s+(terminado|haciendo|trabajando|hecho|siendo|aqui|alli|bien|mal)\b',
     lambda m: f'está {m.group(1)}', 'Missing accent on "está"'),
    (r'\b(no\s+)?tenia\b', lambda m: m.group(0).replace('tenia', 'tenía'), 'Missing accent on "tenía"'),
    (r'\bsabia\s+(que|como|cuando|donde|exactamente)\b',
     lambda m: f'sabía {m.group(1)}', 'Missing accent on "sabía"'),
    (r'\baun\s+no\b', 'aún no', 'Missing accent on "aún"'),

    # Missing accents on adjectives/adverbs
    (r'\bmas\s+(importante|grande|pequeno|rapido|lento|alto|bajo)\b',
     lambda m: f'más {m.group(1)}', 'Missing accent on "más"'),
    (r'\bcual\s+(era|es|fue|seria)\b', lambda m: f'cuál {m.group(1)}', 'Missing accent on "cuál"'),
    (r'\bcomo\s+(estas|esta|estan|estoy|estaba)\b',
     lambda m: f'cómo {m.group(1)}', 'Missing accent on "cómo"'),
]


class HuggingFaceGrammarService:
    """Hugging Face Inference Endpoint grammar checking service."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None
    ):
        """Initialize Hugging Face Grammar Service using InferenceClient."""
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model or "BSC-LT/salamandraTA-2b-instruct"
        self.parameters = {
            "max_new_tokens": 512,
            "do_sample": False,  # Greedy decoding as recommended by the manual
        }
        # Default chunk size for processing long texts
        self.chunk_chars = 800
        if parameters:
            # Filter out parameters that are not valid for the HuggingFace API
            safe_params = dict(parameters)
            # Extract chunk_chars before removing it
            self.chunk_chars = safe_params.pop("chunk_chars", self.chunk_chars)
            safe_params.pop("stop_sequences", None)  # Not supported in text_generation
            self.parameters.update(safe_params)

        self._auth_headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        self.client = InferenceClient(model=self.endpoint, token=api_key)

    def _clean_generation_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Remove unsupported or empty generation parameters."""
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
        """Call the HF endpoint via raw HTTP to avoid strict client parsing."""
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
            raise ValueError(ERR_EMPTY_GRAMMAR_RESPONSE)
        return text

    @staticmethod
    def _clean_output(text: str) -> str:
        """Remove any stray markers or fences and trim."""
        markers = (
            "<START_OF_CORRECTION>",
            "</START_OF_CORRECTION>",
            "START_OF_CORRECTION",
            "```",
        )
        for marker in markers:
            text = text.replace(marker, "")

        if "<|im_end|>" in text:
            text = text.split("<|im_end|>", 1)[0]
        text = text.replace("<|im_start|>", "").replace("<|im_end|>", "")

        # Remove common explanatory phrases that models add
        explanatory_phrases = [
            "The correct answer is",
            "The corrected text is",
            "Corrected version:",
            "Correction:",
            "Here's the corrected text:",
            "Here is the corrected text:",
        ]

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line_lower = line.lower().strip()
            # Skip lines that are just explanations
            is_explanation = any(
                phrase.lower() in line_lower
                for phrase in explanatory_phrases
            )
            if is_explanation:
                continue
            if line_lower in {"user", "assistant", "system"}:
                continue
            for role in ("user:", "assistant:", "system:"):
                if line_lower.startswith(role):
                    line = line[len(role):].strip()
                    line_lower = line.lower()
                    break
            if line.strip():
                cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines).strip()

        # Remove quotes if the entire text is wrapped in quotes
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1].strip()
        if result.startswith("'") and result.endswith("'"):
            result = result[1:-1].strip()

        return result

    @staticmethod
    def _wrap_chatml(content: str) -> str:
        """Wrap prompt content in ChatML format."""
        content = content.rstrip()
        return f"<|im_start|>user\n{content}\n<|im_end|>\n<|im_start|>assistant\n"

    @staticmethod
    def _apply_suggestions(text: str, suggestions: list[GrammarSuggestion]) -> str:
        """Apply suggested corrections to the text when the original is still present."""
        updated = text
        for suggestion in suggestions:
            original = suggestion.original
            correction = suggestion.correction
            if not original or not correction or original == correction:
                continue
            if original in updated:
                updated = updated.replace(original, correction, 1)
                continue
            try:
                pattern = re.compile(re.escape(original), re.IGNORECASE)
            except re.error:
                continue
            updated, _ = pattern.subn(correction, updated, count=1)
        return updated

    @staticmethod
    def _dedupe_suggestions(suggestions: list[GrammarSuggestion]) -> list[GrammarSuggestion]:
        """Remove duplicate suggestions while preserving order."""
        seen: set[tuple[str, str, int | None]] = set()
        deduped: list[GrammarSuggestion] = []
        for suggestion in suggestions:
            key = (suggestion.original, suggestion.correction, suggestion.position)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(suggestion)
        return deduped

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

    def _apply_rule_based_corrections(
        self,
        text: str,
        language_code: str
    ) -> tuple[str, list[GrammarSuggestion]]:
        """Apply rule-based grammar corrections for specific languages."""
        if language_code.lower() != "es":
            # Only Spanish rules are implemented
            return text, []

        corrected_text = text
        suggestions: list[GrammarSuggestion] = []
        offset = 0  # Track position offset due to replacements

        # Collect all matches first
        all_matches: list[tuple[re.Match, str, str]] = []
        for pattern, replacement, explanation in SPANISH_GRAMMAR_RULES:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                all_matches.append((match, replacement, explanation))

        # Sort by position
        all_matches.sort(key=lambda x: x[0].start())

        # Apply corrections
        for match, replacement, explanation in all_matches:
            original = match.group(0)
            position = match.start()

            # Handle callable replacements (lambda functions)
            if callable(replacement):
                replacement_with_case = replacement(match)
            else:
                # Preserve original capitalization for string replacements
                if original[0].isupper() and replacement[0].islower():
                    replacement_with_case = replacement[0].upper() + replacement[1:]
                else:
                    replacement_with_case = replacement

            # Calculate position in original text
            original_position = position

            suggestions.append(GrammarSuggestion(
                original=original,
                correction=replacement_with_case,
                explanation=explanation,
                position=original_position
            ))

            # Apply correction with offset
            corrected_position = position + offset
            corrected_text = (
                corrected_text[:corrected_position] +
                replacement_with_case +
                corrected_text[corrected_position + len(original):]
            )

            # Update offset
            offset += len(replacement_with_case) - len(original)

        return corrected_text, suggestions

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts (0.0 to 1.0)."""
        words1 = text1.lower().split()
        words2 = text2.lower().split()

        if not words1 or not words2:
            return 0.0

        # Count matching words
        matching = sum(1 for w1, w2 in zip(words1, words2) if w1 == w2)
        max_len = max(len(words1), len(words2))

        return matching / max_len if max_len > 0 else 0.0

    def _extract_structured_corrections(self, response: str, original_text: str) -> list[GrammarSuggestion]:
        """Extract structured corrections from model response."""
        suggestions: list[GrammarSuggestion] = []
        correction_pattern = r'Original:\s*"([^"]+)"\s*->\s*Correction:\s*"([^"]+)"(?:\s*\(Explanation:\s*([^)]+)\))?'
        matches = list(re.finditer(correction_pattern, response, re.IGNORECASE))

        for match in matches:
            original = match.group(1).strip()
            correction = match.group(2).strip()
            explanation = match.group(3).strip() if match.group(3) else "Grammar correction suggested"
            position = original_text.find(original)

            suggestions.append(GrammarSuggestion(
                original=original,
                correction=correction,
                explanation=explanation,
                position=position if position != -1 else None
            ))

        return suggestions

    def _find_word_level_changes(self, original_text: str, corrected_text: str) -> list[GrammarSuggestion]:
        """Find word-level differences between original and corrected text."""
        suggestions: list[GrammarSuggestion] = []
        original_words = original_text.split()
        corrected_words = corrected_text.split()

        # Only find word-level changes if texts are similar in length
        if abs(len(original_words) - len(corrected_words)) <= 2:
            for orig_word, corr_word in zip(original_words, corrected_words):
                if orig_word != corr_word:
                    position = original_text.find(orig_word)
                    suggestions.append(GrammarSuggestion(
                        original=orig_word,
                        correction=corr_word,
                        explanation="Spelling or grammar correction",
                        position=position if position != -1 else None
                    ))

        return suggestions

    def _parse_corrections(self, response: str, original_text: str) -> tuple[str, list[GrammarSuggestion]]:
        """Parse the model response to extract corrections and suggestions."""
        corrected_text = self._clean_output(response)

        # If the response is identical to input, the model didn't detect errors
        if corrected_text == original_text:
            return original_text, []

        # Check if the model reformulated too much instead of just correcting errors
        similarity = self._calculate_similarity(original_text, corrected_text)
        if similarity < 0.6 and len(corrected_text) > 0:
            return original_text, []

        # Try to extract structured corrections
        suggestions = self._extract_structured_corrections(response, original_text)

        if suggestions:
            # Apply structured corrections to text
            for suggestion in suggestions:
                corrected_text = corrected_text.replace(suggestion.original, suggestion.correction, 1)
            return corrected_text, suggestions

        # No structured corrections found, find word-level changes
        if not corrected_text or corrected_text == original_text or len(corrected_text) == 0:
            return original_text, []

        original_words = original_text.split()
        corrected_words = corrected_text.split()
        word_diff = abs(len(original_words) - len(corrected_words))

        if word_diff <= 2:
            # Minor length difference, find word-level changes
            suggestions = self._find_word_level_changes(original_text, corrected_text)
        elif word_diff > 5:
            # Too much structural change, likely reformulation - ignore
            return original_text, []
        else:
            # Some structural change but acceptable
            suggestions = [GrammarSuggestion(
                original=original_text,
                correction=corrected_text,
                explanation="Grammar corrections applied",
                position=0
            )]

        return corrected_text, suggestions

    def _build_grammar_prompt(self, chunk: str, language: str) -> str:
        """Build the grammar correction prompt for a text chunk."""
        language_name = self._get_language_name_mapping().get(language.lower(), language)
        base_prompt = (
            f"Please fix any mistakes in the following {language_name} sentence or keep it unedited if it's correct.\n"
            f"Sentence: {chunk}\n"
            "Corrected:"
        )
        return self._wrap_chatml(base_prompt)

    def _call_hf_sync(self, prompt: str) -> str:
        """Call Hugging Face API synchronously (for use with asyncio.to_thread)."""
        clean_params = self._clean_generation_params(self.parameters)
        try:
            return self._generate_via_http(prompt, clean_params)
        except Exception as http_exc:
            try:
                result = self.client.text_generation(prompt, **clean_params)
                extracted = self._extract_generated_text(result)
                if not extracted:
                    raise ValueError(ERR_EMPTY_GRAMMAR_RESPONSE) from http_exc
                return extracted
            except KeyError as key_exc:
                raise ValueError(
                    "Unexpected response format from grammar checking service"
                ) from key_exc

    async def _process_chunk(
        self,
        chunk: str,
        position_offset: int,
        language: str
    ) -> tuple[str, list[GrammarSuggestion]]:
        """Process a single text chunk for grammar checking."""
        if not chunk:
            return "", []

        prompt = self._build_grammar_prompt(chunk, language)
        response = await asyncio.to_thread(self._call_hf_sync, prompt)

        if not response:
            raise HTTPException(status_code=500, detail=ERR_EMPTY_GRAMMAR_RESPONSE)

        # Parse corrections for this chunk
        corrected_chunk, chunk_suggestions = self._parse_corrections(response, chunk)

        # Adjust suggestion positions based on chunk offset
        for suggestion in chunk_suggestions:
            if suggestion.position is not None:
                suggestion.position += position_offset

        # If no corrected text was extracted, use original chunk
        if not corrected_chunk:
            corrected_chunk = chunk

        return corrected_chunk, chunk_suggestions

    async def check_grammar(
        self,
        text: str,
        language: str
    ) -> tuple[str, list[GrammarSuggestion], bool]:
        """Check grammar and return corrected text with suggestions.

        Args:
            text: Text to check
            language: Language code

        Returns:
            Tuple of (corrected_text, suggestions, has_errors)
        """
        try:
            # First apply rule-based corrections for Spanish
            # This catches common errors that the model might miss
            _, rule_suggestions = self._apply_rule_based_corrections(
                text.strip(),
                language
            )

            # Process text in chunks for long texts
            chunks = self._chunk_text(text.strip())
            corrected_chunks: list[str] = []
            all_suggestions: list[GrammarSuggestion] = []
            position_offset = 0

            for chunk in chunks:
                corrected_chunk, chunk_suggestions = await self._process_chunk(
                    chunk,
                    position_offset,
                    language
                )
                corrected_chunks.append(corrected_chunk)
                all_suggestions.extend(chunk_suggestions)
                position_offset += len(chunk) + 2  # +2 for "\n\n" separator

            # Combine all corrected chunks
            corrected_text = "\n\n".join(corrected_chunks).strip()

            if rule_suggestions:
                corrected_text = self._apply_suggestions(corrected_text, rule_suggestions)

            combined_suggestions = self._dedupe_suggestions(rule_suggestions + all_suggestions)

            # Determine if errors were found
            has_errors = len(combined_suggestions) > 0 or corrected_text != text.strip()

            return corrected_text, combined_suggestions, has_errors

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Grammar checking failed: {str(e)}"
            )

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


class GrammarServiceFactory:
    """Factory for creating grammar service instances."""

    @staticmethod
    async def get_service(
        db: AsyncSession,
        provider_id: int | None = None
    ) -> HuggingFaceGrammarService:
        """Get grammar service instance (Hugging Face only).

        Args:
            db: Database session
            provider_id: Optional provider ID (uses default if not provided)

        Returns:
            Grammar service instance

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
                detail="Only Hugging Face provider is supported for grammar checking"
            )

        config = provider.configuration or {}
        model = config.get("model")
        parameters = config.get("parameters") if isinstance(config.get("parameters"), dict) else None

        if not provider.endpoint:
            raise HTTPException(
                status_code=500,
                detail="Hugging Face provider requires an endpoint URL"
            )

        return HuggingFaceGrammarService(
            api_key=api_key,
            endpoint=provider.endpoint,
            model=model,
            parameters=parameters
        )
