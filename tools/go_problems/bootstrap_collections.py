"""
Bootstrap new collection entries from GoProblems sorted collections JSONL.

Reads the sorted JSONL (from sort_collections.py), identifies GoProblems
collections that don't match any existing YenGo collection slug, and
generates new config/collections.json entries for premier/curated tiers.

Auto-merges directly into config/collections.json with timestamped backup.
Filters collections with fewer than MIN_PUZZLE_COUNT puzzles, resolves
slug collisions with -gp suffix, validates entries against schema, and
uses GoProblems API description when available.

Usage:
    python -m tools.go_problems.bootstrap_collections -i <sorted-jsonl>
    python -m tools.go_problems.bootstrap_collections -i <file> --dry-run
    python -m tools.go_problems.bootstrap_collections -i <file> --min-puzzles 50
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.core.paths import rel_path
from tools.core.text_cleaner import (
    NON_LATIN_RE as _NON_LATIN_RE,
)
from tools.core.text_cleaner import (
    clean_name,
    generate_slug,
    infer_curator,
    infer_type,
)
from tools.core.text_cleaner import (
    extract_english_portion as _extract_english_portion,
)
from tools.go_problems.collections import CollectionMatcher
from tools.go_problems.config import get_project_root
from tools.go_problems.sort_collections import read_collections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# GoProblems-Specific Configuration
# ============================================================================

# Minimum puzzle count to include a collection (skip small/stub collections)
MIN_PUZZLE_COUNT = 30

# Map from GoProblems quality_tier to collections schema tier values
_GP_TIER_MAP: dict[str, str] = {
    "premier": "premier",
    "curated": "curated",
    "community": "community",
    "unvetted": "community",
}

# ============================================================================
# Schema Validation Constants
# ============================================================================

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
_VALID_TYPES = {"author", "reference", "graded", "technique", "system"}
_VALID_ORDERINGS = {"source", "difficulty", "manual"}
_VALID_TIERS = {"editorial", "premier", "curated", "community"}

# ============================================================================
# Manual Overrides for GoProblems Collections
# ============================================================================
# Populated after first run. GoProblems collection names are generally
# simpler than OGS, so fewer overrides are needed.

_GP_SLUG_OVERRIDES: dict[int, str] = {
    51: "xuan-xuan-qijing",
    305: "korean-problem-academy-1",
}

_GP_NAME_OVERRIDES: dict[int, str] = {
    51: "Xuan Xuan Qijing",
    305: "Korean Problem Academy Vol. 1",
}

# Skip these GoProblems collection IDs (admin buckets, personal lists, format-only)
_GP_SKIP_IDS: frozenset[int] = frozenset({
    108,  # "0 What Group?" -- admin triage bucket
    278,  # "saxmaam hard" -- personal difficulty list
    13,   # "How Many Ways" -- format-only (count solutions)
    30,   # "Stories" -- narrative format, not a Go concept
    11,   # "Black or White" -- format-only (choose attack/defend)
})


# ============================================================================
# Slug Collision Resolution
# ============================================================================

def _resolve_slug_collision(slug: str, existing_slugs: set[str]) -> str:
    """Resolve slug collision by appending -gp suffix, then -gp-2, -gp-3, etc."""
    candidate = f"{slug}-gp"
    if candidate not in existing_slugs and len(candidate) <= 64:
        return candidate
    counter = 2
    while counter <= 99:
        candidate = f"{slug}-gp-{counter}"
        if candidate not in existing_slugs and len(candidate) <= 64:
            return candidate
        counter += 1
    return f"{slug[:55]}-gp-{counter}"


# ============================================================================
# Schema Validation
# ============================================================================

def _validate_entry(entry: dict[str, Any]) -> list[str]:
    """Validate entry against collection schema. Returns list of error messages."""
    errors: list[str] = []
    slug = entry.get("slug", "")
    if not slug or not _SLUG_RE.match(slug) or len(slug) > 64:
        errors.append(f"Invalid slug: {slug!r}")
    name = entry.get("name", "")
    if not name or len(name) > 128:
        errors.append(f"Invalid name length: {len(name)}")
    desc = entry.get("description", "")
    if not desc or len(desc) > 512:
        errors.append(f"Invalid description length: {len(desc)}")
    if entry.get("type") not in _VALID_TYPES:
        errors.append(f"Invalid type: {entry.get('type')}")
    if entry.get("ordering") not in _VALID_ORDERINGS:
        errors.append(f"Invalid ordering: {entry.get('ordering')}")
    if entry.get("tier") not in _VALID_TIERS:
        errors.append(f"Invalid tier: {entry.get('tier')}")
    return errors


# ============================================================================
# Auto-Merge
# ============================================================================

def _merge_into_collections_json(
    collections_json_path: Path,
    new_entries: list[dict[str, Any]],
    backup: bool = True,
) -> None:
    """Merge new entries directly into config/collections.json with backup."""
    with open(collections_json_path, encoding="utf-8") as f:
        existing_config = json.load(f)

    if backup:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = (
            collections_json_path.parent
            / f"collections-backup-{timestamp}.json"
        )
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, ensure_ascii=False, indent=2)
            f.write("\n")
        logger.info(f"Backup saved to {rel_path(backup_path)}")

    merged = existing_config.get("collections", []) + new_entries
    output_config = {
        "_reference": existing_config.get(
            "_reference", "docs/concepts/collections.md"
        ),
        "schema_version": "3.0",
        "collections": merged,
    }

    with open(collections_json_path, "w", encoding="utf-8") as f:
        json.dump(output_config, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info(
        f"Merged {len(new_entries)} entries into "
        f"{rel_path(collections_json_path)} (total: {len(merged)})"
    )


# ============================================================================
# Entry Generation
# ============================================================================

def generate_collection_entry(record: dict[str, Any]) -> dict[str, Any]:
    """Generate a new collection entry from a GoProblems collection record.

    Fits into the existing collection schema (no new fields).
    Applies manual overrides and bilingual extraction for clean English names.

    Args:
        record: GoProblems collection record from sorted JSONL.

    Returns:
        Collection entry dict conforming to schema.
    """
    gp_id = record.get("id", 0)
    gp_name = record["name"]

    # Priority 1: Manual overrides
    if gp_id in _GP_NAME_OVERRIDES:
        display_name = _GP_NAME_OVERRIDES[gp_id]
    # Priority 2: Bilingual extraction for non-Latin names
    elif _NON_LATIN_RE.search(gp_name):
        english = _extract_english_portion(gp_name)
        if english:
            display_name = clean_name(english)
        else:
            display_name = clean_name(gp_name)
    # Priority 3: Standard cleanup
    else:
        display_name = clean_name(gp_name)

    if gp_id in _GP_SLUG_OVERRIDES:
        slug = _GP_SLUG_OVERRIDES[gp_id]
    else:
        slug = generate_slug(display_name)

    curator = infer_curator(gp_name)
    coll_type = infer_type(gp_name, curator)

    puzzle_count = record.get("stats", {}).get("puzzle_count", 0)
    tier = record.get("quality_tier", "unvetted")
    schema_tier = _GP_TIER_MAP.get(tier, "community")

    # Use GoProblems API description if available, English, and long enough
    gp_description = record.get("description", "")
    if (
        gp_description
        and len(gp_description) >= 10
        and not _NON_LATIN_RE.search(gp_description)
    ):
        description = gp_description.strip()
        if not description.endswith("."):
            description += "."
        if len(description) > 512:
            description = description[:509] + "..."
    else:
        description = (
            f"GoProblems community collection ({tier} tier, {puzzle_count} puzzles). "
            f"Imported from goproblems.com."
        )

    return {
        "slug": slug,
        "name": display_name,
        "description": description,
        "curator": curator,
        "source": "goproblems",
        "type": coll_type,
        "ordering": "source",
        "tier": schema_tier,
        "aliases": [gp_name],
    }


# ============================================================================
# Bootstrap Logic
# ============================================================================

def bootstrap_collections(
    sorted_jsonl_path: Path,
    collections_json_path: Path,
    tiers: frozenset[str] = frozenset({"premier", "curated"}),
    min_puzzle_count: int = MIN_PUZZLE_COUNT,
) -> tuple[list[dict[str, Any]], list[tuple[int, str, str]], list[tuple[int, str, str, str]]]:
    """Identify GoProblems collections needing new YenGo entries.

    Args:
        sorted_jsonl_path: Path to sorted JSONL.
        collections_json_path: Path to config/collections.json.
        tiers: Quality tiers to bootstrap (default: premier + curated).
        min_puzzle_count: Minimum puzzle count to include (default: 30).

    Returns:
        Tuple of:
        - new_entries: List of generated collection entry dicts
        - matched: List of (gp_id, gp_name, yengo_slug) for already-matched
        - skipped: List of (gp_id, gp_name, tier, reason) for skipped
    """
    # Load existing config
    with open(collections_json_path, encoding="utf-8") as f:
        existing_config = json.load(f)
    existing_collections = existing_config.get("collections", [])
    existing_slugs = {c["slug"] for c in existing_collections}

    # Collect all existing aliases
    existing_aliases: set[str] = set()
    for coll in existing_collections:
        existing_aliases.add(coll["slug"])
        if coll.get("name"):
            existing_aliases.add(coll["name"])
        for alias in coll.get("aliases", []):
            existing_aliases.add(alias)

    # Load sorted JSONL
    _, gp_collections = read_collections(sorted_jsonl_path)

    # Initialize matcher from existing collections
    matcher = CollectionMatcher(collections_json_path)

    matched: list[tuple[int, str, str]] = []
    new_entries: list[dict[str, Any]] = []
    skipped: list[tuple[int, str, str, str]] = []

    for record in gp_collections:
        gp_name = record["name"]
        gp_id = record["id"]
        tier = record.get("quality_tier", "unvetted")

        # Skip manually excluded collections
        if gp_id in _GP_SKIP_IDS:
            skipped.append((gp_id, gp_name, tier, "manual_skip"))
            continue

        # Filter by minimum puzzle count
        puzzle_count = record.get("stats", {}).get(
            "puzzle_count", record.get("puzzle_count", 0)
        )
        if puzzle_count < min_puzzle_count:
            skipped.append((gp_id, gp_name, tier, "too_few_puzzles"))
            continue

        # Try to match against existing YenGo slug
        # Skip matcher for overridden IDs (overrides take priority)
        if gp_id not in _GP_SLUG_OVERRIDES:
            slug = matcher.match(gp_name)
        else:
            slug = None

        if slug:
            matched.append((gp_id, gp_name, slug))
            continue

        # Only bootstrap specified tiers
        if tier not in tiers:
            skipped.append((gp_id, gp_name, tier, "tier_too_low"))
            continue

        # Generate new collection entry
        entry = generate_collection_entry(record)

        # Validate: reject entries with non-Latin display names
        if _NON_LATIN_RE.search(entry["name"]):
            skipped.append((gp_id, gp_name, tier, "non_english"))
            continue

        # Schema validation
        validation_errors = _validate_entry(entry)
        if validation_errors:
            logger.warning(
                f"Schema validation failed for GP #{gp_id}: {validation_errors}"
            )
            skipped.append((gp_id, gp_name, tier, "schema_invalid"))
            continue

        # Resolve slug collisions with -gp suffix instead of skipping
        if entry["slug"] in existing_slugs:
            resolved = _resolve_slug_collision(entry["slug"], existing_slugs)
            logger.info(
                f"Slug collision '{entry['slug']}' resolved to '{resolved}'"
            )
            entry["slug"] = resolved

        # Validate alias uniqueness
        if gp_name in existing_aliases:
            skipped.append((gp_id, gp_name, tier, "alias_collision"))
            continue

        existing_slugs.add(entry["slug"])
        existing_aliases.add(gp_name)
        new_entries.append(entry)

    return new_entries, matched, skipped


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bootstrap GoProblems collections into config/collections.json",
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Input sorted JSONL file (from sort_collections.py)",
    )
    parser.add_argument(
        "--collections", "-c",
        type=Path,
        default=None,
        help="Path to config/collections.json (default: auto-detect)",
    )
    parser.add_argument(
        "--min-puzzles",
        type=int,
        default=MIN_PUZZLE_COUNT,
        help=f"Minimum puzzle count to include (default: {MIN_PUZZLE_COUNT})",
    )
    parser.add_argument(
        "--include-community",
        action="store_true",
        help="Also bootstrap community-tier collections (default: premier + curated only)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup before merging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview proposed entries without writing",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    project_root = get_project_root()

    input_path: Path = args.input
    if not input_path.is_absolute():
        input_path = project_root / input_path

    collections_path: Path = args.collections or (
        project_root / "config" / "collections.json"
    )
    if not collections_path.is_absolute():
        collections_path = project_root / collections_path

    tiers = frozenset({"premier", "curated"})
    if args.include_community:
        tiers = frozenset({"premier", "curated", "community"})

    logger.info("GoProblems Collections Bootstrap")
    logger.info("=" * 40)
    logger.info(f"Input:       {rel_path(input_path)}")
    logger.info(f"Collections: {rel_path(collections_path)}")
    logger.info(f"Min puzzles: {args.min_puzzles}")
    logger.info(f"Tiers:       {', '.join(sorted(tiers))}")
    logger.info(f"Dry run:     {args.dry_run}")
    logger.info("")

    # Run bootstrap
    new_entries, matched, skipped = bootstrap_collections(
        sorted_jsonl_path=input_path,
        collections_json_path=collections_path,
        tiers=tiers,
        min_puzzle_count=args.min_puzzles,
    )

    # Log summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("BOOTSTRAP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Already matched: {len(matched)}")
    logger.info(f"New entries:     {len(new_entries)}")
    logger.info(f"Skipped:         {len(skipped)}")
    logger.info("")

    if matched:
        logger.info("Matched collections:")
        for gp_id, gp_name, slug in matched[:10]:
            logger.info(f"  GP #{gp_id:<6} -> {slug:<40} ({gp_name[:50]})")
        if len(matched) > 10:
            logger.info(f"  ... and {len(matched) - 10} more")
        logger.info("")

    if new_entries:
        logger.info("Proposed new entries:")
        for entry in new_entries:
            logger.info(
                f"  {entry['slug']:<40} type={entry['type']:<10} "
                f"curator={entry['curator']:<15} alias={entry['aliases'][0][:40]}"
            )
        logger.info("")

    if skipped:
        reason_counts: dict[str, int] = {}
        for _, _, _, reason in skipped:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        logger.info("Skipped breakdown:")
        for reason, count in sorted(reason_counts.items()):
            logger.info(f"  {reason}: {count}")
        logger.info("")

    if args.dry_run:
        logger.info("[DRY RUN] No changes written.")
        return 0

    if not new_entries:
        logger.info("No new entries to add.")
        return 0

    # Auto-merge into config/collections.json
    _merge_into_collections_json(
        collections_json_path=collections_path,
        new_entries=new_entries,
        backup=not args.no_backup,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
