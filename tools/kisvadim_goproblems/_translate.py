"""Translate CJK characters in SGF C[] and N[] comments.

Consolidates the duplicated logic from _step2_translate.py, _step2b_gap_fill.py,
_step2c_final_pass.py, and _step3_verify.py into reusable functions.

Usage (programmatic):
    from tools.kisvadim_goproblems._translate import translate_sgf_files, verify_no_cjk
    stats = translate_sgf_files(Path("external-sources/kisvadim-goproblems/MyDir"))
    vstats = verify_no_cjk(Path("external-sources/kisvadim-goproblems/MyDir"))

Usage (CLI):
    python -m tools.kisvadim_goproblems translate --source-dir "external-sources/..."
    python -m tools.kisvadim_goproblems verify --source-dir "external-sources/..."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.atomic_write import atomic_write_text
from tools.core.chinese_translator import ChineseTranslator

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
CJK_SEQ_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")
COMMENT_RE = re.compile(r"C\[([^\]]*(?:\\.[^\]]*)*)\]")
NODE_NAME_RE = re.compile(r"N\[([^\]]*(?:\\.[^\]]*)*)\]")

# Publisher watermark to strip entirely (FeiYang Go product branding)
_WATERMARK_PHRASES = frozenset({"飞扬围棋出品"})


def _unescape_sgf(text: str) -> str:
    """Unescape SGF bracket escaping."""
    return text.replace("\\]", "]").replace("\\\\", "\\")


def _escape_sgf(text: str) -> str:
    """Re-escape for SGF bracket format."""
    return text.replace("\\", "\\\\").replace("]", "\\]")


@dataclass
class TranslateStats:
    """Statistics from a translate run."""

    total: int = 0
    modified: int = 0
    comments_translated: int = 0
    files_with_remaining_cjk: int = 0
    remaining_cjk_fragments: set[str] = field(default_factory=set)
    error_files: list[str] = field(default_factory=list)
    errors: int = 0


@dataclass
class VerifyStats:
    """Statistics from a CJK verification scan."""

    total: int = 0
    files_with_cjk: int = 0
    comments_with_cjk: int = 0
    unique_fragments: set[str] = field(default_factory=set)
    problem_files: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.files_with_cjk == 0


def _translate_property_value(
    inner: str,
    translator: ChineseTranslator,
    stats: TranslateStats,
) -> str | None:
    """Translate a single property value if it contains CJK.

    Returns the translated (and re-escaped) value, or None if no change needed.
    """
    unescaped = _unescape_sgf(inner)

    if not CJK_RE.search(unescaped):
        return None

    # Strip watermark phrases
    cleaned = unescaped
    for phrase in _WATERMARK_PHRASES:
        cleaned = cleaned.replace(phrase, "")

    # Clean up leftover whitespace from watermark removal
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned).strip()

    if not cleaned:
        # Entire value was watermark — return empty
        return _escape_sgf("")

    if not CJK_RE.search(cleaned):
        # After watermark removal, no CJK left
        return _escape_sgf(cleaned)

    result = translator.translate(cleaned)
    stats.comments_translated += 1

    if result.has_missing_terms:
        stats.remaining_cjk_fragments.update(result.missing_terms)

    return _escape_sgf(result.translated)


def translate_sgf_files(
    source_dir: Path,
    *,
    dry_run: bool = False,
) -> TranslateStats:
    """Translate CJK in C[] and N[] properties across all SGFs in a directory.

    Args:
        source_dir: Directory to scan (recursive).
        dry_run: If True, report changes without writing files.

    Returns:
        TranslateStats with counts and remaining fragments.
    """
    stats = TranslateStats()
    translator = ChineseTranslator()

    sgf_files = sorted(source_dir.rglob("*.sgf"))
    stats.total = len(sgf_files)

    for sgf_path in sgf_files:
        try:
            content = sgf_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            stats.errors += 1
            stats.error_files.append(str(sgf_path.name))
            continue

        def _replace_comment(m: re.Match) -> str:
            translated = _translate_property_value(m.group(1), translator, stats)
            if translated is not None:
                return f"C[{translated}]"
            return m.group(0)

        def _replace_node_name(m: re.Match) -> str:
            translated = _translate_property_value(m.group(1), translator, stats)
            if translated is not None:
                return f"N[{translated}]"
            return m.group(0)

        new_content = COMMENT_RE.sub(_replace_comment, content)
        new_content = NODE_NAME_RE.sub(_replace_node_name, new_content)

        if new_content != content:
            stats.modified += 1
            if not dry_run:
                atomic_write_text(sgf_path, new_content, encoding="utf-8")

        # Check for remaining CJK
        remaining_in_file: set[str] = set()
        for pattern in (COMMENT_RE, NODE_NAME_RE):
            for m in pattern.finditer(new_content):
                inner = _unescape_sgf(m.group(1))
                cjk_seqs = CJK_SEQ_RE.findall(inner)
                remaining_in_file.update(cjk_seqs)

        if remaining_in_file:
            stats.files_with_remaining_cjk += 1
            stats.remaining_cjk_fragments.update(remaining_in_file)

    return stats


def verify_no_cjk(source_dir: Path) -> VerifyStats:
    """Read-only scan for remaining CJK in C[] and N[] properties.

    Args:
        source_dir: Directory to scan (recursive).

    Returns:
        VerifyStats with counts and problem files.
    """
    stats = VerifyStats()

    sgf_files = sorted(source_dir.rglob("*.sgf"))
    stats.total = len(sgf_files)

    for sgf_path in sgf_files:
        try:
            content = sgf_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        file_has_cjk = False

        for pattern in (COMMENT_RE, NODE_NAME_RE):
            for m in pattern.finditer(content):
                inner = _unescape_sgf(m.group(1))
                cjk_seqs = CJK_SEQ_RE.findall(inner)
                if cjk_seqs:
                    stats.comments_with_cjk += 1
                    stats.unique_fragments.update(cjk_seqs)
                    if not file_has_cjk:
                        file_has_cjk = True
                        stats.files_with_cjk += 1
                        stats.problem_files.append(sgf_path.name)

    return stats
