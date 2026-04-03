"""Render first 6 fixtures only."""
import glob
import os
import re


def parse_sgf_properties(sgf_text):
    props = {}
    for m in re.finditer(r'([A-Z]+)\[([^\]]*)\]', sgf_text):
        key, val = m.group(1), m.group(2)
        if key not in props:
            props[key] = val
    return props

def parse_all_stones(sgf_text):
    black, white = [], []
    for m in re.finditer(r'AB((?:\[[a-z]{2}\])+)', sgf_text):
        for s in re.finditer(r'\[([a-z]{2})\]', m.group(0)):
            black.append(s.group(1))
    for m in re.finditer(r'AW((?:\[[a-z]{2}\])+)', sgf_text):
        for s in re.finditer(r'\[([a-z]{2})\]', m.group(0)):
            white.append(s.group(1))
    return black, white

def sgf_to_xy(coord, size):
    col = ord(coord[0]) - ord('a')
    row = size - 1 - (ord(coord[1]) - ord('a'))
    return col, row

def col_label(c):
    return chr(ord('A') + c + (1 if c >= 8 else 0))

def render(sgf_text, size):
    parse_sgf_properties(sgf_text)
    black_stones, white_stones = parse_all_stones(sgf_text)
    first_move = None
    semicolons = [i for i, ch in enumerate(sgf_text) if ch == ';']
    if len(semicolons) >= 2:
        after_root = sgf_text[semicolons[1]:]
        m = re.search(r'[BW]\[([a-z]{2})\]', after_root)
        if m:
            first_move = m.group(1)

    board = [['.' for _ in range(size)] for _ in range(size)]
    for s in black_stones:
        c, r = sgf_to_xy(s, size)
        if 0 <= c < size and 0 <= r < size:
            board[r][c] = 'X'
    for s in white_stones:
        c, r = sgf_to_xy(s, size)
        if 0 <= c < size and 0 <= r < size:
            board[r][c] = 'O'
    if first_move:
        c, r = sgf_to_xy(first_move, size)
        if 0 <= c < size and 0 <= r < size:
            board[r][c] = '*'

    header = '   ' + ' '.join(col_label(c) for c in range(size))
    lines = [header]
    for row in range(size):
        rn = size - row
        prefix = f'{rn:2d} '
        suffix = f' {rn}'
        lines.append(prefix + ' '.join(board[row]) + suffix)
    lines.append(header)
    return '\n'.join(lines)

fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures', 'perf-10')
files = sorted(glob.glob(os.path.join(fixture_dir, '*.sgf')))[:6]
for f in files:
    name = os.path.basename(f)
    with open(f) as fh:
        sgf = fh.read()
    props = parse_sgf_properties(sgf)
    size = int(props.get('SZ', '19'))
    board_str = render(sgf, size)
    pl = props.get('PL', 'B')
    pc = props.get('PC', '?')
    obj = props.get('GC', '?')
    print(f'=== {name} ===')
    print(f'SZ:{size}  PL:{pl}  Source:{pc}')
    print(f'Objective: {obj}')
    print(board_str)
    print()
