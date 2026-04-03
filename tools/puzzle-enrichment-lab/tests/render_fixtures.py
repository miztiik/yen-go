"""Render all perf fixture SGFs as ASCII boards for Go expert review.

NOTE: This is a standalone utility script, NOT a pytest test module.
Run directly: ``python tests/render_fixtures.py``
It lives in tests/ because it operates on test fixtures.
"""

# Guard against accidental pytest collection
__test__ = False

import re
from pathlib import Path

# Shared SGF parsing utilities (deduped from render_fixtures + generate_review_report)
from _sgf_render_utils import parse_all_stones, parse_sgf_properties

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "perf-33"


def parse_stones(prop_val: str) -> list[tuple[int, int]]:
    """Parse AB[] or AW[] stone list: AB[aa][bb][cc] -> [(0,0),(1,1),(2,2)]."""
    coords = re.findall(r'\[([a-s]{2})\]', prop_val)
    # But we need to re-parse from the full SGF since AB can have multiple []
    return [(ord(c[0]) - ord('a'), ord(c[1]) - ord('a')) for c in coords]


def render_ascii_board(size: int, black: list, white: list,
                       first_move: tuple[str, tuple] | None = None) -> str:
    """Render a Go board as ASCII art."""
    board = [['.' for _ in range(size)] for _ in range(size)]

    for x, y in black:
        if 0 <= x < size and 0 <= y < size:
            board[y][x] = 'X'

    for x, y in white:
        if 0 <= x < size and 0 <= y < size:
            board[y][x] = 'O'

    # Mark the correct first move
    if first_move and first_move[1]:
        color, (fx, fy) = first_move
        if 0 <= fx < size and 0 <= fy < size:
            if board[fy][fx] == '.':
                board[fy][fx] = '*'  # Mark correct move

    lines = []
    # Column headers
    col_labels = "ABCDEFGHJKLMNOPQRST"[:size]
    lines.append("   " + " ".join(col_labels))

    for y in range(size):
        row_num = size - y
        row_str = f"{row_num:2d} "
        for x in range(size):
            row_str += board[y][x] + " "
        row_str += f"{row_num}"
        lines.append(row_str)

    lines.append("   " + " ".join(col_labels))
    return "\n".join(lines)


def count_liberties(board: list[list[str]], size: int, x: int, y: int,
                    color: str, visited: set) -> int:
    """Count liberties of a group containing the stone at (x,y)."""
    if (x, y) in visited:
        return 0
    visited.add((x, y))

    liberties = 0
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < size and 0 <= ny < size:
            if board[ny][nx] == '.':
                liberties += 1
            elif board[ny][nx] == color and (nx, ny) not in visited:
                liberties += count_liberties(board, size, nx, ny, color, visited)
    return liberties


def check_zero_liberty_groups(size: int, black: list, white: list) -> list[str]:
    """Check for groups with zero liberties (illegal position)."""
    board = [['.' for _ in range(size)] for _ in range(size)]
    for x, y in black:
        if 0 <= x < size and 0 <= y < size:
            board[y][x] = 'X'
    for x, y in white:
        if 0 <= x < size and 0 <= y < size:
            board[y][x] = 'O'

    issues = []
    checked = set()

    for x, y in black:
        if (x, y) not in checked and 0 <= x < size and 0 <= y < size:
            visited = set()
            libs = count_liberties(board, size, x, y, 'X', visited)
            checked.update(visited)
            if libs == 0:
                coords = ", ".join(f"{chr(ord('A') + cx)}{size - cy}"
                                  for cx, cy in sorted(visited))
                issues.append(f"CRITICAL: Black group at {coords} has 0 liberties!")

    checked = set()
    for x, y in white:
        if (x, y) not in checked and 0 <= x < size and 0 <= y < size:
            visited = set()
            libs = count_liberties(board, size, x, y, 'O', visited)
            checked.update(visited)
            if libs == 0:
                coords = ", ".join(f"{chr(ord('A') + cx)}{size - cy}"
                                  for cx, cy in sorted(visited))
                issues.append(f"CRITICAL: White group at {coords} has 0 liberties!")

    return issues


def analyze_fixture(filepath: Path) -> str:
    """Analyze a single fixture and return formatted report."""
    sgf = filepath.read_text(encoding="utf-8").strip()
    props = parse_sgf_properties(sgf)

    size = int(props.get("SZ", "19"))
    black, white = parse_all_stones(sgf)

    # Parse correct first move
    first_color, first_coord = "", None
    # Find the main line first move (first child of root)
    m = re.search(r';([BW])\[([a-s]{2})\]', sgf[sgf.find(';', 1):] if ';' in sgf[1:] else "")
    if m:
        first_color = m.group(1)
        first_coord = (ord(m.group(2)[0]) - ord('a'), ord(m.group(2)[1]) - ord('a'))

    # Determine player to move
    pl = props.get("PL", "")
    if not pl and first_color:
        pl = first_color

    # Count solution variations
    correct_count = sgf.count("RIGHT") + sgf.count("CORRECT") + sgf.count("C[+]")
    wrong_count = sgf.count("WRONG") + sgf.count("BM[")
    total_vars = sgf.count(";B[") + sgf.count(";W[")

    # Check for zero-liberty groups
    lib_issues = check_zero_liberty_groups(size, black, white)

    # Check for stones outside board
    oob_issues = []
    for x, y in black:
        if x >= size or y >= size:
            oob_issues.append(f"Black stone at ({x},{y}) outside {size}x{size} board!")
    for x, y in white:
        if x >= size or y >= size:
            oob_issues.append(f"White stone at ({x},{y}) outside {size}x{size} board!")

    # Build report
    report = []
    report.append(f"{'='*60}")
    report.append(f"FIXTURE: {filepath.name}")
    report.append(f"{'='*60}")
    report.append(f"Source:     {props.get('PC', 'unknown')}")
    report.append(f"Board:      {size}×{size}")
    report.append(f"To play:    {'Black' if pl == 'B' else 'White' if pl == 'W' else '?'}")
    report.append(f"Objective:  {props.get('C', 'not specified')}")
    report.append(f"Level:      {props.get('YG', 'not set')}")
    report.append(f"Tags:       {props.get('YT', 'none')}")
    report.append(f"Collection: {props.get('YL', 'none')}")
    report.append(f"Stones:     B={len(black)}, W={len(white)}")
    report.append(f"Solution:   {correct_count} correct lines, {wrong_count} marked wrong, ~{total_vars} total moves")

    if first_coord:
        col = chr(ord('A') + first_coord[0])
        if first_coord[0] >= 8:  # Skip 'I' in Go coordinates
            col = chr(ord('A') + first_coord[0] + 1)
        row = size - first_coord[1]
        report.append(f"1st move:   {first_color}[{chr(ord('a')+first_coord[0])}{chr(ord('a')+first_coord[1])}] = {col}{row} (marked * on board)")

    report.append("")
    report.append(render_ascii_board(size, black, white,
                                      (first_color, first_coord) if first_coord else None))
    report.append("")

    if lib_issues or oob_issues:
        report.append("ISSUES FOUND:")
        for issue in lib_issues + oob_issues:
            report.append(f"  !! {issue}")
    else:
        report.append("No structural issues detected (all groups have liberties, all stones on board)")

    report.append("")
    return "\n".join(report)


def main():
    files = sorted(FIXTURES.glob("*.sgf"))
    print(f"Found {len(files)} fixture files in {FIXTURES}\n")

    all_issues = []
    for f in files:
        report = analyze_fixture(f)
        print(report)
        # Collect issues
        if "CRITICAL" in report:
            all_issues.append((f.name, [line for line in report.split("\n") if "CRITICAL" in line]))

    print("=" * 60)
    print(f"SUMMARY: {len(files)} fixtures analyzed")
    if all_issues:
        print(f"\nFIXTURES WITH ISSUES ({len(all_issues)}):")
        for name, issues in all_issues:
            print(f"  {name}:")
            for i in issues:
                print(f"    {i.strip()}")
    else:
        print("\nAll fixtures passed structural checks.")


if __name__ == "__main__":
    main()
