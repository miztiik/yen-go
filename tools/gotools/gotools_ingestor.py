#!/usr/bin/env python3
"""
GoTools Puzzle Ingestor for YenGo

Downloads Go puzzles from the cameron-martin/tsumego-solver GitHub repository
and converts them to YenGo-compatible SGF format for use with LocalAdapter.

GoTools Data Structure:
- 6 levels (lv1 to lv6, easiest to hardest)
- 14 files per level (e.g., lv1.1, lv1.2, ..., lv1.14)
- ~217 puzzles per file = ~3,038 puzzles per level = ~18,228 total puzzles

Output Structure:
- SGF files stored in external-sources/gotools/{level_slug}/
- Ready for LocalAdapter to ingest into the pipeline

Level Mapping (uses config/puzzle-levels.json):
- GoTools Lv1 → elementary (20k-16k)
- GoTools Lv2 → intermediate (15k-11k)
- GoTools Lv3 → upper-intermediate (10k-6k)
- GoTools Lv4 → advanced (5k-1k)
- GoTools Lv5 → low-dan (1d-3d)
- GoTools Lv6 → high-dan (4d-6d)

Usage (from project root):
    python -m tools.gotools                      # Download all levels
    python -m tools.gotools -l 1                # Download level 1 only
    python -m tools.gotools -l 1-3              # Download levels 1-3
    python -m tools.gotools -l 1,4,6            # Download specific levels
    python -m tools.gotools -l 1 -f 1-5         # Download files 1-5 of level 1
    python -m tools.gotools --status            # Show download progress
"""

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)

# Core infrastructure
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

# ─────────────────────────────────────────────────────────────────────────────
# Configuration - Load from global config files
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # yen-go/
CONFIG_DIR = PROJECT_ROOT / "config"

# All output (SGF, logs, checkpoint) co-located per tool-development-standards §12, §18
OUTPUT_DIR = PROJECT_ROOT / "external-sources" / "gotools"

# GoTools constants
GOTOOLS_REPO = "cameron-martin/tsumego-solver"
GOTOOLS_RAW_URL = "https://raw.githubusercontent.com/{repo}/master/benches/gotools/puzzles"
LEVELS = range(1, 7)       # 6 GoTools levels
FILES_PER_LEVEL = 14       # 14 files per level


def load_puzzle_levels() -> dict:
    """Load level configuration from global config/puzzle-levels.json."""
    levels_file = CONFIG_DIR / "puzzle-levels.json"
    if not levels_file.exists():
        raise FileNotFoundError(f"puzzle-levels.json not found at {levels_file}")

    with open(levels_file, encoding="utf-8") as f:
        config = json.load(f)

    # Build lookup: id -> slug
    return {level["id"]: level["slug"] for level in config["levels"]}


def get_level_mapping() -> dict[int, str]:
    """
    Map GoTools levels (1-6) to YenGo level slugs.

    GoTools has 6 levels, YenGo has 9 levels.
    Based on rank ranges from the config file, we map conservatively:

    GoTools original ranks (approximate):
    - Lv1: 30k-15k (beginner)
    - Lv2: 14k-8k (intermediate)
    - Lv3: 7k-1k (advanced)
    - Lv4: 1d-4d (dan level)
    - Lv5: 5d-7d (high dan)
    - Lv6: 8d-9p (expert/pro)

    We map these to YenGo's 9-level system.
    """
    puzzle_levels = load_puzzle_levels()

    # Map GoTools level to YenGo slug based on rank overlap
    return {
        1: puzzle_levels.get(3, "elementary"),      # GoTools 30k-15k → YenGo 20k-16k
        2: puzzle_levels.get(4, "intermediate"),    # GoTools 14k-8k → YenGo 15k-11k
        3: puzzle_levels.get(5, "upper-intermediate"),  # GoTools 7k-1k → YenGo 10k-6k
        4: puzzle_levels.get(6, "advanced"),        # GoTools 1d-4d → YenGo 5k-1k
        5: puzzle_levels.get(7, "low-dan"),         # GoTools 5d-7d → YenGo 1d-3d
        6: puzzle_levels.get(8, "high-dan"),        # GoTools 8d-9p → YenGo 4d-6d
    }


def get_sub_level(gotools_level: int, file_index: int) -> int:
    """
    Determine sub-level (1-3) based on file index within GoTools level.

    GoTools has 14 files per level. We map to sub-levels:
    - Files 1-5:  sub-level 1 (easier within the level)
    - Files 6-10: sub-level 2 (medium)
    - Files 11-14: sub-level 3 (harder)
    """
    if file_index <= 5:
        return 1
    elif file_index <= 10:
        return 2
    else:
        return 3


def setup_logging(output_dir: Path, verbose: bool = False) -> logging.Logger:
    """Configure structured JSONL + console logging via core infrastructure."""
    return core_setup_logging(
        output_dir=output_dir,
        logger_name="gotools",
        verbose=verbose,
        log_suffix="gotools",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GoProblem:
    """A single Go puzzle from GoTools format."""
    level: int           # GoTools level (1-6)
    file_index: int      # File within level (1-14)
    problem_id: int      # Puzzle index within file
    board: list[str]     # 19 rows of the board position
    first_player: str    # 'B' or 'W'
    solution: str        # Solution move sequence in GoTools format
    wrong_moves: list[str]  # Wrong move sequences for refutations

    @property
    def unique_id(self) -> str:
        """Generate unique puzzle ID for filename."""
        return f"gotools_lv{self.level}_{self.file_index:02d}_p{self.problem_id:04d}"


@dataclass
class DownloadState(ToolCheckpoint):
    """Tracks download progress for resumable operations."""
    completed_files: dict[str, list[int]] = field(default_factory=dict)
    puzzle_counts: dict[str, int] = field(default_factory=dict)

    def mark_file_complete(self, level: int, file_index: int, puzzle_count: int):
        key = f"level_{level}"
        if key not in self.completed_files:
            self.completed_files[key] = []
        if file_index not in self.completed_files[key]:
            self.completed_files[key].append(file_index)

        count_key = f"lv{level}.{file_index}"
        self.puzzle_counts[count_key] = puzzle_count

    def is_complete(self, level: int, file_index: int) -> bool:
        key = f"level_{level}"
        return file_index in self.completed_files.get(key, [])

    def save(self, output_dir: Path):
        """Save state atomically via core checkpoint."""
        core_save(self, output_dir)

    @classmethod
    def load(cls, output_dir: Path) -> "DownloadState":
        state = core_load(output_dir, cls)
        return state if state else cls()


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────

class GoToolsParser:
    """
    Parser for GoTools compressed problem file format.

    Format:
    - `$ P{id}` starts a problem
    - Stone encoding: `AAB` = black at col A row B, `?AB` = white at col A row B
    - `[AB]` at end = marked points (triangles)
    - `?+l...` = correct move sequence, solution in `:XXXX:`
    - `?-d...` = wrong move sequence
    - Columns: A-T (no I), Rows: A-S (A=1, S=19)
    """

    # Column mapping: A-T (skipping I) for 19 columns
    COLS = "ABCDEFGHJKLMNOPQRST"  # Note: no I

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def parse_file(self, content: str, level: int, file_index: int) -> list[GoProblem]:
        """Parse a GoTools file into individual puzzles."""
        puzzles = []
        lines = content.strip().split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for problem start: $ P{id}
            if line.startswith("$ P"):
                problem_id_str = line[3:].strip()
                try:
                    problem_id = int(problem_id_str)
                except ValueError:
                    self.logger.debug(f"Invalid problem ID: {problem_id_str}")
                    i += 1
                    continue

                # Collect all lines until next problem or EOF
                i += 1
                problem_lines = []
                while i < len(lines) and not lines[i].strip().startswith("$ P"):
                    if lines[i].strip():
                        problem_lines.append(lines[i])
                    i += 1

                # Parse this problem
                puzzle = self._parse_problem(problem_id, problem_lines, level, file_index)
                if puzzle:
                    puzzles.append(puzzle)
            else:
                i += 1

        self.logger.debug(f"Parsed lv{level}.{file_index}: {len(puzzles)} puzzles")
        return puzzles

    def _parse_problem(
        self, problem_id: int, lines: list[str], level: int, file_index: int
    ) -> GoProblem | None:
        """Parse a single problem from its lines."""
        if not lines:
            return None

        # Join all lines to handle line continuations (ending with \)
        full_text = ""
        for line in lines:
            line = line.rstrip()
            if line.endswith("\\"):
                full_text += line[:-1]
            else:
                full_text += line + "\n"

        text_lines = [line for line in full_text.split("\n") if line.strip()]
        if not text_lines:
            return None

        # First line contains the board position
        board_line = text_lines[0]

        # Remove markers from board line for stone parsing
        board_clean = re.sub(r'\[.*?\]', '', board_line).strip()

        # Parse stones
        black_stones, white_stones = self._parse_stones(board_clean)

        # Find solution and wrong moves from ?+ and ?- lines
        solution = ""
        wrong_moves = []
        first_player = "B"  # Tsumego convention: attacker (Black) plays first

        for line in text_lines[1:]:
            if line.startswith("?+"):
                # Correct move sequence
                match = re.search(r':([A-T@]+):', line)
                if match and not solution:  # Take first correct solution
                    solution = match.group(1)
            elif line.startswith("?-"):
                # Wrong move sequence
                match = re.search(r':([A-T@]+):', line)
                if match:
                    wrong_moves.append(match.group(1))

        # Convert to board representation (19x19)
        board = self._stones_to_board(black_stones, white_stones)

        return GoProblem(
            level=level,
            file_index=file_index,
            problem_id=problem_id,
            board=board,
            first_player=first_player,
            solution=solution,
            wrong_moves=wrong_moves[:3],  # Limit to 3 refutations
        )

    def _parse_stones(self, encoded: str) -> tuple[list[str], list[str]]:
        """Parse encoded stone positions."""
        black = []
        white = []

        i = 0
        while i < len(encoded):
            if encoded[i] == '?':
                # White stone - next two chars are column and row
                if i + 2 < len(encoded):
                    col = encoded[i + 1]
                    row = encoded[i + 2]
                    if col in self.COLS and row in "ABCDEFGHIJKLMNOPQRS":
                        white.append(f"{col}{row}")
                    i += 3
                else:
                    i += 1
            elif encoded[i] in self.COLS:
                # Check if this is a black stone (col + row)
                if i + 1 < len(encoded) and encoded[i + 1] in "ABCDEFGHIJKLMNOPQRS":
                    col = encoded[i]
                    row = encoded[i + 1]
                    black.append(f"{col}{row}")
                    i += 2
                else:
                    i += 1
            else:
                i += 1

        return black, white

    def _stones_to_board(self, black: list[str], white: list[str]) -> list[str]:
        """Convert stone lists to 19x19 board representation."""
        board = [["." for _ in range(19)] for _ in range(19)]

        for stone in black:
            col_idx = self.COLS.index(stone[0]) if stone[0] in self.COLS else -1
            row_idx = ord(stone[1]) - ord('A') if len(stone) > 1 else -1
            if 0 <= col_idx < 19 and 0 <= row_idx < 19:
                board[row_idx][col_idx] = "X"

        for stone in white:
            col_idx = self.COLS.index(stone[0]) if stone[0] in self.COLS else -1
            row_idx = ord(stone[1]) - ord('A') if len(stone) > 1 else -1
            if 0 <= col_idx < 19 and 0 <= row_idx < 19:
                board[row_idx][col_idx] = "O"

        return ["".join(row) for row in board]


# ─────────────────────────────────────────────────────────────────────────────
# SGF Converter with Preprocessing
# ─────────────────────────────────────────────────────────────────────────────

class SGFConverter:
    """
    Converts GoTools puzzles to SGF format compatible with LocalAdapter.

    Performs preprocessing during conversion:
    - Computes solution depth (number of moves in correct line)
    - Counts stones on board
    - Detects board region (corner, side, center)
    - Includes wrong moves as refutation branches

    The pipeline enricher will add YenGo-specific properties (YV, YG, YT, etc.).
    """

    # Column mapping: GoTools uses A-T (no I), SGF uses a-s
    GOTOOLS_COLS = "ABCDEFGHJKLMNOPQRST"  # Note: no I
    SGF_COLS = "abcdefghijklmnopqrs"

    def __init__(self, logger: logging.Logger, level_mapping: dict[int, str]):
        self.logger = logger
        self.level_mapping = level_mapping

    def convert(self, puzzle: GoProblem) -> str:
        """Convert a single puzzle to SGF format with preprocessing."""
        # Get level mapping
        yengo_level = self.level_mapping.get(puzzle.level, "intermediate")
        sub_level = get_sub_level(puzzle.level, puzzle.file_index)

        # Preprocessing: compute metrics (useful info for enricher)
        self._count_stones(puzzle.board)
        len(puzzle.solution) // 2 if puzzle.solution else 0
        self._detect_board_region(puzzle.board)

        # Build SGF - compatible with LocalAdapter and existing external-sources
        # Format similar to kisvadim-goproblems SGF files
        sgf_parts = [
            "(;GM[1]FF[4]",          # Game=Go, Format version 4
            "SZ[19]",                 # Board size
            "HA[0]",                  # No handicap
            "KM[0]",                  # No komi
            "GN[]",  # Game name (enricher will update to YENGO-{hash})
        ]

        # Add setup stones first (before player to move)
        black_stones, white_stones = self._extract_stones(puzzle.board)
        if black_stones:
            sgf_parts.append(f"AB{black_stones}")
        if white_stones:
            sgf_parts.append(f"AW{white_stones}")

        # Add level/source info as comment (enricher will remove root C[])
        sgf_parts.append(f"C[GoTools Lv{puzzle.level}.{puzzle.file_index} → {yengo_level}:{sub_level}]")

        # Build solution tree with correct and wrong variations
        # Format: (;B[xy]C[Correct.])(;B[ab]WV[];W[cd]C[Wrong.])
        solution_tree = self._build_solution_tree(puzzle)
        sgf_parts.append(solution_tree)

        sgf_parts.append(")")

        return "".join(sgf_parts)

    def _count_stones(self, board: list[str]) -> int:
        """Count total stones on board."""
        count = 0
        for row in board:
            count += row.count("X") + row.count("O")
        return count

    def _detect_board_region(self, board: list[str]) -> str:
        """
        Detect which board region contains the puzzle.

        Returns: TL, TR, BL, BR, T, B, L, R, C (corners, sides, center)
        """
        # Find bounding box of stones
        min_row, max_row = 19, -1
        min_col, max_col = 19, -1

        for row_idx, row in enumerate(board):
            for col_idx, char in enumerate(row[:19]):
                if char in ("X", "O"):
                    min_row = min(min_row, row_idx)
                    max_row = max(max_row, row_idx)
                    min_col = min(min_col, col_idx)
                    max_col = max(max_col, col_idx)

        if min_row > max_row:  # No stones
            return "C"

        # Determine region based on center of mass
        center_row = (min_row + max_row) / 2
        center_col = (min_col + max_col) / 2

        # Corners are within 6 lines of corner
        in_top = center_row < 6
        in_bottom = center_row > 12
        in_left = center_col < 6
        in_right = center_col > 12

        if in_top and in_left:
            return "TL"
        elif in_top and in_right:
            return "TR"
        elif in_bottom and in_left:
            return "BL"
        elif in_bottom and in_right:
            return "BR"
        elif in_top:
            return "T"
        elif in_bottom:
            return "B"
        elif in_left:
            return "L"
        elif in_right:
            return "R"
        else:
            return "C"

    def _extract_stones(self, board: list[str]) -> tuple[str, str]:
        """Extract stone positions from board as SGF coordinates."""
        black = []
        white = []

        for row_idx, row in enumerate(board):
            for col_idx, char in enumerate(row[:19]):
                if char == "X":
                    sgf_coord = self._board_to_sgf(col_idx, row_idx)
                    black.append(f"[{sgf_coord}]")
                elif char == "O":
                    sgf_coord = self._board_to_sgf(col_idx, row_idx)
                    white.append(f"[{sgf_coord}]")

        return "".join(black), "".join(white)

    def _board_to_sgf(self, col: int, row: int) -> str:
        """Convert board coordinates to SGF format."""
        sgf_col = chr(ord('a') + col)
        sgf_row = chr(ord('a') + row)
        return f"{sgf_col}{sgf_row}"

    def _build_solution_tree(self, puzzle: GoProblem) -> str:
        """
        Build SGF solution tree with correct and wrong variations.

        Format matches kisvadim-goproblems style:
        (;B[xy]C[Correct.])(;B[ab]WV[];W[cd]C[Wrong.])
        """
        result = ""

        # Add correct solution if available
        if puzzle.solution:
            correct_var = self._convert_moves(
                puzzle.solution, puzzle.first_player, "Correct."
            )
            if correct_var:
                result += correct_var

        # Add wrong move variations (refutations)
        for wrong in puzzle.wrong_moves:
            wrong_var = self._convert_moves(
                wrong, puzzle.first_player, "Wrong.", add_wv=True
            )
            if wrong_var:
                result += wrong_var

        return result

    def _convert_moves(
        self,
        move_seq: str,
        first_player: str,
        comment: str,
        add_wv: bool = False
    ) -> str:
        """
        Convert GoTools move sequence to SGF variation.

        Args:
            move_seq: GoTools format move sequence (e.g., "CCBC")
            first_player: "B" or "W"
            comment: Comment to add to first move
            add_wv: Whether to add WV[] marker for wrong variations
        """
        if not move_seq:
            return ""

        moves = []
        player = first_player

        i = 0
        while i + 1 < len(move_seq):
            col_letter = move_seq[i]
            row_letter = move_seq[i + 1]

            # Handle @@ which means pass
            if col_letter == '@' and row_letter == '@':
                moves.append((player, ""))  # Empty string = pass
                player = "W" if player == "B" else "B"
                i += 2
                continue

            # Convert to SGF coordinates
            if col_letter in self.GOTOOLS_COLS and row_letter in "ABCDEFGHIJKLMNOPQRS":
                col_idx = self.GOTOOLS_COLS.index(col_letter)
                row_idx = ord(row_letter) - ord('A')

                if 0 <= col_idx < 19 and 0 <= row_idx < 19:
                    sgf_coord = self._board_to_sgf(col_idx, row_idx)
                    moves.append((player, sgf_coord))
                    player = "W" if player == "B" else "B"

            i += 2

        if not moves:
            return ""

        # Build SGF variation
        result = "(;"

        # First move with comment
        p, coord = moves[0]
        result += f"{p}[{coord}]"

        # Add WV[] marker for wrong variations (after first move)
        if add_wv:
            result += "WV[]"

        # Remaining moves
        for p, coord in moves[1:]:
            result += f";{p}[{coord}]"

        # Add comment at the end of the variation
        result += f"C[{comment}]"
        result += ")"

        return result


# ─────────────────────────────────────────────────────────────────────────────
# Downloader
# ─────────────────────────────────────────────────────────────────────────────

class GoToolsDownloader:
    """Downloads and processes GoTools puzzle files."""

    def __init__(
        self,
        output_dir: Path,
        logger: logging.Logger,
        state: DownloadState,
        level_mapping: dict[int, str],
    ):
        self.output_dir = output_dir
        self.logger = logger
        self.state = state
        self.parser = GoToolsParser(logger)
        self.converter = SGFConverter(logger, level_mapping)
        self.level_mapping = level_mapping

        self.base_url = GOTOOLS_RAW_URL.format(repo=GOTOOLS_REPO)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "YenGo-GoTools-Ingestor/4.0"
        })

    def download_level(
        self,
        level: int,
        file_range: tuple[int, int] | None = None,
    ) -> dict:
        """Download all files for a specific level."""
        # Get YenGo level slug for directory structure
        yengo_level = self.level_mapping.get(level, "intermediate")
        sgf_dir = self.output_dir / yengo_level
        sgf_dir.mkdir(parents=True, exist_ok=True)

        start_file = file_range[0] if file_range else 1
        end_file = file_range[1] if file_range else FILES_PER_LEVEL

        stats = {"downloaded": 0, "skipped": 0, "puzzles": 0, "errors": 0}

        for file_idx in range(start_file, end_file + 1):
            # Check if already complete
            if self.state.is_complete(level, file_idx):
                self.logger.info(f"Skipping lv{level}.{file_idx} (already complete)")
                stats["skipped"] += 1
                continue

            try:
                puzzle_count = self._download_file(level, file_idx, sgf_dir)
                self.state.mark_file_complete(level, file_idx, puzzle_count)
                self.state.save(self.output_dir)

                stats["downloaded"] += 1
                stats["puzzles"] += puzzle_count

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Error downloading lv{level}.{file_idx}: {e}")
                stats["errors"] += 1

        return stats

    def _download_file(self, level: int, file_idx: int, sgf_dir: Path) -> int:
        """Download and process a single GoTools file."""
        url = f"{self.base_url}/lv{level}.{file_idx}"
        self.logger.info(f"Downloading: lv{level}.{file_idx}")

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        # Parse puzzles
        puzzles = self.parser.parse_file(response.text, level, file_idx)
        self.logger.info(f"Parsed {len(puzzles)} puzzles from lv{level}.{file_idx}")

        # Convert, validate, and save each puzzle
        saved = 0
        for puzzle in puzzles:
            sgf_content = self.converter.convert(puzzle)
            result = validate_sgf_puzzle(sgf_content)
            if not result.is_valid:
                self.logger.warning(f"Skipping {puzzle.unique_id}: {result.rejection_reason}")
                continue
            sgf_path = sgf_dir / f"{puzzle.unique_id}.sgf"
            sgf_path.write_text(sgf_content, encoding="utf-8")
            saved += 1

        return saved


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_range(range_str: str) -> list[int]:
    """Parse a range string like '1-3' or '1,4,6' into a list of integers."""
    result = []
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            result.extend(range(int(start), int(end) + 1))
        else:
            result.append(int(part))
    return sorted(set(result))


def show_status(state: DownloadState, level_mapping: dict[int, str]):
    """Display current download status."""
    print("\n" + "=" * 65)
    print("GoTools Download Status")
    print("=" * 65)

    if state.last_updated:
        print(f"Last Updated: {state.last_updated}")

    print(f"\nOutput Directory: {rel_path(OUTPUT_DIR)}")
    print("\nLevel Mapping (from config/puzzle-levels.json):")
    for gt_level, yengo_level in sorted(level_mapping.items()):
        print(f"  GoTools Lv{gt_level} → {yengo_level}/")

    print("\nProgress by Level:")
    print("-" * 65)

    total_files = 0
    total_puzzles = 0

    for level in LEVELS:
        key = f"level_{level}"
        completed = state.completed_files.get(key, [])
        level_puzzles = sum(
            state.puzzle_counts.get(f"lv{level}.{f}", 0)
            for f in completed
        )
        yengo_level = level_mapping.get(level, "?")

        print(f"  Lv{level} → {yengo_level:20} {len(completed):2}/{FILES_PER_LEVEL} files, "
              f"{level_puzzles:,} puzzles")

        total_files += len(completed)
        total_puzzles += level_puzzles

    print("-" * 65)
    print(f"  TOTAL: {total_files}/{len(LEVELS) * FILES_PER_LEVEL} files, "
          f"{total_puzzles:,} puzzles")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download GoTools puzzles to external-sources/gotools/ for LocalAdapter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.gotools                  # Download all levels
  python -m tools.gotools -l 1             # Download level 1 only
  python -m tools.gotools -l 1-3           # Download levels 1-3
  python -m tools.gotools -l 1,4,6         # Download specific levels
  python -m tools.gotools -l 1 -f 1-5      # Download files 1-5 of level 1
  python -m tools.gotools --status         # Show download progress

Output:
  SGF files are written to external-sources/gotools/{level}/
  Ready for use with LocalAdapter in the puzzle pipeline.
        """
    )
    parser.add_argument(
        "-l", "--levels",
        help="Levels to download (e.g., '1', '1-3', '1,4,6')"
    )
    parser.add_argument(
        "-f", "--files",
        help="Files within each level (e.g., '1-5', '1,7,14')"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show download status and exit"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset download state and start fresh"
    )

    args = parser.parse_args()

    # Load level mapping from config
    try:
        level_mapping = get_level_mapping()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Make sure you're running from the yen-go project root.")
        sys.exit(1)

    # Load state from output directory (co-located per standards)
    state = DownloadState.load(args.output)

    if args.status:
        show_status(state, level_mapping)
        return

    if args.reset:
        state = DownloadState(started_at=datetime.now().isoformat())
        state.save(args.output)
        print("State reset. Ready for fresh download.")
        return

    # Setup logging in output directory
    logger = setup_logging(args.output)
    logger.info("=" * 60)
    logger.info("GoTools Ingestor Started (YenGo v4.0)")
    logger.info(f"Output directory: {rel_path(args.output)}")
    logger.info("=" * 60)

    # Parse level/file ranges
    levels = parse_range(args.levels) if args.levels else list(LEVELS)
    file_range = None
    if args.files:
        files = parse_range(args.files)
        file_range = (min(files), max(files))

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Create README for the output directory
    readme_content = f"""# GoTools Puzzles for YenGo

Downloaded from [cameron-martin/tsumego-solver](https://github.com/cameron-martin/tsumego-solver).

## Structure

SGF files are organized by YenGo difficulty level:
{chr(10).join(f'- `{level}/` - GoTools Level {gt_level}' for gt_level, level in sorted(level_mapping.items(), key=lambda x: x[0]))}

## Usage

Use with LocalAdapter in sources.yaml:
```yaml
gotools:
  adapter: local
  enabled: true
  path: external-sources/gotools
```

## Source

- Repository: cameron-martin/tsumego-solver
- Format: GoTools compressed format (Thomas Wolf, 1994)
- Total puzzles: ~18,000 across 6 difficulty levels

## Level Mapping

| GoTools | YenGo Level | Rank Range |
|---------|-------------|------------|
| Lv1 | elementary | 20k-16k |
| Lv2 | intermediate | 15k-11k |
| Lv3 | upper-intermediate | 10k-6k |
| Lv4 | advanced | 5k-1k |
| Lv5 | low-dan | 1d-3d |
| Lv6 | high-dan | 4d-6d |
"""
    readme_path = args.output / "README.md"
    if not readme_path.exists():
        readme_path.write_text(readme_content, encoding="utf-8")

    # Create downloader
    downloader = GoToolsDownloader(args.output, logger, state, level_mapping)

    # Download
    total_stats = {"downloaded": 0, "skipped": 0, "puzzles": 0, "errors": 0}

    for level in levels:
        logger.info(f"Processing Level {level} → {level_mapping.get(level, '?')}...")
        stats = downloader.download_level(level, file_range)

        for key in total_stats:
            total_stats[key] += stats[key]

    # Summary
    logger.info("=" * 60)
    logger.info("Download Complete!")
    logger.info(f"  Files downloaded: {total_stats['downloaded']}")
    logger.info(f"  Files skipped: {total_stats['skipped']}")
    logger.info(f"  Puzzles converted: {total_stats['puzzles']:,}")
    logger.info(f"  Errors: {total_stats['errors']}")
    logger.info("=" * 60)

    show_status(state, level_mapping)

    print("\nNext steps:")
    print("1. Add gotools to sources.yaml with LocalAdapter")
    print("2. Run: python -m backend.puzzle_manager run --source gotools")


if __name__ == "__main__":
    main()
