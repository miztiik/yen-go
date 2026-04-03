#!/usr/bin/env python3
"""Update YL[] properties in SGF files to use canonical collection slugs.

Reads the SLUG_MAP from consolidate_collections.py, then updates
the YL[] property in every SGF file that references an old slug.

Usage:
    python tools/update_sgf_collections.py [--dry-run]
"""

import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SGF_DIR = ROOT / "yengo-puzzle-collections" / "sgf"

# Import the SLUG_MAP from the consolidation script
sys.path.insert(0, str(ROOT / "tools"))
from consolidate_collections import SLUG_MAP

YL_PATTERN = re.compile(r"YL\[([^\]]*)\]")


def update_sgf_files() -> None:
    """Update YL[] in SGF files to use canonical slugs."""
    dry_run = "--dry-run" in sys.argv

    sgf_files = list(SGF_DIR.rglob("*.sgf"))
    print(f"Scanning {len(sgf_files)} SGF files...")

    updated = 0
    unchanged = 0

    for sgf_file in sgf_files:
        content = sgf_file.read_text(encoding="utf-8")

        match = YL_PATTERN.search(content)
        if not match:
            continue

        old_value = match.group(1)
        # YL can contain comma-separated slugs
        old_slugs = [s.strip() for s in old_value.split(",") if s.strip()]
        new_slugs = []
        for slug in old_slugs:
            canonical = SLUG_MAP.get(slug, slug)
            if canonical not in new_slugs:
                new_slugs.append(canonical)

        new_value = ",".join(sorted(set(new_slugs)))

        if old_value != new_value:
            new_content = content.replace(f"YL[{old_value}]", f"YL[{new_value}]")
            if not dry_run:
                sgf_file.write_text(new_content, encoding="utf-8")
            print(f"  {sgf_file.name}: YL[{old_value}] -> YL[{new_value}]")
            updated += 1
        else:
            unchanged += 1

    print(f"\nUpdated: {updated}")
    print(f"Unchanged: {unchanged}")
    if dry_run:
        print("[DRY RUN] No files were modified.")


if __name__ == "__main__":
    update_sgf_files()
