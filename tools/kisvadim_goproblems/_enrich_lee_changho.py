#!/usr/bin/env python3
"""Enrichment script for LEE CHANGHO TESUJI (735 SGFs, 6 volumes / 16 topic folders).

Orchestrates: rename → prepare → translate → embed YL[] → verify.

The source has 16 topic subfolders grouped into 6 volumes:
  vol-1: 1. FIGHTING AND CAPTURING (123)
  vol-2: 2. SNAPBACK AND SHORTAGE OF LIBERTIES (123)
  vol-3: 3.1-3.4 (122)
  vol-4: 4. NET AND SQUEEZE TACTICS (123)
  vol-5: 5.1-5.6 (122)
  vol-6: 6.1-6.3 (122)

Files have hierarchical numbering (e.g., 3-2-15.sgf, 5-1-1-10.SGF),
mixed .sgf/.SGF extensions, ★ in 39 filenames, GB2312 encoding.

Usage:
    python -m tools.kisvadim_goproblems._enrich_lee_changho [--step STEP] [--dry-run]

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
logger = logging.getLogger("kisvadim.enrich_lee_changho")

SLUG = "lee-changho-tesuji"
SOURCE_DIR_NAME = "LEE CHANGHO TESUJI"
BASE = Path("external-sources/kisvadim-goproblems")
TOOL_DIR = Path("tools/kisvadim_goproblems")
TOTAL_FILES = 735

# Volume → chapter slug mapping.
# Each volume entry: (chapter_slug, list_of_subfolder_names)
# Subfolder order within each volume determines file ordering.
VOLUMES: list[tuple[str, list[str]]] = [
    ("vol-1", ["1. FIGHTING AND CAPTURING"]),
    ("vol-2", ["2. SNAPBACK AND SHORTAGE OF LIBERTIES"]),
    ("vol-3", [
        "3.1 CONNECTING GROUPS",
        "3.2 SPLITTING GROUPS",
        "3.3 SETTLING GROUPS",
        "3.4 ENDGAME",
    ]),
    ("vol-4", ["4. NET AND SQUEEZE TACTICS"]),
    ("vol-5", [
        "5.1 CONNECTING",
        "5.2 MAKING SHAPE",
        "5.3 END GAME",
        "5.4 LIFE AND DEATH",
        "5.5 ATTACK",
        "5.6 ESCAPE",
    ]),
    ("vol-6", [
        "6.1 CAPTURING RACE",
        "6.2 ATTACK",
        "6.3 ENDGAME",
    ]),
]


def _natural_sort_key(name: str) -> list:
    """Sort key that handles embedded numbers naturally.

    Handles ★ suffix: 3-1-20★.sgf sorts after 3-1-20.sgf.
    """
    # Normalize: strip extension first for sorting
    stem = Path(name).stem
    parts = re.split(r"(\d+)", stem)
    result = []
    for c in parts:
        if c.isdigit():
            result.append((0, int(c), ""))
        else:
            result.append((1, 0, c.lower()))
    return result


def _collect_sgfs_from_folder(folder: Path) -> list[Path]:
    """Collect all SGF files from a folder, handling mixed extensions."""
    files = list(folder.glob("*.[sS][gG][fF]"))
    return sorted(files, key=lambda p: _natural_sort_key(p.name))


# ── Step 3: Rename to 4-digit ──────────────────────────────────────────


def rename_to_4digit(source_dir: Path, *, dry_run: bool = False) -> dict[str, str]:
    """Rename all 735 SGFs to 0001.sgf .. 0735.sgf in volume/folder order.

    Files within each subfolder are natural-sorted.
    The global counter spans all volumes continuously.

    Returns the rename mapping {relative_old_path: new_4digit_name}.
    """
    ordered: list[tuple[Path, str]] = []  # (full_path, relative_display_path)

    for chapter_slug, subfolders in VOLUMES:
        chapter_count = 0
        for subfolder_name in subfolders:
            folder = source_dir / subfolder_name
            if not folder.is_dir():
                raise FileNotFoundError(f"Subfolder not found: {folder}")
            sgfs = _collect_sgfs_from_folder(folder)
            chapter_count += len(sgfs)
            for sgf_path in sgfs:
                rel = f"{subfolder_name}/{sgf_path.name}"
                ordered.append((sgf_path, rel))
        logger.info("  Volume %-6s: %d files", chapter_slug, chapter_count)

    total = len(ordered)
    logger.info("Total files to rename: %d", total)
    if total != TOTAL_FILES:
        logger.warning("Expected %d files, found %d!", TOTAL_FILES, total)

    # Move all files to the root source_dir with 4-digit names.
    # Two-pass: original → temp, then temp → final.
    rename_map: dict[str, str] = {}
    temp_map: list[tuple[Path, str]] = []

    for i, (sgf_path, rel_path) in enumerate(ordered, 1):
        new_name = f"{i:04d}.sgf"
        rename_map[rel_path] = new_name
        temp_name = f"_tmp_rename_{i:04d}.sgf"
        temp_dest = source_dir / temp_name
        if not dry_run:
            sgf_path.rename(temp_dest)
        temp_map.append((temp_dest, new_name))

    for temp_path, new_name in temp_map:
        if not dry_run:
            temp_path.rename(temp_path.parent / new_name)

    # Remove empty subdirectories
    if not dry_run:
        for _, subfolders in VOLUMES:
            for subfolder_name in subfolders:
                folder = source_dir / subfolder_name
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()
                    logger.info("  Removed empty folder: %s", subfolder_name)

    # Save rename mapping
    map_path = TOOL_DIR / "_lee_changho_rename_map.json"
    if not dry_run:
        map_path.write_text(
            json.dumps(rename_map, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Saved rename mapping → %s", map_path)

    logger.info("Renamed %d files to 4-digit format (flat directory)", total)
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
    """Embed YL[lee-changho-tesuji:vol-N/M] based on volume file ranges.

    Files must already be renamed to 4-digit format in the root directory.
    """
    # Compute chapter ranges from volume file counts
    expected_counts: list[tuple[str, int]] = [
        ("vol-1", 123),
        ("vol-2", 123),
        ("vol-3", 122),
        ("vol-4", 123),
        ("vol-5", 122),
        ("vol-6", 122),
    ]

    chapter_assignment: dict[int, tuple[str, int]] = {}
    global_idx = 1
    for chapter_slug, count in expected_counts:
        for pos in range(1, count + 1):
            chapter_assignment[global_idx] = (chapter_slug, pos)
            global_idx += 1

    sgf_files = sorted(source_dir.glob("*.sgf"), key=lambda p: _natural_sort_key(p.name))
    if len(sgf_files) != TOTAL_FILES:
        raise ValueError(f"Expected {TOTAL_FILES} files, found {len(sgf_files)}")

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
        if i <= 5 or i > TOTAL_FILES - 3 or position == 1:
            logger.info("  %s → %s", sgf_path.name, yl_prop)
        embedded += 1

    logger.info("Embedded YL[] in %d files", embedded)
    return embedded


# ── Step 8: Verify ─────────────────────────────────────────────────────


def verify(source_dir: Path) -> bool:
    """Verify enrichment: YL coverage, no stale properties, correct naming."""
    sgf_files = sorted(source_dir.glob("*.sgf"))
    issues: list[str] = []

    if len(sgf_files) != TOTAL_FILES:
        issues.append(f"Expected {TOTAL_FILES} files, found {len(sgf_files)}")

    missing_yl = []
    has_ap = []
    has_ev = []
    has_multigogm = []
    bad_names = []

    for sgf_path in sgf_files:
        name = sgf_path.name
        if not re.match(r"^\d{4}\.sgf$", name):
            bad_names.append(name)

        content = sgf_path.read_text(encoding="utf-8")
        if "YL[" not in content:
            missing_yl.append(name)
        if "AP[" in content:
            has_ap.append(name)
        if "EV[" in content:
            has_ev.append(name)
        if "MULTIGOGM[" in content:
            has_multigogm.append(name)

    if bad_names:
        issues.append(f"Non-4-digit filenames: {bad_names[:5]}... ({len(bad_names)} total)")
    if missing_yl:
        issues.append(f"Missing YL[]: {missing_yl[:5]}... ({len(missing_yl)} total)")
    if has_ap:
        issues.append(f"Stale AP[]: {len(has_ap)} files")
    if has_ev:
        issues.append(f"Stale EV[]: {len(has_ev)} files")
    if has_multigogm:
        issues.append(f"Stale MULTIGOGM[]: {len(has_multigogm)} files")

    if issues:
        for issue in issues:
            logger.error("VERIFY FAIL: %s", issue)
        return False

    # Verify YL chapter/position correctness
    expected_counts: list[tuple[str, int]] = [
        ("vol-1", 123), ("vol-2", 123), ("vol-3", 122),
        ("vol-4", 123), ("vol-5", 122), ("vol-6", 122),
    ]
    global_idx = 1
    yl_errors = []
    for chapter_slug, count in expected_counts:
        for pos in range(1, count + 1):
            expected_yl = f"YL[{SLUG}:{chapter_slug}/{pos}]"
            file_path = source_dir / f"{global_idx:04d}.sgf"
            content = file_path.read_text(encoding="utf-8")
            if expected_yl not in content:
                yl_errors.append(f"{file_path.name}: expected {expected_yl}")
            global_idx += 1

    if yl_errors:
        for err in yl_errors[:10]:
            logger.error("VERIFY FAIL: %s", err)
        if len(yl_errors) > 10:
            logger.error("  ... and %d more", len(yl_errors) - 10)
        return False

    logger.info("VERIFY OK: %d files, 100%% YL coverage, correct chapter/position, no stale props", TOTAL_FILES)
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
    logger.info("=== Lee Changho Tesuji Enrichment (%s) ===", mode)
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
