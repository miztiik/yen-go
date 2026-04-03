#!/usr/bin/env python3
"""
Tian Long Tu (天龙图) Puzzle Ingestor for YenGo

Downloads Go puzzles from the liryan1/101weiqi GitHub repository's tian_long_tu.json
and converts them to YenGo-compatible SGF format.

Data Source:
- URL: https://raw.githubusercontent.com/liryan1/101weiqi/main/data/json/tian_long_tu.json
- Format: JSON with 82 problems (Problem 1 through Problem 82)
- All puzzles are 19x19
- Difficulty ranges from 3K+ to 2D+

Coordinate Format:
- Source uses letter pairs like "hr" (column h, row r) where a=1, s=19
- This matches SGF coordinate system directly

YenGo Level Mapping:
| Source Rating | YenGo Level  | Sub-level | Kyu/Dan Range |
|---------------|--------------|-----------|---------------|
| 3K+, 3K       | intermediate | 1         | 3 kyu         |
| 2K+, 2K       | intermediate | 2         | 2 kyu         |
| 1K+, 1K       | intermediate | 3         | 1 kyu         |
| 1D, 1D+       | advanced     | 1         | 1 dan         |
| 2D, 2D+       | advanced     | 2         | 2 dan         |

SGF Format (YenGo v3.1):
- YV[3] = YenGo version marker
- YG[level:sub-level] = Difficulty (e.g., YG[intermediate:2])
- AP[YENGO:3.1] = Application attribution
- Variations preserved as SGF branches

Usage (from project root):
    python -m tools.liryan1_tianlongtu                    # Download all puzzles
    python -m tools.liryan1_tianlongtu -p 1-10           # Download puzzles 1-10
    python -m tools.liryan1_tianlongtu -p 1,5,10         # Download specific puzzles
    python -m tools.liryan1_tianlongtu --status          # Show download progress
    python -m tools.liryan1_tianlongtu --force           # Re-download all

Author: YenGo Project
License: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)

from tools.core.checkpoint import (
    ToolCheckpoint,
)
from tools.core.checkpoint import (
    load_checkpoint as core_load,
)
from tools.core.checkpoint import (
    save_checkpoint as core_save,
)
from tools.core.logging import setup_logging as core_setup_logging
from tools.core.paths import rel_path
from tools.core.validation import validate_sgf_puzzle

# ============================================================================
# CONSTANTS
# ============================================================================

VERSION = "1.0.0"
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # yen-go/

# All output (SGF, logs, checkpoint) co-located per tool-development-standards §12, §18
OUTPUT_DIR = PROJECT_ROOT / "external-sources" / "liryan1_tianlongtu"

# Source URL
SOURCE_URL = "https://raw.githubusercontent.com/liryan1/101weiqi/main/data/json/tian_long_tu.json"
SOURCE_NAME = "liryan1_tianlongtu"
SOURCE_DISPLAY_NAME = "Tian Long Tu (天龙图)"

# ============================================================================
# LEVEL MAPPING
# ============================================================================

# Map source rating strings to YenGo levels
# YenGo levels: beginner (30k-15k), basic (14k-8k), intermediate (7k-1k),
#               advanced (1d-4d), expert (5d-9d)
LEVEL_MAPPING: dict[str, tuple[str, int]] = {
    # Kyu levels → intermediate
    "3K+": ("intermediate", 1),
    "3K":  ("intermediate", 1),
    "2K+": ("intermediate", 2),
    "2K":  ("intermediate", 2),
    "1K+": ("intermediate", 3),
    "1K":  ("intermediate", 3),
    # Dan levels → advanced
    "1D":  ("advanced", 1),
    "1D+": ("advanced", 1),
    "2D":  ("advanced", 2),
    "2D+": ("advanced", 2),
    "3D":  ("advanced", 3),
    "3D+": ("advanced", 3),
    "4D":  ("advanced", 3),
    "4D+": ("advanced", 3),
    # High dan → expert (in case any exist)
    "5D":  ("expert", 1),
    "5D+": ("expert", 1),
    "6D":  ("expert", 2),
    "6D+": ("expert", 2),
    "7D":  ("expert", 2),
    "7D+": ("expert", 3),
}

DEFAULT_LEVEL = ("intermediate", 2)  # Fallback for unknown ratings


def parse_level(comments: str) -> tuple[str, int]:
    """
    Parse the Comments field to extract YenGo level and sub-level.

    Args:
        comments: The Comments field from the puzzle (e.g., "2K+", "1D")

    Returns:
        Tuple of (level_name, sub_level)
    """
    if not comments:
        return DEFAULT_LEVEL

    # Normalize: uppercase, strip whitespace
    normalized = comments.strip().upper()

    # Direct lookup
    if normalized in LEVEL_MAPPING:
        return LEVEL_MAPPING[normalized]

    # Try without the + suffix
    base = normalized.rstrip('+')
    if base in LEVEL_MAPPING:
        return LEVEL_MAPPING[base]

    return DEFAULT_LEVEL


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class TianLongTuPuzzle:
    """A single puzzle from Tian Long Tu."""
    problem_id: int
    board_size: int
    black_stones: list[str]
    white_stones: list[str]
    start: str  # "B" or "W"
    solution: list[str]
    comments: str  # Original difficulty rating
    other_variations: list[list[str]]
    labels: dict[str, str]

    @property
    def unique_id(self) -> str:
        return f"tlt_p{self.problem_id:04d}"

    @classmethod
    def from_json(cls, problem_key: str, data: dict) -> TianLongTuPuzzle:
        """Parse a puzzle from JSON data."""
        # Extract problem number from key like "Problem 1"
        match = re.match(r"Problem\s+(\d+)", problem_key)
        problem_id = int(match.group(1)) if match else 0

        return cls(
            problem_id=problem_id,
            board_size=data.get("Board size", 19),
            black_stones=data.get("Black stones", []),
            white_stones=data.get("White stones", []),
            start=data.get("Start", "B"),
            solution=data.get("Solution", []),
            comments=data.get("Comments", ""),
            other_variations=data.get("Other variations", []),
            labels=data.get("Labels", {}),
        )


@dataclass
class DownloadState(ToolCheckpoint):
    """Tracks download progress for idempotent operations."""
    source_hash: str = ""
    completed_puzzles: list[int] = field(default_factory=list)
    failed_puzzles: dict[str, str] = field(default_factory=dict)
    total_puzzles: int = 0

    def mark_completed(self, problem_id: int):
        if problem_id not in self.completed_puzzles:
            self.completed_puzzles.append(problem_id)
        self.failed_puzzles.pop(str(problem_id), None)

    def mark_failed(self, problem_id: int, error: str):
        self.failed_puzzles[str(problem_id)] = error

    def is_completed(self, problem_id: int) -> bool:
        return problem_id in self.completed_puzzles

    def save(self, output_dir: Path):
        """Save state atomically via core checkpoint."""
        core_save(self, output_dir)

    @classmethod
    def load(cls, output_dir: Path) -> DownloadState:
        state = core_load(output_dir, cls)
        return state if state else cls()

    def clear(self):
        self.completed_puzzles.clear()
        self.failed_puzzles.clear()
        self.source_hash = ""


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging(output_dir: Path, verbose: bool = False) -> logging.Logger:
    """Configure structured JSONL + console logging via core infrastructure."""
    return core_setup_logging(
        output_dir=output_dir,
        logger_name="tianlongtu",
        verbose=verbose,
        log_suffix="tianlongtu",
    )


# ============================================================================
# SGF CONVERTER
# ============================================================================

class SGFConverter:
    """Converts Tian Long Tu puzzles to YenGo SGF format v3.1."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def convert(self, puzzle: TianLongTuPuzzle) -> str:
        """
        Convert a single puzzle to YenGo SGF format.

        YenGo v3.1 SGF format:
        - GM[1]FF[4] = Game=Go, Format version 4
        - CA[UTF-8] = Character encoding
        - SZ[19] = Board size
        - AP[YENGO:3.1] = Application
        - YV[3] = YenGo version marker
        - YG[level:sub-level] = Difficulty
        - PL[B/W] = Player to move
        - AB[...], AW[...] = Setup stones
        - Solution moves as main line
        - Other variations as SGF branches
        """
        level_name, sub_level = parse_level(puzzle.comments)

        # Build SGF header
        sgf_parts = [
            "(;GM[1]FF[4]",
            "CA[UTF-8]",
            f"SZ[{puzzle.board_size}]",
            "AP[YENGO:3.1]",
            "YV[3]",
            f"YG[{level_name}:{sub_level}]",
        ]

        # Store original difficulty in comment for reference
        if puzzle.comments:
            sgf_parts.append(f"C[Source difficulty: {puzzle.comments}]")

        # Player to move
        sgf_parts.append(f"PL[{puzzle.start}]")

        # Add setup stones
        if puzzle.black_stones:
            black_coords = "][".join(puzzle.black_stones)
            sgf_parts.append(f"AB[{black_coords}]")

        if puzzle.white_stones:
            white_coords = "][".join(puzzle.white_stones)
            sgf_parts.append(f"AW[{white_coords}]")

        # Build solution tree with variations
        solution_sgf = self._build_solution_tree(puzzle)

        # Combine header and solution
        header = "".join(sgf_parts)

        if solution_sgf:
            return f"{header}\n{solution_sgf})"
        else:
            return f"{header})"

    def _build_solution_tree(self, puzzle: TianLongTuPuzzle) -> str:
        """
        Build the SGF solution tree with all variations.

        SGF variation format:
        - Main line: ;B[aa];W[bb];B[cc]
        - Variations: (;B[aa](;W[bb];B[cc])(;W[dd];B[ee]))

        We'll output:
        1. Main solution as the first branch
        2. Other variations as sibling branches
        """
        if not puzzle.solution and not puzzle.other_variations:
            return ""

        all_variations = []

        # Add main solution as first variation
        if puzzle.solution:
            all_variations.append(puzzle.solution)

        # Add other variations
        for var in puzzle.other_variations:
            if var and var not in all_variations:  # Avoid duplicates
                all_variations.append(var)

        if not all_variations:
            return ""

        # If only one variation (main solution), output as simple move sequence
        if len(all_variations) == 1:
            return self._moves_to_sgf(all_variations[0], puzzle.start)

        # Multiple variations - find common prefix and build tree
        return self._build_variation_tree(all_variations, puzzle.start)

    def _build_variation_tree(self, variations: list[list[str]], first_player: str) -> str:
        """
        Build SGF tree from multiple variations.

        Strategy: Find the longest common prefix among all variations,
        output that as the main line, then branch for differences.
        """
        if not variations:
            return ""

        # Find common prefix
        prefix_len = 0
        min_len = min(len(v) for v in variations)

        for i in range(min_len):
            first_move = variations[0][i]
            if all(v[i] == first_move for v in variations):
                prefix_len = i + 1
            else:
                break

        # Build common prefix
        common_moves = variations[0][:prefix_len] if prefix_len > 0 else []
        prefix_sgf = self._moves_to_sgf(common_moves, first_player)

        # Determine player after prefix
        if prefix_len % 2 == 0:
            next_player = first_player
        else:
            next_player = "W" if first_player == "B" else "B"

        # Group remaining moves by their next move
        if prefix_len >= min_len:
            # All variations are the same up to the shortest one
            # Output the main variation fully, others as branches
            main_line = self._moves_to_sgf(variations[0], first_player)

            # For other variations that extend further, add them
            branches = []
            for var in variations[1:]:
                if len(var) > prefix_len:
                    remaining = var[prefix_len:]
                    branch_sgf = self._moves_to_sgf(remaining, next_player)
                    if branch_sgf:
                        branches.append(f"({branch_sgf})")

            if branches:
                return f"{main_line}{''.join(branches)}"
            return main_line

        # Build branches for each distinct continuation
        branches = []
        seen_continuations = set()

        for var in variations:
            remaining = var[prefix_len:]
            if remaining:
                # Use first move as key to avoid duplicates
                continuation_key = remaining[0]
                if continuation_key not in seen_continuations:
                    seen_continuations.add(continuation_key)
                    branch_sgf = self._moves_to_sgf(remaining, next_player)
                    if branch_sgf:
                        branches.append(f"({branch_sgf})")

        if branches:
            return f"{prefix_sgf}{''.join(branches)}"
        return prefix_sgf

    def _moves_to_sgf(self, moves: list[str], first_player: str) -> str:
        """Convert a list of moves to SGF format."""
        if not moves:
            return ""

        sgf_moves = []
        player = first_player

        for move in moves:
            if move and len(move) == 2:
                sgf_moves.append(f";{player}[{move}]")
                player = "W" if player == "B" else "B"

        return "".join(sgf_moves)


# ============================================================================
# DOWNLOADER
# ============================================================================

class TianLongTuDownloader:
    """Downloads and processes Tian Long Tu puzzles."""

    def __init__(
        self,
        output_dir: Path,
        logger: logging.Logger,
        state: DownloadState,
    ):
        self.output_dir = output_dir
        self.logger = logger
        self.state = state
        self.converter = SGFConverter(logger)
        self.raw_data: dict | None = None

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "YenGo-TianLongTu-Ingestor/1.0",
            "Accept": "application/json",
        })

    def fetch_source(self) -> bool:
        """Fetch the source JSON file."""
        self.logger.info(f"Fetching source from: {SOURCE_URL}")

        try:
            response = self.session.get(SOURCE_URL, timeout=30)
            response.raise_for_status()

            self.raw_data = response.json()

            # Calculate hash for idempotency check
            content_hash = hashlib.sha256(response.content).hexdigest()[:16]

            # Log summary
            puzzle_count = len([k for k in self.raw_data.keys() if k.startswith("Problem")])
            self.logger.info(f"Fetched {puzzle_count} puzzles (hash: {content_hash})")

            # Check if source has changed
            if self.state.source_hash and self.state.source_hash != content_hash:
                self.logger.warning("Source content has changed since last run")

            self.state.source_hash = content_hash
            self.state.total_puzzles = puzzle_count

            return True

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch source: {e}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return False

    def parse_puzzles(self) -> list[TianLongTuPuzzle]:
        """Parse all puzzles from the raw JSON data."""
        if not self.raw_data:
            return []

        puzzles = []
        for key, value in self.raw_data.items():
            if key.startswith("Problem"):
                try:
                    puzzle = TianLongTuPuzzle.from_json(key, value)
                    puzzles.append(puzzle)
                except Exception as e:
                    self.logger.error(f"Failed to parse {key}: {e}")

        # Sort by problem ID
        puzzles.sort(key=lambda p: p.problem_id)

        self.logger.info(f"Parsed {len(puzzles)} puzzles")
        return puzzles

    def download_puzzles(
        self,
        puzzle_selection: list[int] | None = None,
        force: bool = False,
    ) -> dict:
        """
        Download and convert puzzles.

        Args:
            puzzle_selection: List of problem IDs to process (None = all)
            force: Force re-download even if already complete

        Returns:
            Stats dictionary with counts
        """
        stats = {"processed": 0, "skipped": 0, "failed": 0, "total": 0}

        # Fetch source
        if not self.fetch_source():
            return stats

        # Parse puzzles
        puzzles = self.parse_puzzles()
        if not puzzles:
            self.logger.error("No puzzles found in source")
            return stats

        # Filter by selection
        if puzzle_selection:
            selection_set = set(puzzle_selection)
            puzzles = [p for p in puzzles if p.problem_id in selection_set]
            self.logger.info(f"Filtered to {len(puzzles)} puzzles by selection")

        stats["total"] = len(puzzles)

        # Create output directories
        sgf_dir = self.output_dir / "sgf"
        json_dir = self.output_dir / "json"
        meta_dir = self.output_dir / "metadata"

        sgf_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

        # Process each puzzle
        for puzzle in puzzles:
            try:
                # Check idempotency
                if not force and self.state.is_completed(puzzle.problem_id):
                    self.logger.debug(f"Skipping puzzle {puzzle.problem_id} (already complete)")
                    stats["skipped"] += 1
                    continue

                # Convert to SGF
                sgf_content = self.converter.convert(puzzle)

                # Validate puzzle
                validation = validate_sgf_puzzle(sgf_content)
                if not validation.is_valid:
                    self.logger.warning(f"Skipping puzzle {puzzle.problem_id}: {validation.rejection_reason}")
                    stats["skipped"] += 1
                    continue

                # Generate filenames
                base_name = f"tlt_p{puzzle.problem_id:04d}"

                # Save SGF
                sgf_path = sgf_dir / f"{base_name}.sgf"
                with open(sgf_path, "w", encoding="utf-8") as f:
                    f.write(sgf_content)

                # Save original JSON data
                original_key = f"Problem {puzzle.problem_id}"
                if original_key in self.raw_data:
                    json_path = json_dir / f"{base_name}.json"
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(self.raw_data[original_key], f, indent=2, ensure_ascii=False)

                # Save metadata
                level_name, sub_level = parse_level(puzzle.comments)
                metadata = {
                    "source": SOURCE_NAME,
                    "source_url": SOURCE_URL,
                    "problem_id": puzzle.problem_id,
                    "unique_id": puzzle.unique_id,
                    "board_size": puzzle.board_size,
                    "first_to_play": "black" if puzzle.start == "B" else "white",
                    "original_difficulty": puzzle.comments,
                    "yengo_level": level_name,
                    "yengo_sublevel": sub_level,
                    "solution_length": len(puzzle.solution),
                    "variation_count": len(puzzle.other_variations),
                    "processed_at": datetime.now().isoformat(),
                }

                meta_path = meta_dir / f"{base_name}_meta.json"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)

                # Mark complete
                self.state.mark_completed(puzzle.problem_id)
                self.state.save(OUTPUT_DIR)

                self.logger.info(f"\u2713 Puzzle {puzzle.problem_id}: {puzzle.comments} \u2192 {level_name}:{sub_level}")
                stats["processed"] += 1

            except Exception as e:
                self.logger.error(f"\u2717 Failed puzzle {puzzle.problem_id}: {e}")
                self.state.mark_failed(puzzle.problem_id, str(e))
                self.state.save(OUTPUT_DIR)
                stats["failed"] += 1

        # Log summary
        self.logger.info("=" * 60)
        self.logger.info(f"Download complete: {stats['processed']} processed, "
                        f"{stats['skipped']} skipped, {stats['failed']} failed")

        return stats

    def show_status(self):
        """Display current download status."""
        print("\n" + "=" * 60)
        print("Tian Long Tu Ingestor Status")
        print("=" * 60)
        print(f"Source:            {SOURCE_URL}")
        print(f"Output directory:  {rel_path(self.output_dir)}")
        print(f"Source hash:       {self.state.source_hash or 'Not fetched'}")
        print(f"Total puzzles:     {self.state.total_puzzles}")
        print(f"Completed:         {len(self.state.completed_puzzles)}")
        print(f"Failed:            {len(self.state.failed_puzzles)}")

        if self.state.failed_puzzles:
            print("\nFailed puzzles:")
            for pid, error in list(self.state.failed_puzzles.items())[:10]:
                print(f"  - Problem {pid}: {error}")
            if len(self.state.failed_puzzles) > 10:
                print(f"  ... and {len(self.state.failed_puzzles) - 10} more")

        print("=" * 60 + "\n")


# ============================================================================
# CLI
# ============================================================================

def parse_puzzle_selection(selection: str | None) -> list[int] | None:
    """
    Parse puzzle selection string.

    Formats:
    - None or "all": returns None (all puzzles)
    - "1-10": returns [1, 2, ..., 10]
    - "1,5,10": returns [1, 5, 10]
    - "5": returns [5]
    """
    if selection is None or selection.lower() == "all":
        return None

    result = []

    # Handle comma-separated values
    for part in selection.split(","):
        part = part.strip()

        # Handle ranges
        if "-" in part:
            try:
                start, end = part.split("-")
                result.extend(range(int(start.strip()), int(end.strip()) + 1))
            except ValueError:
                continue
        else:
            try:
                result.append(int(part))
            except ValueError:
                continue

    return result if result else None


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="tianlongtu-ingestor",
        description=f"""
Tian Long Tu (天龙图) Puzzle Ingestor v{VERSION}

Downloads Go puzzles from liryan1/101weiqi repository and converts
them to YenGo-compatible SGF format.

Source: {SOURCE_URL}
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  Download all puzzles:
    %(prog)s

  Download specific puzzles:
    %(prog)s -p 1,5,10

  Download a range:
    %(prog)s -p 1-20

  Force re-download:
    %(prog)s --force

  Show status:
    %(prog)s --status

LEVEL MAPPING:
  3K+/3K  → intermediate:1 (3 kyu)
  2K+/2K  → intermediate:2 (2 kyu)
  1K+/1K  → intermediate:3 (1 kyu)
  1D/1D+  → advanced:1 (1 dan)
  2D/2D+  → advanced:2 (2 dan)
        """
    )

    # Puzzle selection
    parser.add_argument("-p", "--puzzles", type=str, metavar="SELECTION",
                       help="Puzzle selection: 'all', '1-10', '1,5,10', or '5'")

    # Output options
    parser.add_argument("-o", "--output", type=str, metavar="DIR",
                       help="Output directory (default: ./downloads)")
    parser.add_argument("-f", "--force", action="store_true",
                       help="Force re-download, overwriting existing files")

    # State management
    parser.add_argument("--status", action="store_true",
                       help="Show download status and exit")
    parser.add_argument("--clear", action="store_true",
                       help="Clear all download state")
    parser.add_argument("--retry", action="store_true",
                       help="Retry all failed downloads")

    # Other options
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose (debug) output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging in output directory
    logger = setup_logging(OUTPUT_DIR, verbose=args.verbose)
    logger.info(f"Tian Long Tu Ingestor v{VERSION}")

    # Load state from output directory (co-located per standards)
    state = DownloadState.load(OUTPUT_DIR)

    # Determine output directory
    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    # Create downloader
    downloader = TianLongTuDownloader(output_dir, logger, state)

    # Handle status
    if args.status:
        downloader.show_status()
        return 0

    # Handle clear
    if args.clear:
        state.clear()
        state.save(OUTPUT_DIR)
        logger.info("State cleared")
        print("State cleared.")
        return 0

    # Handle retry
    if args.retry:
        if not state.failed_puzzles:
            logger.info("No failed puzzles to retry")
            return 0

        failed_ids = [int(pid) for pid in state.failed_puzzles.keys()]
        logger.info(f"Retrying {len(failed_ids)} failed puzzles")

        stats = downloader.download_puzzles(
            puzzle_selection=failed_ids,
            force=True,
        )
        return 0 if stats["failed"] == 0 else 1

    # Parse puzzle selection
    puzzle_selection = parse_puzzle_selection(args.puzzles)

    # Download puzzles
    stats = downloader.download_puzzles(
        puzzle_selection=puzzle_selection,
        force=args.force,
    )

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
