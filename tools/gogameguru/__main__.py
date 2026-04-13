"""
Imports 421 SGF puzzles from the gogameguru/go-problems GitHub repo:
  - weekly-go-problems/easy/       (140 SGFs) → elementary
  - weekly-go-problems/intermediate/ (140 SGFs) → intermediate
  - weekly-go-problems/hard/       (140 SGFs) → advanced
  - weekly-go-problems/other/ggg-eternal-life.sgf (1 SGF) → advanced

Usage:
  python -m tools.gogameguru              # auto-clone + import
  python -m tools.gogameguru --dry-run    # preview only
  python -m tools.gogameguru /path/to/clone  # use existing clone
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tools.core.paths import get_project_root, rel_path
from tools.core.sgf_parser import parse_sgf
from tools.core.sgf_builder import SGFBuilder
from tools.core.index import add_entry, sort_and_rewrite

# GoGameGuru difficulty → YenGo level slug
LEVEL_MAP: dict[str, str] = {
    "easy": "elementary",
    "intermediate": "intermediate",
    "hard": "advanced",
}

PROJECT_ROOT = get_project_root()
OUTPUT_DIR = PROJECT_ROOT / "external-sources" / "gogameguru"
SGF_DIR = OUTPUT_DIR / "sgf"
INDEX_PATH = OUTPUT_DIR / "sgf-index.txt"
BATCH_NAME = "batch-001"
REPO_URL = "https://github.com/gogameguru/go-problems.git"


def collect_sgf_files(clone_dir: Path) -> list[tuple[Path, str]]:
    """Collect all SGF files to import with their level slugs.

    Returns list of (sgf_path, yengo_level_slug) tuples.
    """
    weekly_dir = clone_dir / "weekly-go-problems"
    if not weekly_dir.is_dir():
        print(f"ERROR: {weekly_dir} not found. Is this a valid clone?", file=sys.stderr)
        sys.exit(1)

    files: list[tuple[Path, str]] = []

    # Weekly problems: easy, intermediate, hard
    for difficulty, level_slug in LEVEL_MAP.items():
        diff_dir = weekly_dir / difficulty
        if not diff_dir.is_dir():
            print(f"WARNING: {diff_dir} not found, skipping", file=sys.stderr)
            continue
        sgf_paths = sorted(diff_dir.glob("*.sgf"))
        for p in sgf_paths:
            files.append((p, level_slug))

    # Other: only ggg-eternal-life.sgf
    eternal_life = weekly_dir / "other" / "ggg-eternal-life.sgf"
    if eternal_life.is_file():
        files.append((eternal_life, "advanced"))
    else:
        print(f"WARNING: {eternal_life} not found", file=sys.stderr)

    return files


def _clean_comment(text: str) -> str:
    """Strip gogameguru.com URLs from comment text."""
    lines = text.splitlines()
    cleaned = [ln for ln in lines if "gogameguru.com" not in ln]
    return "\n".join(cleaned).strip()


def rebuild_sgf(sgf_text: str, level_slug: str, puzzle_name: str) -> str:
    """Parse source SGF and rebuild with whitelist properties + YG level."""
    tree = parse_sgf(sgf_text)
    builder = SGFBuilder.from_tree(tree)

    # Strip domain URL from root comment
    if builder.root_comment:
        builder.root_comment = _clean_comment(builder.root_comment)

    # Clear any carried-over metadata (SO, AP, RU, KM, etc. are in metadata dict)
    builder.metadata.clear()

    # Set CA[UTF-8] as metadata
    builder.metadata["CA"] = "UTF-8"

    # Set YenGo level
    builder.set_level_slug(level_slug)

    # Set game name to source puzzle name (pipeline will overwrite with YENGO-{hash})
    builder.set_game_name(puzzle_name)

    return builder.build()


def load_existing_ids() -> set[str]:
    """Load already-imported puzzle IDs from index."""
    if not INDEX_PATH.exists():
        return set()
    ids: set[str] = set()
    for line in INDEX_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            # "batch-001/ggg-easy-01.sgf" → "ggg-easy-01"
            filename = line.rsplit("/", 1)[-1]
            ids.add(filename.removesuffix(".sgf"))
    return ids


def _ensure_clone(clone_dir: Path | None) -> tuple[Path, bool]:
    """Return (clone_path, should_cleanup).

    If clone_dir is provided and exists, use it directly.
    Otherwise, shallow-clone the repo to a temp directory.
    """
    if clone_dir and clone_dir.is_dir():
        # Verify it looks like the right repo
        if (clone_dir / "weekly-go-problems").is_dir():
            return clone_dir, False
        print(f"ERROR: {clone_dir} exists but has no weekly-go-problems/", file=sys.stderr)
        sys.exit(1)

    # Auto-clone to temp
    tmp_dir = Path(tempfile.mkdtemp(prefix="gogameguru-"))
    print(f"Cloning {REPO_URL} ...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, str(tmp_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: git clone failed:\n{result.stderr}", file=sys.stderr)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)
    print("Clone complete.\n")
    return tmp_dir, True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import GoGameGuru Weekly Go Problems into YenGo"
    )
    parser.add_argument(
        "clone_dir",
        nargs="?",
        type=Path,
        default=None,
        help="Path to existing clone (auto-clones if omitted)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files",
    )
    args = parser.parse_args()

    clone_dir, cleanup = _ensure_clone(args.clone_dir)

    try:
        return _run_import(clone_dir, dry_run=args.dry_run)
    finally:
        if cleanup:
            shutil.rmtree(clone_dir, ignore_errors=True)


def _run_import(clone_dir: Path, *, dry_run: bool) -> int:

    # Collect SGFs
    files = collect_sgf_files(clone_dir)
    if not files:
        print("No SGF files found.", file=sys.stderr)
        return 1

    existing_ids = load_existing_ids()

    print(f"\n{'='*60}")
    print("GoGameGuru Weekly Go Problems Importer")
    print(f"{'='*60}")
    print(f"Source:     {clone_dir}")
    print(f"Output:     {rel_path(OUTPUT_DIR)}")
    print(f"Total SGFs: {len(files)}")
    print(f"Already:    {len(existing_ids)}")
    print(f"Dry run:    {dry_run}")
    print(f"{'='*60}\n")

    batch_dir = SGF_DIR / BATCH_NAME
    if not dry_run:
        batch_dir.mkdir(parents=True, exist_ok=True)

    stats = {"imported": 0, "skipped": 0, "errors": 0}
    start_time = time.monotonic()

    for sgf_path, level_slug in files:
        puzzle_name = sgf_path.stem  # e.g. "ggg-easy-01"

        # Skip duplicates
        if puzzle_name in existing_ids:
            stats["skipped"] += 1
            continue

        try:
            sgf_text = sgf_path.read_text(encoding="utf-8")
            rebuilt = rebuild_sgf(sgf_text, level_slug, puzzle_name)

            if dry_run:
                print(f"  [DRY] {puzzle_name}.sgf  (YG[{level_slug}])")
                stats["imported"] += 1
                continue

            # Write file
            out_path = batch_dir / f"{puzzle_name}.sgf"
            out_path.write_text(rebuilt, encoding="utf-8")

            # Update index
            add_entry(INDEX_PATH, f"{BATCH_NAME}/{puzzle_name}.sgf")
            existing_ids.add(puzzle_name)

            stats["imported"] += 1

            if stats["imported"] % 50 == 0:
                elapsed = time.monotonic() - start_time
                print(
                    f"  [{stats['imported']}/{len(files)}] "
                    f"imported | {elapsed:.1f}s elapsed"
                )

        except Exception as e:
            stats["errors"] += 1
            print(f"  ERROR: {puzzle_name}: {e}", file=sys.stderr)

    # Sort index
    if not dry_run and INDEX_PATH.exists():
        sort_and_rewrite(INDEX_PATH)

    elapsed = time.monotonic() - start_time

    print(f"\n{'='*60}")
    print("Import Summary")
    print(f"{'='*60}")
    print(f"Imported: {stats['imported']}")
    print(f"Skipped:  {stats['skipped']} (already exist)")
    print(f"Errors:   {stats['errors']}")
    print(f"Duration: {elapsed:.1f}s")
    print(f"Output:   {rel_path(OUTPUT_DIR)}")
    print(f"{'='*60}")

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
