"""
Splitter for Go Seigen / Segoe Tesuji Dictionary dual-puzzle SGF files.

Each source file contains one SGF with two puzzles encoded as:
  - A single root node with composite AB[]/AW[] stones spanning two board regions
  - A root C[] comment describing both figures (GB2312 encoded, no CA[])
  - Sequential solution moves — puzzle 1's solution first, then puzzle 2's
  - An optional W[zz] or B[zz] pass-move separator between puzzles (274 files),
    or just a mid-stream C[] comment marking the boundary (231 files)
  - 8 files contain only a single puzzle (single figure number in filename)

This tool splits each dual-puzzle file into two independent SGFs, each with:
  - Only the AB/AW stones relevant to that puzzle (via proximity analysis)
  - Only the solution moves for that puzzle
  - The relevant root C[] comment fragment
  - SZ[19], PL[B] or PL[W] set correctly
  - Cleaned comments (flygo.net URLs stripped, AP[]/MULTIGOGM[] removed)

Usage:
    python -m tools.kisvadim_goproblems._split_segoe [--dry-run] [--verbose]

The anomalous oki08_77-77.sgf (both puzzles labeled #77) outputs as
oki08_77a.sgf and oki08_77b.sgf.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SOURCE_DIR_NAME = "GO SEIGEN - SEGOE TESUJI DICTIONARY"
_ENCODING_CHAIN: tuple[str, ...] = ("gb2312", "gbk", "utf-8", "latin-1")

# URLs / attribution lines to strip from comments
_STRIP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"http://www\.flygo\.net/?"),
    re.compile(r"https?://www\.flygo\.net/?"),
    re.compile(r"zypzyp\s*@飞扬\s*"),
    re.compile(r"zypzyp\s*@\s*飞扬\s*"),
    re.compile(r"flygo\.net/?"),
    re.compile(r"zypzyp@flygo\.net/?"),
]

# Chinese text patterns
_FIGURE_HEADER_RE = re.compile(r"第(\d+)图\s*(白先|黑先)")
_SOLUTION_END_RE = re.compile(r"以上为第(\d+)图(正解|参考图[^)]*)")
_BOILERPLATE_RE = re.compile(
    r"手筋辞典（濑越宪作、吴清源）\s*\n"
    r"编辑整理：.*?\n\n?",
    re.DOTALL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RawMove:
    """A single move extracted from the SGF move sequence."""

    color: str  # "B" or "W"
    coord: str  # SGF coordinate (e.g., "cd") or "zz" for pass
    comment: str = ""
    is_pass: bool = False


@dataclass
class PuzzleData:
    """One extracted puzzle ready for output."""

    figure_number: str  # e.g., "1", "77a"
    player_to_move: str  # "B" or "W"
    black_stones: list[str] = field(default_factory=list)  # SGF coords
    white_stones: list[str] = field(default_factory=list)  # SGF coords
    moves: list[RawMove] = field(default_factory=list)
    comment: str = ""


@dataclass
class SplitResult:
    """Result of splitting one source file."""

    source_file: str
    puzzles: list[PuzzleData]
    is_single: bool = False  # True if source had only one puzzle
    error: str | None = None


# ---------------------------------------------------------------------------
# SGF reading (raw byte-level, GB2312 aware)
# ---------------------------------------------------------------------------


def _read_sgf_bytes(path: Path) -> str:
    """Read an SGF file with GB2312/GBK encoding fallback.

    Unlike the standard tools.core.sgf_parser.read_sgf_file which uses
    UTF-8 -> latin-1, these files are GB2312-encoded Chinese text without
    a CA[] property. We try GB2312 first, then GBK (superset), then
    UTF-8, then latin-1 as universal fallback.
    """
    raw = path.read_bytes()
    for enc in _ENCODING_CHAIN[:-1]:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode(_ENCODING_CHAIN[-1])


# ---------------------------------------------------------------------------
# Low-level SGF tokenizer (operates on raw text, not the tree parser)
#
# We need byte-level control here because:
#   1. The project parser (tools.core.sgf_parser) restructures the move
#      sequence into a tree and loses pass-move information ([zz] coords)
#   2. We need to preserve raw move ordering for boundary detection
#   3. We need to handle AP[]/MULTIGOGM[] which are non-standard
# ---------------------------------------------------------------------------


def _extract_root_and_moves(
    sgf_text: str,
) -> tuple[dict[str, list[str]], list[RawMove]]:
    """Parse raw SGF into root properties and a flat move list.

    Returns:
        (root_props, moves) where root_props maps property names to lists
        of values, and moves is an ordered list of RawMove objects.
    """
    text = sgf_text.strip()
    if not text.startswith("("):
        raise ValueError("SGF must start with '('")

    pos = 1  # skip '('
    length = len(text)

    def skip_ws() -> None:
        nonlocal pos
        while pos < length and text[pos] in " \t\n\r":
            pos += 1

    def parse_prop_name() -> str:
        nonlocal pos
        start = pos
        while pos < length and text[pos].isupper():
            pos += 1
        return text[start:pos]

    def parse_prop_values() -> list[str]:
        nonlocal pos
        values: list[str] = []
        while True:
            # Skip whitespace between consecutive [value] brackets.
            # Some files (AP[]-enhanced) have newlines mid-property:
            #   AB[dd][cc]\n[kc][jd]...
            while pos < length and text[pos] in " \t\n\r":
                pos += 1
            if pos >= length or text[pos] != "[":
                break
            pos += 1  # skip '['
            val_start = pos
            while pos < length:
                ch = text[pos]
                if ch == "\\":
                    pos += 2
                    continue
                if ch == "]":
                    values.append(text[val_start:pos])
                    pos += 1  # skip ']'
                    break
                pos += 1
        return values

    def parse_node() -> dict[str, list[str]]:
        nonlocal pos
        props: dict[str, list[str]] = {}
        skip_ws()
        if pos >= length or text[pos] != ";":
            return props
        pos += 1  # skip ';'
        while pos < length:
            skip_ws()
            if pos >= length or text[pos] in ";()":
                break
            name = parse_prop_name()
            if not name:
                pos += 1
                continue
            vals = parse_prop_values()
            if name in props:
                props[name].extend(vals)
            else:
                props[name] = vals
        return props

    # Parse root node
    root_props = parse_node()

    # Parse move nodes (flat sequence -- no branching in these files)
    moves: list[RawMove] = []
    while pos < length:
        skip_ws()
        if pos >= length:
            break
        ch = text[pos]
        if ch == ")":
            break
        if ch == "(":
            # Sub-variation -- skip it (shouldn't happen in these files)
            depth = 1
            pos += 1
            while pos < length and depth > 0:
                if text[pos] == "(":
                    depth += 1
                elif text[pos] == ")":
                    depth -= 1
                elif text[pos] == "\\":
                    pos += 1  # skip escaped char
                pos += 1
            continue
        if ch == ";":
            node_props = parse_node()
            color = ""
            coord = ""
            comment = ""
            if "B" in node_props:
                color = "B"
                coord = node_props["B"][0] if node_props["B"] else ""
            elif "W" in node_props:
                color = "W"
                coord = node_props["W"][0] if node_props["W"] else ""
            if "C" in node_props:
                comment = node_props["C"][0]
            if color:
                is_pass = coord.lower() in ("zz", "tt", "")
                moves.append(
                    RawMove(
                        color=color,
                        coord=coord,
                        comment=comment,
                        is_pass=is_pass,
                    )
                )
            continue
        pos += 1

    return root_props, moves


# ---------------------------------------------------------------------------
# Comment cleaning
# ---------------------------------------------------------------------------


def _clean_comment(text: str) -> str:
    """Strip flygo.net URLs, attribution, and boilerplate from a comment."""
    result = text
    # Strip boilerplate header
    result = _BOILERPLATE_RE.sub("", result)
    # Strip URL patterns
    for pat in _STRIP_PATTERNS:
        result = pat.sub("", result)
    # Clean up leftover whitespace artifacts
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = result.strip()
    return result


def _extract_figure_comment(root_comment: str, figure_num: str) -> str:
    """Extract the comment fragment relevant to a specific figure number.

    From the root comment like:
        第1图 白先
        第2图 黑先
    Extract just the line for the given figure.
    """
    cleaned = _clean_comment(root_comment)
    lines = cleaned.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and f"第{figure_num}图" in stripped:
            return stripped
    return ""


# ---------------------------------------------------------------------------
# Stone separation via proximity / flood-fill
# ---------------------------------------------------------------------------


def _coord_to_xy(coord: str) -> tuple[int, int]:
    """Convert SGF coordinate to (x, y) tuple."""
    return (ord(coord[0]) - ord("a"), ord(coord[1]) - ord("a"))


def _xy_to_coord(x: int, y: int) -> str:
    """Convert (x, y) tuple to SGF coordinate."""
    return chr(ord("a") + x) + chr(ord("a") + y)


def _manhattan_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Manhattan distance between two board points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])



def _separate_stones(
    black_stones: list[str],
    white_stones: list[str],
    moves_1: list[RawMove],
    moves_2: list[RawMove],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Separate AB/AW stones into two puzzle regions.

    Strategy: competitive nearest-seed assignment with connected-component
    refinement. Each stone is assigned to the puzzle whose solution moves
    are closest, but only if:
      1. The stone is clearly closer to one puzzle than the other
         (distance ratio > 1.5), OR
      2. The stone is connected (adjacency chain) to the puzzle's core region.

    Stray stones (isolated, far from all solution moves) are dropped rather
    than assigned to the wrong puzzle.

    Returns:
        (black_1, white_1, black_2, white_2) - stone lists for each puzzle.
    """
    # Collect move coordinates as seeds for each puzzle
    seeds_1: set[tuple[int, int]] = set()
    for m in moves_1:
        if not m.is_pass and len(m.coord) == 2:
            seeds_1.add(_coord_to_xy(m.coord))

    seeds_2: set[tuple[int, int]] = set()
    for m in moves_2:
        if not m.is_pass and len(m.coord) == 2:
            seeds_2.add(_coord_to_xy(m.coord))

    # All setup stones as xy tuples
    all_black_xy = {_coord_to_xy(c) for c in black_stones}
    all_white_xy = {_coord_to_xy(c) for c in white_stones}
    all_stones_xy = all_black_xy | all_white_xy

    def _min_dist_to_seeds(
        stone: tuple[int, int], seeds: set[tuple[int, int]]
    ) -> int:
        if not seeds:
            return 999
        return min(_manhattan_distance(stone, s) for s in seeds)

    # Phase 1: Competitive assignment — each stone goes to the nearest puzzle
    # but only if it's unambiguously closer to one side.
    region_1: set[tuple[int, int]] = set()
    region_2: set[tuple[int, int]] = set()
    contested: set[tuple[int, int]] = set()

    for stone in all_stones_xy:
        d1 = _min_dist_to_seeds(stone, seeds_1)
        d2 = _min_dist_to_seeds(stone, seeds_2)

        if d1 == 0:
            region_1.add(stone)
        elif d2 == 0:
            region_2.add(stone)
        elif d1 < d2:
            # Clearly closer to puzzle 1
            if d2 / max(d1, 1) >= 1.5 or d1 <= 4:
                region_1.add(stone)
            else:
                contested.add(stone)
        elif d2 < d1:
            if d1 / max(d2, 1) >= 1.5 or d2 <= 4:
                region_2.add(stone)
            else:
                contested.add(stone)
        else:
            contested.add(stone)

    # Phase 2: Connected-component expansion — contested stones join the
    # region they are adjacent to (within 2 intersections of an already-
    # assigned stone in that region).
    changed = True
    while changed:
        changed = False
        for stone in list(contested):
            near_r1 = any(
                _manhattan_distance(stone, r) <= 2 for r in region_1
            )
            near_r2 = any(
                _manhattan_distance(stone, r) <= 2 for r in region_2
            )
            if near_r1 and not near_r2:
                region_1.add(stone)
                contested.discard(stone)
                changed = True
            elif near_r2 and not near_r1:
                region_2.add(stone)
                contested.discard(stone)
                changed = True
            elif near_r1 and near_r2:
                # Both regions claim it — assign to nearest seeds
                d1 = _min_dist_to_seeds(stone, seeds_1)
                d2 = _min_dist_to_seeds(stone, seeds_2)
                if d1 <= d2:
                    region_1.add(stone)
                else:
                    region_2.add(stone)
                contested.discard(stone)
                changed = True

    # Phase 3: Any remaining contested stones — assign to nearest, but
    # only if within reasonable distance (max 8). Otherwise drop as stray.
    for stone in contested:
        d1 = _min_dist_to_seeds(stone, seeds_1)
        d2 = _min_dist_to_seeds(stone, seeds_2)
        min_d = min(d1, d2)
        if min_d > 8:
            # Stray stone — too far from both puzzles, drop it
            logger.debug(
                "Dropping stray stone at %s (dist to p1=%d, p2=%d)",
                _xy_to_coord(*stone),
                d1,
                d2,
            )
            continue
        if d1 <= d2:
            region_1.add(stone)
        else:
            region_2.add(stone)

    # Convert back to SGF coordinate strings
    black_1 = [c for c in black_stones if _coord_to_xy(c) in region_1]
    white_1 = [c for c in white_stones if _coord_to_xy(c) in region_1]
    black_2 = [c for c in black_stones if _coord_to_xy(c) in region_2]
    white_2 = [c for c in white_stones if _coord_to_xy(c) in region_2]

    return black_1, white_1, black_2, white_2


# ---------------------------------------------------------------------------
# Move boundary detection
# ---------------------------------------------------------------------------


def _find_split_index(
    moves: list[RawMove], fig_1: str, is_anomaly: bool = False
) -> int:
    """Find the index where puzzle 1 ends and puzzle 2 begins.

    Strategy (comment-first, pass-fallback):
      1. Look for the C[] comment "以上为第{fig_1}图正解" (or 参考图) which
         marks the end of puzzle 1's solution. The NEXT non-pass move after
         that starts puzzle 2.
      2. If no such comment, look for a pass move (coord == "zz"/"ZZ") as
         a separator. The first REAL move after the pass starts puzzle 2.

    Why comment-first: some files have pass moves AFTER both solutions
    (trailing pass), not between them. The comment is always reliable.

    For anomaly files (same figure number for both puzzles), we use the
    FIRST occurrence of the solution-end comment rather than the last.

    Returns:
        Index of the first move of puzzle 2, or len(moves) if no split found.
    """
    # Strategy 1: comment-based boundary (most reliable)
    # Find the move node whose comment references fig_1's solution end.
    # For normal files: use LAST occurrence (handles 参考図 after 正解).
    # For anomaly files: use FIRST occurrence (both puzzles share the number).
    fig1_indices: list[int] = []
    for i, m in enumerate(moves):
        if m.comment and f"以上为第{fig_1}图" in m.comment:
            match = _SOLUTION_END_RE.search(m.comment)
            if match and match.group(1) == fig_1:
                fig1_indices.append(i)

    if fig1_indices:
        target_idx = fig1_indices[0] if is_anomaly else fig1_indices[-1]
        split = target_idx + 1
        # Skip any pass moves that immediately follow
        while split < len(moves) and moves[split].is_pass:
            split += 1
        # Only use this split if there are real moves remaining for puzzle 2
        if split < len(moves):
            return split

    # Strategy 2: pass move separator (fallback)
    # Find the first pass move that has REAL moves after it.
    for i, m in enumerate(moves):
        if m.is_pass:
            # Check there are real (non-pass) moves after this pass
            has_real_after = any(not mv.is_pass for mv in moves[i + 1 :])
            if has_real_after:
                return i  # The pass itself is the boundary

    # Fallback: no split found
    return len(moves)


# ---------------------------------------------------------------------------
# SGF output building (minimal, no YenGo properties)
# ---------------------------------------------------------------------------


def _build_output_sgf(puzzle: PuzzleData) -> str:
    """Build a clean SGF string for a single puzzle.

    Output format:
        (;SZ[19]PL[B]C[...]AB[..][..]AW[..][..];B[cd];W[ef];...)
    """
    parts: list[str] = ["(;SZ[19]"]

    # Player to move
    parts.append(f"PL[{puzzle.player_to_move}]")

    # Root comment
    if puzzle.comment:
        escaped = puzzle.comment.replace("\\", "\\\\").replace("]", "\\]")
        parts.append(f"C[{escaped}]")

    # Setup stones
    if puzzle.black_stones:
        ab_parts = "][".join(puzzle.black_stones)
        parts.append(f"AB[{ab_parts}]")

    if puzzle.white_stones:
        aw_parts = "][".join(puzzle.white_stones)
        parts.append(f"AW[{aw_parts}]")

    # Solution moves
    for move in puzzle.moves:
        if move.is_pass:
            continue
        node = f";{move.color}[{move.coord}]"
        if move.comment:
            cleaned = _clean_comment(move.comment)
            if cleaned:
                escaped = cleaned.replace("\\", "\\\\").replace("]", "\\]")
                node += f"C[{escaped}]"
        parts.append(node)

    parts.append(")")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------


# Filename patterns:
#   Dual-puzzle: {technique}{section}_{fig1}-{fig2}.sgf
#   Single-puzzle: {technique}{section}_{fig}.sgf
# Technique may contain underscores (e.g., "hane_osae01").
# Section number is optional (e.g., "damedumari_1-2.sgf").
# We match greedily up to the last underscore before figure numbers.
_DUAL_FILE_RE = re.compile(r"^(.+)_(\d+)-(\d+)\.sgf$")
_SINGLE_FILE_RE = re.compile(r"^(.+)_(\d+)\.sgf$")

# Sub-pattern to split technique+section from the prefix
_TECH_SECTION_RE = re.compile(r"^([a-z_]+?)(\d*)$")


@dataclass
class FileInfo:
    """Parsed information from a source filename."""

    technique: str  # e.g., "atekomi"
    section: str  # e.g., "01" or "" if no section
    fig_1: str  # First figure number
    fig_2: str | None  # Second figure number (None for single-puzzle files)
    is_dual: bool
    is_anomaly: bool = False  # oki08_77-77 case


def _parse_filename(name: str) -> FileInfo | None:
    """Parse a source filename into its components.

    Handles both sectioned names (atekomi01_1-2.sgf) and unsectioned
    names (damedumari_1-2.sgf). Also handles underscore-containing
    technique names (hane_osae04_37-38.sgf).
    """
    m = _DUAL_FILE_RE.match(name)
    if m:
        prefix, p1, p2 = m.groups()
        ts = _TECH_SECTION_RE.match(prefix)
        if ts:
            tech, sec = ts.groups()
        else:
            tech, sec = prefix, ""
        is_anomaly = p1 == p2
        return FileInfo(
            technique=tech,
            section=sec,
            fig_1=p1,
            fig_2=p2,
            is_dual=True,
            is_anomaly=is_anomaly,
        )

    m = _SINGLE_FILE_RE.match(name)
    if m:
        prefix, p1 = m.groups()
        ts = _TECH_SECTION_RE.match(prefix)
        if ts:
            tech, sec = ts.groups()
        else:
            tech, sec = prefix, ""
        return FileInfo(
            technique=tech,
            section=sec,
            fig_1=p1,
            fig_2=None,
            is_dual=False,
        )

    return None


def _output_filenames(info: FileInfo) -> list[str]:
    """Generate output filename(s) for a given source file.

    Normal dual: atekomi01_1-2.sgf -> [atekomi01_1.sgf, atekomi01_2.sgf]
    No section:  damedumari_1-2.sgf -> [damedumari_1.sgf, damedumari_2.sgf]
    Anomaly:     oki08_77-77.sgf   -> [oki08_77a.sgf, oki08_77b.sgf]
    Single:      geta06_53.sgf     -> [geta06_53.sgf]
    """
    prefix = f"{info.technique}{info.section}"
    if not info.is_dual:
        return [f"{prefix}_{info.fig_1}.sgf"]

    if info.is_anomaly:
        return [
            f"{prefix}_{info.fig_1}a.sgf",
            f"{prefix}_{info.fig_1}b.sgf",
        ]

    return [
        f"{prefix}_{info.fig_1}.sgf",
        f"{prefix}_{info.fig_2}.sgf",
    ]


# ---------------------------------------------------------------------------
# Core split logic
# ---------------------------------------------------------------------------


def split_file(sgf_text: str, file_info: FileInfo) -> SplitResult:
    """Split a single SGF file into one or two puzzles.

    Args:
        sgf_text: Decoded SGF content.
        file_info: Parsed filename information.

    Returns:
        SplitResult with extracted puzzles.
    """
    source_name = (
        f"{file_info.technique}{file_info.section}"
        f"_{file_info.fig_1}"
        + (f"-{file_info.fig_2}" if file_info.fig_2 else "")
        + ".sgf"
    )

    try:
        root_props, moves = _extract_root_and_moves(sgf_text)
    except Exception as e:
        return SplitResult(
            source_file=source_name,
            puzzles=[],
            error=f"Parse error: {e}",
        )

    # Extract setup stones
    black_stones = root_props.get("AB", [])
    white_stones = root_props.get("AW", [])

    # Extract root comment
    root_comment = root_props.get("C", [""])[0]

    # Parse figure headers from root comment to get player-to-move
    fig_headers = _FIGURE_HEADER_RE.findall(root_comment)
    fig_color_map: dict[str, str] = {}
    for fig_num, color_text in fig_headers:
        fig_color_map[fig_num] = "W" if color_text == "白先" else "B"

    # --- Single-puzzle file ---
    if not file_info.is_dual:
        ptm = fig_color_map.get(file_info.fig_1, "B")
        # If no root comment hint, infer from first move
        if not ptm and moves:
            ptm = moves[0].color
        comment = _extract_figure_comment(root_comment, file_info.fig_1)
        puzzle = PuzzleData(
            figure_number=file_info.fig_1,
            player_to_move=ptm,
            black_stones=black_stones,
            white_stones=white_stones,
            moves=moves,
            comment=comment,
        )
        return SplitResult(
            source_file=source_name,
            puzzles=[puzzle],
            is_single=True,
        )

    # --- Dual-puzzle file ---
    assert file_info.fig_2 is not None

    # Find the split boundary
    split_idx = _find_split_index(
        moves, file_info.fig_1, is_anomaly=file_info.is_anomaly
    )

    # Separate moves
    moves_1_raw = moves[:split_idx]
    moves_2_raw = moves[split_idx:]

    # Filter out pass moves and reference-diagram moves from each puzzle's moves
    # For puzzle 1: everything before split (excluding pass)
    moves_1 = [m for m in moves_1_raw if not m.is_pass]
    # For puzzle 2: everything after split (excluding pass)
    # The first move after a pass separator may be a pass too; skip it
    moves_2 = [m for m in moves_2_raw if not m.is_pass]

    # Strip trailing reference-diagram moves from puzzle 2
    # These are moves AFTER a "正解" comment that come before another section
    # (seen in files like tuke06_53-54.sgf where 参考图 follows 正解)
    # We keep all moves for each puzzle -- the reference diagram is useful context

    if not moves_1 or not moves_2:
        # Edge case: couldn't split properly
        logger.warning(
            "Could not split %s: puzzle 1 has %d moves, puzzle 2 has %d moves",
            source_name,
            len(moves_1),
            len(moves_2),
        )
        if not moves_1 and not moves_2:
            return SplitResult(
                source_file=source_name,
                puzzles=[],
                error="No moves found in either puzzle",
            )

    # Separate setup stones
    if moves_1 and moves_2:
        b1, w1, b2, w2 = _separate_stones(
            black_stones, white_stones, moves_1, moves_2
        )
    elif moves_1:
        b1, w1 = black_stones, white_stones
        b2, w2 = [], []
    else:
        b1, w1 = [], []
        b2, w2 = black_stones, white_stones

    # Determine player to move for each puzzle
    ptm_1 = fig_color_map.get(file_info.fig_1, "")
    ptm_2 = fig_color_map.get(file_info.fig_2, "")

    # For the anomaly case (77-77), both figures have the same number
    # Use the first and second occurrence from the header
    if file_info.is_anomaly and len(fig_headers) >= 2:
        ptm_1 = "W" if fig_headers[0][1] == "白先" else "B"
        ptm_2 = "W" if fig_headers[1][1] == "白先" else "B"

    # Fallback: infer from first move color
    if not ptm_1 and moves_1:
        ptm_1 = moves_1[0].color
    if not ptm_2 and moves_2:
        ptm_2 = moves_2[0].color
    if not ptm_1:
        ptm_1 = "B"
    if not ptm_2:
        ptm_2 = "B"

    # Extract per-puzzle comments from root
    comment_1 = _extract_figure_comment(root_comment, file_info.fig_1)
    if file_info.is_anomaly:
        # For anomaly, just label them distinctly
        comment_1 = _extract_figure_comment(root_comment, file_info.fig_1)
        comment_2 = comment_1  # Same figure number
    else:
        comment_2 = _extract_figure_comment(root_comment, file_info.fig_2)

    # Figure numbers for output naming
    if file_info.is_anomaly:
        fig_num_1 = f"{file_info.fig_1}a"
        fig_num_2 = f"{file_info.fig_1}b"
    else:
        fig_num_1 = file_info.fig_1
        fig_num_2 = file_info.fig_2

    puzzle_1 = PuzzleData(
        figure_number=fig_num_1,
        player_to_move=ptm_1,
        black_stones=b1,
        white_stones=w1,
        moves=moves_1,
        comment=comment_1,
    )
    puzzle_2 = PuzzleData(
        figure_number=fig_num_2,
        player_to_move=ptm_2,
        black_stones=b2,
        white_stones=w2,
        moves=moves_2,
        comment=comment_2,
    )

    return SplitResult(
        source_file=source_name,
        puzzles=[puzzle_1, puzzle_2],
    )


# ---------------------------------------------------------------------------
# File I/O and main driver
# ---------------------------------------------------------------------------


def _resolve_source_dir() -> Path:
    """Locate the source directory relative to this script's location."""
    # Script lives in tools/kisvadim_goproblems/
    # Source is external-sources/kisvadim-goproblems/GO SEIGEN - .../
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_dir = repo_root / "external-sources" / "kisvadim-goproblems" / _SOURCE_DIR_NAME
    return source_dir


def _resolve_output_dir(source_dir: Path) -> Path:
    """Output directory is a sibling of source called 'split'."""
    return source_dir.parent / "segoe-tesuji-split"


def process_all(
    source_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Process all SGF files in the source directory.

    Args:
        source_dir: Path to the source SGF directory.
        output_dir: Path to write split files.
        dry_run: If True, report actions without writing files.
        verbose: If True, print detailed per-file information.
    """
    if not source_dir.is_dir():
        logger.error("Source directory not found: %s", source_dir)
        sys.exit(1)

    sgf_files = sorted(
        f for f in source_dir.iterdir() if f.suffix.lower() == ".sgf"
    )
    logger.info("Found %d SGF files in %s", len(sgf_files), source_dir)

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "total": len(sgf_files),
        "dual": 0,
        "single": 0,
        "skipped": 0,
        "errors": 0,
        "puzzles_written": 0,
    }

    for sgf_path in sgf_files:
        file_info = _parse_filename(sgf_path.name)
        if file_info is None:
            logger.warning("Unrecognized filename pattern: %s", sgf_path.name)
            stats["skipped"] += 1
            continue

        sgf_text = _read_sgf_bytes(sgf_path)
        result = split_file(sgf_text, file_info)

        if result.error:
            logger.error("Error in %s: %s", sgf_path.name, result.error)
            stats["errors"] += 1
            continue

        if result.is_single:
            stats["single"] += 1
        else:
            stats["dual"] += 1

        output_names = _output_filenames(file_info)

        for puzzle, out_name in zip(result.puzzles, output_names):
            sgf_output = _build_output_sgf(puzzle)
            out_path = output_dir / out_name

            if dry_run:
                move_count = len([m for m in puzzle.moves if not m.is_pass])
                stone_count = len(puzzle.black_stones) + len(puzzle.white_stones)
                if verbose:
                    print(
                        f"  [DRY-RUN] {sgf_path.name} -> {out_name}  "
                        f"(PL={puzzle.player_to_move}, "
                        f"stones={stone_count}, "
                        f"moves={move_count})"
                    )
                stats["puzzles_written"] += 1
            else:
                out_path.write_text(sgf_output, encoding="utf-8")
                stats["puzzles_written"] += 1
                if verbose:
                    move_count = len([m for m in puzzle.moves if not m.is_pass])
                    stone_count = len(puzzle.black_stones) + len(
                        puzzle.white_stones
                    )
                    print(
                        f"  {sgf_path.name} -> {out_name}  "
                        f"(PL={puzzle.player_to_move}, "
                        f"stones={stone_count}, "
                        f"moves={move_count})"
                    )

    # Summary
    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{mode}Split summary:")
    print(f"  Source files:     {stats['total']}")
    print(f"  Dual-puzzle:      {stats['dual']}")
    print(f"  Single-puzzle:    {stats['single']}")
    print(f"  Skipped:          {stats['skipped']}")
    print(f"  Errors:           {stats['errors']}")
    print(f"  Puzzles written:  {stats['puzzles_written']}")
    if not dry_run:
        print(f"  Output directory:  {output_dir}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split Segoe Tesuji Dictionary dual-puzzle SGF files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would happen without writing files.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed per-file information.",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Override source directory (default: auto-detected).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory (default: sibling of source).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    source_dir = args.source_dir or _resolve_source_dir()
    output_dir = args.output_dir or _resolve_output_dir(source_dir)

    process_all(
        source_dir=source_dir,
        output_dir=output_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
