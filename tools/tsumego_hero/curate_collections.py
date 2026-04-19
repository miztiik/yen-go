"""
Curate Tsumego Hero collections: drop, merge, assign levels and tiers.

Reads local_collections.json + curation_rules.json, produces
curated_collections.json with fewer, cleaner collection entries.

Entry point: python -m tools.tsumego_hero.curate_collections
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("tsumego_hero.curate_collections")

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "local_collections.json"
DEFAULT_RULES = SCRIPT_DIR / "curation_rules.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "curated_collections.json"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def curate(
    input_path: Path = DEFAULT_INPUT,
    rules_path: Path = DEFAULT_RULES,
    output_path: Path = DEFAULT_OUTPUT,
    dry_run: bool = False,
) -> None:
    """Apply curation rules to produce a curated collection list."""
    data = load_json(input_path)
    rules = load_json(rules_path)

    collections = data["collections"]
    drop_set_ids = set(rules.get("drop_set_ids", []))
    merge_groups = rules.get("merge_groups", True)
    rename_single_parts = rules.get("rename_single_parts", True)
    difficulty_map = rules.get("difficulty_to_yengo_level", {})
    tier_map = rules.get("tier_assignments", {})

    # Step 1: Drop Tier D
    dropped = []
    kept = []
    for c in collections:
        if c["set_id"] in drop_set_ids:
            dropped.append(c)
            logger.info(f"Dropping: {c['name']} (set_id={c['set_id']})")
        else:
            kept.append(c)

    # Step 2: Merge multi-part collections by group
    if merge_groups:
        groups: dict[str, list[dict]] = {}
        ungrouped: list[dict] = []

        for c in kept:
            group = c.get("group")
            if group:
                groups.setdefault(group, []).append(c)
            else:
                ungrouped.append(c)

        merged: list[dict] = []
        for group_slug, members in sorted(groups.items()):
            if len(members) == 1:
                # Single-part: optionally rename slug
                entry = members[0].copy()
                if rename_single_parts and entry["slug"].endswith("-1"):
                    entry["slug"] = entry["slug"][:-2]  # strip "-1"
                entry["group"] = None  # no longer multi-part
                merged.append(entry)
            else:
                # Multi-part: merge puzzle_ids in order
                members.sort(key=lambda c: c["slug"])  # deterministic order
                combined_ids: list[int] = []
                for m in members:
                    combined_ids.extend(m.get("puzzle_ids", []))

                # Use first member's metadata as base
                base = members[0]
                merged_entry = {
                    "set_id": base["set_id"],
                    "name": base["name"].split("#")[0].strip(),
                    "slug": group_slug,
                    "difficulty": base.get("difficulty"),
                    "puzzle_count_advertised": sum(
                        m.get("puzzle_count_advertised") or 0 for m in members
                    ),
                    "puzzle_count_scraped": len(combined_ids),
                    "puzzle_ids": combined_ids,
                    "group": None,
                    "sources_json_entry": base.get("sources_json_entry"),
                    "merged_from": [m["slug"] for m in members],
                }
                merged.append(merged_entry)
                logger.info(
                    f"Merged {len(members)} parts -> {group_slug} "
                    f"({len(combined_ids)} puzzles)"
                )

        kept = ungrouped + merged

    # Step 3: Assign yengo_level and tier
    for c in kept:
        # Resolve yengo_level
        yengo_level = None
        sources_entry = c.get("sources_json_entry")
        if sources_entry:
            yengo_level = sources_entry.get("yengo_level")
        if not yengo_level and c.get("difficulty"):
            yengo_level = difficulty_map.get(c["difficulty"])
        c["yengo_level"] = yengo_level

        # Assign tier
        slug = c["slug"]
        c["tier"] = tier_map.get(slug)

    # Sort by tier (A first) then slug
    tier_order = {"A": 0, "B": 1, "C": 2, "D": 3, None: 4}
    kept.sort(key=lambda c: (tier_order.get(c.get("tier"), 4), c["slug"]))

    # Build output
    all_puzzle_ids: set[int] = set()
    for c in kept:
        all_puzzle_ids.update(c.get("puzzle_ids", []))

    output = {
        "version": "1.0.0",
        "curated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(input_path.name),
        "rules_file": str(rules_path.name),
        "total_collections": len(kept),
        "total_unique_puzzles": len(all_puzzle_ids),
        "dropped_collections": len(dropped),
        "collections": kept,
    }

    # Summary
    tier_counts = {}
    for c in kept:
        t = c.get("tier", "?")
        tier_counts[t] = tier_counts.get(t, 0) + 1

    print(f"\n{'='*60}")
    print("Collection Curation Summary")
    print(f"{'='*60}")
    print(f"Input: {len(collections)} collections")
    print(f"Dropped: {len(dropped)}")
    print(f"Output: {len(kept)} collections, {len(all_puzzle_ids)} unique puzzles")
    print(f"By tier: {dict(sorted(tier_counts.items()))}")
    if dropped:
        for d in dropped:
            print(f"  Dropped: {d['name']} (set_id={d['set_id']})")
    print(f"{'='*60}")

    if not dry_run:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"Wrote: {output_path}")
    else:
        print("(dry run, no files written)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Curate Tsumego Hero collections (drop, merge, assign tiers).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input collections JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES,
        help=f"Curation rules JSON (default: {DEFAULT_RULES})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show summary without writing files.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    curate(
        input_path=args.input,
        rules_path=args.rules,
        output_path=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
