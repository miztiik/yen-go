"""
Japanese text translation helper for OGS puzzles.

Translates Japanese Go terminology using config/jp-en-dictionary.json.
Ported from backend/puzzle_manager/adapters/ogs/translator.py.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.paths import rel_path

logger = logging.getLogger("ogs.translator")


class TranslationError(Exception):
    """Raised when translation fails in strict mode."""

    def __init__(self, term: str, context: str = ""):
        self.term = term
        self.context = context
        super().__init__(f"Missing translation for '{term}'" + (f" in {context}" if context else ""))


@dataclass
class TranslationResult:
    """Result of translation attempt."""

    original: str
    translated: str
    missing_terms: list[str] = field(default_factory=list)

    @property
    def has_missing_terms(self) -> bool:
        """Check if any terms were not translated."""
        return len(self.missing_terms) > 0


class JapaneseTranslator:
    """Translator for Japanese Go terminology.

    Loads dictionary from config/jp-en-dictionary.json and provides
    translation with configurable strict/lenient modes.

    Usage:
        translator = JapaneseTranslator(dictionary_path, strict=False)
        result = translator.translate("黒先 生き")
        # result.translated = "Black to play live"
    """

    def __init__(self, dictionary_path: Path | None = None, strict: bool = False):
        """Initialize translator with dictionary.

        Args:
            dictionary_path: Path to jp-en-dictionary.json. If None, uses default.
            strict: If True, raise TranslationError on first missing term.
                   If False, collect all missing terms and continue.

        Raises:
            FileNotFoundError: If dictionary file not found (only in strict mode).
        """
        self.strict = strict
        self._dictionary: dict[str, str] = {}
        self._missing_terms: set[str] = set()

        if dictionary_path is None:
            dictionary_path = self._get_default_dictionary_path()

        self._load_dictionary(dictionary_path)

    def _get_default_dictionary_path(self) -> Path:
        """Get default path to jp-en-dictionary.json."""
        # tools/ogs/translator.py -> config/jp-en-dictionary.json
        return Path(__file__).parent.parent.parent / "config" / "jp-en-dictionary.json"

    def _load_dictionary(self, path: Path) -> None:
        """Load and flatten dictionary from JSON file."""
        if not path.exists():
            if self.strict:
                raise FileNotFoundError(f"Dictionary file not found: {rel_path(path)}")
            logger.warning(f"Dictionary file not found: {rel_path(path)}")
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Flatten nested categories into single lookup dict
            for key, value in data.items():
                if key.startswith("_"):  # Skip metadata
                    continue
                if isinstance(value, dict):
                    # Nested category: {"player_and_turn": {"黒": "Black", ...}}
                    for jp_term, en_term in value.items():
                        self._dictionary[jp_term] = en_term
                elif isinstance(value, str):
                    # Direct mapping: {"黒": "Black"}
                    self._dictionary[key] = value

            logger.debug(f"Loaded {len(self._dictionary)} terms from dictionary")

        except (json.JSONDecodeError, OSError) as e:
            if self.strict:
                raise
            logger.warning(f"Failed to load dictionary: {e}")

    def translate(self, text: str, context: str = "") -> TranslationResult:
        """Translate Japanese terms in text.

        Args:
            text: Input text containing Japanese terms
            context: Optional context for error messages (e.g., puzzle ID)

        Returns:
            TranslationResult with translated text and any missing terms.

        Raises:
            TranslationError: In strict mode, when a term is not found.
        """
        if not text:
            return TranslationResult(original=text, translated=text)

        result_text = text
        missing = []

        # Sort by length (longest first) to match longer terms before shorter
        sorted_terms = sorted(self._dictionary.keys(), key=len, reverse=True)

        for jp_term in sorted_terms:
            if jp_term in result_text:
                result_text = result_text.replace(jp_term, self._dictionary[jp_term])

        # Check for remaining Japanese characters
        remaining_jp = self._find_japanese_chars(result_text)
        if remaining_jp:
            missing.extend(remaining_jp)
            self._missing_terms.update(remaining_jp)

            if self.strict and remaining_jp:
                raise TranslationError(remaining_jp[0], context)

        return TranslationResult(
            original=text,
            translated=result_text,
            missing_terms=missing,
        )

    def _find_japanese_chars(self, text: str) -> list[str]:
        """Find sequences of Japanese characters not yet translated.

        Returns list of unique Japanese character sequences.
        """
        # Match hiragana, katakana, and kanji
        # Hiragana: U+3040-U+309F
        # Katakana: U+30A0-U+30FF
        # Kanji: U+4E00-U+9FFF (CJK Unified Ideographs)
        pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+'
        matches = re.findall(pattern, text)
        return list(set(matches))  # Return unique terms

    def get_all_missing_terms(self) -> set[str]:
        """Get all missing terms encountered across all translations.

        Useful in lenient mode to collect all missing terms for reporting.
        """
        return self._missing_terms.copy()

    def reset_missing_terms(self) -> None:
        """Reset the missing terms tracker."""
        self._missing_terms.clear()


# Global singleton instance
_translator: JapaneseTranslator | None = None


def get_translator(strict: bool = False) -> JapaneseTranslator:
    """Get the global JapaneseTranslator instance.

    Args:
        strict: If True, raise on missing terms. Default False.
    """
    global _translator
    if _translator is None:
        _translator = JapaneseTranslator(strict=strict)
    return _translator


def translate_text(text: str, context: str = "") -> str:
    """Convenience function to translate Japanese text.

    Args:
        text: Text to translate
        context: Context for logging (e.g., puzzle ID)

    Returns:
        Translated text (best effort, keeps untranslated terms)
    """
    result = get_translator().translate(text, context)
    return result.translated
