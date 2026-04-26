"""Rename enriched SGF files to section-based naming convention.

Renames numeric filenames (0001.sgf, problem_0001_p1.sgf) to section-based
names (Live-001.sgf, Kill-05.sgf) using Senseis section categorization.

Supports:
  - Gokyo Shumyo: uses position mapping + config section ranges
  - Igo Hatsuyo-ron: uses config section ranges directly

Usage:
    python -m tools.senseis_enrichment.rename_to_sections --config <config.json> --dry-run
    python -m tools.senseis_enrichment.rename_to_sections --config <config.json>
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from tools.senseis_enrichment.config import SenseisConfig, load_config

logger = logging.getLogger("senseis_enrichment.rename")


def _has_range_sections(config: SenseisConfig) -> bool:
    """Check if config has sections with 'range' fields (Hatsuyo-ron style)."""
    if not config.sections:
        return False
    for s in config.sections:
        s_dict = s if isinstance(s, dict) else vars(s)
        if "range" in s_dict:
            return True
    return False


def _sanitize_section_name(name: str) -> str:
    """Convert section name to PascalCase filename component.

    'Play Inside' -> 'PlayInside', 'Capturing Race' -> 'CapturingRace'
    'L-shape Corner' -> 'LShapeCorner', 'Long-living Corner' -> 'LongLivingCorner'
    """
    # Split on spaces and hyphens, capitalize each part, rejoin
    import re
    parts = re.split(r"[\s-]+", name)
    return "".join(p.capitalize() for p in parts if p)


def _section_pad_width(config: SenseisConfig) -> int:
    """Determine zero-padding width based on max section size."""
    max_count = max(
        (s.get("count", 0) if isinstance(s, dict) else s.count
         for s in (config.sections or [])),
        default=99,
    )
    return 3 if max_count >= 100 else 2


def _build_rename_map_gokyo(config: SenseisConfig) -> dict[str, str]:
    """Build old->new filename mapping for Gokyo Shumyo using position mapping."""
    # Check _results/ first (new location), fall back to _working/ (legacy)
    mapping_path = config.results_dir() / "_position_mapping.json"
    if not mapping_path.exists():
        mapping_path = config.working_dir() / "_position_mapping.json"
    if not mapping_path.exists():
        logger.error("Position mapping not found: %s", mapping_path)
        return {}

    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    pad = _section_pad_width(config)
    rename_map: dict[str, str] = {}

    # Mapped problems: use section_name and section_pos from mapping
    for m in mapping["mappings"]:
        local_n = m["local_n"]
        section_name = _sanitize_section_name(m["section_name"])
        section_pos = m["section_pos"]
        old_name = config.local_filename_pattern.replace("{N:04d}", f"{local_n:04d}").replace("{N}", str(local_n))
        new_name = f"{section_name}_{section_pos:0{pad}d}.sgf"
        rename_map[old_name] = new_name

    # Unmapped locals: derive section from config ranges
    mapped_locals = {m["local_n"] for m in mapping["mappings"]}
    sections = config.sections or ()

    # Compute section ranges from config (cumulative counts)
    section_ranges: list[tuple[int, int, str, int]] = []
    start = 1
    for s in sections:
        s_dict = s if isinstance(s, dict) else vars(s)
        count = s_dict.get("count", 0)
        name = s_dict.get("name", "")
        end = start + count - 1
        section_ranges.append((start, end, name, count))
        start = end + 1

    # Local file ranges mapped to sections (empirically determined):
    # Live: 1-103, Kill: 104-174, Ko: 175-265, Attack: 266-361,
    # Chasing: 362-401, Mixed: 402-447
    local_section_ranges = [
        (1, 103, "Live"),
        (104, 174, "Kill"),
        (175, 265, "Ko"),
        (266, 361, "Attack"),
        (362, 401, "Chasing"),
        (402, 447, "Mixed"),
    ]

    # For each unmapped local, find its section and assign an unused position
    enriched_dir = config.enriched_dir()
    all_local_sgfs = sorted(
        int(f.stem)
        for f in enriched_dir.glob("[0-9]*.sgf")
        if f.stem.isdigit()
    )

    # Track which section_pos values are already taken (from mapped entries)
    taken_positions: dict[str, set[int]] = {}
    for m in mapping["mappings"]:
        sec = m["section_name"]
        taken_positions.setdefault(sec, set()).add(m["section_pos"])

    for local_n in all_local_sgfs:
        if local_n in mapped_locals:
            continue  # Already handled above

        # Find section for this local file
        section_name = None
        for lo, hi, sec in local_section_ranges:
            if lo <= local_n <= hi:
                section_name = sec
                break

        if not section_name:
            logger.warning("Cannot determine section for local %d", local_n)
            continue

        # Find next available position in this section
        taken = taken_positions.setdefault(section_name, set())
        pos = 1
        while pos in taken:
            pos += 1
        taken.add(pos)

        clean_section = _sanitize_section_name(section_name)
        old_name = f"{local_n:04d}.sgf"
        new_name = f"{clean_section}_{pos:0{pad}d}.sgf"
        rename_map[old_name] = new_name

    return rename_map


def _global_pad_width(config: SenseisConfig) -> int:
    """Determine zero-padding width for global prefix based on problem_count."""
    count = config.problem_count
    if count >= 1000:
        return 4
    if count >= 100:
        return 3
    return 2


def _build_rename_map_hatsuyo(config: SenseisConfig) -> dict[str, str]:
    """Build old->new filename mapping for range-based sections."""
    sections = config.sections or ()
    pad = _section_pad_width(config)
    gpad = _global_pad_width(config) if config.global_prefix else 0
    rename_map: dict[str, str] = {}

    for s in sections:
        s_dict = s if isinstance(s, dict) else vars(s)
        name = s_dict.get("name", "")
        range_vals = s_dict.get("range", [])
        if len(range_vals) != 2:
            continue

        lo, hi = range_vals
        clean_name = _sanitize_section_name(name)

        for n in range(lo, hi + 1):
            section_pos = n - lo + 1
            old_name = config.local_filename_pattern.replace(
                "{N:04d}", f"{n:04d}"
            ).replace("{N}", str(n))
            section_part = f"{clean_name}_{section_pos:0{pad}d}.sgf"
            if gpad:
                new_name = f"{n:0{gpad}d}_{section_part}"
            else:
                new_name = section_part
            rename_map[old_name] = new_name

    return rename_map


def rename_files(
    config: SenseisConfig,
    target_dir: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Rename files in the target directory using section-based naming.

    Args:
        config: Collection config.
        target_dir: Directory to rename files in. Defaults to enriched_dir for
                    Gokyo or local_dir for Hatsuyo-ron.
        dry_run: If True, just print what would happen.

    Returns:
        Summary dict.
    """
    # Determine which collection and build appropriate rename map
    slug = config.collection_slug

    if _has_range_sections(config):
        # Any collection with range-based sections (Hatsuyo-ron, Gokyo Shumyo, Xian Ji Wu Ku, etc.)
        rename_map = _build_rename_map_hatsuyo(config)
        if target_dir is None:
            target_dir = config.enriched_dir()
    elif "gokyo" in slug:
        # Legacy: Gokyo without range fields, uses position mapping
        rename_map = _build_rename_map_gokyo(config)
        if target_dir is None:
            target_dir = config.enriched_dir()
    else:
        logger.error("Unsupported collection for renaming: %s", slug)
        return {"renamed": 0, "skipped": 0, "errors": 0}

    logger.info("Rename map: %d entries for %s", len(rename_map), target_dir)

    renamed = 0
    skipped = 0
    errors = 0

    # Check for conflicts (different old files mapping to same new name)
    new_names = list(rename_map.values())
    duplicates = {n for n in new_names if new_names.count(n) > 1}
    if duplicates:
        logger.error("Duplicate new names detected: %s", duplicates)
        return {"renamed": 0, "skipped": 0, "errors": len(duplicates)}

    for old_name, new_name in sorted(rename_map.items()):
        old_path = target_dir / old_name
        new_path = target_dir / new_name

        if not old_path.exists():
            # File might already be renamed (idempotent)
            if new_path.exists():
                skipped += 1
            else:
                logger.warning("  Missing: %s", old_name)
                errors += 1
            continue

        if new_path.exists() and old_path != new_path:
            logger.warning("  Conflict: %s -> %s (target exists)", old_name, new_name)
            errors += 1
            continue

        if dry_run:
            logger.info("  %s -> %s", old_name, new_name)
            renamed += 1
        else:
            os.rename(old_path, new_path)
            renamed += 1

    # After renaming, remove any leftover numeric files that weren't in the map
    # (these would be files that were superseded by newly created section-named files)
    if not dry_run:
        leftover_numeric = list(target_dir.glob("[0-9][0-9][0-9][0-9].sgf"))
        if leftover_numeric:
            logger.info("Leftover numeric files (not in rename map): %d", len(leftover_numeric))

    logger.info(
        "Rename complete: renamed=%d, skipped=%d, errors=%d",
        renamed, skipped, errors,
    )
    return {"renamed": renamed, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--target-dir", type=str, default=None,
                        help="Override target directory")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    target = Path(args.target_dir) if args.target_dir else None
    rename_files(config, target_dir=target, dry_run=args.dry_run)
