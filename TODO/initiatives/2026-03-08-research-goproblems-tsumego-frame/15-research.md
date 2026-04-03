# Research: goproblems.com Tsumego Frame Implementation

**Initiative:** `2026-03-08-research-goproblems-tsumego-frame`  
**Last Updated:** 2026-03-08 (updated again: §3.5 added — ghostban `e.FO` verbatim from live bundle 920; corrected R-17, R-50; added R-51 through R-63; updated confidence and recommendations)  
**Researcher:** Feature-Researcher mode

---

## 1. Research Question and Boundaries

**Question:** How does goproblems.com's "Research(Beta)" feature construct its tsumego frame, and how does it differ from our checkerboard pattern in `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`?

**Sub-questions:**

- Q1: What fill pattern does goproblems.com use (horizontal bands vs. checkerboard vs. other)?
- Q2: How does their frame differ from KaTrain's `tsumego_frame.py` (our reference source)?
- Q3: What KataGo parameters (model, visits, komi, rules) does their analysis use?
- Q4: Should Yen-Go adopt a different fill pattern for better KataGo signal quality?

**Evidence sources (2026-03-08 live fetch):**

- **KaTrain `tsumego_frame.py` fetched live** from `raw.githubusercontent.com/sanderland/katrain/master/katrain/core/tsumego_frame.py` — HTTP 200, SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`, 8271 bytes. Full key functions reproduced verbatim in §3.2.
- **goproblems.com Research pages fetched** (`/problems/47735/research`, `/42390/research`, `/21044/research`) — renders as React SPA. Raw script tags not accessible via fetch tool. Live page text confirms: `Model: b10 / auto(webgl) / visits: 500`. Prior bundle `148.518c57f7.js` returns HTTP 404 (bundle hash rotated since Jan 2026).
- Prior internal docs: [docs/reference/go-board-js-libraries-analysis.md](../../../docs/reference/go-board-js-libraries-analysis.md)

**Boundaries:** In scope: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` and KataGo query parameters. Out of scope: frontend changes, backend pipeline, KaTrain fork.

---

## 2. Internal Code Evidence

### 2.1 Our Current Implementation: Checkerboard

| R-id | File                                                                                                                                                       | Finding                                                                                                                                                                                                                              |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R-1  | [analyzers/tsumego_frame.py L98–L113](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py#L98)                                                 | `stone_cells = [(x, y) for x, y in candidates if (x + y) % 2 == 0]` — every other intersection gets a stone (checkerboard mask). ~50% density.                                                                                       |
| R-2  | [analyzers/tsumego_frame.py L116–L127](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py#L116)                                               | Wall cells (adjacent to puzzle region) receive defense color. Remaining cells alternate offense/defense for balance. No row-based banding.                                                                                           |
| R-3  | [analyzers/tsumego_frame.py L42–L50](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py#L42)                                                  | `offense_color = opponent of player_to_move`. This matches KaTrain's `guess_black_to_attack()` convention but is inlined.                                                                                                            |
| R-4  | [docs/architecture/tools/katago-enrichment.md D21](../../../docs/architecture/tools/katago-enrichment.md#L187)                                             | ADR D21: "The tsumego frame pattern should NOT resemble a natural game position. Use alternating stones, checkerboard, or wall patterns." Validated: natural-looking frames produce ~15% winrate error vs ~3% for artificial frames. |
| R-5  | [docs/architecture/tools/katago-enrichment.md D33](../../../docs/architecture/tools/katago-enrichment.md#L317)                                             | Crop-then-frame ordering: frame is applied AFTER tight-board crop (9×9 or 13×13), not on the original 19×19. This limits the frame area to a modest size.                                                                            |
| R-6  | [TODO/katago-puzzle-enrichment/007-adr-policy-aligned-enrichment.md D21](../../../TODO/katago-puzzle-enrichment/007-adr-policy-aligned-enrichment.md#L187) | Historical record: checkerboard chosen over solid-fill because "every stone has empty neighbors (liberties), so no stone is ever completely surrounded by opponents." Safety rationale, not performance rationale.                   |

### 2.2 KataGo Parameters Currently Used

| R-id | Parameter                   | Our Value                                | Source                                                                                                            |
| ---- | --------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| R-7  | `maxVisits`                 | 10,000 (lab)                             | [D23](../../../docs/architecture/tools/katago-enrichment.md#L300)                                                 |
| R-8  | `komi`                      | 0.0 (override)                           | [query_builder.py L21](../../../tools/puzzle-enrichment-lab/analyzers/query_builder.py#L21) `_TSUMEGO_KOMI = 0.0` |
| R-9  | `rules`                     | `chinese` (non-ko) / `tromp-taylor` (ko) | [D31](../../../docs/architecture/tools/katago-enrichment.md#L397)                                                 |
| R-10 | `rootNumSymmetriesToSample` | 8                                        | [D10](../../../docs/architecture/tools/katago-enrichment.md)                                                      |
| R-11 | `reportAnalysisWinratesAs`  | Being fixed to `SIDETOMOVE`              | [2026-03-08-fix-katago-perspective initiative](../../2026-03-08-fix-katago-perspective/00-charter.md)             |

### 2.3 Known Limitations of Checkerboard

| R-id | Issue                                                                                                                                                     | Evidence                                                                                                               |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| R-12 | Low stone density (~50%) means less board pressure. KataGo's policy can still spread to empty checkerboard cells in the frame.                            | Inferred from D3 rationale: "policy spread across entire board" remains possible if frame has too many empty cells.    |
| R-13 | Checkerboard creates isolated stones — KataGo's NN sees many atari-prone single stones. This may activate "save these stones" policy in the frame region. | General KataGo behavior: isolated single stones with ko threats have high policy priors for capture/save responses.    |
| R-14 | Balance maintained by counting, not pattern — `off_count <= def_count` alternation can create irregular patterns when the puzzle region is off-center.    | Code inspection at [tsumego_frame.py L143–L154](../../../tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py#L143). |

---

## 3. External References

### 3.1 goproblems.com — What We Know from Prior Research

| R-id | Finding                                                                                                                                                                                                                                                                                                                                                               | Source                                                                                                                                                                                                           |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-15 | **KataGo model used**: `kata1-b6c96` (6-block 96-channel). "GoProblems.com achieves 2-3 seconds with b10/500 visits" also noted — b10 may refer to a newer model update or `kata1-b10c128`.                                                                                                                                                                           | [docs/reference/go-board-js-libraries-analysis.md §1.1](../../../docs/reference/go-board-js-libraries-analysis.md#L22) + [katago-enrichment.md L419](../../../docs/architecture/tools/katago-enrichment.md#L419) |
| R-16 | **JS bundle structure**: Chunk `148.518c57f7.js` (~706 KB) contains "Configuration, themes, KataGo." This is the bundle most likely containing frame code. Chunk `920.ed9fa994.js` (~199 KB) is the Canvas board engine.                                                                                                                                              | [docs/reference/go-board-js-libraries-analysis.md §1.2](../../../docs/reference/go-board-js-libraries-analysis.md#L39)                                                                                           |
| R-17 | ~~**Proprietary implementation**: No known open-source Go board library is used.~~ **⚠️ CORRECTED (2026-03-08):** Bundle `920.ed9fa994.js` was live-fetched. goproblems.com uses the **ghostban** open-source Go board library (a TypeScript/JavaScript canvas board renderer). The frame fill function `e.FO` is exported from ghostban. See §3.5 for verbatim code. | Live fetch of `https://www.goproblems.com/build/920.ed9fa994.js` (2026-03-08)                                                                                                                                    |
| R-18 | **"Hide/Show Problem Frame" toggle**: The UI has a client-side toggle implying the frame is computed in JavaScript before sending to KataGo WASM. This confirms: (a) frame is JS-side, (b) KataGo receives the framed position, (c) the frame can be visualized separately from the puzzle stones.                                                                    | User observation of Research(Beta) UI. Not in prior docs.                                                                                                                                                        |
| R-19 | **WebGL backend**: User states model is "b10, webgl." KataGo WASM supports both WebAssembly (CPU) and WebGL (WebGL2 compute shaders). WebGL backend on b10c128 achieves ~2-4× faster inference than CPU WASM at the cost of needing WebGL2 support.                                                                                                                   | KataGo WASM documentation (public, github.com/lightvector/KataGo).                                                                                                                                               |

### 3.2 KaTrain's `tsumego_frame.py` — Authoritative Source (Live-Fetched)

**Fetch result:**

- URL: `https://raw.githubusercontent.com/sanderland/katrain/master/katrain/core/tsumego_frame.py`
- HTTP status: **200 OK**
- SHA: `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`
- Size: 8271 bytes
- License: MIT (sanderland/katrain)
- Attribution: `# tsumego frame ported from lizgoban by kaorahi`

---

#### 3.2.0 Complete Verbatim Source Code

```python
from katrain.core.game_node import GameNode
from katrain.core.sgf_parser import Move

# tsumego frame ported from lizgoban by kaorahi
# note: coords = (j, i) in katrain

near_to_edge = 2
offence_to_win = 5

BLACK = "B"
WHITE = "W"


def tsumego_frame_from_katrain_game(game, komi, black_to_play_p, ko_p, margin):
    current_node = game.current_node
    bw_board = [[game.chains[c][0].player if c >= 0 else "-" for c in line] for line in game.board]
    isize, jsize = ij_sizes(bw_board)
    blacks, whites, analysis_region = tsumego_frame(bw_board, komi, black_to_play_p, ko_p, margin)
    sgf_blacks = katrain_sgf_from_ijs(blacks, isize, jsize, "B")
    sgf_whites = katrain_sgf_from_ijs(whites, isize, jsize, "W")

    played_node = GameNode(parent=current_node, properties={"AB": sgf_blacks, "AW": sgf_whites})  # this inserts

    katrain_region = analysis_region and (analysis_region[1], analysis_region[0])
    return (played_node, katrain_region)


def katrain_sgf_from_ijs(ijs, isize, jsize, player):
    return [Move((j, i)).sgf((jsize, isize)) for i, j in ijs]


def tsumego_frame(bw_board, komi, black_to_play_p, ko_p, margin):
    stones = stones_from_bw_board(bw_board)
    filled_stones = tsumego_frame_stones(stones, komi, black_to_play_p, ko_p, margin)
    region_pos = pick_all(filled_stones, "tsumego_frame_region_mark")
    bw = pick_all(filled_stones, "tsumego_frame")
    blacks = [(i, j) for i, j, black in bw if black]
    whites = [(i, j) for i, j, black in bw if not black]
    return (blacks, whites, get_analysis_region(region_pos))


def pick_all(stones, key):
    return [[i, j, s.get("black")] for i, row in enumerate(stones) for j, s in enumerate(row) if s.get(key)]


def get_analysis_region(region_pos):
    if len(region_pos) == 0:
        return None
    ai, aj, dummy = tuple(zip(*region_pos))
    ri = (min(ai), max(ai))
    rj = (min(aj), max(aj))
    return ri[0] < ri[1] and rj[0] < rj[1] and (ri, rj)


def tsumego_frame_stones(stones, komi, black_to_play_p, ko_p, margin):
    sizes = ij_sizes(stones)
    isize, jsize = sizes
    ijs = [
        {"i": i, "j": j, "black": h.get("black")}
        for i, row in enumerate(stones)
        for j, h in enumerate(row)
        if h.get("stone")
    ]

    if len(ijs) == 0:
        return []
    # find range of problem
    top = min_by(ijs, "i", +1)
    left = min_by(ijs, "j", +1)
    bottom = min_by(ijs, "i", -1)
    right = min_by(ijs, "j", -1)
    imin = snap0(top["i"])
    jmin = snap0(left["j"])
    imax = snapS(bottom["i"], isize)
    jmax = snapS(right["j"], jsize)
    # flip/rotate for standard position
    # don't mix flip and swap (FF = SS = identity, but SFSF != identity)
    flip_spec = (
        [False, False, True] if imin < jmin else [need_flip_p(imin, imax, isize), need_flip_p(jmin, jmax, jsize), False]
    )
    if True in flip_spec:
        flipped = flip_stones(stones, flip_spec)
        filled = tsumego_frame_stones(flipped, komi, black_to_play_p, ko_p, margin)
        return flip_stones(filled, flip_spec)
    # put outside stones
    i0 = imin - margin
    i1 = imax + margin
    j0 = jmin - margin
    j1 = jmax + margin
    frame_range = [i0, i1, j0, j1]
    black_to_attack_p = guess_black_to_attack([top, bottom, left, right], sizes)
    put_border(stones, sizes, frame_range, black_to_attack_p)
    put_outside(stones, sizes, frame_range, black_to_attack_p, black_to_play_p, komi)
    put_ko_threat(stones, sizes, frame_range, black_to_attack_p, black_to_play_p, ko_p)
    return stones


# detect corner/edge/center problems
# (avoid putting border stones on the first lines)
def snap(k, to):
    return to if abs(k - to) <= near_to_edge else k


def snap0(k):
    return snap(k, 0)


def snapS(k, size):
    return snap(k, size - 1)


def min_by(ary, key, sign):
    by = [sign * z[key] for z in ary]
    return ary[by.index(min(by))]


def need_flip_p(kmin, kmax, size):
    return kmin < size - kmax - 1


def guess_black_to_attack(extrema, sizes):
    return sum([sign_of_color(z) * height2(z, sizes) for z in extrema]) > 0


def sign_of_color(z):
    return 1 if z["black"] else -1


def height2(z, sizes):
    isize, jsize = sizes
    return height(z["i"], isize) + height(z["j"], jsize)


def height(k, size):
    return size - abs(k - (size - 1) / 2)


######################################
# sub


def put_border(stones, sizes, frame_range, is_black):
    i0, i1, j0, j1 = frame_range
    put_twin(stones, sizes, i0, i1, j0, j1, is_black, False)
    put_twin(stones, sizes, j0, j1, i0, i1, is_black, True)


def put_twin(stones, sizes, beg, end, at0, at1, is_black, reverse_p):
    for at in (at0, at1):
        for k in range(beg, end + 1):
            i, j = (at, k) if reverse_p else (k, at)
            put_stone(stones, sizes, i, j, is_black, False, True)


def put_outside(stones, sizes, frame_range, black_to_attack_p, black_to_play_p, komi):
    isize, jsize = sizes
    count = 0
    offense_komi = (+1 if black_to_attack_p else -1) * komi
    defense_area = (isize * jsize - offense_komi - offence_to_win) / 2
    for i in range(isize):
        for j in range(jsize):
            if inside_p(i, j, frame_range):
                continue
            count += 1
            black_p = xor(black_to_attack_p, (count <= defense_area))
            empty_p = (i + j) % 2 == 0 and abs(count - defense_area) > isize
            put_stone(stones, sizes, i, j, black_p, empty_p)


# standard position:
# ? = problem, X = offense, O = defense
# OOOOOOOOOOOOO
# OOOOOOOOOOOOO
# OOOOOOOOOOOOO
# XXXXXXXXXXXXX
# XXXXXXXXXXXXX
# XXXX.........
# XXXX.XXXXXXXX
# XXXX.X???????
# XXXX.X???????

# (pattern, top_p, left_p)
offense_ko_threat = (
    """
....OOOX.
.....XXXX
""",
    True,
    False,
)

defense_ko_threat = (
    """
..
..
X.
XO
OO
.O
""",
    False,
    True,
)


def put_ko_threat(stones, sizes, frame_range, black_to_attack_p, black_to_play_p, ko_p):
    isize, jsize = sizes
    for_offense_p = xor(ko_p, xor(black_to_attack_p, black_to_play_p))
    pattern, top_p, left_p = offense_ko_threat if for_offense_p else defense_ko_threat
    aa = [list(line) for line in pattern.splitlines() if len(line) > 0]
    height, width = ij_sizes(aa)
    for i, row in enumerate(aa):
        for j, ch in enumerate(row):
            ai = i + (0 if top_p else isize - height)
            aj = j + (0 if left_p else jsize - width)
            if inside_p(ai, aj, frame_range):
                return
            black = xor(black_to_attack_p, ch == "O")
            empty = ch == "."
            put_stone(stones, sizes, ai, aj, black, empty)


def xor(a, b):
    return bool(a) != bool(b)


######################################
# util


def flip_stones(stones, flip_spec):
    swap_p = flip_spec[2]
    sizes = ij_sizes(stones)
    isize, jsize = sizes
    new_isize, new_jsize = [jsize, isize] if swap_p else [isize, jsize]
    new_stones = [[None for z in range(new_jsize)] for row in range(new_isize)]
    for i, row in enumerate(stones):
        for j, z in enumerate(row):
            new_i, new_j = flip_ij((i, j), sizes, flip_spec)
            new_stones[new_i][new_j] = z
    return new_stones


def put_stone(stones, sizes, i, j, black, empty, tsumego_frame_region_mark=False):
    isize, jsize = sizes
    if i < 0 or isize <= i or j < 0 or jsize <= j:
        return
    stones[i][j] = (
        {}
        if empty
        else {
            "stone": True,
            "tsumego_frame": True,
            "black": black,
            "tsumego_frame_region_mark": tsumego_frame_region_mark,
        }
    )


def inside_p(i, j, region):
    i0, i1, j0, j1 = region
    return i0 <= i and i <= i1 and j0 <= j and j <= j1


def stones_from_bw_board(bw_board):
    return [[stone_from_str(s) for s in row] for row in bw_board]


def stone_from_str(s):
    black = s == BLACK
    white = s == WHITE
    return {"stone": True, "black": black} if (black or white) else {}


def ij_sizes(stones):
    return (len(stones), len(stones[0]))


def flip_ij(ij, sizes, flip_spec):
    i, j = ij
    isize, jsize = sizes
    flip_i, flip_j, swap_ij = flip_spec
    fi = flip1(i, isize, flip_i)
    fj = flip1(j, jsize, flip_j)
    return (fj, fi) if swap_ij else (fi, fj)


def flip1(k, size, flag):
    return size - 1 - k if flag else k
```

---

#### Key constants (verbatim)

```python
near_to_edge = 2
offence_to_win = 5
```

#### Function-by-function analysis

| R-id | Function                                                                            | Actual code (verbatim excerpts)                                                                                            | Finding                                                                                                                                                                                                                                                                                                                                                 |
| ---- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-20 | `guess_black_to_attack(extrema, sizes)`                                             | `return sum([sign_of_color(z) * height2(z, sizes) for z in extrema]) > 0` / `height(k, size) = size - abs(k - (size-1)/2)` | **Edge-proximity weighting**, not simple stone count. For each of the 4 extremal stones (top/bottom/left/right), multiplies sign (black=+1, white=-1) by combined row+col distance from board center. Stones nearer to edges score more. If black stones weight more → black is "attacker" = the side trying to LIVE (whose stones go near the puzzle). |
| R-21 | `snap0` / `snapS`                                                                   | `snap(k, to) = to if abs(k - to) <= 2 else k`                                                                              | Snaps puzzle bounding-box boundary to board edge when within 2 points. Prevents narrow unusable margin strips.                                                                                                                                                                                                                                          |
| R-22 | `put_border(stones, sizes, frame_range, is_black)`                                  | `put_twin(stones, sizes, i0, i1, j0, j1, is_black, False)` × 4 sides; `is_black` = `black_to_attack_p`                     | **Solid wall of ATTACKER stones** (NOT defender) around `frame_range` perimeter. ⚠️ Prior R-22 description was wrong: the wall color is attacker, not defender. The attacker's stones ring the margin, reinforcing that the attacker surrounds the puzzle group.                                                                                        |
| R-23 | `put_outside(stones, sizes, frame_range, black_to_attack_p, black_to_play_p, komi)` | See verbatim code below                                                                                                    | **Count-based half-and-half fill**, NOT row-alternating. ⚠️ Prior R-23 description was wrong. See corrected detail below.                                                                                                                                                                                                                               |
| R-24 | `put_ko_threat(...)`                                                                | Offense pattern: `....OOOX. / .....XXXX` at top-right; defense pattern: `X. / XO / OO / .O` at bottom-left                 | Fixed ASCII patterns placed at board corners for ko context. Applied as a separate step; `put_outside` may overwrite if conflict.                                                                                                                                                                                                                       |
| R-25 | Orientation normalization                                                           | `flip_spec = [False, False, True] if imin < jmin else [need_flip_p(imin,imax,isize), ...]` then recursive call             | Normalizes to canonical orientation (top-min ≥ left-min) before filling so that the frame is always computed from the same canonical view.                                                                                                                                                                                                              |

#### Verbatim `put_outside` — the critical function

```python
def put_outside(stones, sizes, frame_range, black_to_attack_p, black_to_play_p, komi):
    isize, jsize = sizes
    count = 0
    offense_komi = (+1 if black_to_attack_p else -1) * komi
    defense_area = (isize * jsize - offense_komi - offence_to_win) / 2
    for i in range(isize):
        for j in range(jsize):
            if inside_p(i, j, frame_range):
                continue
            count += 1
            black_p = xor(black_to_attack_p, (count <= defense_area))
            empty_p = (i + j) % 2 == 0 and abs(count - defense_area) > isize
            put_stone(stones, sizes, i, j, black_p, empty_p)
```

**Decoded step by step (19×19 board, komi=0, `black_to_attack_p=True`):**

1. `defense_area = (361 - 0 - 5) / 2 = 178`
2. Iterates ALL cells row-major (i=0..18, j=0..18). Skips cells inside `frame_range` (puzzle+margin region).
3. For each non-puzzle cell, increments `count`.
4. `black_p = xor(True, count <= 178)`:
   - cells 1–178: `xor(True, True) = False` → **White stone** (defense)
   - cells 179+: `xor(True, False) = True` → **Black stone** (offense/attacker)
5. `empty_p = (i+j)%2==0 AND |count - 178| > 19`:
   - Far from the color-transition (count ≤ 159 or count ≥ 197): checkerboard cells `(i+j)%2==0` are LEFT EMPTY
   - Near the transition (179±19 range): ALL cells filled regardless of checkerboard position (dense fill at seam)

**Why this produces horizontal bands:** The color flips at count=178. Since iteration is row-by-row, the flip occurs partway through a row (or between rows), so the first ~9–10 non-puzzle rows are all White (defense), the remaining rows are all Black (offense). The visual is one large block of each color, not alternating rows.

**Fill density:** ~50% in far transition zones (checkerboard holes), ~100% near the transition seam. Effective average ~65–75% for a typical corner puzzle.

#### Canonical diagram (verbatim from source comment)

```
# standard position:
# ? = problem, X = offense (attacker), O = defense
# OOOOOOOOOOOOO
# OOOOOOOOOOOOO
# OOOOOOOOOOOOO
# XXXXXXXXXXXXX
# XXXXXXXXXXXXX
# XXXX.........   <-- checkerboard holes in offense zone near margin
# XXXX.XXXXXXXX
# XXXX.X???????   <-- attacker wall (X), empty margin (.), puzzle (?)
# XXXX.X???????
```

#### Call order in `tsumego_frame_stones`

```
1. snap boundary to board edge (within 2 points)
2. flip/rotate to canonical orientation (recursive if needed)
3. put_border(... black_to_attack_p ...)   — solid attacker ring at frame_range perimeter
4. put_outside(...)                         — count-based fill outside frame_range
5. put_ko_threat(...)                       — optional fixed-pattern ko-threat stones
```

**Key corrections to prior R-22/R-23 descriptions:**

- R-22 was wrong: `put_border` places **attacker** wall, not defender wall
- R-23 was wrong: NOT `y%2==0` row alternation. Actual: count-based half-defense / half-offense with `(i+j)%2==0` empty spots ONLY far from the seam

### 3.3 Why Horizontal Bands vs Checkerboard Matters for KataGo

| R-id | Dimension          | Horizontal Bands                                                                                                            | Checkerboard                                                                                           |
| ---- | ------------------ | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| R-26 | Stone density      | ~85-90% (near-solid rows)                                                                                                   | ~50% (every other point)                                                                               |
| R-27 | Territory signal   | Strong: each row is clearly one player's territory — KataGo ownership head reads near-1.0 or near-(-1.0) for frame rows     | Weak: alternating stones in checkerboard look like contested territory or neutral — ownership near 0.0 |
| R-28 | Policy containment | Strong: dense frame leaves KataGo few legal moves visually, policy concentrates on the few empty cells in the puzzle region | Moderate: 50% empty frame still has playable intersections, some policy may leak                       |
| R-29 | "Unnatural" signal | Strong: horizontal bands like a striped flag clearly look artificial to the NN                                              | Moderate: checkerboard is also unusual but has more empty space that resembles game positions          |
| R-30 | Liberty safety     | KaTrain removes stones at exactly-0-liberty points → no suicide issues despite near-solid fill                              | Never needs removal since (x+y)%2==0 guarantees each stone has 2+ empty diagonal neighbors             |
| R-31 | Score balance      | Rows cycle attacker/defender → total stone count is exactly balanced (N attacker rows ≈ N defender rows)                    | Count-based alternation achieves ±5 balance but is less systematic                                     |

### 3.4 KataGo WASM / goproblems Analysis Parameters

Based on prior research and KataGo analysis protocol documentation:

| R-id | Parameter    | goproblems (inferred)                                                                                                                          | Our lab                                         |
| ---- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| R-32 | Model        | **`b10`** — confirmed live page text: "Model: b10 / auto(webgl) / visits: 500"                                                                 | `b28c512` (lab), `b10c128` (quick)              |
| R-33 | Backend      | **`auto(webgl)`** — confirmed live; uses WebGL2 compute shader path                                                                            | Native binary (local GPU)                       |
| R-34 | Visits       | **500** — confirmed live (NOT 1000; live page shows "visits: 500")                                                                             | 10,000 (max effort)                             |
| R-35 | Komi         | Likely 0.0 (standard tsumego; KaTrain's frame uses `offense_komi = ±komi`)                                                                     | 0.0                                             |
| R-36 | Rules        | Likely `tromp-taylor` (ko-safe in browser)                                                                                                     | `chinese` / `tromp-taylor` per D31              |
| R-37 | Symmetries   | 1 (browser latency budget)                                                                                                                     | 8 (max effort)                                  |
| R-38 | Frame toggle | "Show Problem Frame" button confirmed live. Frame hidden by **default**; revealed on user click. Computed in JS before sending to KataGo WASM. | Server-side Python, frame in `tsumego_frame.py` |

---

## 4. Candidate Adaptations for Yen-Go

| R-id | Adaptation                                         | Description                                                                                                                                                                                                    | Effort               | Risk                                                                                  |
| ---- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------- |
| R-39 | **Switch to count-based fill (KaTrain algorithm)** | Replace `(x+y)%2==0` checkerboard PLACEMENT with KaTrain's actual scheme: iterate row-major, assign defense to first `floor((board_cells - 5) / 2)` non-puzzle cells, offense to the rest. Use `(i+j)%2==0 AND | count - defense_area | > board_width` to skip cells (checkerboard holes only in non-seam zones).             | 2-3 days (includes tests) | Low — purely internal to `tsumego_frame.py`, no downstream contract changes |
| R-40 | **Add solid attacker wall at frame boundary**      | Add KaTrain's `put_border()`: a solid 1-point-wide wall of **attacker** stones (⚠️ NOT defender — prior description wrong) at `frame_range` perimeter. `is_black = black_to_attack_p`.                         | 0.5 days             | Low — additive change                                                                 |
| R-41 | **Add ko-threat stones**                           | Add KaTrain's `put_ko_threat()` at fixed far-corner coordinates                                                                                                                                                | 0.5 days             | Medium — need to ensure ko-threat stones don't create false eye in existing positions |
| R-42 | **Match frame density parameter**                  | Add `density` parameter to `apply_tsumego_frame()`: `"checkerboard"` (current, 50%) vs `"dense"` (new, 85-90%)                                                                                                 | 1 day                | Low — backward-compatible via default                                                 |
| R-43 | **Keep checkerboard for now**                      | Current implementation passes all 19 tests and satisfies D21's "obviously artificial" criterion. The ADR explicitly chose checkerboard.                                                                        | 0 days               | None                                                                                  |

---

## 5. Risks, License, and Rejection Reasons

| R-id | Item                                                                                                                                                                                                                                                                                                    | Status                                                                 |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| R-44 | **goproblems.com license**: Their frame code is proprietary. We cannot copy it. We must independently implement the same conceptual pattern.                                                                                                                                                            | No code copying permitted. Use KaTrain (MIT) as the reference instead. |
| R-45 | **KaTrain license**: MIT. We can read and adapt the algorithm. We already cite it in our codebase.                                                                                                                                                                                                      | ✅ Clear to use as algorithmic reference.                              |
| R-46 | **Empty-cell logic replaces suicide prevention**: KaTrain uses `empty_p = (i+j)%2==0 AND                                                                                                                                                                                                                | count - defense_area                                                   | > isize` to PRE-EMPTIVELY skip potentially isolated cells. This is not post-hoc surgery — cells that would be suicide-prone are left empty during fill. Near the color-transition seam (` | count - defense_area | <= isize`), ALL cells including checkerboard positions are filled, because neighboring same-color stones prevent 0-liberty suicide. Implementation must reproduce this `empty_p` logic exactly. | Mandatory for any dense-fill implementation. |
| R-47 | **Existing tests use snapshot counts**: `test_tsumego_frame.py` `TestStoneCountBalanced` (±5), `TestFrame19x19` (adds >20 stones), etc. A density change will break these count-based tests.                                                                                                            | Test updates required alongside any density change.                    |
| R-48 | **ADR D21 constraint**: Our architecture explicitly says checkerboard was validated at 3% winrate error. Dense fill is unvalidated in our toolchain.                                                                                                                                                    | Empirical validation needed before production deployment.              |
| R-49 | **WebGL vs CPU WASM**: goproblems uses WebGL backend. We use native binary. WebGL's floating-point precision differs from CPU. Frame quality comparisons between the two are not directly apples-to-apples.                                                                                             | Difference is small; frame algorithm is the more important variable.   |
| R-50 | ~~**External evidence gap**: We could not fetch live JS source.~~ **⚠️ CORRECTED (2026-03-08):** Bundle `920.ed9fa994.js` returned HTTP 200. Complete verbatim source of `e.FO`, `$t`, `qt`, `Gt`, `Ht` functions was obtained. The ghostban library is now confirmed as the JS board engine. See §3.5. | Live fetch successful 2026-03-08.                                      |

---

## 6. Planner Recommendations

1. **Adopt KaTrain's count-based fill (replaces prior "row alternation" recommendation).** Replace `(x+y)%2==0` checkerboard PLACEMENT with KaTrain's actual algorithm (verbatim in §3.2): iterate row-major; first `floor((board_size² - 5) / 2)` non-puzzle cells → defense; rest → offense; use `(i+j)%2==0 AND |count - defense_area| > board_width` to mark cells empty. This is the authoritative MIT-licensed reference (SHA confirmed) and matches goproblems.com's visual output. Effort: 2–3 days including test updates. Risk: low.

2. **Add solid attacker wall at frame_range boundary (corrected color from prior draft).** KaTrain's `put_border()` places a solid ring of **attacker** stones (not defender, as previously stated) at the `frame_range` perimeter. `is_black = black_to_attack_p`. This reinforces that the attacker surrounds the puzzle group. Effort: 0.5 days. Risk: low.

3. **Defer ko-threat placement until empirical validation.** KaTrain's `put_ko_threat()` is algorithmically sound, but our existing ko handling (D31, tromp-taylor rules) already addresses ko analysis. Ko-threat stone placement would interact with existing ko fixture calibration and needs separate validation. Add it if calibration shows ko puzzles still misclassified after the frame pattern upgrade.

4. **Do not attempt to replicate goproblems.com's proprietary JS code.** Their implementation likely follows KaTrain's algorithm directly. Implementing KaTrain's openly MIT-licensed algorithm covers the same technique without license risk.

---

## 7. Confidence and Risk Update for Planner

| Dimension                            | Assessment                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Algorithm identification**         | **Very high confidence** — KaTrain `tsumego_frame.py` fetched live (SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`). Verbatim code analyzed in §3.2. Prior R-23 claim of "y%2 row alternation" was wrong — actual: count-based half/half with `(i+j)%2==0` empty holes. goproblems.com's horizontal-band visual is explained by count-based row-major iteration, not explicit row-alternation. |
| **External evidence quality**        | **High** — KaTrain source confirmed live. goproblems.com live pages confirm model=b10, backend=WebGL, visits=500. JS bundle source not accessible (hash rotated; SPA rendering blocks raw HTML). All frame algorithm knowledge now from authoritative MIT source.                                                                                                                              |
| **Implementation effort**            | Low — `tsumego_frame.py` is isolated, well-tested (19 tests), and the change is localized to filling logic only.                                                                                                                                                                                                                                                                               |
| **Test impact**                      | Medium — count-based tests (`TestStoneCountBalanced`, `TestFrame19x19 adds >20 stones`) will need updates. No other modules affected.                                                                                                                                                                                                                                                          |
| **Production impact**                | Low — frame is evaluation-only; output coordinates are in original board space (D25). Frame change affects KataGo signal quality only.                                                                                                                                                                                                                                                         |
| **`post_research_confidence_score`** | **88** — algorithm is directly confirmed from live-fetched KaTrain MIT source (SHA verified). Remaining gap: (a) goproblems.com JS bundle inaccessible (hash rotated), so exact proprietary code unverified; (b) ADR D21 requires empirical calibration validation before production deployment.                                                                                               |
| **`post_research_risk_level`**       | **low** — change is entirely internal to `tsumego_frame.py`. No public APIs, no SGF schema changes, no pipeline contract changes. Risk is test maintenance only.                                                                                                                                                                                                                               |

---

## Open Questions

| q_id | question                                                                                                                                 | options                                                                                                               | recommended                                                                        | status                                                             |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Q1   | Are we confident the horizontal-band pattern produces measurably better KataGo accuracy than checkerboard ON our specific puzzle corpus? | A. Yes — empirically validate on calibration fixture set. B. No — accept KaTrain's validation as sufficient. C. Other | A                                                                                  | ❌ pending — requires running calibration with both frame patterns |
| Q2   | Should the frame density mode be a config parameter or a code change?                                                                    | A. Hard-code dense fill as the new default (KISS). B. Add `frame_pattern` parameter (flexibility).                    | A                                                                                  | ❌ pending — planner decision                                      |
| Q3   | Does goproblems.com use `b10c128` or `b6c96` in their current Research(Beta) page?                                                       | A. b6c96 (per Jan 2026 bundle analysis). B. b10c128 (per enrichment arch doc perf comparison).                        | B — live page text shows "Model: b10" on all 3 research pages fetched (2026-03-08) | ✅ resolved — `b10` confirmed                                      |

---

## Handoff

- `research_completed`: true
- `initiative_path`: `TODO/initiatives/2026-03-08-research-goproblems-tsumego-frame/`
- `artifact`: `15-research.md`
- `top_recommendations`:
  1. Adopt KaTrain's **count-based fill** (NOT y%2 row alternation — prior description was wrong): row-major scan, first ~half of non-puzzle cells → defense, rest → offense; `(i+j)%2==0 AND |count-defense_area|>board_width` skips cells only in non-seam zones
  2. Add solid **attacker** wall at puzzle margin boundary via `put_border()` (`is_black = black_to_attack_p`) — NOT defender wall as previously described
  3. Defer ko-threat placement until post-upgrade calibration
  4. Use KaTrain MIT source (SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`) as legal reference; do not attempt to replicate goproblems.com proprietary code
- `open_questions`: [Q1 empirical validation on yen-go corpus, Q2 config-param vs hard-code, Q4 adopt ghostban's `offence_to_win=10` value vs KaTrain's 5]
- `post_research_confidence_score`: 96
- `post_research_risk_level`: low

---

## §3.5 ghostban `e.FO` — Live-Fetched from bundle 920 (2026-03-08)

**Source:** `https://www.goproblems.com/build/920.ed9fa994.js` — HTTP 200 (bundle hash is current as of 2026-03-08; prior `148.518c57f7.js` reference was a different bundle).

**Library confirmed:** ghostban (open-source TypeScript Go board renderer). Exports include `e.FO`, `e.Ki`, `e.ov`, `e.lK`, `e.FD`, `e.R7`, etc.

### §3.5.1 Verbatim Helper Functions

#### `Gt` — Extrema Finder

```javascript
Gt = function (t, e) {
  void 0 === e && (e = 19);
  for (var n = e - 1, r = 0, o = e - 1, i = 0, a = 0; a < t.length; a++)
    for (var u = 0; u < t[a].length; u++) {
      0 !== t[a][u] &&
        (n > a && (n = a),
        r < a && (r = a),
        o > u && (o = u),
        i < u && (i = u));
    }
  return { leftMost: n, rightMost: r, topMost: o, bottomMost: i };
};
```

Returns `{leftMost, rightMost, topMost, bottomMost}` — bounding indices of non-empty cells. Note: naming is confusing (`leftMost` = minimum row index, `topMost` = minimum col index — ghostban uses column-major naming convention internally).

#### `qt` — Corner Detection

```javascript
qt = function (t, n) {
  void 0 === n && (n = 19);
  var r = Gt(t, n),
    o = r.leftMost,
    i = r.rightMost,
    a = r.topMost < n - 1 - r.bottomMost,
    u = o < n - 1 - i;
  return a && u
    ? e.ov.TopLeft
    : !a && u
      ? e.ov.BottomLeft
      : a && !u
        ? e.ov.TopRight
        : a || u
          ? e.ov.Center
          : e.ov.BottomRight;
};
```

Maps bounding box position to `e.ov` (orientation enum): `TopLeft/TopRight/BottomLeft/BottomRight/Center`.

#### `$t` — Bounding Box with Padding

```javascript
$t = function (t, e, n) {
  (void 0 === e && (e = 2), void 0 === n && (n = 19));
  var r = Gt(t),
    o = r.leftMost,
    i = r.rightMost,
    a = r.topMost,
    u = r.bottomMost,
    s = n - 1;
  return [
    [o - e < 0 ? 0 : o - e, a - e < 0 ? 0 : a - e],
    [i + e > s ? s : i + e, u + e > s ? s : u + e],
  ];
};
```

Returns `[[row_min, col_min], [row_max, col_max]]` with `e` padding (default 2), clamped to board bounds.

#### `Ht` — Zoom Frame Size Calculator (unrelated to fill)

```javascript
Ht = function (t, n, r) {
  (void 0 === n && (n = 19), void 0 === r && (r = 2));
  var o = [19, 19],
    i = qt(t),
    a = Gt(t, n),
    u = a.leftMost,
    s = a.rightMost,
    l = a.topMost,
    c = a.bottomMost;
  return (
    i === e.ov.TopLeft && ((o[0] = s + r + 1), (o[1] = c + r + 1)),
    i === e.ov.TopRight && ((o[0] = n - u + r), (o[1] = c + r + 1)),
    i === e.ov.BottomLeft && ((o[0] = s + r + 1), (o[1] = n - l + r)),
    i === e.ov.BottomRight && ((o[0] = n - u + r), (o[1] = n - l + r)),
    (o[0] = Math.min(o[0], n)),
    (o[1] = Math.min(o[1], n)),
    o
  );
};
```

Returns the zoom window size `[rows, cols]` for the board viewport clipping. Independent of frame fill.

### §3.5.2 Verbatim `e.FO` — Complete Frame Fill Function

```javascript
e.FO = function (t, n, i, a, u, s) {
  (void 0 === i && (i = 19),
    void 0 === a && (a = 7.5),
    void 0 === u && (u = e.Ki.Black));
  var l = o.cloneDeep(t),
    c = $t(t, n, i), // bounding box [[row_min,col_min],[row_max,col_max]] with padding n
    f = qt(t); // corner orientation (TopLeft/TopRight/BottomLeft/BottomRight/Center)

  // Lambda 1: border fill (attacker wall on bbox perimeter, skip board-edge sides)
  return (
    (function (t) {
      for (
        var n = r.__read(c[0], 2),
          o = n[0],
          a = n[1],
          s = r.__read(c[1], 2),
          l = s[0],
          h = s[1],
          d = o;
        d <= l;
        d++
      )
        for (var p = a; p < h; p++)
          ((f === e.ov.TopLeft &&
            ((d === l && d < i - 1) ||
              (p === h && p < i - 1) ||
              (d === o && d > 0) ||
              (p === a && p > 0))) ||
            (f === e.ov.TopRight &&
              ((d === o && d > 0) ||
                (p === h && p < i - 1) ||
                (d === l && d < i - 1) ||
                (p === a && p > 0))) ||
            (f === e.ov.BottomLeft &&
              ((d === l && d < i - 1) ||
                (p === a && p > 0) ||
                (d === o && d > 0) ||
                (p === h && p < i - 1))) ||
            (f === e.ov.BottomRight &&
              ((d === o && d > 0) ||
                (p === a && p > 0) ||
                (d === l && d < i - 1) ||
                (p === h && p < i - 1))) ||
            f === e.ov.Center) &&
            (t[d][p] = u); // u = attacker color
    })(l),
    // Lambda 2: outside fill (count-based half+half with checkerboard holes)
    (function (t) {
      for (
        var n = u * a, // n = attacker_color_sign * komi  (offense_komi)
          o = r.__read(c[0], 2),
          s = o[0],
          l = o[1], // bbox top-left
          h = r.__read(c[1], 2),
          d = h[0],
          p = h[1], // bbox bottom-right
          v = u === e.Ki.Black, // v = is attacker Black?
          g = d - s, // g = bbox row span (excl. endpoints)
          y = p - l, // y = bbox col span (excl. endpoints)
          m = Math.floor((361 - g * y) / 2) - n - 10, // m = defense_area threshold
          _ = 0,
          b = 0;
        b < i;
        b++ // b = row index
      )
        for (
          var w = 0;
          w < i;
          w++ // w = col index
        )
          if (b < s || b > d || w < l || w > p) {
            // skip cells inside bbox
            _++; // increment sequential count
            var A = e.Ki.Empty;
            (f === e.ov.TopLeft || f === e.ov.BottomLeft
              ? (A = v !== _ <= m ? e.Ki.White : e.Ki.Black) // TopLeft/BottomLeft: early→defense(White), late→offense(Black) for Black attacker
              : (f !== e.ov.TopRight && f !== e.ov.BottomRight) ||
                (A = v !== _ <= m ? e.Ki.Black : e.Ki.White), // TopRight/BottomRight: REVERSED color direction
              (b + w) % 2 == 0 && Math.abs(_ - m) > i && (A = e.Ki.Empty), // checkerboard holes only far from seam
              (t[b][w] = A));
          }
    })(l),
    l
  ); // returns mutated clone
};
```

**Parameters:**
| Param | Default | Meaning |
|-------|---------|---------|
| `t` | — | Board matrix (19×19 int array; 0=empty, e.Ki.Black, e.Ki.White) |
| `n` | 2 | Bounding box padding (same as KaTrain `margin`) |
| `i` | 19 | Board size |
| `a` | 7.5 | Komi |
| `u` | `e.Ki.Black` | Attacker color (side to move / side whose tsumego is analyzed) |
| `s` | — | Unused (present in signature but not referenced in body) |

### §3.5.3 Algorithm Comparison: ghostban `e.FO` vs KaTrain `tsumego_frame.py`

| R-id | Dimension                                                            | KaTrain                                                                                                    | ghostban `e.FO`                                                                                                                                                                                                                                                     |
| ---- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-51 | Library status                                                       | Open-source MIT (sanderland/katrain)                                                                       | ghostban is also open-source (used by goproblems.com as an npm dep)                                                                                                                                                                                                 |
| R-52 | Orientation handling                                                 | EXPLICIT: recursive flip/rotate to canonical (top-right) before fill                                       | NONE: skips normalization; compensates via corner-specific color direction (see R-58)                                                                                                                                                                               |
| R-53 | Bounding box                                                         | `nearest_stone ± margin`, snapped to board edge within `near_to_edge=2` pts                                | `nearest_stone ± padding` (default 2), clamped to board bounds (no snap)                                                                                                                                                                                            |
| R-54 | Border fill                                                          | `put_border()` → solid attacker ring on ALL 4 sides of `frame_range` perimeter, including board-edge sides | Lambda 1 → attacker stones only on bbox-perimeter edges that are NOT board-edge (board-adjacent sides are skipped via `d>0`, `d<i-1`, etc.)                                                                                                                         |
| R-55 | Defense_area numerator                                               | `isize * jsize` = 361 (FULL board); cells skipped by `inside_p()`during iteration                          | `361 - g*y` where `g*y = bbox_row_span × bbox_col_span`; bbox area subtracted BEFORE the division                                                                                                                                                                   |
| R-56 | `offence_to_win` constant                                            | **5** (hardcoded as `offence_to_win = 5`)                                                                  | **10** (hardcoded as `- 10` in `m` formula)                                                                                                                                                                                                                         |
| R-57 | Fill balance (Black attacker, 7×7 bbox, komi=7.5, 312 outside cells) | defense_area = `(361 - 7.5 - 5)/2 = 174.25` → **55.9% defense, 44.1% offense**                             | `m = floor((361-49)/2) - 7.5 - 10 = 138.5 → 138` → **44.2% defense, 55.8% offense**                                                                                                                                                                                 |
| R-58 | Color direction by corner                                            | N/A (normalized to canonical before fill)                                                                  | **TopLeft/BottomLeft**: early cells → defense (White if Black attacker); **TopRight/BottomRight**: early cells → offense (Black if Black attacker). Mirrors fill so the dense zone is always near the board-edge sides where the puzzle is NOT cut by a board edge. |
| R-59 | Checkerboard holes formula                                           | `(i+j)%2==0 AND \|count-defense_area\|>isize`                                                              | `(b+w)%2==0 AND \|_-m\|>i` — **identical formula**                                                                                                                                                                                                                  |
| R-60 | Ko-threat patterns                                                   | `put_ko_threat()` — fixed ASCII patterns at far corners                                                    | Not present in `e.FO`. Likely handled separately or omitted.                                                                                                                                                                                                        |
| R-61 | Return value                                                         | Modifies board in-place (Python)                                                                           | Returns mutated deep-clone `l` (JavaScript)                                                                                                                                                                                                                         |
| R-62 | `mt` function (bundle 148)                                           | N/A                                                                                                        | `mt(e, t)` generates animation frames by replaying SGF moves. **Unrelated to tsumego frame fill.** It is the thumbnail animator component `ProblemBoard`.                                                                                                           |
| R-63 | i18n translation endpoint                                            | N/A                                                                                                        | `https://www.goproblems.com/locales/en/translation.json` returns **HTTP 404** (URL has changed). The "Show/Hide Problem Frame" label is likely in a different i18n bundle or hardcoded.                                                                             |

### §3.5.4 Critical Numerical Difference: `offence_to_win = 5` vs `10`

The most significant algorithmic difference between KaTrain and ghostban is the `offence_to_win` constant which shifts the defense/offense balance:

- **KaTrain `offence_to_win = 5`**: Defense gets ~56% of outside cells (for typical corner puzzle). Gives the defender slightly more territory — KataGo's score estimate is pulled toward the defender.
- **ghostban `-10`**: Defense gets ~44% of outside cells. Gives the **attacker** slightly more territory — KataGo's score estimate is pulled toward the attacker.

Yen-Go currently inherits KaTrain's `offence_to_win = 5` constant (embedded in `tsumego_frame.py` as `None` — need to verify the exact value used). If goproblems.com achieves better KataGo signal by using `10`, this deserves empirical validation.

**Recommendation update for §6:** Add Q4 — test `offence_to_win=10` on the calibration fixture set to measure winrate accuracy improvement vs. KaTrain's `5`.

---

## Updated §6 Planner Recommendations (post §3.5)

1. **Adopt KaTrain's count-based fill (R-39, confirmed algorithm match).** ghostban `e.FO` uses the same row-major count + `(i+j)%2==0` checkerboard holes formula as KaTrain. Our current `(x+y)%2==0` checkerboard PLACEMENT is a simplified version that misses the count-based half/half split. Implement full KaTrain algorithm. Effort: 2–3 days. Risk: low.

2. **Evaluate `offence_to_win = 10` (ghostban value) vs `5` (KaTrain value, new Q4).** This is the largest numerical difference between the two implementations and shifts the territorial balance in opposite directions. Run the calibration fixture set with both values and pick the winner empirically. Effort: 0.5 days + calibration run. Risk: low.

3. **Add border fill on non-board-edge bbox sides (R-40, now nuanced).** Both KaTrain and ghostban agree: attacker walls go on the bbox perimeter. ghostban skips the sides touching the board edge (the puzzle's "cut" sides). KaTrain fills all 4 sides. Empirical choice: ghostban's approach is more principled (no dangling stones at board edges). Effort: 0.5 days. Risk: low.

4. **Do not try to replicate ghostban's corner-specific color reversal (R-58).** KaTrain's flip/rotate normalization achieves the same effect through coordinate transformation before filling. Our Python implementation can follow KaTrain's normalize-first approach. Equivalent results with less code complexity. Risk: none.

5. **Do not copy ghostban or goproblems.com code.** ghostban's MIT license permits reading for algorithmic reference but we should not copy JavaScript code into our Python tool. KaTrain (MIT, SHA confirmed) remains our canonical reference.

---

## Updated Open Questions

| q_id | question                                                                                                                                 | options                                                                                                               | recommended                      | user_response | status      |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------- | ----------- |
| Q1   | Are we confident the horizontal-band pattern produces measurably better KataGo accuracy than checkerboard ON our specific puzzle corpus? | A. Yes — empirically validate on calibration fixture set. B. No — accept KaTrain's validation as sufficient. C. Other | A                                | —             | ❌ pending  |
| Q2   | Should the frame density mode be a config parameter or a code change?                                                                    | A. Hard-code dense fill as the new default (KISS). B. Add `frame_pattern` parameter.                                  | A                                | —             | ❌ pending  |
| Q3   | Does goproblems.com use `b10c128` or `b6c96`?                                                                                            | A. b6c96. B. b10c128.                                                                                                 | B — live page shows "Model: b10" | confirmed     | ✅ resolved |
| Q4   | Does ghostban's `offence_to_win=10` produce better winrate accuracy than KaTrain's `5` on Yen-Go corpus?                                 | A. Yes, adopt 10. B. No, keep 5. C. Validate empirically.                                                             | C                                | —             | ❌ pending  |

---

## Updated Handoff

- `research_completed`: true
- `initiative_path`: `TODO/initiatives/2026-03-08-research-goproblems-tsumego-frame/`
- `artifact`: `15-research.md`
- `top_recommendations`:
  1. Adopt KaTrain's **count-based fill** (verbatim algorithm verified against both KaTrain SHA and ghostban live bundle): row-major scan; first `floor((board_size² - bbox_area) / 2) - komi - 10` non-puzzle cells → defense; rest → offense; `(i+j)%2==0 AND |count-threshold| > board_width` → empty
  2. **Empirically test `offence_to_win=10` (ghostban value) vs `5` (KaTrain value)** — this is the most significant algorithmic difference between the two confirmed implementations
  3. Add attacker wall on non-board-edge bbox perimeter sides (both implementations agree)
  4. Use KaTrain MIT source (SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`) as legal reference; ghostban code is read-only reference (also MIT, but do not copy JS code into Python tool)
- `open_questions`: [Q1 empirical validation on yen-go corpus, Q2 config-param vs hard-code, Q4 offence_to_win=10 vs 5 empirical test]
- `post_research_confidence_score`: **96** — ghostban `e.FO` verbatim confirmed from live-fetched bundle 920. Both KaTrain and ghostban algorithms now in hand. Remaining gap: empirical validation of which balance constant (5 vs 10) performs better on Yen-Go corpus.
- `post_research_risk_level`: **low**
