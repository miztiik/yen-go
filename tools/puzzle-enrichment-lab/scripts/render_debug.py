"""Temporary debug script — render 14_net at all 3 pipeline stages."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from analyzers.ascii_board import render_ascii, render_sgf_ascii
from analyzers.frame_adapter import apply_frame
from core.tsumego_analysis import extract_position, parse_sgf
from models.position import Color

COL_LETTERS = "ABCDEFGHJKLMNOPQRST"

original_sgf = (
    "(;SZ[19]FF[4]GM[1]PL[B]"
    "AB[kd][ld][md][nd][oc][pb][pc][pd][pe][qf][qg]"
    "AW[jc][kc][lc][lf][nb][nc][od][oe][oh][pf][pg][qc][qd][qe][qh][rg])"
)

# ── 1. ORIGINAL ──────────────────────────────────────────────────────────
print("=" * 60)
print("1. ORIGINAL POSITION  (14_net — 27 stones)")
print("=" * 60)
print(render_sgf_ascii(original_sgf))

# ── 2. FRAMED ────────────────────────────────────────────────────────────
root = parse_sgf(original_sgf)
position = extract_position(root)
frame_result = apply_frame(position, margin=2, ko=False)
framed = frame_result.position

print()
print("=" * 60)
print(f"2. FRAMED POSITION  ({len(framed.stones)} stones — border fill applied)")
print("=" * 60)
print(render_ascii(framed))

# ── 3. FRAMED + ALLOWED MOVES overlay ────────────────────────────────────
region_moves = position.get_puzzle_region_moves(margin=2)

def gtp_to_xy(gtp, board_size):
    x = COL_LETTERS.index(gtp[0])
    y = board_size - int(gtp[1:])
    return x, y

size = framed.board_size
stone_map = {(s.x, s.y): s.color for s in framed.stones}
allowed_xy = {gtp_to_xy(m, size) for m in region_moves}

print()
print("=" * 60)
print(f"3. FRAMED + ALLOWED MOVES  (* = allowed move, {len(region_moves)} coords)")
print("=" * 60)

col_labels = "   " + " ".join(COL_LETTERS[c] for c in range(size))
print(col_labels)
occupied_by_frame = 0
for y in range(size):
    row_num = size - y
    cells = []
    for x in range(size):
        color = stone_map.get((x, y))
        if color == Color.BLACK:
            if (x, y) in allowed_xy:
                cells.append("#")  # Frame stone occupying an allowed coord
                occupied_by_frame += 1
            else:
                cells.append("X")
        elif color == Color.WHITE:
            if (x, y) in allowed_xy:
                cells.append("#")  # Frame stone occupying an allowed coord
                occupied_by_frame += 1
            else:
                cells.append("O")
        elif (x, y) in allowed_xy:
            cells.append("*")
        else:
            cells.append(".")
    print(f"{row_num:2d} {' '.join(cells)} {row_num}")
print(col_labels)
playable = len(region_moves) - occupied_by_frame
print()
print(f"OVERLAP STATS: {len(region_moves)} total allowed_moves coords")
print(f"  Playable (empty):     {playable}")
print(f"  Occupied by frame (#): {occupied_by_frame}")
print(f"  Overlap rate:          {100 * occupied_by_frame / len(region_moves):.1f}%")
print("To move: Black (X)")
print()
print("Legend:  X=Black  O=White  *=Allowed move (KataGo whitelist)  .=Frame border area")
