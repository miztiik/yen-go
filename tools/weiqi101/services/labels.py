"""Pure helpers for resolving CJK chapter/book labels into English slugs.

Extracted from ``receiver.py`` so routing code stays focused on HTTP I/O
and these utilities can be reused / unit-tested in isolation.

Public API:
    * ``has_cjk(s)`` — True iff string contains CJK ideograph or kana
    * ``slugify_ascii(text)`` — lowercase ASCII slug, dash-separated
    * ``resolve_label(visible, raw, context="")`` — full label resolution
      pipeline (visible → translate raw → fallback). Returns a dict with
      ``display`` / ``english`` / ``slug`` / ``raw`` / ``source`` keys.

Behavior is byte-identical to the previous receiver-internal versions;
``receiver.py`` re-exports these names with their leading-underscore
aliases (``_has_cjk`` etc.) so existing tests keep working.
"""

from __future__ import annotations

import logging
import re

from tools.core.chinese_translator import ChineseTranslator

logger = logging.getLogger(__name__)

_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# Lazy module-level translator — instantiated once on first use.
_translator: ChineseTranslator | None = None


def has_cjk(s: str) -> bool:
    """True if ``s`` contains any CJK ideograph or kana codepoint."""
    return bool(s) and bool(_CJK_RE.search(s))


def get_translator() -> ChineseTranslator:
    global _translator
    if _translator is None:
        _translator = ChineseTranslator(strict=False)
    return _translator


def slugify_ascii(text: str) -> str:
    """Lowercase ASCII slug with single dashes, stripped. Empty -> ''."""
    if not text:
        return ""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s


def resolve_label(
    visible: str | None,
    raw: str | None,
    *,
    context: str = "",
) -> dict[str, str]:
    """Resolve a CJK chapter/book label into an English slug + display form.

    Priority:
      1. ``visible`` if it is non-empty and contains no CJK (assume the
         browser translation extension already produced English).
      2. ``raw`` translated via ``ChineseTranslator``; if any English
         tokens result, use them.
      3. ``visible`` or ``raw`` raw fallback (still CJK — callers must
         decide how to slugify it).

    Returns a dict::

        {
            "display":   <best human-readable form>,   # may be CJK fallback
            "english":   <ascii lower-case form>,       # '' if none
            "slug":      <ascii dash-slug>,             # '' if none
            "raw":       <original CJK text or ''>,     # for traceability
            "source":    "visible|translated|fallback|empty",
        }

    The returned ``slug`` is safe to embed in filenames. When ``slug`` is
    empty the caller should substitute a numeric fallback (e.g. chapter
    number) rather than embedding raw CJK in filenames.
    """
    visible = (visible or "").strip()
    raw = (raw or "").strip()

    # 1. Trust visible if it is already non-CJK.
    if visible and not has_cjk(visible):
        slug = slugify_ascii(visible)
        if slug:
            return {
                "display": visible,
                "english": visible.lower(),
                "slug": slug,
                "raw": raw,
                "source": "visible",
            }

    # 2. Library-translate the raw CJK.
    if raw:
        try:
            res = get_translator().translate(raw)
            translated = (res.translated or "").strip()
        except Exception:
            logger.debug(
                "[LABEL] translator failed for %r (%s)", raw, context,
                exc_info=True,
            )
            translated = ""
        if translated and not has_cjk(translated):
            slug = slugify_ascii(translated)
            if slug:
                return {
                    "display": translated,
                    "english": translated.lower(),
                    "slug": slug,
                    "raw": raw,
                    "source": "translated",
                }

    # 3. Fallback — nothing usable; surface raw text + empty slug so the
    # caller can substitute a numeric label.
    fallback = visible or raw
    return {
        "display": fallback,
        "english": "",
        "slug": "",
        "raw": raw,
        "source": "fallback" if fallback else "empty",
    }
