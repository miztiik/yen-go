# GoGoGo — 8 Basic Instincts: Distilled Algorithms

**Source:** [PLNech/gogogo](https://github.com/PLNech/gogogo) `training/instincts.py`, `training/INSTINCTS.md`  
**License:** GPL-3.0 (algorithms extracted, not code verbatim)  
**Relevance:** Pattern detectors for auto-tagging and hint generation

---

## Overview

GoGoGo defines 8 "instincts" — local board patterns that skilled players
recognize instantly. Each instinct has a measured **advantage** (empirical
win-rate delta) and a **boost multiplier** used during training.

For yen-go: these patterns can **auto-tag** puzzles and **generate hints**.

---

## The 8 Instincts (ranked by measured advantage)

| #   | Instinct             | Boost | Advantage | Description                                          |
| --- | -------------------- | ----: | --------: | ---------------------------------------------------- |
| 1   | Extend from atari    |  3.0× |     +9.7% | Extend a stone in atari rather than abandoning it    |
| 2   | Block thrust         |  1.8× |     +9.6% | Block opponent's thrust through your position        |
| 3   | Hane response        |  1.5× |    +13.2% | Respond to opponent's hane with counter-hane         |
| 4   | Connect against peep |  2.5× |     +3.4% | Connect stones when opponent peeps the cutting point |
| 5   | Block angle          |  1.5× |     +3.5% | Block opponent's diagonal approach                   |
| 6   | Hane at head of two  |  2.0× |     +1.9% | Play hane at the head of two opponent stones         |
| 7   | Stretch from kosumi  |  1.4× |     +3.0% | Extend from a diagonal (kosumi) formation            |
| 8   | Stretch from bump    |  1.3× |     +3.2% | Extend from a bump (tsuke) formation                 |

---

## Detection Algorithms

### 1. Extend from Atari (征子逃脱)

**Pattern:** Player has a stone/group in atari (1 liberty). The correct move
extends that group by one stone, gaining liberties.

```python
def detect_extend_from_atari(board, move_x, move_y, color):
    """Check if move extends a friendly group that was in atari."""
    # Before move: find adjacent friendly group in atari
    for nx, ny in neighbors(move_x, move_y):
        group = get_group(board, nx, ny)
        if group and group.color == color and count_liberties(group) == 1:
            # After move: group's liberty count increases
            test = board.copy()
            test.play(move_x, move_y, color)
            new_group = get_group(test, move_x, move_y)
            if count_liberties(new_group) >= 2:
                return True
    return False
```

**Yen-go mapping:** Auto-tag `escape`. Hint: "Extend to gain liberties."

### 2. Block Thrust (挡住突破)

**Pattern:** Opponent played adjacent to a cutting point in player's formation.
Player blocks by connecting the cut.

```python
def detect_block_thrust(board, move_x, move_y, color):
    """Check if move blocks opponent's thrust through a position."""
    opponent = opposite(color)
    # Move must be adjacent to both a friendly stone and an opponent stone
    has_friendly = any(get_color(n) == color for n in neighbors(move_x, move_y))
    has_opponent = any(get_color(n) == opponent for n in neighbors(move_x, move_y))
    if not (has_friendly and has_opponent):
        return False
    # The move must connect two previously disconnected friendly groups
    test = board.copy()
    test.play(move_x, move_y, color)
    connected_groups = set()
    for nx, ny in neighbors(move_x, move_y):
        g = get_group(test, nx, ny)
        if g and g.color == color:
            connected_groups.add(id(g))
    return len(connected_groups) == 1  # All now in one group
```

**Yen-go mapping:** Auto-tag `connection`. Hint: "Block the opponent's attempt to cut through."

### 3. Hane Response (扳反应)

**Pattern:** Opponent played a hane (diagonal contact). Player responds
with a counter-hane or blocking move.

```python
def detect_hane_response(board, move_x, move_y, color):
    """Check if move responds to opponent's hane."""
    opponent = opposite(color)
    # Check diagonals for recent opponent hane
    for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
        nx, ny = move_x + dx, move_y + dy
        if get_color(board, nx, ny) == opponent:
            # Check if opponent stone is a hane (contact with friendly stone)
            adj_friendly = any(
                get_color(board, ax, ay) == color
                for ax, ay in neighbors(nx, ny)
                if (ax, ay) != (move_x, move_y)
            )
            if adj_friendly:
                return True
    return False
```

**Yen-go mapping:** Auto-tag `shape` or `tesuji`. Hint: "Respond to the hane."

### 4. Connect Against Peep (防断连接)

**Pattern:** Opponent peeps a cutting point. Player connects to prevent the cut.

```python
def detect_connect_against_peep(board, move_x, move_y, color):
    """Check if move connects against opponent's peep."""
    opponent = opposite(color)
    # Move must fill a cutting point (between two friendly groups)
    friendly_groups_adjacent = set()
    opponent_adjacent = False
    for nx, ny in neighbors(move_x, move_y):
        if get_color(board, nx, ny) == color:
            friendly_groups_adjacent.add(id(get_group(board, nx, ny)))
        elif get_color(board, nx, ny) == opponent:
            opponent_adjacent = True
    # Cutting point = adjacent to 2+ distinct friendly groups AND opponent
    return len(friendly_groups_adjacent) >= 2 and opponent_adjacent
```

**Yen-go mapping:** Auto-tag `connection`. Hint: "Connect to prevent the cut."

### 5. Hane at Head of Two (二子头扳)

**Pattern:** Opponent has exactly two stones in a row. Player plays hane
at the head of the two stones.

```python
def detect_hane_at_head_of_two(board, move_x, move_y, color):
    """Check if move is hane at head of two opponent stones."""
    opponent = opposite(color)
    for dx, dy in [(0,1), (1,0)]:  # Check horizontal and vertical
        # Two opponent stones in a line
        if (get_color(board, move_x+dx, move_y+dy) == opponent and
            get_color(board, move_x+2*dx, move_y+2*dy) == opponent):
            # Move is diagonal to the first stone (hane position)
            # and opponent stones extend exactly 2 in that direction
            group = get_group(board, move_x+dx, move_y+dy)
            if group and len(group.stones) == 2:
                return True
    return False
```

**Yen-go mapping:** Auto-tag `shape`. Hint: "Play at the head of the two stones."

### 6–8. Kosumi/Bump Extensions

These detect extensions from specific stone formations.
Less relevant for tsumego tagging but useful for difficulty assessment
(puzzles requiring these patterns are typically intermediate+).

---

## Mapping to Yen-Go Features

### Auto-Tagging (YT enrichment)

| Instinct Detected    | YT Tag Candidate        | Confidence                                       |
| -------------------- | ----------------------- | ------------------------------------------------ |
| Extend from atari    | `escape`                | High — if first correct move extends atari group |
| Block thrust         | `connection`, `cutting` | Medium — context-dependent                       |
| Connect against peep | `connection`            | High — structural detection reliable             |
| Hane at head of two  | `shape`, `tesuji`       | High — well-defined pattern                      |
| Hane response        | `shape`                 | Low — too common, might over-tag                 |

### Hint Generation (YH enrichment)

| Instinct             | Hint Template                                         |
| -------------------- | ----------------------------------------------------- |
| Extend from atari    | "A group is in danger — extend to gain liberties."    |
| Block thrust         | "Block the opponent's attempt to break through."      |
| Connect against peep | "Your groups need to connect before being cut apart." |
| Hane at head of two  | "Look for the head of the opponent's formation."      |

### Difficulty Signal

**Instinct count per puzzle** can serve as a difficulty input:

- 0 instincts detected → likely trivial or requires pure reading
- 1 instinct → focused tactical problem (beginner-intermediate)
- 2+ instincts → multi-tactic (intermediate+)

This complements the existing YX complexity metrics and is NOT a replacement
for the difficulty classifier — it's an additional signal.

---

## Implementation Notes

1. **Detection runs on the FIRST correct move only.** Analyzing the full
   solution tree for instincts would be expensive and unnecessary for tagging.
2. **Board state needed:** Build sgfmill Board from initial position (AB/AW),
   then check each instinct against the first correct move.
3. **Order of evaluation matters:** Check in priority order (extend_from_atari
   first) and use the highest-priority match for tagging.
4. **Policy:** `ENRICH_IF_ABSENT` — don't override manually assigned tags.
