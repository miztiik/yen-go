# gogamev4.0 — Territory & Dead Stone Analysis: Distilled Algorithms

**Source:** [zhoumeng-creater/gogamev4.0](https://github.com/zhoumeng-creater/gogamev4.0) `core/territory.py`, `core/board.py`  
**License:** MIT  
**Relevance:** Life/death verification, eye counting, group strength assessment

---

## Overview

gogamev4.0's `Territory` and `DeadStoneAnalyzer` classes implement
rule-based Go position evaluation. Key algorithms:

1. **Flood-fill territory** — identify enclosed empty regions
2. **Influence propagation** — exponential decay from stone strength
3. **Eye counting** (true vs false eye distinction)
4. **Group status assessment** (alive/dead/unsettled)
5. **Escape potential** and **eye-making potential**
6. **Seki (dual life) detection**

All algorithms are CPU-only, use no ML, and operate on a simple grid board.

---

## Algorithm 1: Flood-Fill Territory (`_flood_fill_territory`)

**Purpose:** Identify connected empty regions and their owner (based on
what color borders the region).

**Algorithm:**

1. BFS from each unvisited empty point
2. Track all border colors encountered
3. **Owner determination:**
   - If borders have exactly 1 color → that color owns the territory
   - If borders have 0 colors → neutral (isolated empty area)
   - If borders have 2+ colors AND region is 1 point → dame (neutral point)
   - If borders have 2+ colors AND region is larger → neutral

**Pseudocode:**

```python
def flood_fill_territory(board, start_x, start_y, visited):
    territory = set()
    borders = set()  # Colors found at boundaries
    queue = [(start_x, start_y)]

    while queue:
        x, y = queue.pop(0)
        if (x, y) in visited or not is_valid(x, y):
            continue
        if is_empty(board, x, y):
            visited.add((x, y))
            territory.add((x, y))
            for nx, ny in neighbors(x, y):
                color = get_color(board, nx, ny)
                if color == EMPTY:
                    queue.append((nx, ny))
                else:
                    borders.add(color)
        # Already handled: non-empty cells just add to borders

    # Determine owner
    if len(borders) == 1:
        return territory, borders.pop()
    elif len(borders) == 0:
        return territory, 'neutral'
    elif len(territory) == 1:
        return territory, 'dame'
    else:
        return territory, 'neutral'
```

**Yen-go use:** After playing out a solution sequence, verify the territory
outcome matches the puzzle objective.

---

## Algorithm 2: Influence Map (`calculate_influence`)

**Purpose:** Estimate which player controls which area of the board using
distance-based influence propagation.

**Algorithm:**

1. For each stone group, compute **strength** = `num_stones × √(num_liberties)`
2. Black groups have positive strength, white groups have negative strength
3. Propagate influence from each stone using exponential decay:
   `influence[dy][dx] += strength × decay_factor^distance`
4. Distance metric: Chebyshev (max of abs differences)
5. Max propagation distance: `board_size // 2`

**Key parameters:**

- `decay_factor`: 0.5 (default) — influence halves per unit distance
- Threshold for territory: ±5.0

**Pseudocode:**

```python
def calculate_influence(board, decay_factor=0.5):
    influence = zeros(board.size, board.size)

    for group in board.get_all_groups():
        strength = len(group.stones) * sqrt(group.num_liberties)
        if group.color == BLACK:
            strength = +strength
        else:
            strength = -strength

        for stone_x, stone_y in group.stones:
            for dy in range(board.size):
                for dx in range(board.size):
                    dist = max(abs(dx - stone_x), abs(dy - stone_y))
                    if dist == 0:
                        influence[dy][dx] += strength * 2
                    elif dist <= board.size // 2:
                        influence[dy][dx] += strength * (decay_factor ** dist)

    return influence
```

**Yen-go use:** The influence map can serve as a **context signal** for
difficulty estimation. Puzzles where influence is clearly unbalanced (one side
dominates) are typically easier than balanced positions.

---

## Algorithm 3: Eye Counting (`_count_eyes`, `_is_eye`, `_is_real_eye`)

**Purpose:** Count true eyes for a group to determine life/death status.

**Eye detection (orthogonal check + diagonal validation):**

```python
def is_eye(board, x, y, color):
    """Position x,y is an eye for color if:
    1. All 4 orthogonal neighbors are same color or board edge
    2. At least 3 of 4 diagonal neighbors are same color or board edge
    """
    if not is_empty(board, x, y):
        return False

    # Check orthogonal neighbors
    for nx, ny in orthogonal_neighbors(x, y):
        if get_color(board, nx, ny) != color:
            return False

    # Check diagonals
    diagonals = [(x-1,y-1), (x-1,y+1), (x+1,y-1), (x+1,y+1)]
    friendly = 0
    total = 0
    for dx, dy in diagonals:
        if is_valid(dx, dy):
            total += 1
            if get_color(board, dx, dy) == color:
                friendly += 1
        else:
            friendly += 1  # Board edge counts as friendly

    if total == 4:
        return friendly >= 3
    else:
        return friendly >= total - 1
```

**Real eye verification:**

```python
def is_real_eye(board, x, y, group):
    """True eye = all orthogonal neighbors belong to the SAME group."""
    for nx, ny in orthogonal_neighbors(x, y):
        if not is_empty(board, nx, ny):
            if (nx, ny) not in group.stones:
                return False  # Neighbor belongs to different group = false eye
    return True
```

**Yen-go use:** Eye counting is critical for:

1. **Validating life-and-death puzzles** — does the solution actually create
   or destroy the required number of eyes?
2. **Difficulty signal** — puzzles requiring false-eye recognition are harder
3. **Auto-tagging** — `eye-shape` tag when eye formation is the key technique

---

## Algorithm 4: Group Status Assessment (`_analyze_group`)

**Purpose:** Classify a group as alive, dead, or unsettled.

**Decision tree:**

```
liberties == 0                     → DEAD
liberties >= 2 AND eyes >= 2       → ALIVE
liberties >= 2 AND eyes == 1
  AND liberties >= 4               → ALIVE
can_escape(group)                  → UNSETTLED
can_make_eyes(group)               → UNSETTLED
liberties >= 5                     → ALIVE (heuristic)
liberties <= 1                     → DEAD
else                               → UNSETTLED
```

**Escape potential:**

```python
def can_escape(board, group):
    # Large groups with enough liberties can likely escape
    if len(group.stones) >= 4 and group.num_liberties >= 3:
        return True
    # Groups on the edge with few liberties are harder to escape
    edge_distance = min(min_x, min_y, size-1-max_x, size-1-max_y)
    if edge_distance == 0 and group.num_liberties <= 2:
        return False
    return group.num_liberties >= 3
```

**Eye-making potential:**

```python
def can_make_eyes(board, group):
    internal_space = count_internal_space(group)
    # Need at least 6-7 internal points for two eyes
    return internal_space >= 6
```

**Internal space** = count empty points inside the group's bounding box
that are surrounded by the group's stones (≥3 neighboring stones from group).

**Yen-go use:** Group status assessment provides:

1. **Quality validation** — a puzzle where the target group is already ALIVE
   at position setup is a poorly constructed puzzle (q:1)
2. **Difficulty signal** — UNSETTLED groups are harder to evaluate than
   clearly DEAD or ALIVE groups
3. **Content-type signal** — trivial kill of a DEAD group → training material

---

## Algorithm 5: Seki Detection (`_is_seki`)

**Purpose:** Detect dual-life (seki/双活) situations where neither player
can capture the other.

**Algorithm:**

1. Find pairs of adjacent groups of different colors
2. Check if they share liberties (`group1.liberties ∩ group2.liberties`)
3. For each shared liberty, simulate both players trying to fill it
4. If filling any shared liberty results in self-capture for both players
   → seki confirmed
5. Both groups need ≥2 shared liberties for stable seki

**Yen-go use:** Auto-tag `seki` when seki situation exists in the initial
position or results from the correct solution.

---

## Mapping to Yen-Go Pipeline

| gogamev4.0 Algorithm | Yen-Go Application                                          | Where                       |
| -------------------- | ----------------------------------------------------------- | --------------------------- |
| Flood-fill territory | Verify puzzle outcomes, calculate territory delta           | `core/tactical_analyzer.py` |
| Influence map        | Difficulty signal (position balance), context for hints     | `core/classifier.py`        |
| Eye counting         | Validate life/death puzzles, auto-tag `eye-shape`           | `core/tactical_analyzer.py` |
| Group status         | Quality validation (flag broken puzzles), difficulty signal | `core/quality.py`           |
| Escape potential     | Auto-tag `escape`, difficulty signal                        | `core/tactical_analyzer.py` |
| Seki detection       | Auto-tag `seki`                                             | `core/tactical_analyzer.py` |

---

## Implementation Notes

1. **sgfmill integration:** sgfmill provides `Board.get()` and `Board.play()`
   but NOT group/liberty APIs. We need a thin wrapper that does BFS group
   traversal on sgfmill's board state — similar to what `hints.py` already
   does with `_analyze_liberties()`.
2. **Performance consideration:** Eye counting and group status involve
   multiple BFS traversals. Budget ~20ms per puzzle. Pre-build group cache.
3. **Avoid full-board territory at initial position.** Territory calculation
   is meaningful AFTER the solution is played out, not at puzzle setup.
