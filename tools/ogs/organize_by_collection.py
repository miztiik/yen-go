"""
Organize OGS SGF files into collection-based directory structure.

Reads the collections JSONL, filters by tier (premier + curated),
copies SGF files into per-collection directories with manifests.

Directory structure:
  sgf-by-collection/
  ├── manifest-index.json
  ├── premier/
  │   ├── 01/  (first 100 collections by sort_rank)
  │   │   ├── {id}-{slug}/
  │   │   │   ├── manifest.json
  │   │   │   ├── 30705.sgf
  │   │   │   └── ...
  │   │   └── ...
  │   ├── 02/
  │   └── ...
  └── curated/
      ├── 01/
      └── ...

Usage:
  python organize_by_collection.py [--dry-run] [--batch-size 100]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
JSONL_PATH = SCRIPT_DIR / "20260211-203516-collections-sorted.jsonl"
SGF_INDEX_PATH = SCRIPT_DIR / "sgf-index.txt"
SGF_SOURCE_DIR = SCRIPT_DIR / "sgf"
OUTPUT_DIR = SCRIPT_DIR / "sgf-by-collection"
TRANSLATIONS_PATH = SCRIPT_DIR / "collection-name-translations.json"

ALLOWED_TIERS = {"premier", "curated"}
DEFAULT_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def load_translations() -> dict[str, str]:
    """Load English slug overrides for non-Latin collection names."""
    if TRANSLATIONS_PATH.exists():
        with open(TRANSLATIONS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Remove comment keys
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}


def slugify(name: str) -> str:
    """Convert collection name to an ASCII-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def get_slug(collection_id: int, name: str, translations: dict[str, str]) -> str:
    """Get the best English slug for a collection, using translations if needed."""
    override = translations.get(str(collection_id))
    if override:
        return override

    slug = slugify(name)
    if len(slug) >= 4:
        return slug

    # Fallback: just use what we can
    return slug if slug else "untitled"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_collections() -> list[dict]:
    """Load and filter collections from JSONL (premier + curated only)."""
    collections = []
    with open(JSONL_PATH, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0:  # metadata line
                continue
            rec = json.loads(line)
            if rec.get("quality_tier") in ALLOWED_TIERS:
                collections.append(rec)
    # Sort by sort_rank (should already be sorted, but ensure)
    collections.sort(key=lambda r: r.get("sort_rank", 9999))
    return collections


def build_puzzle_index() -> dict[int, str]:
    """Build puzzle_id -> batch_path mapping from sgf-index.txt.

    Index lines look like: batch-001/2.sgf
    We extract puzzle_id = 2, path = batch-001/2.sgf
    """
    index: dict[int, str] = {}
    with open(SGF_INDEX_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Extract filename without .sgf extension -> puzzle_id
            parts = line.rsplit("/", 1)
            if len(parts) == 2:
                filename = parts[1]
                if filename.endswith(".sgf"):
                    try:
                        puzzle_id = int(filename[:-4])
                        index[puzzle_id] = line
                    except ValueError:
                        pass
    return index


# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------

def assign_batches(
    collections: list[dict], batch_size: int
) -> dict[str, list[tuple[str, dict]]]:
    """Assign collections to tier/batch-NN directories.

    Returns: {tier: [(batch_label, collection_record), ...]}
    """
    by_tier: dict[str, list[dict]] = {"premier": [], "curated": []}
    for rec in collections:
        tier = rec["quality_tier"]
        if tier in by_tier:
            by_tier[tier].append(rec)

    result: dict[str, list[tuple[str, dict]]] = {}
    for tier, recs in by_tier.items():
        assignments = []
        for idx, rec in enumerate(recs):
            batch_num = (idx // batch_size) + 1
            batch_label = f"{batch_num:02d}"
            assignments.append((batch_label, rec))
        result[tier] = assignments

    return result


# ---------------------------------------------------------------------------
# Copy logic
# ---------------------------------------------------------------------------

def process_collection(
    rec: dict,
    tier: str,
    batch_label: str,
    puzzle_index: dict[int, str],
    translations: dict[str, str],
    dry_run: bool,
) -> dict:
    """Process a single collection: create dir, copy files, write manifest.

    Returns a summary dict for the master index.
    """
    coll_id = rec["id"]
    name = rec["name"]
    slug = get_slug(coll_id, name, translations)
    dir_name = f"{coll_id}-{slug}"
    coll_dir = OUTPUT_DIR / tier / batch_label / dir_name

    puzzles = rec.get("puzzles", [])
    puzzle_entries = []
    files_found = 0
    files_missing = 0

    if not dry_run:
        coll_dir.mkdir(parents=True, exist_ok=True)

    for pid in puzzles:
        batch_path = puzzle_index.get(pid)
        found = batch_path is not None
        entry = {"ogs_id": pid, "found": found}

        if found:
            src = SGF_SOURCE_DIR / batch_path
            dst = coll_dir / f"{pid}.sgf"
            entry["file"] = f"{pid}.sgf"
            if not dry_run and src.exists():
                shutil.copy2(src, dst)
                files_found += 1
            elif not dry_run:
                entry["found"] = False
                files_missing += 1
            else:
                if src.exists():
                    files_found += 1
                else:
                    entry["found"] = False
                    files_missing += 1
        else:
            files_missing += 1

        puzzle_entries.append(entry)

    # Build manifest
    difficulty = rec.get("difficulty", {})
    manifest = {
        "ogs_collection_id": coll_id,
        "name": name,
        "quality_tier": tier,
        "priority_score": rec.get("priority_score"),
        "sort_rank": rec.get("sort_rank"),
        "bayesian_rating": rec.get("bayesian_rating"),
        "solve_rate": rec.get("solve_rate"),
        "difficulty": {
            "min_rank": difficulty.get("min_rank"),
            "max_rank": difficulty.get("max_rank"),
            "yengo_level": difficulty.get("yengo_level"),
        },
        "puzzle_count": len(puzzles),
        "files_found": files_found,
        "files_missing": files_missing,
        "puzzles": puzzle_entries,
    }

    if not dry_run:
        manifest_path = coll_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    return {
        "dir": f"{tier}/{batch_label}/{dir_name}",
        "id": coll_id,
        "name": name,
        "tier": tier,
        "batch": batch_label,
        "puzzles": len(puzzles),
        "found": files_found,
        "missing": files_missing,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Organize OGS SGF files into collection directories"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without copying files",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Collections per batch directory (default: {DEFAULT_BATCH_SIZE})",
    )
    args = parser.parse_args()

    # Pre-flight checks
    for path, desc in [
        (JSONL_PATH, "Collections JSONL"),
        (SGF_INDEX_PATH, "SGF index"),
        (SGF_SOURCE_DIR, "SGF source directory"),
    ]:
        if not path.exists():
            print(f"ERROR: {desc} not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Check if output exists
    if OUTPUT_DIR.exists() and not args.dry_run:
        response = input(
            f"Output directory already exists: {OUTPUT_DIR}\n"
            f"Continue and overwrite? (y/N): "
        )
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    print("Loading collections...")
    collections = load_collections()
    print(f"  {len(collections)} premier+curated collections loaded")

    print("Loading translations...")
    translations = load_translations()
    print(f"  {len(translations)} slug overrides loaded")

    print("Building puzzle index...")
    puzzle_index = build_puzzle_index()
    print(f"  {len(puzzle_index)} puzzles indexed")

    print(f"Assigning batches (batch_size={args.batch_size})...")
    batched = assign_batches(collections, args.batch_size)
    for tier, assignments in batched.items():
        max_batch = assignments[-1][0] if assignments else "00"
        print(f"  {tier}: {len(assignments)} collections -> batches 01-{max_batch}")

    if args.dry_run:
        print("\n=== DRY RUN — no files will be copied ===\n")
    else:
        print(f"\nOutput directory: {OUTPUT_DIR}\n")

    # Process collections
    start_time = time.time()
    master_entries = []
    total_found = 0
    total_missing = 0
    seen_ids = set()

    for tier, assignments in batched.items():
        for i, (batch_label, rec) in enumerate(assignments):
            coll_id = rec["id"]
            # Skip duplicates in JSONL
            if coll_id in seen_ids:
                continue
            seen_ids.add(coll_id)

            summary = process_collection(
                rec, tier, batch_label, puzzle_index, translations, args.dry_run
            )
            master_entries.append(summary)
            total_found += summary["found"]
            total_missing += summary["missing"]

            # Progress every 100 collections
            count = len(master_entries)
            if count % 100 == 0:
                elapsed = time.time() - start_time
                print(
                    f"  [{count:>4}/{len(collections)}] "
                    f"{summary['dir'][:50]}... "
                    f"({elapsed:.1f}s)"
                )

    elapsed = time.time() - start_time

    # Write master index
    if not args.dry_run:
        master_index = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source_jsonl": JSONL_PATH.name,
            "translations_file": TRANSLATIONS_PATH.name,
            "filter": {"tiers": sorted(ALLOWED_TIERS), "batch_size": args.batch_size},
            "total_collections": len(master_entries),
            "total_files_copied": total_found,
            "total_files_missing": total_missing,
            "tier_summary": {
                tier: {
                    "collections": len([e for e in master_entries if e["tier"] == tier]),
                    "batches": len(
                        set(e["batch"] for e in master_entries if e["tier"] == tier)
                    ),
                }
                for tier in sorted(ALLOWED_TIERS)
            },
            "collections": [
                {
                    "dir": e["dir"],
                    "id": e["id"],
                    "tier": e["tier"],
                    "puzzles": e["puzzles"],
                    "found": e["found"],
                    "missing": e["missing"],
                }
                for e in master_entries
            ],
        }
        index_path = OUTPUT_DIR / "manifest-index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(master_index, f, indent=2, ensure_ascii=False)
        print(f"\nMaster index written: {index_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"{'DRY RUN ' if args.dry_run else ''}COMPLETE in {elapsed:.1f}s")
    print(f"{'='*60}")
    print(f"  Collections processed: {len(master_entries)}")
    print(f"  Files {'would be ' if args.dry_run else ''}copied: {total_found:,}")
    print(f"  Files missing from index: {total_missing:,}")
    for tier in sorted(ALLOWED_TIERS):
        tier_entries = [e for e in master_entries if e["tier"] == tier]
        tier_batches = len(set(e["batch"] for e in tier_entries))
        print(f"  {tier}: {len(tier_entries)} collections in {tier_batches} batches")


if __name__ == "__main__":
    main()
