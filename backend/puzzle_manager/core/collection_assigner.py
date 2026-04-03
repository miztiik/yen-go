"""Collection assignment based on source metadata matching against aliases.

Parallel to tagger.py: tagger reads SGF board content to detect techniques,
collection_assigner reads source metadata (paths, IDs) to assign collections.

Spec 128: Tsumego Collections V2
Research: R-002 (alias matching), R-009 (module design)
"""

import re
import unicodedata


def normalize(text: str) -> str:
    """Normalize text: logical lowercasing, NFKC."""
    return unicodedata.normalize('NFKC', text).lower()


def tokenize(text: str) -> list[str]:
    """Tokenize text into words, splitting on non-alphanumeric chars."""
    # Split by any character that is NOT a letter or number (e.g. / \ - _ . space)
    # Filter out empty strings
    return [t for t in re.split(r'[^a-z0-9]+', text) if t]


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """Check if 'needle' tokens appear contiguously in 'haystack'.

    Phrase matching: the tokens must appear in the exact order without gaps.
    """
    if not needle:
        return False

    n_len = len(needle)
    h_len = len(haystack)

    if n_len > h_len:
        return False

    for i in range(h_len - n_len + 1):
        if haystack[i : i + n_len] == needle:
            return True

    return False


def assign_collections(
    source_link: str,
    puzzle_id: str,
    existing_collections: list[str],
    alias_map: dict[str, str],
) -> list[str]:
    """Assign collection slugs based on source metadata matching against aliases.

    Uses phrase matching to support multi-word aliases (e.g. "Life and Death").

    Args:
        source_link: Original file path or URL from adapter.
        puzzle_id: Adapter-generated puzzle identifier.
        existing_collections: Already-assigned collection slugs.
        alias_map: Mapping from alias string to collection slug.

    Returns:
        Sorted, deduplicated list of collection slugs.
    """
    matched_slugs: set[str] = set(existing_collections)

    # 1. Prepare haystack tokens
    combined_text = f"{source_link or ''} {puzzle_id or ''}"
    norm_text = normalize(combined_text)
    haystack = tokenize(norm_text)

    if not haystack:
        return sorted(matched_slugs)

    # 2. Check each alias against the haystack
    for alias, slug in alias_map.items():
        if slug in matched_slugs:
            continue

        norm_alias = normalize(alias)
        needle = tokenize(norm_alias)

        if _is_subsequence(needle, haystack):
            matched_slugs.add(slug)

    return sorted(matched_slugs)
