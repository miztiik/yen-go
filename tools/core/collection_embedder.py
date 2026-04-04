"""Embed YL[slug:chapter/position] into SGF files from directory structure.

Pre-pipeline utility that resolves directory names to collection slugs
and writes the `YL` property into each SGF file.

Does NOT import from backend/ (architecture boundary).

Usage:
    from tools.core.collection_embedder import (
        embed_collections,
        restore_backups,
        PhraseMatchStrategy,
        ManifestLookupStrategy,
        FilenamePatternStrategy,
        EmbedResult,
        EmbedSummary,
    )

    matcher = CollectionMatcher()
    strategy = PhraseMatchStrategy(matcher)
    logger = setup_logging(source_dir, "embed", verbose=True)
    summary = embed_collections(source_dir, strategy, matcher, logger)
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from tools.core.atomic_write import atomic_write_text
from tools.core.checkpoint import ToolCheckpoint, load_checkpoint, save_checkpoint
from tools.core.collection_matcher import CollectionMatcher
from tools.core.logging import StructuredLogger
from tools.core.sgf_builder import publish_sgf
from tools.core.sgf_parser import SGFParseError, parse_sgf

_logger = logging.getLogger("tools.core.collection_embedder")

BACKUP_SUFFIX = ".yl-backup"
CHECKPOINT_FILENAME = ".embed-checkpoint.json"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class EmbedResult:
    """Resolution result from a strategy."""

    slug: str
    chapter: int | str  # 0 = no chapter concept; string for named chapters (e.g. "seki")
    position: int  # 1-based position within chapter


@dataclass
class EmbedSummary:
    """Aggregate statistics for an embed run."""

    total_files: int = 0
    embedded: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    already_embedded: int = 0
    conflicts: int = 0

    @property
    def coverage_pct(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.embedded + self.updated + self.already_embedded) / self.total_files * 100.0


@dataclass
class EmbedCheckpoint(ToolCheckpoint):
    """Checkpoint for embed progress — tracks completed directories."""

    completed_dirs: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Strategy interface + registry
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbedStrategy(Protocol):
    """Resolves an SGF file path + context to a YL embed value."""

    def resolve(
        self, sgf_path: Path, dir_name: str, filename: str
    ) -> EmbedResult | None:
        """Given an SGF file path and its context, return YL value to embed."""
        ...


STRATEGIES: dict[str, type[EmbedStrategy]] = {}


# ---------------------------------------------------------------------------
# Strategy A: PhraseMatchStrategy
# ---------------------------------------------------------------------------


class PhraseMatchStrategy:
    """Resolves directory name → collection slug via CollectionMatcher.

    Position = enumeration order of SGF files within directory (sorted by
    filename).  Chapter = 0 (no chapter concept).
    """

    def __init__(self, matcher: CollectionMatcher) -> None:
        self._matcher = matcher
        # Cached per-directory position map: dir_path -> {filename: position}
        self._position_cache: dict[str, dict[str, int]] = {}

    def prime_directory(self, dir_path: Path, filenames: list[str]) -> None:
        """Pre-calculate position numbers for all SGF files in a directory."""
        sorted_names = sorted(filenames)
        self._position_cache[str(dir_path)] = {
            name: idx + 1 for idx, name in enumerate(sorted_names)
        }

    def resolve(
        self, sgf_path: Path, dir_name: str, filename: str
    ) -> EmbedResult | None:
        match = self._matcher.match(dir_name)
        if match is None:
            return None

        positions = self._position_cache.get(str(sgf_path.parent), {})
        position = positions.get(filename, 0)

        return EmbedResult(slug=match.slug, chapter=0, position=position)


STRATEGIES["phrase_match"] = PhraseMatchStrategy  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Strategy B: ManifestLookupStrategy
# ---------------------------------------------------------------------------


class ManifestLookupStrategy:
    """Strategy B: Look up puzzle by numeric ID in a JSONL manifest.

    Parses a JSONL file where each line (after the metadata header) is a
    collection record with ``name`` and ``puzzles`` (list of numeric IDs).
    Builds a reverse index mapping each puzzle ID to its collection name
    and 1-based position within that collection's ``puzzles`` array.
    """

    def __init__(self, jsonl_path: Path, matcher: CollectionMatcher) -> None:
        self._matcher = matcher
        # {puzzle_numeric_id: (collection_name, 1-based position)}
        self._reverse_index: dict[int, tuple[str, int]] = {}
        self._parse_jsonl(jsonl_path)

    def _parse_jsonl(self, jsonl_path: Path) -> None:
        """Parse JSONL and build reverse index."""
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("type") == "metadata":
                    continue
                name = record.get("name", "")
                puzzles = record.get("puzzles", [])
                for idx, puzzle_id in enumerate(puzzles):
                    # Only record first occurrence (earlier = higher-priority collection)
                    if puzzle_id not in self._reverse_index:
                        self._reverse_index[puzzle_id] = (name, idx + 1)

    @property
    def index_size(self) -> int:
        """Number of puzzle IDs in the reverse index."""
        return len(self._reverse_index)

    def resolve(
        self, sgf_path: Path, dir_name: str, filename: str
    ) -> EmbedResult | None:
        # Extract numeric puzzle ID from filename (e.g. "ogs-12345.sgf" → 12345)
        stem = sgf_path.stem
        parts = stem.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            puzzle_id = int(parts[1])
        elif stem.isdigit():
            puzzle_id = int(stem)
        else:
            return None

        if puzzle_id not in self._reverse_index:
            return None

        collection_name, position = self._reverse_index[puzzle_id]
        match = self._matcher.match(collection_name)
        if match is None:
            return None

        return EmbedResult(slug=match.slug, chapter=0, position=position)


STRATEGIES["manifest_lookup"] = ManifestLookupStrategy  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Strategy C: FilenamePatternStrategy
# ---------------------------------------------------------------------------


class FilenamePatternStrategy:
    """Strategy C: Extract collection/chapter/position from filename regex.

    Constructor takes a compiled regex with optional named groups
    ``level``, ``chapter``, and ``position``.  A ``level_map`` translates
    the captured level value to a name suitable for
    :meth:`CollectionMatcher.match`.
    """

    def __init__(
        self,
        pattern: re.Pattern[str],
        matcher: CollectionMatcher,
        *,
        level_map: dict[str, str] | None = None,
    ) -> None:
        self._pattern = pattern
        self._matcher = matcher
        self._level_map: dict[str, str] = level_map or {}

    def resolve(
        self, sgf_path: Path, dir_name: str, filename: str
    ) -> EmbedResult | None:
        m = self._pattern.search(filename)
        if m is None:
            return None

        groups = m.groupdict()
        level_raw = groups.get("level", "")
        chapter = int(groups["chapter"]) if groups.get("chapter") else 0
        position = int(groups["position"]) if groups.get("position") else 0

        level_name = self._level_map.get(level_raw, level_raw)
        match = self._matcher.match(level_name)
        if match is None:
            return None

        return EmbedResult(slug=match.slug, chapter=chapter, position=position)


STRATEGIES["filename_pattern"] = FilenamePatternStrategy  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Strategy D: DirectoryChapterStrategy
# ---------------------------------------------------------------------------


class DirectoryChapterStrategy:
    """Strategy D: Map directory names to chapter slugs via static mapping.

    Constructor takes a dict mapping directory names to chapter slugs and a
    fixed collection slug.  Position is derived from sorted file order within
    each directory (1-based).

    Designed for sources where chapters correspond to subdirectories with
    a fixed collection slug (e.g. Essential Go Techniques, Yamada Kimio).
    """

    def __init__(
        self,
        chapter_map: dict[str, str],
        collection_slug: str,
    ) -> None:
        self._chapter_map = chapter_map
        self._collection_slug = collection_slug
        self._position_cache: dict[str, dict[str, int]] = {}

    def prime_directory(self, dir_path: Path, filenames: list[str]) -> None:
        """Pre-calculate position numbers for all SGF files in a directory."""
        sorted_names = sorted(filenames)
        self._position_cache[str(dir_path)] = {
            name: idx + 1 for idx, name in enumerate(sorted_names)
        }

    def resolve(
        self, sgf_path: Path, dir_name: str, filename: str
    ) -> EmbedResult | None:
        chapter_slug = self._chapter_map.get(dir_name)
        if chapter_slug is None:
            return None

        positions = self._position_cache.get(str(sgf_path.parent), {})
        position = positions.get(filename, 0)

        return EmbedResult(
            slug=self._collection_slug,
            chapter=chapter_slug,
            position=position,
        )


STRATEGIES["directory_chapter"] = DirectoryChapterStrategy  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# YL helpers
# ---------------------------------------------------------------------------


def _format_yl(result: EmbedResult) -> str:
    """Format an EmbedResult as a YL value string."""
    return f"{result.slug}:{result.chapter}/{result.position}"


def _extract_slug(yl_entry: str) -> str:
    """Extract the slug portion from a YL entry like 'slug:chapter/pos'."""
    return yl_entry.split(":")[0] if ":" in yl_entry else yl_entry


# ---------------------------------------------------------------------------
# Core embed logic
# ---------------------------------------------------------------------------


def embed_collections(
    source_dir: Path,
    strategy: EmbedStrategy,
    matcher: CollectionMatcher,
    logger: StructuredLogger,
    *,
    dry_run: bool = False,
    backup: bool = True,
    checkpoint: EmbedCheckpoint | None = None,
) -> EmbedSummary:
    """Walk source_dir and embed YL into matching SGF files.

    Args:
        source_dir: Root directory to walk.
        strategy: Resolution strategy to use.
        matcher: CollectionMatcher instance (used by some strategies).
        logger: Structured logger for JSONL events.
        dry_run: If True, report what would change without writing.
        backup: If True (default), create .yl-backup before writing.
        checkpoint: Optional checkpoint for resume support.

    Returns:
        EmbedSummary with aggregate counts.
    """
    summary = EmbedSummary()

    # Load or create checkpoint
    if checkpoint is None:
        checkpoint = load_checkpoint(
            source_dir, EmbedCheckpoint, CHECKPOINT_FILENAME
        ) or EmbedCheckpoint()

    completed_set = set(checkpoint.completed_dirs)

    # Discover directories containing SGF files
    sgf_dirs = _discover_sgf_dirs(source_dir)

    logger.event(
        "embed_summary",
        f"Discovered {len(sgf_dirs)} directories with SGF files",
        total_dirs=len(sgf_dirs),
        dry_run=dry_run,
    )

    for dir_path, sgf_files in sgf_dirs:
        dir_key = str(dir_path.relative_to(source_dir))

        # Skip already-checkpointed directories
        if dir_key in completed_set:
            continue

        dir_name = dir_path.name

        # Prime strategy position cache
        if hasattr(strategy, "prime_directory"):
            strategy.prime_directory(dir_path, sgf_files)  # type: ignore[attr-defined]

        dir_embedded = 0
        dir_updated = 0
        dir_skipped = 0
        dir_errors = 0
        dir_already = 0
        dir_conflicts = 0

        logger.event(
            "folder_start",
            f"Processing directory: {dir_name} ({len(sgf_files)} SGF files)",
            dir_name=dir_name,
            dir_key=dir_key,
            file_count=len(sgf_files),
        )

        sorted_files = sorted(sgf_files)
        file_count = len(sorted_files)
        for file_idx, filename in enumerate(sorted_files, 1):
            sgf_path = dir_path / filename
            summary.total_files += 1

            logger.event(
                "file_progress",
                f"[{file_idx}/{file_count}] {filename}",
                dir_name=dir_name,
                file_idx=file_idx,
                file_count=file_count,
                filename=filename,
            )

            try:
                result = strategy.resolve(sgf_path, dir_name, filename)
            except Exception as exc:
                logger.event(
                    "folder_error",
                    f"Strategy error: {sgf_path}: {exc}",
                    level=logging.ERROR,
                    path=str(sgf_path),
                    error=str(exc),
                )
                dir_errors += 1
                continue

            if result is None:
                dir_skipped += 1
                continue

            try:
                outcome = _embed_single_file(
                    sgf_path, result, logger, dry_run=dry_run, backup=backup
                )
            except Exception as exc:
                logger.event(
                    "folder_error",
                    f"Embed error: {sgf_path}: {exc}",
                    level=logging.ERROR,
                    path=str(sgf_path),
                    error=str(exc),
                )
                dir_errors += 1
                continue

            if outcome == "embedded":
                dir_embedded += 1
            elif outcome == "updated":
                dir_updated += 1
            elif outcome == "already_embedded":
                dir_already += 1
            elif outcome == "conflict":
                dir_conflicts += 1
            elif outcome == "error":
                dir_errors += 1

        summary.embedded += dir_embedded
        summary.updated += dir_updated
        summary.skipped += dir_skipped
        summary.errors += dir_errors
        summary.already_embedded += dir_already
        summary.conflicts += dir_conflicts

        logger.event(
            "folder_done",
            f"{dir_name}: embedded={dir_embedded} updated={dir_updated} "
            f"already={dir_already} conflicts={dir_conflicts} "
            f"skip={dir_skipped} err={dir_errors}",
            dir_name=dir_name,
            dir_key=dir_key,
            embedded=dir_embedded,
            updated=dir_updated,
            already_embedded=dir_already,
            conflicts=dir_conflicts,
            skipped=dir_skipped,
            errors=dir_errors,
        )

        # Save checkpoint after each directory
        if not dry_run:
            checkpoint.completed_dirs.append(dir_key)
            save_checkpoint(checkpoint, source_dir, CHECKPOINT_FILENAME)

    logger.event(
        "embed_summary",
        f"Done: embedded={summary.embedded} updated={summary.updated} "
        f"already={summary.already_embedded} conflicts={summary.conflicts} "
        f"skipped={summary.skipped} errors={summary.errors} "
        f"coverage={summary.coverage_pct:.1f}%",
        **asdict(summary),
    )

    return summary


def _discover_sgf_dirs(root: Path) -> list[tuple[Path, list[str]]]:
    """Return (dir_path, [sgf_filenames]) for every dir with .sgf files."""
    results: list[tuple[Path, list[str]]] = []
    for dir_path in sorted(root.rglob("*")):
        if not dir_path.is_dir():
            continue
        sgf_files = [
            f.name for f in dir_path.iterdir() if f.suffix.lower() == ".sgf"
        ]
        if sgf_files:
            results.append((dir_path, sgf_files))
    # Also check root itself
    root_sgfs = [f.name for f in root.iterdir() if f.is_file() and f.suffix.lower() == ".sgf"]
    if root_sgfs:
        results.insert(0, (root, root_sgfs))
    return results


def _embed_single_file(
    sgf_path: Path,
    result: EmbedResult,
    logger: StructuredLogger,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> str:
    """Embed YL into a single SGF file.

    Returns one of: 'embedded', 'updated', 'already_embedded', 'conflict', 'error'.
    """
    content = sgf_path.read_text(encoding="utf-8")

    try:
        tree = parse_sgf(content)
    except SGFParseError as exc:
        logger.event(
            "folder_error",
            f"Parse error: {sgf_path.name}: {exc}",
            level=logging.WARNING,
            path=str(sgf_path),
            error=str(exc),
        )
        return "error"

    existing = tree.yengo_props.collections
    new_slug = result.slug
    yl_value = _format_yl(result)

    if existing:
        existing_slugs = [_extract_slug(e) for e in existing]
        if new_slug in existing_slugs:
            # Slug matches — check if the full value (with chapter/position) also matches
            idx = existing_slugs.index(new_slug)
            if existing[idx] == yl_value:
                logger.event(
                    "collection_skip",
                    f"Already embedded YL[{yl_value}] in {sgf_path.name}",
                    path=str(sgf_path),
                    yl=yl_value,
                )
                return "already_embedded"
            # Slug matches but chapter/position differs — update in place
            old_yl = existing[idx]
            existing[idx] = yl_value
            tree.yengo_props.collections = existing
            return _write_sgf(sgf_path, tree, yl_value, logger, dry_run=dry_run, backup=backup, action="updated", old_yl=old_yl)
        # Different slug(s) present — conflict
        logger.event(
            "folder_error",
            f"Conflict: {sgf_path.name} has YL={existing}, want slug={new_slug}",
            level=logging.WARNING,
            path=str(sgf_path),
            existing=existing,
            wanted=new_slug,
        )
        return "conflict"

    # No existing YL — embed
    tree.yengo_props.collections = [yl_value]
    return _write_sgf(sgf_path, tree, yl_value, logger, dry_run=dry_run, backup=backup, action="embedded")


def _write_sgf(
    sgf_path: Path,
    tree: object,
    yl_value: str,
    logger: StructuredLogger,
    *,
    dry_run: bool = False,
    backup: bool = True,
    action: str = "embedded",
    old_yl: str | None = None,
) -> str:
    """Write SGF and log. Returns the action string."""
    new_content = publish_sgf(tree)

    old_info = f" (was YL[{old_yl}])" if old_yl else ""

    if dry_run:
        label = "Would embed" if action == "embedded" else "Would update"
        logger.event(
            "collection_embed",
            f"[DRY-RUN] {label} YL[{yl_value}] in {sgf_path.name}{old_info}",
            path=str(sgf_path),
            yl=yl_value,
            old_yl=old_yl,
            dry_run=True,
        )
        return action

    # Create backup before writing (unless disabled)
    if backup:
        backup_path = sgf_path.with_suffix(sgf_path.suffix + BACKUP_SUFFIX)
        if not backup_path.exists():
            shutil.copy2(sgf_path, backup_path)

    atomic_write_text(sgf_path, new_content)

    verb = "Embedded" if action == "embedded" else "Updated"
    logger.event(
        "collection_embed",
        f"{verb} YL[{yl_value}] in {sgf_path.name}{old_info}",
        path=str(sgf_path),
        yl=yl_value,
        old_yl=old_yl,
    )
    return action


# ---------------------------------------------------------------------------
# Restore backups
# ---------------------------------------------------------------------------


def restore_backups(
    source_dir: Path,
    logger: StructuredLogger | None = None,
) -> int:
    """Scan for .yl-backup files and restore originals.

    Returns the number of files restored.
    """
    restored = 0
    for backup_path in sorted(source_dir.rglob(f"*{BACKUP_SUFFIX}")):
        original = backup_path.with_suffix("")  # strip .yl-backup
        # .sgf.yl-backup → .sgf  (suffix chain)
        stem = str(backup_path)
        if stem.endswith(BACKUP_SUFFIX):
            original = Path(stem[: -len(BACKUP_SUFFIX)])

        shutil.copy2(backup_path, original)
        backup_path.unlink()
        restored += 1
        if logger:
            logger.event(
                "collection_embed",
                f"Restored {original.name} from backup",
                path=str(original),
            )

    # Remove checkpoint since we're reverting
    cp_path = source_dir / CHECKPOINT_FILENAME
    if cp_path.exists():
        cp_path.unlink()

    return restored
