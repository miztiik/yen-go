# GoGoGo — TacticalAnalyzer: Distilled Algorithms

**Source:** [PLNech/gogogo](https://github.com/PLNech/gogogo) `training/tactics.py`  
**License:** GPL-3.0 (algorithms extracted, not code verbatim)  
**Relevance:** Symbolic tactical pattern detection — no ML required

---

## Overview

GoGoGo's `TacticalAnalyzer` provides **pure symbolic** (no neural network)
detection of 6 tactical patterns. Every algorithm uses only board state + BFS/DFS
traversal. CPU-only, deterministic, suitable for pipeline-time analysis.

---

## Algorithm 1: Ladder Detection (`trace_ladder`)

**Purpose:** Traces a ladder (征子) from a stone in atari to see if it
successfully captures or if the target escapes.

**Algorithm:**

1. Start from a stone with exactly 1 liberty (atari)
2. Get the single liberty point → that's where attacker plays
3. After attacker plays, defender extends in direction of escape
4. **Escape direction** = diagonal away from the attacker's last move
5. Recurse: if defender's extension has 2 liberties → ladder continues
6. **Termination:**
   - Defender reaches edge → **captured** (ladder succeeds)
   - Defender's extension has 3+ liberties → **escape** (ladder fails)
   - A friendly stone of defender exists on the escape path → **ladder breaker**
   - Max depth exceeded (30 moves) → inconclusive

**Key insight for yen-go:** Ladder detection can auto-tag puzzles with `ladder`
technique and generate hint "This begins the chase" or "Watch for ladder breakers
on the escape diagonal."

**Pseudocode:**

```python
def trace_ladder(board, stone_x, stone_y, attacker_color, max_depth=30):
    """Returns: ('captured' | 'escaped' | 'breaker', depth)"""
    group = get_group(board, stone_x, stone_y)
    if count_liberties(group) != 1:
        return None  # Not in atari

    for depth in range(max_depth):
        liberty = get_single_liberty(group)
        # Attacker plays at the liberty
        board.play(liberty, attacker_color)

        # Defender extends in escape direction
        escape_point = compute_escape_diagonal(liberty, group)
        if not is_valid(escape_point) or is_edge(escape_point):
            return ('captured', depth)

        board.play(escape_point, defender_color)
        group = get_group(board, escape_point)

        if count_liberties(group) >= 3:
            return ('escaped', depth)
        if has_ladder_breaker(board, escape_point, defender_color):
            return ('breaker', depth)

    return ('inconclusive', max_depth)
```

---

## Algorithm 2: Snapback Detection (`detect_snapback`)

**Purpose:** Detects the snapback (征子回吃) pattern where letting the opponent
capture creates an immediate recapture of a larger group.

**Algorithm:**

1. Find a defender group with exactly 1 liberty
2. Attacker fills the last liberty → captures the group
3. After capture, check: does the capturing stone now have only 1 liberty?
4. If yes → the previously captured stones' area is now a snapback trap
5. Verify: defender can play in the captured area and recapture more stones

**Key insight:** Snapback = "atari first, then recapture more." The
heuristic is: `captured_count_after_recapture > original_group_size`.

**Pseudocode:**

```python
def detect_snapback(board, target_x, target_y):
    """Returns True if playing at target creates snapback opportunity."""
    group = get_group(board, target_x, target_y)
    if count_liberties(group) != 1:
        return False

    # Simulate: opponent fills last liberty → captures
    liberty = get_single_liberty(group)
    test_board = board.copy()
    test_board.play(liberty, opponent_color)

    # After capture: does the capturing stone have only 1 liberty?
    new_group = get_group(test_board, liberty)
    if count_liberties(new_group) == 1:
        # Defender can recapture → snapback!
        recapture_liberty = get_single_liberty(new_group)
        return True

    return False
```

---

## Algorithm 3: Capture Verification (`verify_capture` — alpha-beta)

**Purpose:** Verifies whether a capture (吃子) sequence is forced,
using shallow alpha-beta search (depth 4).

**Algorithm:**

1. From current position, try all legal moves for attacker
2. For each attacker move, try all defender responses
3. Score = change in captured stone count
4. Alpha-beta pruning at depth 4 (≤16 positions)
5. If attacker can force a positive score → verified capture

**Key insight:** Depth 4 is sufficient for most tsumego tactics.
The alpha-beta is used to verify, not to find moves.

---

## Algorithm 4: Life/Death Evaluation (`evaluate_life_death` — minimax)

**Purpose:** Determines whether a group lives or dies with perfect play,
using minimax search.

**Algorithm:**

1. Identify the target group (usually the largest opponent group)
2. Minimax with alpha-beta: attacker tries to kill, defender tries to live
3. **Terminal conditions:**
   - Group has 0 liberties → dead (-1)
   - Group has ≥2 eyes → alive (+1)
   - Group has ≥5 liberties → alive (heuristic escape)
   - Max depth (12) reached → evaluate heuristically
4. **Heuristic evaluation at leaf:**
   - `score = (liberties × 0.1) + (eyes × 10) + (connections × 2)`
   - Positive = likely alive, negative = likely dead

**Key insight:** The 2-eye detection (`has_eye()` + counted distinct eyes)
is reusable for puzzle validation: does a life-and-death puzzle actually result
in life (2+ eyes) or death (0 eyes)?

---

## Algorithm 5: Position Classification (`is_tactical_position`)

**Purpose:** Classifies whether a board position contains active tactical elements.

**Heuristic:**

```python
def is_tactical_position(board):
    has_atari = any group with 1 liberty
    has_near_capture = any group with 2 liberties
    has_cutting = disconnected friendly groups adjacent to opponent
    return has_atari or has_near_capture or has_cutting
```

---

## Algorithm 6: Tactical Feature Planes (6 planes)

**Purpose:** Generates 6 binary feature maps of the board, each highlighting
a different tactical pattern.

| Plane | Name              | What it detects                            |
| ----- | ----------------- | ------------------------------------------ |
| 0     | ladder-threatened | Stones in atari that face a ladder         |
| 1     | ladder-breaker    | Friendly stones that break an enemy ladder |
| 2     | snapback          | Positions where snapback can occur         |
| 3     | capture-in-1      | Groups that can be captured in 1 move      |
| 4     | capture-in-2      | Groups that can be captured in 2 moves     |
| 5     | dead-groups       | Groups with 0 eyes in enclosed area        |

**Key insight for yen-go:** The COUNT of non-zero planes correlates with
puzzle difficulty. A position with 0 active planes is likely trivial;
3+ active planes suggests complex tactics.

```
tactical_complexity = count(plane for plane in 6_planes if any_nonzero(plane))
# 0: trivial, 1-2: focused, 3+: complex multi-tactic
```

---

## Mapping to Yen-Go Pipeline

| GoGoGo Algorithm       | Yen-Go Application                                              | Where                        |
| ---------------------- | --------------------------------------------------------------- | ---------------------------- |
| `trace_ladder`         | Auto-tag `YT[ladder]`, generate YH hint                         | `core/tactical_analyzer.py`  |
| `detect_snapback`      | Auto-tag `YT[snapback]`, validate quality                       | `core/tactical_analyzer.py`  |
| `verify_capture`       | Validate solution correctness, flag trivial captures            | `core/quality.py`            |
| `evaluate_life_death`  | Validate `life-and-death` tagged puzzles, eye counting          | `core/tactical_analyzer.py`  |
| `is_tactical_position` | Content-type classifier input (tactical=practice, not training) | `core/content_classifier.py` |
| Tactical planes count  | Difficulty scoring signal (`core/classifier.py`)                | `core/classifier.py`         |

---

## Implementation Notes for Yen-Go

1. **Board representation:** Use sgfmill's `Board` class (already a dependency),
   not GoGoGo's custom `Board`. Liberty counting via sgfmill's group methods.
2. **No tensor conversion needed:** GoGoGo's `to_tensor()` is for ML training.
   We only need the symbolic analysis functions.
3. **Depth limits:** GoGoGo uses depth 30 for ladder, 4 for capture, 12 for
   life/death. These are good defaults for pipeline analysis.
4. **Performance:** Each analysis function is O(board_size²) per step.
   For 19×19 puzzles with depth limits, expect <10ms per puzzle.
   At ~194K puzzles: ~30 minutes total (parallelizable per-puzzle).
