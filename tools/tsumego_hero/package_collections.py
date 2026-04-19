"""
Package Tsumego Hero puzzles into global-slug-based directory structure.

Reads the collection_slug_mapping.json and per-collection manifests from
sgf-by-collection/, then copies SGF files into the final directory structure
under external-sources/t-hero/sgf-by-global-slug/.

Each copied SGF file gets its YL[] property stamped/updated to match the
global slug and chapter assignment. Originals in sgf/batch-NNN/ are untouched.

Directory structure:
  sgf-by-global-slug/
    gokyo-shumyo/
      01-volume-i/
        th-6750.sgf   # contains YL[gokyo-shumyo:01-volume-i/1]
      02-volume-ii/
        ...
    capture-problems/
      th-1234.sgf     # contains YL[capture-problems]

Entry point: python -m tools.tsumego_hero.package_collections
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("tsumego_hero.package_collections")

SCRIPT_DIR = Path(__file__).resolve().parent
T_HERO_DIR = Path("external-sources/t-hero")
MAPPING_FILE = SCRIPT_DIR / "collection_slug_mapping.json"
MANIFESTS_DIR = T_HERO_DIR / "sgf-by-collection"
OUTPUT_DIR = T_HERO_DIR / "sgf-by-global-slug"

# Regex to match existing YL property in SGF root node
YL_PATTERN = re.compile(r"YL\[[^\]]*\]")


def format_yl_value(global_slug: str, chapter: str | None, position: int) -> str:
    """Build the YL property value string.

    Examples:
        format_yl_value("gokyo-shumyo", "01-volume-i", 15)
          -> "gokyo-shumyo:01-volume-i/15"
        format_yl_value("capture-problems", None, 0)
          -> "capture-problems"
    """
    if chapter and position > 0:
        return f"{global_slug}:{chapter}/{position}"
    if chapter:
        return f"{global_slug}:{chapter}"
    return global_slug


def stamp_yl(sgf_content: str, yl_value: str) -> str:
    """Stamp or replace YL[] property in SGF content.

    If YL[] already exists, replace it. Otherwise insert after the
    first property in the root node (after the opening "(;").
    """
    yl_prop = f"YL[{yl_value}]"

    if YL_PATTERN.search(sgf_content):
        return YL_PATTERN.sub(yl_prop, sgf_content)

    # Insert YL after the first "]" in the root node
    # SGF starts with "(;" then properties like "SZ[19]FF[4]..."
    # We insert after the first complete property
    first_bracket = sgf_content.find("]")
    if first_bracket == -1:
        return sgf_content
    return sgf_content[:first_bracket + 1] + yl_prop + sgf_content[first_bracket + 1:]


def load_mapping(mapping_path: Path) -> list[dict]:
    """Load the TH-to-global slug mapping."""
    with open(mapping_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["mappings"]


def load_manifest(manifests_dir: Path, th_slug: str) -> dict | None:
    """Load manifest.json for a TH collection slug.

    Multi-part collections may have slug-1, slug-2 etc. suffixes in
    sgf-by-collection/. We search for the base slug directory first,
    then also look for -N suffixed directories for multi-part collections.
    """
    candidates = sorted(manifests_dir.glob(f"{th_slug}*/manifest.json"))
    if not candidates:
        return None

    # Merge all matching manifests (base + parts)
    merged_puzzles: list[dict] = []
    base_manifest: dict | None = None

    for manifest_path in candidates:
        dir_name = manifest_path.parent.name
        # Only match exact slug or slug-N pattern
        if dir_name != th_slug and not dir_name.startswith(f"{th_slug}-"):
            continue
        # Skip if it's a different collection entirely (e.g., "gokyo-shumyo-ii" != "gokyo-1-*")
        suffix = dir_name[len(th_slug):]
        if suffix and not (suffix.startswith("-") and suffix[1:].isdigit()):
            continue

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        if base_manifest is None:
            base_manifest = manifest

        for p in manifest.get("puzzles", []):
            if p.get("found"):
                merged_puzzles.append(p)

    if base_manifest:
        base_manifest["_merged_puzzles"] = merged_puzzles
    return base_manifest


def package_collection(
    mapping: dict,
    manifests_dir: Path,
    output_dir: Path,
    t_hero_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Package a single collection mapping into the output directory.

    Returns summary dict with counts.
    """
    th_slug = mapping["th_slug"]
    global_slug = mapping["global_slug"]
    chapter = mapping["chapter"]
    action = mapping["action"]

    if action == "drop":
        return {
            "th_slug": th_slug,
            "global_slug": None,
            "action": "drop",
            "files": 0,
            "skipped": 0,
        }

    manifest = load_manifest(manifests_dir, th_slug)
    if manifest is None:
        logger.warning(f"No manifest found for {th_slug}")
        return {
            "th_slug": th_slug,
            "global_slug": global_slug,
            "action": "error",
            "files": 0,
            "skipped": 0,
            "error": "manifest_not_found",
        }

    puzzles = manifest.get("_merged_puzzles", [])

    # Build target directory
    if chapter:
        target_dir = output_dir / global_slug / chapter
    else:
        target_dir = output_dir / global_slug

    copied = 0
    skipped = 0
    yl_stamped = 0

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    # Sort puzzles by source path for deterministic position numbering
    sorted_puzzles = sorted(puzzles, key=lambda p: p.get("source", ""))

    for position, puzzle in enumerate(sorted_puzzles, 1):
        source_rel = puzzle.get("source", "")
        if not source_rel:
            skipped += 1
            continue

        source_path = t_hero_dir / source_rel
        if not source_path.exists():
            logger.debug(f"Source not found: {source_path}")
            skipped += 1
            continue

        target_path = target_dir / source_path.name

        if not dry_run:
            # Read, stamp YL, write (always copy, never hardlink)
            try:
                content = source_path.read_text(encoding="utf-8")
                yl_value = format_yl_value(global_slug, chapter, position)
                content = stamp_yl(content, yl_value)
                target_path.write_text(content, encoding="utf-8")
                yl_stamped += 1
            except Exception as exc:
                logger.warning(f"YL stamp failed for {source_path.name}: {exc}, falling back to plain copy")
                shutil.copy2(source_path, target_path)
        copied += 1

    return {
        "th_slug": th_slug,
        "global_slug": global_slug,
        "chapter": chapter,
        "action": "packaged",
        "files": copied,
        "skipped": skipped,
        "yl_stamped": yl_stamped,
    }


def build_sgf_index(t_hero_dir: Path) -> dict[str, str]:
    """Build mapping from SGF filename to relative path by scanning sgf-index.txt."""
    index: dict[str, str] = {}
    index_path = t_hero_dir / "sgf-index.txt"
    with open(index_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                index[Path(line).name] = line
    return index


def package_uncollected(
    output_dir: Path,
    t_hero_dir: Path,
    packaged_filenames: set[str],
    dry_run: bool = False,
) -> dict:
    """Copy uncollected SGF files into general-practice with YL stamping.

    Returns summary dict.
    """
    sgf_index = build_sgf_index(t_hero_dir)
    uncollected_paths = sorted(
        rel_path for fname, rel_path in sgf_index.items()
        if fname not in packaged_filenames
    )

    if not uncollected_paths:
        return {"action": "uncollected", "files": 0, "yl_stamped": 0}

    target_dir = output_dir / "general-practice"
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    yl_stamped = 0
    # Get existing file count for position numbering continuation
    existing = len(list(target_dir.glob("*.sgf"))) if target_dir.exists() else 0

    for i, rel_path in enumerate(uncollected_paths, existing + 1):
        source_path = t_hero_dir / rel_path
        if not source_path.exists():
            continue
        target_path = target_dir / source_path.name
        if target_path.exists():
            # Already packaged from a collection mapping — skip
            continue
        if not dry_run:
            try:
                content = source_path.read_text(encoding="utf-8")
                content = stamp_yl(content, "general-practice")
                target_path.write_text(content, encoding="utf-8")
                yl_stamped += 1
            except Exception as exc:
                logger.warning(f"YL stamp failed for {source_path.name}: {exc}")
                shutil.copy2(source_path, target_path)
        copied += 1

    return {"action": "uncollected", "files": copied, "yl_stamped": yl_stamped}


def write_directory_manifests(output_dir: Path) -> int:
    """Write a manifest.json into each directory in the output structure.

    Returns number of manifests written.
    """
    manifests_written = 0

    for dir_path in sorted(output_dir.rglob("*")):
        if not dir_path.is_dir():
            continue
        sgf_files = sorted(f.name for f in dir_path.iterdir() if f.suffix == ".sgf")
        if not sgf_files:
            continue

        manifest = {
            "directory": str(dir_path.relative_to(output_dir)),
            "file_count": len(sgf_files),
            "files": sgf_files,
        }

        manifest_path = dir_path / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        manifests_written += 1

    # Also write a root manifest with collection-level summary
    collections: list[dict] = []
    for entry in sorted(output_dir.iterdir()):
        if not entry.is_dir():
            continue
        slug = entry.name
        # Count total SGFs including subdirectories
        total_sgfs = len(list(entry.rglob("*.sgf")))
        chapters = sorted(
            d.name for d in entry.iterdir()
            if d.is_dir() and any(d.glob("*.sgf"))
        )
        collections.append({
            "slug": slug,
            "total_files": total_sgfs,
            "chapters": chapters if chapters else None,
        })

    root_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_collections": len(collections),
        "total_files": sum(c["total_files"] for c in collections),
        "collections": collections,
    }
    with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(root_manifest, f, indent=2, ensure_ascii=False)
    manifests_written += 1

    return manifests_written


def package_all(
    mapping_path: Path = MAPPING_FILE,
    manifests_dir: Path = MANIFESTS_DIR,
    output_dir: Path = OUTPUT_DIR,
    t_hero_dir: Path = T_HERO_DIR,
    dry_run: bool = False,
) -> None:
    """Package all TH collections into global-slug directory structure."""
    mappings = load_mapping(mapping_path)
    logger.info(f"Loaded {len(mappings)} slug mappings")

    if not dry_run and output_dir.exists():
        logger.info(f"Clearing previous output: {output_dir}")
        shutil.rmtree(output_dir)

    results: list[dict] = []
    total_files = 0
    total_skipped = 0
    total_yl = 0
    dropped = 0
    packaged_filenames: set[str] = set()

    for i, mapping in enumerate(mappings, 1):
        result = package_collection(
            mapping, manifests_dir, output_dir, t_hero_dir, dry_run
        )
        results.append(result)

        if result["action"] == "drop":
            dropped += 1
            print(f"  [{i}/{len(mappings)}] {mapping['th_slug']}: DROPPED")
        elif result["action"] == "error":
            print(f"  [{i}/{len(mappings)}] {mapping['th_slug']}: ERROR - {result.get('error')}")
        else:
            total_files += result["files"]
            total_skipped += result["skipped"]
            total_yl += result.get("yl_stamped", 0)
            chapter_info = f" -> {result['chapter']}" if result.get("chapter") else ""
            print(f"  [{i}/{len(mappings)}] {mapping['th_slug']} -> {result['global_slug']}{chapter_info}: {result['files']} files ({result.get('yl_stamped', 0)} YL)")

    # Collect filenames already packaged (to find uncollected)
    if not dry_run:
        for sgf_path in output_dir.rglob("*.sgf"):
            packaged_filenames.add(sgf_path.name)

    # Package uncollected puzzles into general-practice
    print(f"\n  Packaging uncollected puzzles into general-practice...")
    uc_result = package_uncollected(output_dir, t_hero_dir, packaged_filenames, dry_run)
    total_files += uc_result["files"]
    total_yl += uc_result["yl_stamped"]
    print(f"  [+] uncollected -> general-practice: {uc_result['files']} files ({uc_result['yl_stamped']} YL)")

    # Write per-directory manifests
    manifests_count = 0
    if not dry_run:
        print(f"\n  Writing per-directory manifests...")
        manifests_count = write_directory_manifests(output_dir)
        print(f"  [+] {manifests_count} manifest.json files written")

    # Write packaging report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mapping_file": str(mapping_path),
        "dry_run": dry_run,
        "total_mappings": len(mappings),
        "total_files_packaged": total_files,
        "total_yl_stamped": total_yl,
        "total_skipped": total_skipped,
        "total_dropped": dropped,
        "uncollected_added": uc_result["files"],
        "manifests_written": manifests_count,
        "results": results,
    }

    if not dry_run:
        report_path = output_dir / "packaging-report.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    # Count unique global slugs
    unique_slugs = {r["global_slug"] for r in results if r["action"] == "packaged" and r["global_slug"]}

    print(f"\n{'='*60}")
    print(f"Mappings processed: {len(mappings)}")
    print(f"Unique global collections: {len(unique_slugs)}")
    print(f"Files packaged (collections): {total_files - uc_result['files']}")
    print(f"Files packaged (uncollected): {uc_result['files']}")
    print(f"Files packaged (total): {total_files}")
    print(f"YL[] stamped: {total_yl}")
    print(f"Files skipped: {total_skipped}")
    print(f"Collections dropped: {dropped}")
    print(f"Directory manifests: {manifests_count}")
    if not dry_run:
        print(f"Output: {output_dir}")
    else:
        print("(dry run, no files written)")
    print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package TH puzzles into global-slug-based directory structure.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without writing files.",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=MAPPING_FILE,
        help=f"Path to collection_slug_mapping.json (default: {MAPPING_FILE})",
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

    package_all(
        mapping_path=args.mapping,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
