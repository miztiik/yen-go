"""
Generate a list of recoverable puzzle IDs for backfill download.

Reads enriched manifests to find missing puzzles, then filters to only
those with recoverable skip reasons (solution_too_deep, board_too_small).

Entry point: python -m tools.tsumego_hero.generate_backfill_ids
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MANIFEST_INDEX = Path("external-sources/t-hero/sgf-by-collection/manifest-index.json")
DEFAULT_OUTPUT = Path("external-sources/t-hero/backfill-ids.txt")

# Reasons that can be recovered by relaxing validation
RECOVERABLE_REASONS = {"solution_too_deep", "board_too_small"}


def collect_missing_ids(
    manifest_dir: Path,
    recoverable_only: bool = True,
) -> dict[str, list[int]]:
    """Scan per-collection manifests for missing puzzle IDs.

    Args:
        manifest_dir: Directory containing per-collection subdirs with manifest.json.
        recoverable_only: If True, only include IDs with recoverable skip reasons.

    Returns:
        Dict mapping reason code to sorted list of puzzle IDs.
    """
    by_reason: dict[str, list[int]] = {}

    index_path = manifest_dir / "manifest-index.json"
    if not index_path.exists():
        print(f"Error: {index_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    for coll_entry in index["collections"]:
        slug_dir = coll_entry["dir"]
        manifest_path = manifest_dir / slug_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        for puzzle in manifest.get("puzzles", []):
            if puzzle.get("found"):
                continue
            reason = puzzle.get("skip_reason", "unknown")
            if recoverable_only and reason not in RECOVERABLE_REASONS:
                continue
            by_reason.setdefault(reason, []).append(puzzle["url_id"])

    # Sort each reason list
    for reason in by_reason:
        by_reason[reason].sort()

    return by_reason


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate backfill ID list from enriched manifests.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include all missing IDs, not just recoverable ones.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("external-sources/t-hero/sgf-by-collection"),
        help="Path to sgf-by-collection directory.",
    )

    args = parser.parse_args()

    by_reason = collect_missing_ids(
        args.manifest_dir,
        recoverable_only=not args.all,
    )

    if not by_reason:
        print("No missing puzzle IDs found matching criteria.")
        return

    # Combine all IDs, deduplicate, sort
    all_ids = sorted(set(uid for ids in by_reason.values() for uid in ids))

    # Print summary
    print(f"Missing puzzle IDs by reason:")
    for reason, ids in sorted(by_reason.items()):
        print(f"  {reason}: {len(ids)}")
    print(f"  Total (deduplicated): {len(all_ids)}")

    # Write output
    with open(args.output, "w", encoding="utf-8") as f:
        for uid in all_ids:
            f.write(f"{uid}\n")

    print(f"Wrote {len(all_ids)} IDs to {args.output}")


if __name__ == "__main__":
    main()
