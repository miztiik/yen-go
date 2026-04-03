#!/usr/bin/env python3
"""Hydrate calibration fixtures from external-sources.

Reads puzzles from external-sources/ matching target difficulty ranges,
copies a balanced sample to tests/fixtures/calibration/{source}-{level}/,
and does NOT overwrite existing Cho Chikun fixtures.

Usage:
    python scripts/hydrate_calibration_fixtures.py \
        --source-dir ../../external-sources/sanderland/sgf \
        --target-dir tests/fixtures/calibration/sanderland-elementary \
        --level elementary \
        --count 10

Plan 010, P4.3: Fixture Hydration Script.
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

# Level slug → approximate difficulty ranges (level_id from puzzle-levels.json)
_LEVEL_RANGES = {
    "novice": (110, 119),
    "beginner": (120, 129),
    "elementary": (130, 139),
    "intermediate": (140, 149),
    "upper-intermediate": (150, 159),
    "advanced": (160, 169),
    "low-dan": (170, 179),
    "high-dan": (180, 189),
    "expert": (190, 230),
}

# Protected fixture directories — never overwrite
_PROTECTED_PREFIXES = ["cho-"]


def _read_yg_from_sgf(sgf_path: Path) -> str | None:
    """Extract YG (level slug) from an SGF file.

    Uses simple string search — no regex, no sgfmill dependency.
    """
    try:
        content = sgf_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # Find YG[...] property
    marker = "YG["
    idx = content.find(marker)
    if idx < 0:
        return None
    start = idx + len(marker)
    end = content.find("]", start)
    if end < 0:
        return None
    return content[start:end].strip()


def hydrate(
    source_dir: Path,
    target_dir: Path,
    level: str,
    count: int = 10,
    seed: int | None = 42,
) -> list[Path]:
    """Copy a balanced sample of puzzles to the calibration fixture directory.

    Args:
        source_dir: Directory containing source SGF files.
        target_dir: Destination calibration fixture directory.
        level: Target difficulty level slug (e.g. "elementary").
        count: Number of puzzles to sample.
        seed: Random seed for reproducibility (None for random).

    Returns:
        List of copied file paths.
    """
    # Safety check: don't overwrite protected directories
    target_name = target_dir.name
    for prefix in _PROTECTED_PREFIXES:
        if target_name.startswith(prefix):
            print(
                f"ERROR: Target directory '{target_name}' starts with "
                f"protected prefix '{prefix}'. Cho Chikun fixtures must "
                f"not be overwritten.",
                file=sys.stderr,
            )
            return []

    if level not in _LEVEL_RANGES:
        print(f"ERROR: Unknown level '{level}'. Valid: {list(_LEVEL_RANGES.keys())}", file=sys.stderr)
        return []

    if not source_dir.exists():
        print(f"ERROR: Source directory does not exist: {source_dir}", file=sys.stderr)
        return []

    # Collect SGFs matching the target level
    matching: list[Path] = []
    for sgf_file in sorted(source_dir.glob("*.sgf")):
        yg = _read_yg_from_sgf(sgf_file)
        if yg == level:
            matching.append(sgf_file)

    if not matching:
        print(f"No SGFs found with YG={level} in {source_dir}")
        return []

    # Sample
    rng = random.Random(seed)
    sample = rng.sample(matching, min(count, len(matching)))

    # Copy to target
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for sgf in sample:
        dest = target_dir / sgf.name
        if dest.exists():
            print(f"  SKIP (exists): {sgf.name}")
            continue
        shutil.copy2(sgf, dest)
        copied.append(dest)
        print(f"  COPY: {sgf.name}")

    print(f"\nHydrated {len(copied)} puzzles to {target_dir}")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hydrate calibration fixtures from external sources."
    )
    parser.add_argument(
        "--source-dir", type=Path, required=True,
        help="Source directory containing SGF files",
    )
    parser.add_argument(
        "--target-dir", type=Path, required=True,
        help="Target calibration fixture directory",
    )
    parser.add_argument(
        "--level", required=True, choices=list(_LEVEL_RANGES.keys()),
        help="Target difficulty level slug",
    )
    parser.add_argument(
        "--count", type=int, default=10,
        help="Number of puzzles to sample (default: 10)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42, use -1 for random)",
    )
    args = parser.parse_args()

    seed = args.seed if args.seed >= 0 else None
    hydrate(args.source_dir, args.target_dir, args.level, args.count, seed)


if __name__ == "__main__":
    main()
