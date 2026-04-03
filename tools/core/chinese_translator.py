"""
Chinese text translation helper for Go puzzles.

Translates Chinese Go terminology using config/cn-en-dictionary.json.
Mirrors tools/ogs/translator.py (JapaneseTranslator) with added alias
resolution for traditional-to-simplified character normalization.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.paths import rel_path

logger = logging.getLogger("core.chinese_translator")


class TranslationError(Exception):
    """Raised when translation fails in strict mode."""

    def __init__(self, term: str, context: str = ""):
        self.term = term
        self.context = context
        super().__init__(
            f"Missing translation for '{term}'"
            + (f" in {context}" if context else "")
        )


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


class ChineseTranslator:
    """Translator for Chinese Go terminology.

    Loads dictionary from config/cn-en-dictionary.json and provides
    translation with configurable strict/lenient modes. Supports an
    ``_aliases`` section for traditional-to-simplified character
    normalization applied before dictionary lookup.

    Usage:
        translator = ChineseTranslator(dictionary_path, strict=False)
        result = translator.translate("黑先 活")
        # result.translated = "Black to play live"
    """

    def __init__(
        self,
        dictionary_path: Path | None = None,
        strict: bool = False,
    ):
        """Initialize translator with dictionary.

        Args:
            dictionary_path: Path to cn-en-dictionary.json. If None, uses default.
            strict: If True, raise TranslationError on first missing term.
                   If False, collect all missing terms and continue.

        Raises:
            FileNotFoundError: If dictionary file not found (only in strict mode).
        """
        self.strict = strict
        self._dictionary: dict[str, str] = {}
        self._aliases: dict[str, str] = {}
        self._missing_terms: set[str] = set()

        if dictionary_path is None:
            dictionary_path = self._get_default_dictionary_path()

        self._load_dictionary(dictionary_path)

    def _get_default_dictionary_path(self) -> Path:
        """Get default path to cn-en-dictionary.json."""
        # tools/core/chinese_translator.py -> tools/core -> tools -> project root -> config/
        return Path(__file__).parent.parent.parent / "config" / "cn-en-dictionary.json"

    def _load_dictionary(self, path: Path) -> None:
        """Load and flatten dictionary from JSON file.

        Populates ``self._dictionary`` with flattened category term mappings
        and ``self._aliases`` with character-level alias mappings. Keys
        starting with ``_`` (other than ``_aliases``) are skipped.
        """
        if not path.exists():
            if self.strict:
                raise FileNotFoundError(
                    f"Dictionary file not found: {rel_path(path)}"
                )
            logger.warning("Dictionary file not found: %s", rel_path(path))
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Load aliases section (traditional -> simplified mappings)
            aliases_section = data.get("_aliases")
            if isinstance(aliases_section, dict):
                for source, target in aliases_section.items():
                    if isinstance(target, str):
                        self._aliases[source] = target
                logger.debug(
                    "Loaded %d aliases from dictionary", len(self._aliases)
                )

            # Flatten nested categories into single lookup dict
            for key, value in data.items():
                if key.startswith("_"):  # Skip metadata and aliases
                    continue
                if isinstance(value, dict):
                    # Nested category: {"player_and_turn": {"黑": "Black", ...}}
                    for cn_term, en_term in value.items():
                        self._dictionary[cn_term] = en_term
                elif isinstance(value, str):
                    # Direct mapping (shouldn't occur per schema, but handle gracefully)
                    self._dictionary[key] = value

            logger.debug(
                "Loaded %d terms from dictionary", len(self._dictionary)
            )

        except (json.JSONDecodeError, OSError) as e:
            if self.strict:
                raise
            logger.warning("Failed to load dictionary: %s", e)

    def _resolve_aliases(self, text: str) -> str:
        """Resolve character aliases in text before dictionary lookup.

        Performs longest-first replacement of alias mappings (e.g.,
        traditional Chinese characters to simplified equivalents).

        Args:
            text: Input text potentially containing aliased characters.

        Returns:
            Text with all known aliases replaced.
        """
        if not self._aliases:
            return text

        # Sort by length (longest first) to match multi-character aliases
        # before single-character ones
        sorted_aliases = sorted(self._aliases.keys(), key=len, reverse=True)

        for alias in sorted_aliases:
            if alias in text:
                text = text.replace(alias, self._aliases[alias])

        return text

    @staticmethod
    def _is_cjk_char(char: str) -> bool:
        """Check if a character is a CJK Unified Ideograph."""
        cp = ord(char)
        return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)

    def _join_tokens(self, tokens: list[str]) -> str:
        """Join translated tokens with intelligent spacing.

        Inserts spaces between adjacent Latin words and between
        Latin/CJK boundaries. Preserves CJK-CJK adjacency (no space)
        and digit-CJK adjacency (e.g., 第1章 stays compact).
        """
        if not tokens:
            return ""

        parts: list[str] = []
        for token in tokens:
            if not token:
                continue
            if parts:
                prev = parts[-1][-1]
                curr = token[0]
                prev_letter = prev.isascii() and prev.isalpha()
                curr_letter = curr.isascii() and curr.isalpha()
                prev_cjk = self._is_cjk_char(prev)
                curr_cjk = self._is_cjk_char(curr)
                prev_digit = prev.isdigit()
                needs_space = (
                    (prev_letter and curr_letter)
                    or (prev_letter and curr_cjk)
                    or (prev_cjk and curr_letter)
                    or (prev_digit and curr_letter)
                    or (prev_letter and curr.isdigit())
                )
                if needs_space:
                    parts.append(" ")
            parts.append(token)

        result = "".join(parts)
        # Space after closing brackets/parens before word characters
        result = re.sub(r"([)\]])\s*([a-zA-Z\u4E00-\u9FFF])", r"\1 \2", result)
        # Space before opening brackets/parens after word characters
        result = re.sub(r"([a-zA-Z0-9\u4E00-\u9FFF])([(\[])", r"\1 \2", result)
        # Collapse multiple spaces
        result = re.sub(r" +", " ", result)
        return result.strip()

    def translate(self, text: str, context: str = "") -> TranslationResult:
        """Translate Chinese terms in text.

        Pipeline: resolve aliases -> position-based longest-match tokenization
        -> intelligent spacing -> detect remaining untranslated CJK.

        Uses position-based scanning instead of global str.replace() to:
        (a) prevent short terms from matching inside longer compound words
        (b) produce properly spaced English output

        Args:
            text: Input text containing Chinese terms.
            context: Optional context for error messages (e.g., puzzle ID).

        Returns:
            TranslationResult with translated text and any missing terms.

        Raises:
            TranslationError: In strict mode, when a term is not found.
        """
        if not text:
            return TranslationResult(original=text, translated=text)

        # Step 1: Resolve aliases (e.g., traditional -> simplified)
        work_text = self._resolve_aliases(text)

        # Step 2: Position-based longest-match tokenization
        sorted_terms = sorted(
            self._dictionary.keys(), key=len, reverse=True
        )

        tokens: list[str] = []
        pos = 0
        while pos < len(work_text):
            # Non-CJK characters: collect as a single pass-through token
            if not self._is_cjk_char(work_text[pos]):
                start = pos
                while pos < len(work_text) and not self._is_cjk_char(
                    work_text[pos]
                ):
                    pos += 1
                tokens.append(work_text[start:pos])
                continue

            # CJK character: try longest dictionary match at this position
            matched = False
            for cn_term in sorted_terms:
                end = pos + len(cn_term)
                if end <= len(work_text) and work_text[pos:end] == cn_term:
                    tokens.append(self._dictionary[cn_term])
                    pos = end
                    matched = True
                    break

            if not matched:
                # Unmatched CJK character: pass through as-is
                tokens.append(work_text[pos])
                pos += 1

        # Step 3: Join tokens with proper spacing
        result_text = self._join_tokens(tokens)

        # Step 4: Check for remaining Chinese characters
        missing: list[str] = []
        remaining_cn = self._find_chinese_chars(result_text)
        if remaining_cn:
            missing.extend(remaining_cn)
            self._missing_terms.update(remaining_cn)

            if self.strict and remaining_cn:
                raise TranslationError(remaining_cn[0], context)

        return TranslationResult(
            original=text,
            translated=result_text,
            missing_terms=missing,
        )

    def _find_chinese_chars(self, text: str) -> list[str]:
        """Find sequences of Chinese characters not yet translated.

        Matches CJK Unified Ideographs (U+4E00-U+9FFF) and CJK Unified
        Ideographs Extension A (U+3400-U+4DBF). Does NOT match Hiragana
        or Katakana ranges to avoid false positives on Japanese text.

        Returns:
            List of unique Chinese character sequences found in text.
        """
        pattern = r"[\u4E00-\u9FFF\u3400-\u4DBF]+"
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
_translator: ChineseTranslator | None = None


def get_chinese_translator(strict: bool = False) -> ChineseTranslator:
    """Get the global ChineseTranslator instance.

    Args:
        strict: If True, raise on missing terms. Default False.
    """
    global _translator
    if _translator is None:
        _translator = ChineseTranslator(strict=strict)
    return _translator


def translate_chinese_text(text: str, context: str = "") -> str:
    """Convenience function to translate Chinese text.

    Args:
        text: Text to translate.
        context: Context for logging (e.g., puzzle ID).

    Returns:
        Translated text (best effort, keeps untranslated terms).
    """
    result = get_chinese_translator().translate(text, context)
    return result.translated
