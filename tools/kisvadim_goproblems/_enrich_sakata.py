#!/usr/bin/env python3
"""Enrichment script for SAKATA EIO TESUJI (110 SGFs, 9 technique chapters).

Orchestrates: rename → prepare → embed YL[] → verify.

The source directory is flat (no subdirectories) with chapter structure
encoded in filename prefixes (e.g., Hane-s-01.sgf, Sagari-s-03.sgf).
"A" suffix files (e.g., Hane-s-01A.sgf) are reference diagrams and are
included in sequence right after their parent exercise.

Usage:
    python -m tools.kisvadim_goproblems._enrich_sakata [--step STEP] [--dry-run]

Steps: rename, embed-yl, verify, all (default: all)
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kisvadim.enrich_sakata")

SLUG = "sakata-eio-tesuji"
SOURCE_DIR_NAME = "SAKATA EIO TESUJI"
BASE = Path("external-sources/kisvadim-goproblems")
TOOL_DIR = Path("tools/kisvadim_goproblems")

# Chapter order follows the book's technique sections.
# Each tuple: (prefix_pattern, chapter_slug)
# Prefix matching is case-insensitive.
CHAPTERS: list[tuple[str, str]] = [
    ("Hane-s-", "hane"),
    ("Sagari-s-", "sagari"),
    ("Tsuke-s-", "tsuke"),
    ("oki-s-", "oki"),
    ("kiri-s-", "kiri"),
    ("Kosumi-s-", "kosumi"),
    ("Kake-s-", "kake"),
    ("Tobi-s-", "tobi"),
    ("Warikomi-s-", "warikomi"),
]


def _natural_sort_key(name: str) -> list:
    """Sort key that handles embedded numbers naturally.

    Handles 'A'/'a' suffix so e.g. 01A sorts right after 01:
    Hane-s-01 → [..., 1, ''] → before Hane-s-01A → [..., 1, 'a']
    """
    parts = re.split(r"(\d+)", name)
    result = []
    for c in parts:
        if c.isdigit():
            result.append((0, int(c), ""))
        else:
            result.append((1, 0, c.lower()))
    return result


def _classify_file(filename: str) -> str | None:
    """Return the chapter slug for a filename, or None if no match."""
    lower = filename.lower()
    for prefix, chapter in CHAPTERS:
        if lower.startswith(prefix.lower()):
            return chapter
    return None


# ── Step 3: Rename to 4-digit ──────────────────────────────────────────


def rename_to_4digit(source_dir: Path, *, dry_run: bool = False) -> dict[str, str]:
    """Rename SGFs to 0001.sgf .. 0110.sgf in chapter order.

    Returns the rename mapping {old_name: new_name}.
    """
    # Group files by chapter
    chapter_files: dict[str, list[Path]] = {ch: [] for _, ch in CHAPTERS}
    unmatched: list[Path] = []

    for sgf_path in source_dir.glob("*.sgf"):
        chapter = _classify_file(sgf_path.name)
        if chapter:
            chapter_files[chapter].append(sgf_path)
        else:
            unmatched.append(sgf_path)

    if unmatched:
        logger.error("Unmatched files: %s", [p.name for p in unmatched])
        raise ValueError(f"{len(unmatched)} files could not be classified into chapters")

    # Build ordered list: chapters in order, files natural-sorted within each
    ordered: list[Path] = []
    for _, chapter in CHAPTERS:
        files = sorted(chapter_files[chapter], key=lambda p: _natural_sort_key(p.name))
        logger.info("  Chapter %-10s: %d files", chapter, len(files))
        ordered.extend(files)

    total = len(ordered)
    logger.info("Total files to rename: %d", total)

    # Two-pass rename (original → temp → final) to avoid collisions
    rename_map: dict[str, str] = {}
    temp_map: list[tuple[Path, str]] = []

    for i, sgf_path in enumerate(ordered, 1):
        new_name = f"{i:04d}.sgf"
        rename_map[sgf_path.name] = new_name
        if sgf_path.name != new_name:
            temp_name = f"_tmp_rename_{i:04d}.sgf"
            if not dry_run:
                sgf_path.rename(sgf_path.parent / temp_name)
            temp_map.append((sgf_path.parent / temp_name, new_name))

    for temp_path, new_name in temp_map:
        if not dry_run:
            temp_path.rename(temp_path.parent / new_name)

    # Save rename mapping for traceability
    map_path = TOOL_DIR / "_sakata_rename_map.json"
    if not dry_run:
        map_path.write_text(
            json.dumps(rename_map, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Saved rename mapping → %s", map_path)

    logger.info("Renamed %d files to 4-digit format", len(temp_map))
    return rename_map


# ── Step 5: Embed YL[] ─────────────────────────────────────────────────


def _insert_yl(content: str, yl_prop: str) -> str:
    """Insert YL[] property after PL[] or SZ[], fallback to after '(;'."""
    pl_match = re.search(r"(PL\[[BW]\])", content)
    if pl_match:
        pos = pl_match.end()
        return content[:pos] + yl_prop + content[pos:]

    sz_match = re.search(r"(SZ\[\d+\])", content)
    if sz_match:
        pos = sz_match.end()
        return content[:pos] + yl_prop + content[pos:]

    return content.replace("(;", f"(;{yl_prop}", 1)


def embed_yl(source_dir: Path, *, dry_run: bool = False) -> int:
    """Embed YL[sakata-eio-tesuji:chapter/N] based on chapter file ranges.

    Chapter ranges are computed from the known file counts per chapter.
    Files must already be renamed to 4-digit format.
    """
    # Compute chapter ranges from counts
    chapter_counts = []
    for _, chapter in CHAPTERS:
        chapter_counts.append(chapter)

    # We need the actual file counts. Compute from the rename map or from known structure.
    # Since files are 4-digit-named and sorted, we compute ranges from expected counts.
    expected_counts: list[tuple[str, int]] = [
        ("hane", 13),
        ("sagari", 12),
        ("tsuke", 17),
        ("oki", 12),
        ("kiri", 12),
        ("kosumi", 19),
        ("kake", 8),
        ("tobi", 10),
        ("warikomi", 7),
    ]

    # Build chapter assignment: global_index → (chapter_slug, position_in_chapter)
    chapter_assignment: dict[int, tuple[str, int]] = {}
    global_idx = 1
    for chapter_slug, count in expected_counts:
        for pos in range(1, count + 1):
            chapter_assignment[global_idx] = (chapter_slug, pos)
            global_idx += 1

    sgf_files = sorted(source_dir.glob("*.sgf"), key=lambda p: _natural_sort_key(p.name))
    if len(sgf_files) != 110:
        logger.error("Expected 110 SGF files, found %d", len(sgf_files))
        raise ValueError(f"Expected 110 files, found {len(sgf_files)}")

    embedded = 0
    for i, sgf_path in enumerate(sgf_files, 1):
        content = sgf_path.read_text(encoding="utf-8")
        if "YL[" in content:
            logger.info("  Skipping %s (already has YL[])", sgf_path.name)
            continue

        chapter_slug, position = chapter_assignment[i]
        yl_prop = f"YL[{SLUG}:{chapter_slug}/{position}]"
        content = _insert_yl(content, yl_prop)

        if not dry_run:
            sgf_path.write_text(content, encoding="utf-8")
        logger.info("  %s → %s", sgf_path.name, yl_prop)
        embedded += 1

    logger.info("Embedded YL[] in %d files", embedded)
    return embedded


# ── Step 8: Verify ─────────────────────────────────────────────────────


def verify(source_dir: Path) -> bool:
    """Verify enrichment: YL coverage, no stale properties, correct naming."""
    sgf_files = sorted(source_dir.glob("*.sgf"))
    issues: list[str] = []

    if len(sgf_files) != 110:
        issues.append(f"Expected 110 files, found {len(sgf_files)}")

    missing_yl = []
    has_ap = []
    has_gn = []
    bad_names = []

    for sgf_path in sgf_files:
        name = sgf_path.name
        # Check 4-digit naming
        if not re.match(r"^\d{4}\.sgf$", name):
            bad_names.append(name)

        content = sgf_path.read_text(encoding="utf-8")
        if "YL[" not in content:
            missing_yl.append(name)
        if "AP[" in content:
            has_ap.append(name)
        if re.search(r"GN\[(?!YENGO)", content):
            has_gn.append(name)

    if bad_names:
        issues.append(f"Non-4-digit filenames: {bad_names[:5]}...")
    if missing_yl:
        issues.append(f"Missing YL[]: {missing_yl[:5]}... ({len(missing_yl)} total)")
    if has_ap:
        issues.append(f"Stale AP[]: {has_ap[:5]}...")
    if has_gn:
        issues.append(f"Stale GN[]: {has_gn[:5]}...")

    if issues:
        for issue in issues:
            logger.error("VERIFY FAIL: %s", issue)
        return False

    # Verify YL chapter/position correctness
    expected_counts: list[tuple[str, int]] = [
        ("hane", 13), ("sagari", 12), ("tsuke", 17), ("oki", 12),
        ("kiri", 12), ("kosumi", 19), ("kake", 8), ("tobi", 10), ("warikomi", 7),
    ]
    global_idx = 1
    for chapter_slug, count in expected_counts:
        for pos in range(1, count + 1):
            expected_yl = f"YL[{SLUG}:{chapter_slug}/{pos}]"
            file_path = source_dir / f"{global_idx:04d}.sgf"
            content = file_path.read_text(encoding="utf-8")
            if expected_yl not in content:
                issues.append(f"{file_path.name}: expected {expected_yl}")
            global_idx += 1

    if issues:
        for issue in issues:
            logger.error("VERIFY FAIL: %s", issue)
        return False

    logger.info("VERIFY OK: 110 files, 100%% YL coverage, correct chapter/position, no stale props")
    return True


# ── CLI ────────────────────────────────────────────────────────────────


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    step = "all"
    if "--step" in sys.argv:
        idx = sys.argv.index("--step")
        step = sys.argv[idx + 1]

    source_dir = BASE / SOURCE_DIR_NAME
    if not source_dir.is_dir():
        logger.error("Source directory not found: %s", source_dir)
        sys.exit(1)

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info("=== Sakata Eio Tesuji Enrichment (%s) ===", mode)
    logger.info("Source: %s", source_dir)
    logger.info("Step: %s", step)

    if step in ("rename", "all"):
        logger.info("── Step 3: Rename to 4-digit ──")
        rename_to_4digit(source_dir, dry_run=dry_run)

    if step in ("embed-yl", "all"):
        logger.info("── Step 5: Embed YL[] ──")
        embed_yl(source_dir, dry_run=dry_run)

    if step in ("verify", "all"):
        logger.info("── Step 8: Verify ──")
        ok = verify(source_dir)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
