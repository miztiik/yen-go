"""
Organize Tsumego Hero puzzles by collection.

Reads local_collections.json and the sgf-index.txt to build per-collection
manifest files showing which puzzles belong to which collections.

No files are copied -- this creates manifests only.

Entry point: python -m tools.tsumego_hero.organize_collections
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .log_parser import parse_rejection_log

logger = logging.getLogger("tsumego_hero.organize_collections")

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_COLLECTIONS_JSON = SCRIPT_DIR / "local_collections.json"
T_HERO_DIR = Path("external-sources/t-hero")
SGF_INDEX_FILE = T_HERO_DIR / "sgf-index.txt"
OUTPUT_DIR = T_HERO_DIR / "sgf-by-collection"


def build_puzzle_index(index_path: Path) -> dict[int, str]:
    """Build mapping from puzzle URL ID to relative SGF path.

    Parses sgf-index.txt lines like: sgf/batch-016/th-1.sgf

    Returns:
        Dict mapping url_id (int) to relative path string.
    """
    index: dict[int, str] = {}
    with open(index_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.search(r"th-(\d+)\.sgf$", line)
            if m:
                index[int(m.group(1))] = line
    return index


def load_collections(json_path: Path) -> dict:
    """Load local_collections.json."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def process_collection(
    entry: dict,
    puzzle_index: dict[int, str],
    output_dir: Path,
    dry_run: bool = False,
    rejections: dict[int, str] | None = None,
) -> dict:
    """Process a single collection: match puzzles, write manifest.

    Returns:
        Summary dict for the master index.
    """
    slug = entry["slug"]
    name = entry["name"]
    set_id = entry["set_id"]
    puzzle_ids = entry.get("puzzle_ids", [])

    found = 0
    missing = 0
    missing_reasons: Counter = Counter()
    puzzles_list = []

    for url_id in puzzle_ids:
        source_path = puzzle_index.get(url_id)
        if source_path:
            found += 1
            puzzles_list.append({
                "url_id": url_id,
                "found": True,
                "source": source_path,
            })
        else:
            missing += 1
            puzzle_entry: dict = {
                "url_id": url_id,
                "found": False,
            }
            if rejections and url_id in rejections:
                reason = rejections[url_id]
                puzzle_entry["skip_reason"] = reason
                missing_reasons[reason] += 1
            else:
                missing_reasons["unknown"] += 1
            puzzles_list.append(puzzle_entry)

    # Determine yengo_level from sources_json_entry if available
    yengo_level = None
    sources_entry = entry.get("sources_json_entry")
    if sources_entry:
        yengo_level = sources_entry.get("yengo_level")

    manifest = {
        "set_id": set_id,
        "name": name,
        "slug": slug,
        "difficulty": entry.get("difficulty"),
        "yengo_level": yengo_level,
        "group": entry.get("group"),
        "puzzle_count": len(puzzle_ids),
        "files_found": found,
        "files_missing": missing,
        "missing_breakdown": dict(missing_reasons) if missing_reasons else None,
        "puzzles": puzzles_list,
    }

    if not dry_run:
        coll_dir = output_dir / slug
        coll_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = coll_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    return {
        "dir": slug,
        "set_id": set_id,
        "name": name,
        "puzzles": len(puzzle_ids),
        "found": found,
        "missing": missing,
    }


def process_uncollected(
    puzzle_index: dict[int, str],
    all_collected_ids: set[int],
    output_dir: Path,
    dry_run: bool = False,
) -> dict | None:
    """Process puzzles not in any collection.

    Returns:
        Summary dict for the master index, or None if no uncollected puzzles.
    """
    uncollected_ids = sorted(set(puzzle_index.keys()) - all_collected_ids)
    if not uncollected_ids:
        return None

    puzzles_list = [
        {
            "url_id": uid,
            "found": True,
            "source": puzzle_index[uid],
        }
        for uid in uncollected_ids
    ]

    manifest = {
        "set_id": None,
        "name": "(Uncollected)",
        "slug": "_uncollected",
        "difficulty": None,
        "yengo_level": None,
        "group": None,
        "puzzle_count": len(uncollected_ids),
        "files_found": len(uncollected_ids),
        "files_missing": 0,
        "puzzles": puzzles_list,
    }

    if not dry_run:
        coll_dir = output_dir / "_uncollected"
        coll_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = coll_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    return {
        "dir": "_uncollected",
        "set_id": None,
        "name": "(Uncollected)",
        "puzzles": len(uncollected_ids),
        "found": len(uncollected_ids),
        "missing": 0,
    }


def organize(
    collections_json: Path = DEFAULT_COLLECTIONS_JSON,
    output_dir: Path = OUTPUT_DIR,
    dry_run: bool = False,
    include_uncollected: bool = True,
    rejection_log: Path | None = None,
) -> None:
    """Build collection manifests from local_collections.json and sgf-index.txt."""
    # Load rejection reasons if log provided
    rejections: dict[int, str] | None = None
    if rejection_log:
        logger.info(f"Parsing rejection log from {rejection_log}")
        rejections = parse_rejection_log(rejection_log)

    # Load data
    logger.info(f"Loading collections from {collections_json}")
    data = load_collections(collections_json)
    collections = data["collections"]
    logger.info(f"Loaded {len(collections)} collections")

    logger.info(f"Building puzzle index from {SGF_INDEX_FILE}")
    puzzle_index = build_puzzle_index(SGF_INDEX_FILE)
    logger.info(f"Indexed {len(puzzle_index)} puzzles")

    if dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - Manifest Generation Plan")
        print(f"{'='*60}")

    # Track all collected puzzle IDs
    all_collected_ids: set[int] = set()
    master_entries: list[dict] = []
    total_found = 0
    total_missing = 0

    for i, entry in enumerate(collections, 1):
        all_collected_ids.update(entry.get("puzzle_ids", []))
        summary = process_collection(entry, puzzle_index, output_dir, dry_run, rejections)
        master_entries.append(summary)
        total_found += summary["found"]
        total_missing += summary["missing"]

        status = f"  [{i}/{len(collections)}] {entry['name']}: {summary['found']}/{summary['puzzles']} found"
        if summary["missing"] > 0:
            status += f" ({summary['missing']} missing)"
        print(status)

    # Handle uncollected puzzles
    uncollected_count = 0
    if include_uncollected:
        uncollected_summary = process_uncollected(
            puzzle_index, all_collected_ids, output_dir, dry_run
        )
        if uncollected_summary:
            master_entries.append(uncollected_summary)
            uncollected_count = uncollected_summary["puzzles"]
            print(f"  [+] Uncollected: {uncollected_count} puzzles")

    # Write master index
    master_index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(collections_json.name),
        "total_collections": len(collections) + (1 if uncollected_count > 0 else 0),
        "total_indexed_puzzles": len(puzzle_index),
        "total_collected_puzzles": total_found,
        "total_uncollected_puzzles": uncollected_count,
        "total_missing_from_index": total_missing,
        "collections": master_entries,
    }

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        index_path = output_dir / "manifest-index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(master_index, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Collections: {len(collections)}")
    print(f"Indexed puzzles: {len(puzzle_index)}")
    print(f"Collected (found in index): {total_found}")
    print(f"Collected (missing from index): {total_missing}")
    print(f"Uncollected: {uncollected_count}")
    if not dry_run:
        print(f"Output: {output_dir}")
    else:
        print("(dry run, no files written)")
    print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize Tsumego Hero puzzles by collection (manifests only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without writing files.",
    )
    parser.add_argument(
        "--no-uncollected",
        action="store_true",
        help="Skip the _uncollected manifest.",
    )
    parser.add_argument(
        "--scraped-json",
        type=Path,
        default=DEFAULT_COLLECTIONS_JSON,
        help=f"Path to local_collections.json (default: {DEFAULT_COLLECTIONS_JSON})",
    )
    parser.add_argument(
        "--rejection-log",
        type=Path,
        default=None,
        help="Path to download log JSONL file for enriching manifests with skip reasons.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging.",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    organize(
        collections_json=args.scraped_json,
        dry_run=args.dry_run,
        include_uncollected=not args.no_uncollected,
        rejection_log=args.rejection_log,
    )


if __name__ == "__main__":
    main()
