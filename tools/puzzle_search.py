"""
Search external-sources/ for SGF files matching various criteria.

Standalone CLI script. Does NOT import from backend/.

Usage:
    python tools/puzzle_search.py --source "SAKATA EIO TESUJI" --pattern "kiri-*"
    python tools/puzzle_search.py --comment "hane" --board-size 19
    python tools/puzzle_search.py --property "C" --value "correct"
    python tools/puzzle_search.py --all --source "SAKATA EIO TESUJI"
    python tools/puzzle_search.py --count --source "SAKATA EIO TESUJI"
"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import sys
from pathlib import Path

# Allow running as `python tools/puzzle_search.py` from project root
if __name__ == "__main__" and "tools" not in sys.modules:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.core.paths import get_project_root
from tools.core.sgf_parser import SGFParseError, parse_sgf

logger = logging.getLogger(__name__)


def _collect_root_properties(tree) -> dict[str, str]:
    """Collect root-level SGF properties from a parsed SgfTree.

    parse_sgf() distributes root props across tree fields; this
    reassembles a flat lookup dict for --property/--value matching.
    """
    props: dict[str, str] = {}

    # Standard metadata (GN, GC, PB, PW, DT, RE, SO, AP, MN)
    for key, value in tree.metadata.items():
        props[key] = value

    # Root comment
    if tree.root_comment:
        props["C"] = tree.root_comment

    # Board size
    props["SZ"] = str(tree.board_size)

    # YenGo custom properties
    yp = tree.yengo_props
    if yp.version is not None:
        props["YV"] = str(yp.version)
    if yp.level_slug:
        props["YG"] = yp.level_slug
    if yp.tags:
        props["YT"] = ",".join(yp.tags)
    if yp.hint_texts:
        props["YH"] = "|".join(yp.hint_texts)
    if yp.run_id:
        props["YI"] = yp.run_id
    if yp.quality:
        props["YQ"] = yp.quality
    if yp.complexity:
        props["YX"] = yp.complexity
    if yp.source:
        props["YS"] = yp.source
    if yp.collections:
        props["YL"] = ",".join(yp.collections)
    if yp.corner:
        props["YC"] = yp.corner
    if yp.ko_context:
        props["YK"] = yp.ko_context
    if yp.move_order:
        props["YO"] = yp.move_order
    if yp.refutation_count:
        props["YR"] = yp.refutation_count

    return props


def find_sgf_files(
    external_sources_dir: Path,
    *,
    source_filter: str | None = None,
    pattern: str | None = None,
    comment: str | None = None,
    property_name: str | None = None,
    property_value: str | None = None,
    board_size: int | None = None,
) -> list[Path]:
    """Search for SGF files matching the given criteria.

    Args:
        external_sources_dir: Path to the external-sources/ directory.
        source_filter: Case-insensitive substring matched against source
            directory paths (relative to external_sources_dir).
        pattern: Glob pattern matched against filename only.
        comment: Case-insensitive substring searched in root C[] comment.
        property_name: SGF property name to check (requires parsing).
        property_value: Substring to match within the property value.
        board_size: Required board size (SZ property).

    Returns:
        List of absolute paths to matching SGF files.
    """
    if not external_sources_dir.is_dir():
        logger.warning("external-sources directory not found: %s", external_sources_dir)
        return []

    needs_parse = any([comment, property_name, board_size])

    # Determine which source directories to scan
    source_dirs: list[Path] = []
    if source_filter:
        filter_lower = source_filter.lower()
        for child in sorted(external_sources_dir.iterdir()):
            if child.is_dir() and filter_lower in str(child.relative_to(external_sources_dir)).lower():
                source_dirs.append(child)
    else:
        source_dirs = sorted(
            d for d in external_sources_dir.iterdir() if d.is_dir()
        )

    results: list[Path] = []

    for src_dir in source_dirs:
        for sgf_path in sorted(src_dir.rglob("*.sgf")):
            if not sgf_path.is_file():
                continue

            # Filename glob filter
            if pattern and not fnmatch.fnmatch(sgf_path.name, pattern):
                continue

            # Parsing-dependent filters
            if needs_parse:
                try:
                    content = sgf_path.read_text(encoding="utf-8", errors="replace")
                    tree = parse_sgf(content)
                except (SGFParseError, Exception) as exc:
                    logger.warning("Skipping %s: %s", sgf_path, exc)
                    continue

                if board_size is not None and tree.board_size != board_size:
                    continue

                if comment:
                    if comment.lower() not in (tree.root_comment or "").lower():
                        continue

                if property_name:
                    root_props = _collect_root_properties(tree)
                    prop_val = root_props.get(property_name)
                    if prop_val is None:
                        continue
                    if property_value and property_value not in prop_val:
                        continue

            results.append(sgf_path)

    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search external-sources/ for SGF files.",
    )
    parser.add_argument(
        "--source",
        help="Filter source directories (case-insensitive substring match)",
    )
    parser.add_argument(
        "--pattern",
        help="Glob pattern matched against filename (e.g. 'kiri-*')",
    )
    parser.add_argument(
        "--comment",
        help="Case-insensitive substring search in root C[] comment",
    )
    parser.add_argument(
        "--property",
        dest="property_name",
        help="SGF property name to check (e.g. 'C', 'YG', 'GN')",
    )
    parser.add_argument(
        "--value",
        dest="property_value",
        help="Substring to match within the property value (used with --property)",
    )
    parser.add_argument(
        "--board-size",
        type=int,
        help="Filter by board size (e.g. 19, 9)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="List all SGF files (apply other filters if given)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Print only the count of matching files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a note that search is read-only, then run normally",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.dry_run:
        print("[dry-run] Search is read-only; running normally.")

    # Require at least one filter unless --all
    has_filter = any([
        args.source,
        args.pattern,
        args.comment,
        args.property_name,
        args.board_size,
    ])
    if not has_filter and not args.all:
        parser.error("Specify at least one filter (--source, --pattern, --comment, --property, --board-size) or --all")

    ext_dir = get_project_root() / "external-sources"

    matches = find_sgf_files(
        ext_dir,
        source_filter=args.source,
        pattern=args.pattern,
        comment=args.comment,
        property_name=args.property_name,
        property_value=args.property_value,
        board_size=args.board_size,
    )

    project_root = get_project_root()

    if args.count:
        print(len(matches))
    else:
        for path in matches:
            try:
                rel = path.relative_to(project_root)
            except ValueError:
                rel = path
            print(rel)


if __name__ == "__main__":
    main()
