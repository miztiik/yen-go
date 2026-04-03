#!/usr/bin/env python3
"""Update views/by-collection/*.json to use canonical collection slugs.

Reads the SLUG_MAP from consolidate_collections.py, then:
1. For each view file, determines the canonical slug
2. Merges entries from multiple old files that map to the same canonical slug
3. Writes merged canonical view files
4. Removes old view files that were absorbed
5. Rebuilds index.json

Usage:
    python tools/update_collection_views.py [--dry-run]
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from tools.core.atomic_write import atomic_write_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
VIEWS_DIR = ROOT / "yengo-puzzle-collections" / "views" / "by-collection"

# Import the SLUG_MAP from the consolidation script
sys.path.insert(0, str(ROOT / "tools"))
from consolidate_collections import SLUG_MAP


def update_views() -> None:
    """Update collection view files to use canonical slugs."""
    dry_run = "--dry-run" in sys.argv

    # Gather all existing view files (excluding index.json)
    view_files = sorted(VIEWS_DIR.glob("*.json"))
    view_files = [f for f in view_files if f.name != "index.json"]

    print(f"Found {len(view_files)} view files")

    # Build mapping: canonical_slug -> list of (old_slug, entries)
    canonical_entries: dict[str, list[dict]] = {}
    old_slugs_per_canonical: dict[str, list[str]] = {}

    for vf in view_files:
        old_slug = vf.stem  # filename without .json
        with open(vf, encoding="utf-8") as f:
            data = json.load(f)

        canonical_slug = SLUG_MAP.get(old_slug, "general-practice")

        canonical_entries.setdefault(canonical_slug, [])
        old_slugs_per_canonical.setdefault(canonical_slug, [])

        canonical_entries[canonical_slug].extend(data.get("entries", []))
        old_slugs_per_canonical[canonical_slug].append(old_slug)

    print(f"\nMapped to {len(canonical_entries)} canonical view files")

    # Deduplicate entries by path
    for slug in canonical_entries:
        seen_paths = set()
        unique = []
        for entry in canonical_entries[slug]:
            if entry["path"] not in seen_paths:
                seen_paths.add(entry["path"])
                unique.append(entry)
        canonical_entries[slug] = unique

    # Renumber sequence numbers
    for slug in canonical_entries:
        for i, entry in enumerate(canonical_entries[slug], 1):
            entry["sequence_number"] = i

    # Actions
    files_to_remove = []
    files_to_write = []

    for canonical_slug, entries in sorted(canonical_entries.items()):
        old_slugs = old_slugs_per_canonical[canonical_slug]

        # Write the canonical view file
        view_data = {
            "version": "3.0",
            "type": "collection",
            "name": canonical_slug,
            "total": len(entries),
            "entries": entries,
        }
        target_file = VIEWS_DIR / f"{canonical_slug}.json"
        files_to_write.append((target_file, view_data))

        # Mark old files for removal (if different from canonical)
        for old_slug in old_slugs:
            old_file = VIEWS_DIR / f"{old_slug}.json"
            if old_file != target_file and old_file.exists():
                files_to_remove.append(old_file)

    # Report
    print(f"\nFiles to write: {len(files_to_write)}")
    print(f"Files to remove: {len(files_to_remove)}")

    for slug, entries in sorted(canonical_entries.items()):
        old_slugs = old_slugs_per_canonical[slug]
        if len(old_slugs) > 1 or old_slugs[0] != slug:
            print(f"  {slug} <- {old_slugs} ({len(entries)} entries)")

    if dry_run:
        print("\n[DRY RUN] Not writing files.")
        return

    # Execute writes - atomic for cross-platform safety
    for target_file, view_data in files_to_write:
        atomic_write_json(target_file, view_data, ensure_ascii=False)

    # Execute removals
    for old_file in files_to_remove:
        os.remove(old_file)
        print(f"  Removed: {old_file.name}")

    # Rebuild index.json
    index_entries = []
    for _target_file, view_data in sorted(files_to_write, key=lambda entry: entry[0].stem):
        index_entries.append({
            "name": view_data["name"],
            "slug": view_data["name"],
            "paginated": False,
            "count": view_data["total"],
        })

    index_data = {
        "version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "collections": index_entries,
    }

    index_file = VIEWS_DIR / "index.json"
    atomic_write_json(index_file, index_data, ensure_ascii=False)

    print(f"\n✓ Updated {len(files_to_write)} view files")
    print(f"✓ Removed {len(files_to_remove)} old files")
    print(f"✓ Rebuilt index.json with {len(index_entries)} entries")


if __name__ == "__main__":
    update_views()
