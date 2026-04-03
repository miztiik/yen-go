"""
Tasuki SGF Collection Extractor.

Downloads multi-puzzle SGF collection files from the tasuki2sgf GitHub
repository and splits them into individual puzzle SGF files.

Uses the existing tools.core.sgf_parser for proper SGF parsing — no regex.

Usage:
    python -m tools.tasuki.extract                       # All collections
    python -m tools.tasuki.extract --collection cho-1    # Single collection
    python -m tools.tasuki.extract --local ./generated/  # Local directory
    python -m tools.tasuki.extract --dry-run             # Preview only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.request
from pathlib import Path

from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import SGFParseError, parse_sgf
from tools.core.sgf_types import Color, Point

logger = logging.getLogger("tools.tasuki")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://raw.githubusercontent.com/Seon82/tasuki2sgf/main"
COMMENTS_URL = f"{BASE_URL}/comments.json"

COLLECTIONS = [
    "cho-1",
    "cho-2",
    "cho-3",
    "gokyoshumyo",
    "hatsuyoron",
    "lee-chang-ho",
    "xxqj",
]

# Map collection keys to human-readable names and output directory slugs
COLLECTION_META: dict[str, dict[str, str]] = {
    "cho-1": {
        "name": "Cho Chikun - Encyclopedia of Life & Death - Elementary",
        "dir": "cho-chikun-elementary",
    },
    "cho-2": {
        "name": "Cho Chikun - Encyclopedia of Life & Death - Intermediate",
        "dir": "cho-chikun-intermediate",
    },
    "cho-3": {
        "name": "Cho Chikun - Encyclopedia of Life & Death - Advanced",
        "dir": "cho-chikun-advanced",
    },
    "gokyoshumyo": {
        "name": "Gokyo Shumyo",
        "dir": "gokyoshumyo",
    },
    "hatsuyoron": {
        "name": "Igo Hatsuyo-ron",
        "dir": "hatsuyoron",
    },
    "lee-chang-ho": {
        "name": "Lee Chang-ho - Selected Life and Death Problems",
        "dir": "lee-chang-ho",
    },
    "xxqj": {
        "name": "Xuanxuan Qijing (Gengen Gokyo)",
        "dir": "xuanxuan-qijing",
    },
}

# Max files per directory (project convention)
MAX_FILES_PER_BATCH = 1000

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "external-sources" / "tasuki"


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def download_text(url: str) -> str:
    """Download text content from a URL."""
    logger.info("Downloading %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "tasuki-extractor/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def download_comments() -> dict[str, str]:
    """Download and parse comments.json from the repo."""
    raw = download_text(COMMENTS_URL)
    return json.loads(raw)


def download_collection_sgf(key: str) -> str:
    """Download a collection SGF file from the repo."""
    url = f"{BASE_URL}/generated/{key}.sgf"
    return download_text(url)


# ---------------------------------------------------------------------------
# SGF parsing and extraction
# ---------------------------------------------------------------------------


def extract_puzzles_from_collection(sgf_content: str, board_size: int = 19) -> list[dict]:
    """Parse a multi-puzzle collection SGF and extract individual puzzles.

    The collection SGF format is:
        (;FF[4]GM[1]SZ[19]C[description]
          (;C[problem 1]PL[B]AB[be][dc]AW[bb][ab])
          (;C[problem 2]PL[B]AB[...]AW[...])
          ...
        )

    Each child variation of the root is a puzzle with:
    - AB/AW: Setup stones
    - PL: Player to move
    - C: Comment with problem number

    Uses the tools.core.sgf_parser for proper bracket-aware parsing.

    Args:
        sgf_content: Raw SGF collection content.
        board_size: Board size (from root SZ property).

    Returns:
        List of dicts with keys: number, black_stones, white_stones,
        player_to_move, comment, raw_properties.
    """
    tree = parse_sgf(sgf_content)
    puzzles = []

    for idx, child in enumerate(tree.solution_tree.children, start=1):
        props = child.properties

        # Extract problem number from comment
        comment = props.get("C", f"problem {idx}")
        number = idx  # Sequential numbering (comment formats vary)
        original_label = _extract_problem_label(comment)

        # Extract setup stones from the child's properties
        # The parser joins multiple values as comma-separated
        black_stones: list[Point] = []
        if "AB" in props:
            for coord_str in props["AB"].split(","):
                coord_str = coord_str.strip()
                if coord_str:
                    try:
                        black_stones.append(Point.from_sgf(coord_str))
                    except ValueError:
                        logger.warning(
                            "Skipping invalid black stone coord %r in problem %d",
                            coord_str, number,
                        )

        white_stones: list[Point] = []
        if "AW" in props:
            for coord_str in props["AW"].split(","):
                coord_str = coord_str.strip()
                if coord_str:
                    try:
                        white_stones.append(Point.from_sgf(coord_str))
                    except ValueError:
                        logger.warning(
                            "Skipping invalid white stone coord %r in problem %d",
                            coord_str, number,
                        )

        # Player to move (default: Black)
        pl_value = props.get("PL", "B").strip()
        player = Color.WHITE if pl_value == "W" else Color.BLACK

        puzzles.append({
            "number": number,
            "original_label": original_label,
            "black_stones": black_stones,
            "white_stones": white_stones,
            "player_to_move": player,
            "comment": comment.strip(),
            "board_size": tree.board_size,
        })

    return puzzles


def _extract_problem_label(comment: str) -> str:
    """Extract the problem identifier from a comment string.

    Examples:
        'problem 42'                    -> '42'
        'problem 1-103, white to play'  -> '1-103'
        'problem 7-46, white to play'   -> '7-46'
        'anything else'                 -> ''
    """
    comment_lower = comment.lower().strip()
    prefix = "problem"
    if not comment_lower.startswith(prefix):
        return ""
    rest = comment_lower[len(prefix):].strip()
    # Take everything up to the first comma or end of string
    label_chars: list[str] = []
    for ch in rest:
        if ch == ",":
            break
        label_chars.append(ch)
    return "".join(label_chars).strip()


def build_puzzle_sgf(puzzle: dict, collection_name: str = "") -> str:
    """Build a standalone SGF string for a single puzzle.

    Uses tools.core.sgf_builder for proper SGF construction.

    Args:
        puzzle: Dict with number, black_stones, white_stones,
                player_to_move, comment, board_size.
        collection_name: Human-readable collection name for the comment.

    Returns:
        Valid SGF string.
    """
    builder = SGFBuilder(board_size=puzzle["board_size"])

    # Setup stones
    builder.add_black_stones(puzzle["black_stones"])
    builder.add_white_stones(puzzle["white_stones"])

    # Player to move
    builder.set_player_to_move(puzzle["player_to_move"])

    # Comment with problem number and collection info
    comment_parts = [puzzle["comment"]]
    if collection_name:
        comment_parts.append(f"Source: {collection_name}")
    builder.set_comment(" | ".join(comment_parts))

    return builder.build()


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------


def batch_dir_name(batch_number: int) -> str:
    """Generate batch directory name for file organization.

    Returns names like 'batch-001', 'batch-002' (matches ambak-tsumego convention).
    """
    return f"batch-{batch_number:03d}"


def write_puzzles(
    puzzles: list[dict],
    collection_key: str,
    collection_name: str,
    output_root: Path,
    dry_run: bool = False,
) -> int:
    """Write individual puzzle SGF files to disk.

    Organizes into batch subdirectories of MAX_FILES_PER_BATCH (1000) to comply
    with the project's batch directory convention.

    Args:
        puzzles: List of puzzle dicts.
        collection_key: Collection identifier (e.g., 'cho-1').
        collection_name: Human-readable name.
        output_root: Root output directory (external-sources/tasuki/).
        dry_run: If True, only log what would be written.

    Returns:
        Number of files written.
    """
    collection_dir = output_root / COLLECTION_META[collection_key]["dir"]
    written = 0

    for puzzle in puzzles:
        num = puzzle["number"]

        # Determine batch subdirectory (1-indexed batch number)
        batch_number = ((num - 1) // MAX_FILES_PER_BATCH) + 1
        batch = batch_dir_name(batch_number)

        file_dir = collection_dir / batch
        label = puzzle.get("original_label", "")
        if label:
            filename = f"problem_{num:04d}_p{label}.sgf"
        else:
            filename = f"problem_{num:04d}.sgf"
        filepath = file_dir / filename

        sgf_content = build_puzzle_sgf(puzzle, collection_name)

        if dry_run:
            logger.info("[DRY RUN] Would write %s (%d bytes)", filepath, len(sgf_content))
        else:
            file_dir.mkdir(parents=True, exist_ok=True)
            filepath.write_text(sgf_content, encoding="utf-8")
            logger.debug("Wrote %s", filepath)

        written += 1

    return written


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def process_collection(
    collection_key: str,
    sgf_content: str,
    output_root: Path,
    dry_run: bool = False,
) -> int:
    """Process a single collection: parse and write puzzles.

    Args:
        collection_key: Collection identifier (e.g., 'cho-1').
        sgf_content: Raw SGF collection content.
        output_root: Root output directory.
        dry_run: If True, only log what would be written.

    Returns:
        Number of puzzles extracted.
    """
    meta = COLLECTION_META[collection_key]
    logger.info("Processing %s (%s)...", collection_key, meta["name"])

    try:
        puzzles = extract_puzzles_from_collection(sgf_content)
    except SGFParseError as e:
        logger.error("Failed to parse %s: %s", collection_key, e)
        return 0

    if not puzzles:
        logger.warning("No puzzles found in %s", collection_key)
        return 0

    logger.info("  Found %d puzzles", len(puzzles))

    written = write_puzzles(
        puzzles,
        collection_key,
        meta["name"],
        output_root,
        dry_run=dry_run,
    )

    logger.info("  Wrote %d puzzle files", written)
    return written


def main(args: list[str] | None = None) -> int:
    """CLI entry point.

    Returns:
        Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        prog="tasuki-extract",
        description="Extract individual puzzle SGFs from tasuki2sgf collections.",
    )
    parser.add_argument(
        "--collection",
        choices=COLLECTIONS,
        help="Process a single collection (default: all).",
    )
    parser.add_argument(
        "--local",
        type=Path,
        help="Local directory containing collection .sgf files (skip download).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_ROOT,
        help=f"Output directory (default: {OUTPUT_ROOT}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be written without creating files.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    opts = parser.parse_args(args)

    # Setup logging
    level = logging.DEBUG if opts.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    collections_to_process = [opts.collection] if opts.collection else COLLECTIONS
    total = 0

    for key in collections_to_process:
        # Load SGF content
        if opts.local:
            local_path = opts.local / f"{key}.sgf"
            if not local_path.exists():
                logger.warning("Local file not found: %s — skipping", local_path)
                continue
            sgf_content = local_path.read_text(encoding="utf-8")
        else:
            try:
                sgf_content = download_collection_sgf(key)
            except Exception as e:
                logger.error("Failed to download %s: %s", key, e)
                continue

        count = process_collection(key, sgf_content, opts.output, dry_run=opts.dry_run)
        total += count

    logger.info("Total: %d puzzles extracted from %d collections", total, len(collections_to_process))
    return 0


if __name__ == "__main__":
    sys.exit(main())
