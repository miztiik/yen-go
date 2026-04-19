"""
Backfill utilities for existing SGF files.

Functions:
- backfill_yl: Rewrite YL[] in qday SGFs from telemetry logs
- backfill_annotations: Fix solution tree annotations (TE[1]/BM[1] on
  first moves only, strip C[Correct]/C[Wrong] from continuations)

Usage:
    python -m tools.weiqi101 backfill-yl --dry-run
    python -m tools.weiqi101 backfill-annotations --dry-run
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from ._local_collections_mapping import resolve_book_slug

logger = logging.getLogger("101weiqi.backfill")

# Regex to extract puzzle_id from qday filename: YYYYMMDD-N-PUZZLEID.sgf
_QDAY_FILENAME_RE = re.compile(r"^\d{8}-\d+-(\d+)\.sgf$")

# Regex to match YL[...] property in SGF (non-greedy, single property)
_YL_PROPERTY_RE = re.compile(r"YL\[[^\]]*\]")

# Regex to parse TELEM OK log lines for puzzle_id and books
_TELEM_PUZZLE_RE = re.compile(r"puzzle=(\d+)")
_TELEM_BOOKS_RE = re.compile(r"books=\[([^\]]+)\]")
_TELEM_BOOK_ENTRY_RE = re.compile(r"(\d+):")


def parse_telemetry_books(log_dir: Path) -> dict[int, list[int]]:
    """Parse JSONL telemetry logs to build puzzle_id -> [book_id, ...] mapping.

    Only entries with `books=[...]` in the TELEM OK line are included.

    Returns:
        Dict mapping puzzle_id to list of book_ids.
    """
    puzzle_books: dict[int, list[int]] = {}

    for log_file in sorted(log_dir.glob("*.jsonl")):
        with log_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = record.get("message", "")
                if "[TELEM]" not in msg or " OK " not in msg:
                    continue

                # Extract puzzle_id
                puzzle_match = _TELEM_PUZZLE_RE.search(msg)
                if not puzzle_match:
                    continue
                puzzle_id = int(puzzle_match.group(1))

                # Extract books (only if present)
                books_match = _TELEM_BOOKS_RE.search(msg)
                if not books_match:
                    continue

                # Parse book IDs from "id:name,id:name,..." format
                books_str = books_match.group(1)
                book_ids = [
                    int(m.group(1))
                    for m in _TELEM_BOOK_ENTRY_RE.finditer(books_str)
                ]
                if book_ids:
                    # Later log entries override earlier ones for same puzzle
                    puzzle_books[puzzle_id] = book_ids

    return puzzle_books


def backfill_yl(
    qday_dir: Path,
    log_dir: Path,
    dry_run: bool = False,
) -> dict[str, int]:
    """Backfill YL[] in existing qday SGFs from telemetry logs.

    Args:
        qday_dir: Path to qday directory (e.g., external-sources/101weiqi/qday).
        log_dir: Path to logs directory (e.g., external-sources/101weiqi/logs).
        dry_run: If True, show what would change without modifying files.

    Returns:
        Stats dict with keys: updated, removed, unchanged, errors.
    """
    stats = {"updated": 0, "removed": 0, "unchanged": 0, "errors": 0, "total": 0}

    # Step 1: Parse telemetry logs
    puzzle_books = parse_telemetry_books(log_dir)
    logger.info(f"Parsed {len(puzzle_books)} puzzles with book data from telemetry logs")
    print(f"Telemetry: {len(puzzle_books)} puzzles with book data")

    # Step 2: Scan all qday SGFs
    sgf_files = sorted(qday_dir.rglob("*.sgf"))
    stats["total"] = len(sgf_files)
    print(f"SGF files: {len(sgf_files)} in {qday_dir}")

    for sgf_path in sgf_files:
        # Extract puzzle_id from filename
        name_match = _QDAY_FILENAME_RE.match(sgf_path.name)
        if not name_match:
            logger.warning(f"Skipping non-qday filename: {sgf_path.name}")
            stats["errors"] += 1
            continue

        puzzle_id = int(name_match.group(1))

        try:
            content = sgf_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {sgf_path}: {e}")
            stats["errors"] += 1
            continue

        # Determine new YL value
        book_ids = puzzle_books.get(puzzle_id)
        if book_ids:
            # Resolve book IDs to slugs (skip unknown books)
            slugs = []
            for bid in book_ids:
                slug = resolve_book_slug(bid)
                if slug and slug not in slugs:
                    slugs.append(slug)

            if slugs:
                new_yl = f"YL[{','.join(slugs)}]"
                if _YL_PROPERTY_RE.search(content):
                    new_content = _YL_PROPERTY_RE.sub(new_yl, content)
                else:
                    # Insert YL before the closing ) of root node
                    new_content = content.replace(")\n", f"{new_yl})\n", 1)
                action = "updated"
            else:
                # All books unknown — remove YL
                new_content = _YL_PROPERTY_RE.sub("", content)
                action = "removed"
        else:
            # No book data — remove YL entirely
            new_content = _YL_PROPERTY_RE.sub("", content)
            action = "removed"

        if new_content == content:
            stats["unchanged"] += 1
            continue

        if dry_run:
            old_yl = _YL_PROPERTY_RE.search(content)
            old_str = old_yl.group(0) if old_yl else "(none)"
            new_yl_match = _YL_PROPERTY_RE.search(new_content)
            new_str = new_yl_match.group(0) if new_yl_match else "(removed)"
            print(f"  [{action}] {sgf_path.name}: {old_str} -> {new_str}")
        else:
            try:
                sgf_path.write_text(new_content, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to write {sgf_path}: {e}")
                stats["errors"] += 1
                continue

        stats[action] = stats.get(action, 0) + 1

    return stats


# ---------------------------------------------------------------------------
# Annotation backfill: TE[1]/BM[1] on first moves, strip from continuations
# ---------------------------------------------------------------------------

# Match a move node: ;B[xy] or ;W[xy] followed by optional properties
_MOVE_RE = re.compile(
    r"(;[BW]\[[a-z]{2}\])"   # group 1: the move itself
    r"((?:[A-Z]+\[[^\]]*\])*)"  # group 2: properties after the move
)


def _fix_annotations(content: str) -> str:
    """Rewrite solution tree annotations in an SGF string.

    Rules:
    - First move after ``(`` or the very first move in the solution
      tree: keep ``C[Correct]``/``C[Wrong]`` and add ``TE[1]``/``BM[1]``
    - Continuation moves: strip ``C[Correct]``/``C[Wrong]`` entirely

    Preserves all other C[] comments (teaching text, root comment).
    """
    # Find the start of the solution tree (after setup stones AB/AW)
    # The root node ends and the solution tree starts at the first ;B or ;W
    # after the root properties.

    # Strategy: walk through the content character by character tracking
    # whether the next move is a "variation start" (after '(' or the first
    # move in the file after setup).

    result: list[str] = []
    i = 0
    n = len(content)
    # Track if the next move we see is a variation start
    next_is_variation_start = True
    # Track if we're past the root node (inside solution tree)
    in_solution_tree = False
    # Count depth — we enter solution tree on the first move after root
    root_props_ended = False

    while i < n:
        # Detect transition into solution tree: first ;B[ or ;W[ with a move
        if not in_solution_tree:
            if content[i] == ';' and i + 1 < n and content[i + 1] in 'BW':
                # Check if this is a move (;B[xy]) not a setup (AB[...])
                if i + 2 < n and content[i + 2] == '[':
                    in_solution_tree = True
                    next_is_variation_start = True

        if in_solution_tree and content[i] == '(':
            result.append('(')
            next_is_variation_start = True
            i += 1
            continue

        if in_solution_tree and content[i] == ')':
            result.append(')')
            i += 1
            continue

        # Match a move node
        if in_solution_tree and content[i] == ';':
            m = _MOVE_RE.match(content, i)
            if m:
                move_part = m.group(1)  # ;B[xy]
                props_part = m.group(2)  # C[Correct]TE[1] etc.

                if next_is_variation_start:
                    # This is a variation start — ensure TE[1]/BM[1] + C[Correct/Wrong]
                    props_part = _ensure_first_move_markers(props_part)
                    next_is_variation_start = False
                else:
                    # Continuation — strip C[Correct]/C[Wrong] only
                    props_part = _strip_correctness_comment(props_part)

                result.append(move_part)
                result.append(props_part)
                i = m.end()
                continue

        result.append(content[i])
        i += 1

    return "".join(result)


def _ensure_first_move_markers(props: str) -> str:
    """Ensure first-move markers: TE[1]+C[Correct] or BM[1]+C[Wrong].

    If C[Correct] present but no TE[1] → add TE[1].
    If C[Wrong] present but no BM[1] → add BM[1].
    If already has TE[1]/BM[1] → leave as-is.
    """
    has_correct = "C[Correct]" in props
    has_wrong = "C[Wrong]" in props
    has_te = "TE[1]" in props
    has_bm = "BM[1]" in props

    if has_correct and not has_te:
        # Add TE[1] before C[Correct]
        props = props.replace("C[Correct]", "TE[1]C[Correct]")
    elif has_wrong and not has_bm:
        # Add BM[1] before C[Wrong]
        props = props.replace("C[Wrong]", "BM[1]C[Wrong]")

    return props


def _strip_correctness_comment(props: str) -> str:
    """Remove C[Correct] and C[Wrong] from continuation move properties.

    Also removes any existing TE[1]/BM[1] from continuations.
    Preserves other C[] comments (teaching text).
    """
    props = props.replace("TE[1]", "")
    props = props.replace("BM[1]", "")
    props = props.replace("C[Correct]", "")
    props = props.replace("C[Wrong]", "")
    return props


def backfill_annotations(
    sgf_dirs: list[Path],
    dry_run: bool = False,
) -> dict[str, int]:
    """Fix solution tree annotations in existing SGF files.

    Adds TE[1]/BM[1] to first moves of each variation, strips
    C[Correct]/C[Wrong] from continuation moves.

    Args:
        sgf_dirs: List of directories to scan for SGF files.
        dry_run: If True, show what would change without modifying files.

    Returns:
        Stats dict with keys: fixed, unchanged, errors, total.
    """
    stats = {"fixed": 0, "unchanged": 0, "errors": 0, "total": 0}

    for sgf_dir in sgf_dirs:
        if not sgf_dir.exists():
            logger.warning(f"Directory not found: {sgf_dir}")
            continue

        sgf_files = sorted(sgf_dir.rglob("*.sgf"))
        for sgf_path in sgf_files:
            stats["total"] += 1

            try:
                content = sgf_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read {sgf_path}: {e}")
                stats["errors"] += 1
                continue

            new_content = _fix_annotations(content)

            if new_content == content:
                stats["unchanged"] += 1
                continue

            if dry_run:
                # Count how many C[Correct]/C[Wrong] were removed
                old_count = content.count("C[Correct]") + content.count("C[Wrong]")
                new_count = new_content.count("C[Correct]") + new_content.count("C[Wrong]")
                removed = old_count - new_count
                te_added = new_content.count("TE[1]") - content.count("TE[1]")
                bm_added = new_content.count("BM[1]") - content.count("BM[1]")
                print(
                    f"  {sgf_path.name}: "
                    f"-{removed} comments, +{te_added} TE[1], +{bm_added} BM[1]"
                )
            else:
                try:
                    sgf_path.write_text(new_content, encoding="utf-8")
                except Exception as e:
                    logger.error(f"Failed to write {sgf_path}: {e}")
                    stats["errors"] += 1
                    continue

            stats["fixed"] += 1

    return stats
