"""Build complete puzzle SGFs with solution trees from image pairs.

Takes a problem image (setup position) and answer images (correct,
wrong, variation) and produces an SGF with a full move tree — main
line for the correct answer, variation branches for wrong answers.

Algorithm:
  1. Recognize problem image → setup stones (AB/AW)
  2. For each answer image, diff against problem → ordered moves
  3. Build SGF: main-line = correct answer, branches = wrong answers
  4. Attach answer text as root comment
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from tools.core.image_to_board import (
    BLACK,
    EMPTY,
    WHITE,
    RecognitionConfig,
    RecognizedPosition,
    detect_digit,
    recognize_position,
)
from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import SgfNode
from tools.core.sgf_types import Color, Point

from tools.minoru_harada_tsumego.models import PuzzleEntry, PuzzleImage
from tools.minoru_harada_tsumego.sgf_converter import (
    extract_solution_moves,
    position_to_sgf,
)

log = logging.getLogger(__name__)

# Answer images have digit overlays on stones.  The default multi-blur
# voting (blur_kernels=(0,3,5)) kills white numbered stone detection
# because Gaussian blur smears the digit into the white stone, dropping
# bright_ratio below the WHITE threshold at blur=3 and blur=5.
# Single-pass (blur=0) correctly detects all numbered stones.
_ANSWER_CONFIG = RecognitionConfig(blur_kernels=(0,))

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class BuildResult:
    """Result of building one SGF for a puzzle/level combination."""

    puzzle_number: int
    level: str
    sgf: str
    correct_move_count: int = 0
    wrong_branch_count: int = 0
    variation_branch_count: int = 0
    error: str = ""
    validation_warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.error


# ---------------------------------------------------------------------------
# Comment normalization
# ---------------------------------------------------------------------------

# Section markers that should start on a new line
_SECTION_MARKERS = re.compile(
    r"^(Wrong Answer|Correct Answer|\(Variation\))",
    re.MULTILINE,
)

# Copyright / boilerplate patterns to strip from comments
_COPYRIGHT_PATTERN = re.compile(
    r"\s*\(C\)\s*Hitachi.*$|"
    r"\s*Copyright\s.*$|"
    r"\s*All [Rr]ights [Rr]eserved.*$|"
    r"\s*Term of Use.*$|"
    r"\s*page top.*$",
    re.MULTILINE | re.IGNORECASE,
)


def _normalize_comment(raw: str) -> str:
    """Normalize extracted answer text for SGF comments.

    - Joins mid-sentence line breaks into spaces
    - Preserves paragraph breaks before section markers
      (Wrong Answer, (Variation), etc.)
    - Collapses multiple whitespace into single spaces
    - Strips leading/trailing whitespace
    """
    if not raw:
        return raw

    # Split into lines, mark section-marker lines
    lines = raw.split("\n")
    normalized: list[str] = []
    buf: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Empty line → flush buffer as a paragraph
            if buf:
                normalized.append(" ".join(buf))
                buf = []
            continue
        if _SECTION_MARKERS.match(stripped):
            # Section marker → flush buffer, start new paragraph
            if buf:
                normalized.append(" ".join(buf))
                buf = []
            buf.append(stripped)
        else:
            buf.append(stripped)

    if buf:
        normalized.append(" ".join(buf))

    result = "\n".join(normalized)
    # Strip copyright / boilerplate
    result = _COPYRIGHT_PATTERN.sub("", result)
    # Collapse multiple spaces
    result = re.sub(r"  +", " ", result)
    return result.strip()


# GTP column letters (skip 'I')
_GTP_COLS = "ABCDEFGHJKLMNOPQRST"


def _sgf_coord_to_gtp(coord: str, board_size: int = 19) -> str:
    """Convert SGF coordinate like 'ca' to GTP like 'C19'."""
    if len(coord) < 2:
        return coord
    col = ord(coord[0]) - ord("a")  # 0-based column
    row = ord(coord[1]) - ord("a")  # 0-based row from top
    gtp_col = _GTP_COLS[col] if col < len(_GTP_COLS) else "?"
    gtp_row = board_size - row  # GTP numbers from bottom
    return f"{gtp_col}{gtp_row}"


def _replace_move_refs(
    comment: str,
    all_branches: list[list[tuple[Color, Point]]],
    board_size: int = 19,
) -> str:
    """Replace 'Black 1', 'White 2' etc. with GTP coordinates.

    Uses the longest branch (correct answer) to map move numbers to
    coordinates.  'Black 1' → 'Black C19'.  References to moves
    beyond the extracted sequence are dropped (they refer to
    continuation diagrams we don't have).
    """
    if not all_branches:
        return comment

    # Use the longest branch for coordinate mapping
    moves = max(all_branches, key=len)

    # Build mapping: move_number (1-based) → GTP coordinate string
    coord_map: dict[int, str] = {}
    for i, (color, point) in enumerate(moves):
        col_char = chr(ord("a") + point.x)
        row_char = chr(ord("a") + point.y)
        gtp = _sgf_coord_to_gtp(col_char + row_char, board_size)
        coord_map[i + 1] = gtp

    def replace_single(m: re.Match) -> str:
        color_word = m.group(1)  # "Black" or "White"
        num = int(m.group(2))
        gtp = coord_map.get(num)
        if gtp:
            return f"{color_word} {gtp}"
        # Move not in our sequence — drop the number, keep just color
        return color_word

    # Replace "Black N" / "White N" with coordinate
    result = re.sub(r"(Black|White)\s+(\d+)", replace_single, comment)

    # Clean up phrases like "with 3 to 11" → "with 3 (C19) to 11 (B18)"
    # Also handle "moves N to M" and "N and M" patterns
    def replace_range_num(m: re.Match) -> str:
        num = int(m.group(1))
        gtp = coord_map.get(num)
        return gtp if gtp else ""

    # Replace bare numbers after "to", "and", "at" that reference moves
    result = re.sub(
        r"(?<=\bto\s)(\d+)\b",
        replace_range_num, result,
    )
    result = re.sub(
        r"(?<=\band\s)(\d+)\b",
        replace_range_num, result,
    )

    # Collapse "with  to" → "with ... to ..." cleanup
    result = re.sub(r"\s{2,}", " ", result)
    # Remove dangling empty refs like "with to" or "and ."
    result = re.sub(r"\bwith\s+to\b", "through", result)
    result = re.sub(r"\bto\s+\.", ".", result)

    return result.strip()


# ---------------------------------------------------------------------------
# Comment section splitting
# ---------------------------------------------------------------------------

# Markers that delimit sections in the root comment
_WRONG_MARKER = re.compile(r"^Wrong\s+Answer\b", re.MULTILINE | re.IGNORECASE)
_VARIATION_MARKER = re.compile(r"^\(Variation\)", re.MULTILINE)


def _split_comment_sections(comment: str) -> dict[str, str]:
    """Split a root comment into header/correct/wrong/variation sections.

    Returns a dict with keys:
      'header'    — puzzle identifier line (always present)
      'correct'   — teaching text for the correct answer
      'wrong'     — teaching text for the wrong answer (if any)
      'variation' — teaching text for the variation (if any)
    """
    lines = comment.split("\n")
    header = lines[0] if lines else ""
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

    result: dict[str, str] = {"header": header, "correct": "", "wrong": "", "variation": ""}
    if not body:
        return result

    # Find section boundaries
    wrong_match = _WRONG_MARKER.search(body)
    var_match = _VARIATION_MARKER.search(body)

    # Determine section ranges
    boundaries: list[tuple[int, str]] = [(0, "correct")]
    if wrong_match:
        boundaries.append((wrong_match.start(), "wrong"))
    if var_match:
        boundaries.append((var_match.start(), "variation"))
    boundaries.sort(key=lambda b: b[0])

    for i, (start, key) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(body)
        section_text = body[start:end].strip()
        # Strip the marker prefix itself for wrong/variation
        if key == "wrong":
            section_text = _WRONG_MARKER.sub("", section_text).strip()
        elif key == "variation":
            section_text = _VARIATION_MARKER.sub("", section_text).strip()
        result[key] = section_text

    return result


# ---------------------------------------------------------------------------
# Low-level tree assembly
# ---------------------------------------------------------------------------


def _find_common_prefix(
    correct: list[tuple[Color, Point]],
    branch: list[tuple[Color, Point]],
) -> int:
    """Return the number of leading moves shared between correct and branch."""
    prefix = 0
    for cm, bm in zip(correct, branch):
        if cm == bm:
            prefix += 1
        else:
            break
    return prefix


def build_solution_tree(
    setup_pos: RecognizedPosition,
    correct_moves: list[tuple[Color, Point]],
    wrong_branches: list[list[tuple[Color, Point]]],
    variation_branches: list[list[tuple[Color, Point]]],
    player_to_move: Color = Color.BLACK,
    board_size: int = 19,
    comment: str = "",
) -> str:
    """Assemble a puzzle SGF from pre-extracted moves.

    Teaching text in *comment* is split by section markers:
    - Text before "Wrong Answer" → attached to correct branch
    - Text after "Wrong Answer" → attached to wrong branch
    - Text after "(Variation)" → attached to variation branch
    - Puzzle header stays as root comment

    Args:
        setup_pos: Recognised problem position (setup stones).
        correct_moves: Ordered correct-answer moves.
        wrong_branches: Each inner list is a wrong-answer sequence.
        variation_branches: Each inner list is a variation sequence.
        player_to_move: Who plays first.
        board_size: Full board size.
        comment: Root comment (answer text, attribution, etc.).

    Returns:
        Complete SGF string with solution tree.
    """
    # Split comment into sections
    sections = _split_comment_sections(comment)

    builder = SGFBuilder(board_size=board_size)
    builder.set_player_to_move(player_to_move)

    # Root comment: just the header (puzzle identifier)
    if sections["header"]:
        builder.set_comment(sections["header"])

    # Setup stones
    for iy, row in enumerate(setup_pos.board):
        for ix, cell in enumerate(row):
            x = setup_pos.board_left + ix
            y = setup_pos.board_top + iy
            if cell == "X":
                builder.add_black_stone(Point(x, y))
            elif cell == "O":
                builder.add_white_stone(Point(x, y))

    # Main line — correct answer, collecting node references by depth
    correct_text = sections["correct"]
    main_line_nodes: list[SgfNode] = [builder.solution_tree]  # index 0 = root
    for i, (color, point) in enumerate(correct_moves):
        if i == 0 and correct_text:
            move_comment = f"Correct: {correct_text}"
        elif i == 0:
            move_comment = "Correct"
        else:
            move_comment = ""
        builder.add_solution_move(color, point, comment=move_comment, is_correct=True)
        main_line_nodes.append(builder._current_node)

    # Wrong-answer branches (with shared-prefix merging)
    wrong_text = sections["wrong"]
    for branch in wrong_branches:
        if not branch:
            continue
        # Find how many leading moves match the correct line
        prefix_len = _find_common_prefix(correct_moves, branch)
        if prefix_len > 0 and prefix_len < len(main_line_nodes):
            # Branch from the divergence point on the main line
            builder._current_node = main_line_nodes[prefix_len]
            divergent_moves = branch[prefix_len:]
        else:
            builder.add_variation()  # branch from root
            divergent_moves = branch

        for i, (color, point) in enumerate(divergent_moves):
            if i == 0 and wrong_text:
                move_comment = f"Wrong: {wrong_text}"
            elif i == 0:
                move_comment = "Wrong"
            else:
                move_comment = ""
            # BM[1] only on the first divergent move (the actual mistake)
            builder.add_solution_move(
                color, point, comment=move_comment, is_correct=(i != 0),
            )

    # Variation branches (correct alternatives or continuations)
    variation_text = sections["variation"]
    for branch in variation_branches:
        if not branch:
            continue
        # Same shared-prefix merging for variations
        prefix_len = _find_common_prefix(correct_moves, branch)
        if prefix_len > 0 and prefix_len < len(main_line_nodes):
            builder._current_node = main_line_nodes[prefix_len]
            divergent_moves = branch[prefix_len:]
        else:
            builder.add_variation()
            divergent_moves = branch

        for i, (color, point) in enumerate(divergent_moves):
            if i == 0 and variation_text:
                move_comment = f"Variation: {variation_text}"
                variation_text = ""  # only attach to first variation branch
            else:
                move_comment = ""
            builder.add_solution_move(color, point, comment=move_comment, is_correct=True)

    return builder.build()


# ---------------------------------------------------------------------------
# High-level: from PuzzleEntry → SGF
# ---------------------------------------------------------------------------


def _images_by_type(
    entry: PuzzleEntry,
    level: str,
) -> dict[str, list[PuzzleImage]]:
    """Group downloaded images by type for a given level.

    For problem images, prefer level-specific images over shared
    (``level=""``) ones.  Tiny files (< 500 bytes) are skipped — they
    are site decoration placeholders, not board diagrams.
    """
    # Minimum file size for a valid board image (real boards are > 5 KB)
    _MIN_IMAGE_BYTES = 500

    groups: dict[str, list[PuzzleImage]] = {
        "problem": [],
        "answer_correct": [],
        "answer_wrong": [],
        "answer_unknown": [],
    }
    for img in entry.images:
        if not img.downloaded:
            continue
        if img.level != level and img.level != "":
            continue
        # Skip tiny files — placeholders like space.gif (43 bytes)
        if img.file_size < _MIN_IMAGE_BYTES:
            continue
        key = img.image_type
        if key in groups:
            groups[key].append(img)

    # For problem images: prefer level-specific over shared (level="")
    if groups["problem"]:
        level_specific = [im for im in groups["problem"] if im.level == level]
        if level_specific:
            groups["problem"] = level_specific

    # Sort variants by number
    for key in groups:
        groups[key].sort(key=lambda im: im.variant)
    return groups


def _check_alternation(moves: list[tuple[Color, Point]]) -> bool:
    """Check that move colors strictly alternate."""
    for i in range(len(moves) - 1):
        if moves[i][0] == moves[i + 1][0]:
            return False
    return True


def _validate_moves(
    correct_moves: list[tuple[Color, Point]],
    wrong_branches: list[list[tuple[Color, Point]]],
    variation_branches: list[list[tuple[Color, Point]]],
    player_to_move: Color = Color.BLACK,
) -> list[str]:
    """Validate extracted move sequences for structural integrity.

    Returns a list of warning codes. Empty list = all checks passed.
    """
    warnings: list[str] = []

    # 1. PL color mismatch — first correct move must match player_to_move
    if correct_moves and correct_moves[0][0] != player_to_move:
        warnings.append("PL_COLOR_MISMATCH")

    # 2. No correct branch (only wrong branches exist)
    if not correct_moves and wrong_branches:
        warnings.append("NO_CORRECT_BRANCH")

    # 3. Color alternation in correct line
    if correct_moves and not _check_alternation(correct_moves):
        warnings.append("CONSECUTIVE_COLORS_CORRECT")

    # 4. Color alternation in wrong branches
    for i, branch in enumerate(wrong_branches):
        if branch and not _check_alternation(branch):
            warnings.append(f"CONSECUTIVE_COLORS_WRONG_{i}")

    # 4b. Color alternation in variation branches
    for i, branch in enumerate(variation_branches):
        if branch and not _check_alternation(branch):
            warnings.append(f"CONSECUTIVE_COLORS_VARIATION_{i}")

    # 5. Empty branches
    for i, branch in enumerate(wrong_branches):
        if not branch:
            warnings.append(f"EMPTY_WRONG_BRANCH_{i}")

    # 6. Shared prefix — same opening moves in correct and wrong.
    # No longer a warning: build_solution_tree uses shared-prefix merging
    # to branch at the divergence point, placing BM[1] correctly.
    # Kept as info for diagnostics only.

    # 7. Wrong branch first move color mismatch
    for i, branch in enumerate(wrong_branches):
        if branch and branch[0][0] != player_to_move:
            warnings.append(f"WRONG_BRANCH_PL_MISMATCH_{i}")

    return warnings


# Warnings that indicate the SGF solution tree is structurally broken
# and should NOT be written to the output directory.
_CRITICAL_WARNINGS = frozenset({
    "CONSECUTIVE_COLORS_CORRECT",
})


def has_critical_warnings(warnings: list[str]) -> bool:
    """Return True if any warning indicates a broken solution tree."""
    return any(
        w in _CRITICAL_WARNINGS
        or w.startswith("CONSECUTIVE_COLORS_WRONG")
        or w.startswith("CONSECUTIVE_COLORS_VARIATION")
        for w in warnings
    )


def _is_compatible_variation(
    problem: RecognizedPosition,
    variation: RecognizedPosition,
    threshold: float = 0.90,
) -> bool:
    """Check if a variation image is compatible with the problem position.

    A compatible variation should contain most of the problem's setup
    stones.  Low overlap indicates the variation belongs to a different
    difficulty level.
    """
    problem_stones: set[tuple[int, int, str]] = set()
    for iy, row in enumerate(problem.board):
        for ix, cell in enumerate(row):
            if cell in (BLACK, WHITE):
                problem_stones.add((problem.board_left + ix, problem.board_top + iy, cell))

    if not problem_stones:
        return True

    var_stones: set[tuple[int, int, str]] = set()
    for iy, row in enumerate(variation.board):
        for ix, cell in enumerate(row):
            if cell in (BLACK, WHITE):
                var_stones.add((variation.board_left + ix, variation.board_top + iy, cell))

    overlap = len(problem_stones & var_stones)
    return overlap / len(problem_stones) >= threshold


def _infer_problem_from_answer(
    groups: dict[str, list[PuzzleImage]],
    image_dir: Path,
    board_size: int,
) -> RecognizedPosition | None:
    """Infer problem position from answer image by removing numbered stones.

    Recognizes the answer image, detects digits on every stone,
    and blanks out stones that have a detected digit (those are answer
    moves).  The remaining stones form the problem position.
    """
    for key in ("answer_correct", "answer_wrong", "answer_unknown"):
        for img_meta in groups.get(key, []):
            ans_path = image_dir / img_meta.local_path
            if not ans_path.exists():
                continue
            try:
                pos = recognize_position(
                    ans_path, board_size=board_size, config=_ANSWER_CONFIG,
                )
                img = Image.open(str(ans_path)).convert("RGB")

                new_board = [list(row) for row in pos.board]
                for iy, row in enumerate(pos.board):
                    for ix, cell in enumerate(row):
                        if cell in (BLACK, WHITE):
                            cx = pos.grid.x_lines[ix]
                            cy = pos.grid.y_lines[iy]
                            dr = detect_digit(img, cx, cy, cell)
                            if dr.digit > 0:
                                new_board[iy][ix] = EMPTY

                return RecognizedPosition(
                    grid=pos.grid,
                    board=new_board,
                    board_top=pos.board_top,
                    board_left=pos.board_left,
                    has_top_edge=pos.has_top_edge,
                    has_bottom_edge=pos.has_bottom_edge,
                    has_left_edge=pos.has_left_edge,
                    has_right_edge=pos.has_right_edge,
                )
            except Exception:
                continue
    return None


def build_puzzle_sgf(
    entry: PuzzleEntry,
    level: str,
    image_dir: Path,
    board_size: int = 19,
) -> BuildResult:
    """Build a complete puzzle SGF for one level of a PuzzleEntry.

    Args:
        entry: Catalog puzzle entry with image metadata.
        level: ``"elementary"`` or ``"intermediate"``.
        image_dir: Base directory containing downloaded images.
        board_size: Full board size (default 19).

    Returns:
        BuildResult with SGF string or error detail.
    """
    result = BuildResult(
        puzzle_number=entry.problem_number,
        level=level,
        sgf="",
    )
    t0 = time.perf_counter()

    groups = _images_by_type(entry, level)

    # --- Problem image (required, with answer-image inference fallback) ---
    if not groups["problem"]:
        problem_pos = _infer_problem_from_answer(groups, image_dir, board_size)
        if problem_pos is None:
            result.error = f"No problem image for #{entry.problem_number} {level}"
            return result
        log.info(
            "Puzzle #%d %s: inferred problem from answer image",
            entry.problem_number, level,
        )
    else:
        problem_path = image_dir / groups["problem"][0].local_path
        if not problem_path.exists():
            result.error = f"Problem image not found: {problem_path}"
            return result
        try:
            problem_pos = recognize_position(problem_path, board_size=board_size)
        except Exception as exc:
            result.error = f"Recognition failed for problem: {exc}"
            return result

    bc, wc = problem_pos.stone_count()
    log.debug(
        "Puzzle #%d %s: grid=%dx%d stones=%dB/%dW edges=%s",
        entry.problem_number, level,
        problem_pos.n_cols, problem_pos.n_rows, bc, wc,
        "".join(s for s, f in [
            ("T", problem_pos.has_top_edge), ("R", problem_pos.has_right_edge),
            ("B", problem_pos.has_bottom_edge), ("L", problem_pos.has_left_edge),
        ] if f) or "none",
    )

    # --- Validate position has stones ---
    has_stones = any(
        cell in ("X", "O")
        for row in problem_pos.board
        for cell in row
    )
    if not has_stones:
        result.error = f"Empty board — no stones recognised in #{entry.problem_number} {level}"
        return result

    # --- Correct answer moves ---
    correct_moves: list[tuple[Color, Point]] = []
    for answer_img in groups["answer_correct"]:
        ans_path = image_dir / answer_img.local_path
        if not ans_path.exists():
            continue
        try:
            answer_pos = recognize_position(ans_path, board_size=board_size, config=_ANSWER_CONFIG)
            moves = extract_solution_moves(problem_pos, answer_pos, ans_path)
            if moves:
                correct_moves = moves
                break  # Use the first correct answer
        except Exception as exc:
            log.warning("Failed to extract correct answer from %s: %s", ans_path.name, exc)

    # --- Wrong answer branches ---
    wrong_branches: list[list[tuple[Color, Point]]] = []
    for wrong_img in groups["answer_wrong"]:
        wrong_path = image_dir / wrong_img.local_path
        if not wrong_path.exists():
            continue
        try:
            wrong_pos = recognize_position(wrong_path, board_size=board_size, config=_ANSWER_CONFIG)
            moves = extract_solution_moves(problem_pos, wrong_pos, wrong_path)
            if moves:
                wrong_branches.append(moves)
        except Exception as exc:
            log.warning("Failed to extract wrong answer from %s: %s", wrong_path.name, exc)

    # --- Variation branches ---
    variation_branches: list[list[tuple[Color, Point]]] = []
    for var_img in groups["answer_unknown"]:
        var_path = image_dir / var_img.local_path
        if not var_path.exists():
            continue
        try:
            var_pos = recognize_position(var_path, board_size=board_size, config=_ANSWER_CONFIG)
            if not _is_compatible_variation(problem_pos, var_pos):
                log.debug(
                    "Skipping %s — low overlap with %s problem",
                    var_path.name, level,
                )
                continue
            moves = extract_solution_moves(problem_pos, var_pos, var_path)
            if moves:
                variation_branches.append(moves)
        except Exception as exc:
            log.warning("Failed to extract variation from %s: %s", var_path.name, exc)

    # --- Build root comment ---
    answer_text = ""
    if level == "elementary":
        answer_text = entry.elementary_answer_text
    elif level == "intermediate":
        answer_text = entry.intermediate_answer_text

    comment_parts: list[str] = [
        f"Harada #{entry.problem_number} ({level.capitalize()})",
    ]
    if answer_text:
        comment_parts.append(_normalize_comment(answer_text))
    root_comment = "\n".join(comment_parts)

    # --- Promote: if no correct branch, use first variation or wrong ---
    if not correct_moves and variation_branches:
        correct_moves = variation_branches.pop(0)
    elif not correct_moves and wrong_branches:
        correct_moves = wrong_branches.pop(0)

    # --- Truncate excessively long branches (likely image noise) ---
    _MAX_BRANCH_MOVES = 15
    if len(correct_moves) > _MAX_BRANCH_MOVES:
        correct_moves = correct_moves[:_MAX_BRANCH_MOVES]
    wrong_branches = [
        b[:_MAX_BRANCH_MOVES] for b in wrong_branches
    ]
    variation_branches = [
        b[:_MAX_BRANCH_MOVES] for b in variation_branches
    ]

    # --- No solution moves → emit setup-only SGF with puzzle_only marker ---
    if not correct_moves and not wrong_branches:
        puzzle_only_comment = f"{root_comment} puzzle_only"
        result.sgf = position_to_sgf(
            problem_pos,
            player_to_move=Color.BLACK,
            board_size=board_size,
            comment=puzzle_only_comment,
        )
        result.correct_move_count = 0
        result.wrong_branch_count = 0
        result.variation_branch_count = 0
        elapsed_ms = (time.perf_counter() - t0) * 1000
        log.info(
            "Built #%d %s: puzzle_only (no solution moves) (%.0fms)",
            entry.problem_number, level, elapsed_ms,
        )
        return result

    # --- Replace "Black 1", "White 2" with coordinates per section ---
    # Each comment section uses its own branch for coordinate mapping:
    # correct section → correct_moves, wrong → wrong_branches, variation → variation_branches
    sections_for_mapping = _split_comment_sections(root_comment)
    mapped_parts: list[str] = [sections_for_mapping["header"]]

    if sections_for_mapping["correct"]:
        mapped_correct = _replace_move_refs(
            sections_for_mapping["correct"],
            [correct_moves] if correct_moves else [],
            board_size,
        )
        mapped_parts.append(mapped_correct)

    if sections_for_mapping["wrong"]:
        mapped_wrong = _replace_move_refs(
            sections_for_mapping["wrong"],
            wrong_branches if wrong_branches else [],
            board_size,
        )
        mapped_parts.append(f"Wrong Answer\n{mapped_wrong}")

    if sections_for_mapping["variation"]:
        mapped_var = _replace_move_refs(
            sections_for_mapping["variation"],
            variation_branches if variation_branches else [],
            board_size,
        )
        mapped_parts.append(f"(Variation)\n{mapped_var}")

    root_comment = "\n".join(mapped_parts)

    # --- Infer PL from actual first move ---
    actual_player = Color.BLACK
    if correct_moves:
        actual_player = correct_moves[0][0]

    # --- Structural validation ---
    warnings = _validate_moves(
        correct_moves, wrong_branches, variation_branches,
        player_to_move=actual_player,
    )
    result.validation_warnings = warnings

    # --- Gate: skip output for critically broken puzzles ---
    if has_critical_warnings(warnings):
        log.warning(
            "Skipping #%d %s — critical validation failures: %s",
            entry.problem_number, level, ", ".join(warnings),
        )
        result.error = f"Critical validation: {', '.join(warnings)}"
        return result

    # --- Build full tree ---
    result.sgf = build_solution_tree(
        setup_pos=problem_pos,
        correct_moves=correct_moves,
        wrong_branches=wrong_branches,
        variation_branches=variation_branches,
        player_to_move=actual_player,
        board_size=board_size,
        comment=root_comment,
    )
    result.correct_move_count = len(correct_moves)
    result.wrong_branch_count = len(wrong_branches)
    result.variation_branch_count = len(variation_branches)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    log.debug(
        "Built #%d %s: %d correct, %d wrong, %d var, %d warnings (%.0fms)",
        entry.problem_number, level,
        result.correct_move_count, result.wrong_branch_count,
        result.variation_branch_count, len(warnings), elapsed_ms,
    )

    return result
