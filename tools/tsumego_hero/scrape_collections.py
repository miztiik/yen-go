"""
Scrape Tsumego Hero collection metadata and puzzle memberships.

Fetches all collections from tsumego.com/sets, then for each collection
scrapes the puzzle URL IDs via pagination. Outputs local_collections.json
with full metadata and ordered puzzle ID lists.

Entry point: python -m tools.tsumego_hero.scrape_collections
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import TsumegoHeroClient, TsumegoHeroClientError

logger = logging.getLogger("tsumego_hero.scrape_collections")

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCES_JSON = SCRIPT_DIR / "sources.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "local_collections.json"


def slugify(name: str) -> str:
    """Convert a collection name to a URL-safe slug.

    Lowercase, replace non-alphanumeric with hyphens, strip, truncate to 60 chars.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60]


def detect_multi_part(name: str) -> tuple[str, int | None]:
    """Detect if a collection name has a #N multi-part suffix.

    Returns:
        Tuple of (base_name, part_number). part_number is None if not multi-part.
    """
    match = re.search(r"#(\d+)\s*$", name)
    if match:
        part_num = int(match.group(1))
        base_name = name[: match.start()].strip()
        return base_name, part_num
    return name, None


def load_sources_metadata() -> dict[str, dict]:
    """Load hand-curated collection metadata from sources.json.

    Returns a name-based index because sources.json set_ids are stale
    (the website has reshuffled IDs since the file was written).
    Matching by normalized name is more reliable.

    Returns:
        Dict mapping normalized name (lowercase, stripped) to collection entry.
    """
    if not SOURCES_JSON.exists():
        logger.warning(f"sources.json not found at {SOURCES_JSON}")
        return {}

    with open(SOURCES_JSON, encoding="utf-8") as f:
        data = json.load(f)

    by_name: dict[str, dict] = {}
    for entry in data.get("collections", {}).values():
        name = entry.get("name", "").strip().lower()
        if name:
            by_name[name] = entry
    return by_name


def generate_slug(
    name: str,
    sources_meta: dict[str, dict],
    part_number: int | None,
) -> tuple[str, str | None]:
    """Generate a slug for a collection.

    Priority:
    1. Hand-curated slug from sources.json matched by name (+ -N suffix for multi-part)
    2. Auto-generated from name via slugify()

    Returns:
        Tuple of (slug, group). group is the base slug for multi-part, None otherwise.
    """
    group: str | None = None

    # Match by name (try full name first, then base name for multi-part)
    base_name, _ = detect_multi_part(name)
    lookup_name = name.strip().lower()
    base_lookup = base_name.strip().lower()

    source_entry = sources_meta.get(lookup_name) or sources_meta.get(base_lookup)

    if source_entry and source_entry.get("slug"):
        base_slug = source_entry["slug"]
    else:
        base_name, _ = detect_multi_part(name)
        base_slug = slugify(base_name)

    if part_number is not None:
        group = base_slug
        slug = f"{base_slug}-{part_number}"
    else:
        slug = base_slug

    return slug, group


def scrape_all_collections(
    output_path: Path = DEFAULT_OUTPUT,
    dry_run: bool = False,
) -> None:
    """Scrape all collection metadata and puzzle memberships.

    Args:
        output_path: Path to write local_collections.json.
        dry_run: If True, fetch collection list only (skip per-collection puzzle scraping).
    """
    sources_meta = load_sources_metadata()
    logger.info(f"Loaded {len(sources_meta)} entries from sources.json")

    with TsumegoHeroClient() as client:
        # Step 1: Fetch all collection metadata from /sets
        logger.info("Fetching collections from /sets...")
        raw_collections = client.fetch_collections()
        logger.info(f"Found {len(raw_collections)} collections")

        if dry_run:
            print(f"\n{'='*60}")
            print("DRY RUN - Collection List Only")
            print(f"{'='*60}")
            for set_id in sorted(raw_collections, key=lambda x: int(x)):
                info = raw_collections[set_id]
                name = info.get("name", f"(unknown, set_id={set_id})")
                count = info.get("puzzle_count", "?")
                diff = info.get("difficulty", "?")
                print(f"  [{set_id:>6}] {name} ({count} puzzles, ~{diff})")
            print(f"\nTotal: {len(raw_collections)} collections")
            print("Run without --dry-run to scrape puzzle IDs for each collection.")
            return

        # Step 2: For each collection, scrape puzzle IDs
        entries = []
        all_puzzle_ids: set[int] = set()
        slugs_seen: dict[str, str] = {}  # slug -> set_id for uniqueness

        sorted_set_ids = sorted(raw_collections.keys(), key=lambda x: int(x))

        for i, set_id in enumerate(sorted_set_ids, 1):
            info = raw_collections[set_id]
            name = info.get("name", f"Collection {set_id}")
            advertised_count = info.get("puzzle_count")
            difficulty = info.get("difficulty")

            # Detect multi-part
            _, part_number = detect_multi_part(name)

            # Generate slug
            slug, group = generate_slug(name, sources_meta, part_number)

            # Enforce slug uniqueness
            if slug in slugs_seen:
                slug = f"{slug}-{set_id}"
            slugs_seen[slug] = set_id

            # Scrape puzzle IDs
            logger.info(f"[{i}/{len(sorted_set_ids)}] {name} (set_id={set_id})...")
            try:
                puzzle_ids = client.fetch_collection_puzzles(int(set_id))
            except TsumegoHeroClientError as e:
                logger.warning(f"Failed to scrape puzzles for {name} (set_id={set_id}): {e}")
                puzzle_ids = []

            scraped_count = len(puzzle_ids)
            all_puzzle_ids.update(puzzle_ids)

            # Warn on count mismatch
            if advertised_count is not None and scraped_count != advertised_count:
                logger.warning(
                    f"  Count mismatch for {name}: advertised={advertised_count}, scraped={scraped_count}"
                )

            # Build sources.json entry reference (if available, matched by name)
            base_name_for_lookup, _ = detect_multi_part(name)
            name_key = name.strip().lower()
            base_key = base_name_for_lookup.strip().lower()
            src = sources_meta.get(name_key) or sources_meta.get(base_key)
            sources_entry = None
            if src:
                sources_entry = {
                    "yengo_level": src.get("yengo_level"),
                    "slug": src.get("slug"),
                }

            entry = {
                "set_id": int(set_id),
                "name": name,
                "slug": slug,
                "difficulty": difficulty,
                "puzzle_count_advertised": advertised_count,
                "puzzle_count_scraped": scraped_count,
                "puzzle_ids": puzzle_ids,
                "group": group,
                "sources_json_entry": sources_entry,
            }
            entries.append(entry)

            print(f"  [{i}/{len(sorted_set_ids)}] {name}: {scraped_count} puzzles -> {slug}")

    # Build output
    output = {
        "version": "1.0.0",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total_collections": len(entries),
        "total_unique_puzzles": len(all_puzzle_ids),
        "collections": entries,
    }

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Scraped {len(entries)} collections, {len(all_puzzle_ids)} unique puzzles")
    print(f"Output: {output_path}")
    print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Tsumego Hero collection metadata and puzzle memberships.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch collection list only, skip per-collection puzzle scraping.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging.",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    scrape_all_collections(
        output_path=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
