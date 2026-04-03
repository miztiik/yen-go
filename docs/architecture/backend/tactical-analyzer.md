# Tactical Analyzer Architecture

> **See also**:
>
> - [Architecture: Enrichment](./enrichment.md) — Enrichment pipeline overview
> - [Architecture: Tagging Strategy](./tagging-strategy.md) — Tag detection design
> - [Concepts: Tags](../../concepts/tags.md) — Tag taxonomy and definitions
> - [Concepts: Quality](../../concepts/quality.md) — YQ/YX metrics

**Last Updated**: 2026-02-26

**Implementation**: [`core/tactical_analyzer.py`](../../../backend/puzzle_manager/core/tactical_analyzer.py)

---

## Overview

The tactical analyzer performs board-level pattern detection on puzzle positions. Unlike the comment-based `tagger.py` which extracts evidence from SGF comments, the tactical analyzer simulates moves on the Board to detect structural patterns (ladders, snapbacks, eye shapes, group status).

It runs during the **analyze** stage after technique detection, merging its auto-tags with existing tags via the ENRICH_IF_ABSENT policy.

---

## Design Decisions

### Why a Separate Module from `tagger.py`?

The existing tagger (`core/tagger.py`) focuses on comment-keyword detection with confidence scoring. The tactical analyzer uses a fundamentally different approach: **board simulation**. Keeping them separate:

1. **Single Responsibility** — Comment parsing vs. board analysis are orthogonal concerns
2. **Independent testability** — Board positions can be unit-tested without SGF parsing
3. **Composability** — Tags from both sources merge at the analyze stage level

### Board Simulation Over Heuristics

All detectors work by actually playing moves on a `Board` copy:

- **Ladder detection**: Simulates the full chase sequence (runner extends → chaser re-ataris) with 1-step lookahead for move selection
- **Snapback detection**: Plays sacrifice, simulates opponent capture, verifies group size comparison
- **Capture pattern**: Plays the first move and counts immediate captures
- **Eye counting**: Flood-fills enclosed empty regions surrounded by the target group

This ensures **high precision** — a ladder is only reported if the chase actually works for ≥3 iterations on the board.

### Error Isolation with `_safe_detect()`

Each detector is wrapped in `_safe_detect()` which catches all exceptions and returns a default value. A single buggy detector never crashes the pipeline. Errors are logged with the puzzle's trace_id for debugging.

---

## Algorithm Design Decisions

All algorithms are original implementations using board simulation. They are **not** ports from external Go libraries. The docstrings and code are our own, informed by standard Go pattern definitions.

### Ladder: 1-Step Lookahead for Move Selection

**Problem**: When the chaser puts the runner in atari, the runner extends. The chaser then needs to re-atari from one of the runner's 2 liberties. A naive implementation picks the first candidate sorted by `(x, y)` coordinates. This fails because **sort order doesn't correlate with the correct chase diagonal** — picking the wrong atari lets the runner escape with 3+ liberties on the next iteration.

**Solution**: For each atari candidate, simulate one more step: play the candidate, let the runner extend, check if the runner still has exactly 2 liberties. If yes, this candidate continues the ladder shape. This adds one extra `Board.copy()` per candidate per iteration — negligible cost for correctness.

**Threshold**: ≥3 chase iterations confirms a ladder. This filters out short atari-escape sequences that aren't true ladders.

**Test coverage**: Wall-backed ladder position with B stones forming a wall at column 1, W(2,2) chased diagonally down. The wall forces the runner into the correct diagonal; without the wall, the runner escapes.

### Snapback: Group-Size Comparison Without Recapture

**Problem**: The natural algorithm is: sacrifice → opponent captures → player recaptures. But the `Board.play()` method's ko detection triggers a false positive on the recapture. When opponent captures a single stone at point P, P becomes an empty intersection. If the opponent's new group has 1 liberty at P, playing at P looks like an immediate recapture of a single stone — which the Board interprets as a ko violation.

**Solution**: Skip the recapture entirely. After the opponent captures our bait, check:

1. Opponent's group at the capture point has exactly 1 liberty
2. Opponent's group size > number of stones we sacrificed

This is equivalent to confirming the recapture would net more stones. It's a deliberate shortcut that avoids modifying `Board.play()`'s ko logic, which is used across the entire codebase.

**Why not fix the Board's ko detection?** The ko rule (`Board.play()` lines 207-213) sets `_ko_point` whenever exactly 1 stone is captured and the capturing group has exactly 1 liberty. This is correct for actual ko situations. A snapback is the edge case where the recapture captures _more_ stones, which means it's not really a ko — but the Board checks the _capturing_ move, not the _result_. Fixing this would require the Board to distinguish "single stone captured" from "multi-stone group will be captured at the recapture point," which adds complexity to a low-level primitive used everywhere.

**Test coverage**: Position with B surrounding 3 W stones + 1 W stone at (1,3), B plays (1,1) as sacrifice with 1 liberty. W captures at (1,2), forming a 2-stone group {(1,2),(1,3)} with 1 liberty at (1,1). Group size 2 > sacrifice size 1 → snapback confirmed.

### Hane at Head of Two: Directional Extension Check

**Problem**: The initial implementation checked `len(opponent_neighbors) == 2` where both belong to the same 2-stone group. This is **geometrically impossible** — with orthogonal adjacency on a Go board, a single point can be adjacent to at most 1 stone of a 2-stone line (they form a straight line, and a point can only touch one end or be beside one stone, not both simultaneously via orthogonal adjacency).

**Solution**: Check directional extension instead:

1. Find an adjacent opponent stone `n` belonging to a 2-stone group
2. Get the other stone `other` in the group
3. Compute direction vector: `dx = n.x - other.x`, `dy = n.y - other.y`
4. The first move must be at `n + (dx, dy)` — i.e., extending the line beyond `n`

This correctly identifies the "head" position: the point that continues the line of two stones.

**Test coverage**: W(2,1) and W(2,2) forming a vertical line. B plays (2,0) which is at the head (2,2→2,1 direction extended to 2,0).

### Eye Counting: Flood-Fill with Neighbor Threshold

Eyes are counted by finding enclosed empty regions where all orthogonal neighbors of each empty point belong to the target group. Corner and edge points have 2-3 neighbors (not 4), which naturally makes them easier to enclose — this matches real Go rules where corner eyes require fewer surrounding stones.

**Not a liberty count** — liberties and eyes are different concepts. A group can have many liberties but no eyes (open-ended chains).

### Seki Detection: Mutual Low-Liberty Heuristic

True seki detection requires life-and-death reading which is beyond a simple board analyzer. We use a heuristic: find adjacent groups of opposite colors where both have 1-2 liberties and share at least one liberty. This catches the most common seki shapes but may miss complex ones — acceptable for tagging purposes where false negatives are preferable to false positives.

### Instinct Patterns: Board-State Inspection

The four instinct patterns (extend-from-atari, connect-against-peep, hane-at-head-of-two, block-thrust) are **not** simulation-based — they inspect the board state _before_ the first move is played. This is because instincts are about recognizing the _shape_ that motivates the move, not simulating its consequences.

---

## Architecture

```
analyze_tactics(game: SGFGame) → TacticalAnalysis
    │
    ├── _build_board(game) → Board
    │
    ├── detect_ladder(board, first_move, color) → LadderResult | None
    ├── detect_snapback(board, first_move, color) → bool
    ├── detect_capture_pattern(board, first_move, color) → CaptureType
    ├── count_eyes(board, group) → int
    ├── assess_group_status(board, group) → GroupStatus
    ├── find_weak_groups(board, color) → list[WeakGroup]
    ├── detect_seki(board) → bool
    ├── detect_instinct_pattern(board, first_move, color) → InstinctType
    │
    ├── derive_auto_tags(analysis) → list[str]
    ├── generate_tactical_hint(analysis) → str | None
    ├── validate_position(board, game, analysis) → (bool, list[str])
    └── compute_tactical_complexity(analysis) → int
```

---

## Detector Summary

| Detector                             | Output            | Tag(s) Produced                | Threshold             |
| ------------------------------------ | ----------------- | ------------------------------ | --------------------- |
| `detect_ladder`                      | `LadderResult`    | `ladder`                       | depth ≥ 3             |
| `detect_snapback`                    | `bool`            | `snapback`                     | sacrifice recaptured  |
| `detect_capture_pattern`             | `CaptureType`     | `capture` (fallback)           | —                     |
| `count_eyes` / `assess_group_status` | `GroupStatus`     | `life-and-death`               | dead/critical groups  |
| `find_weak_groups`                   | `list[WeakGroup]` | `life-and-death`               | ≤2 liberties          |
| `detect_seki`                        | `bool`            | `seki`                         | mutual 1-2 lib groups |
| `detect_instinct_pattern`            | `InstinctType`    | `escape`, `connection`, `hane` | pattern-specific      |

### Ladder Detection Algorithm

See [Algorithm Design Decisions → Ladder](#ladder-1-step-lookahead-for-move-selection) for full rationale.

1. Play first move → check if adjacent opponent group is newly in atari
2. Trace chase: runner extends at single liberty → must get exactly 2 liberties
3. Chaser picks the atari move via **1-step lookahead**: for each candidate, simulate the runner's next extension and prefer the move where the runner still gets exactly 2 libs (correct ladder diagonal)
4. Chase ≥3 iterations → confirmed ladder

### Snapback Detection Algorithm

See [Algorithm Design Decisions → Snapback](#snapback-group-size-comparison-without-recapture) for full rationale.

1. Play first move → check if our group has exactly 1 liberty (bait)
2. Simulate opponent capturing bait at that liberty
3. Check if opponent's new group at capture point has exactly 1 liberty
4. Compare group sizes: `opponent_group_size > sacrificed_stones` → snapback
5. Recapture is **not** played (avoids false ko detection — see design decisions)

---

## Integration Point

In `stages/analyze.py`, after `detect_techniques()`:

```python
tactical = analyze_tactics(game)
auto_tags = derive_auto_tags(tactical)
# Merge: only add tags not already present
existing_tags = set(current_tags)
new_tags = [t for t in auto_tags if t not in existing_tags]
tags = sorted(set(current_tags + new_tags))
```

The ENRICH_IF_ABSENT policy ensures source-provided tags are never overwritten.

---

## Data Types

| Type               | Fields                                                         | Purpose                             |
| ------------------ | -------------------------------------------------------------- | ----------------------------------- |
| `TacticalAnalysis` | ladder, snapback, capture, groups, weak_groups, seki, instinct | Container for all detection results |
| `LadderResult`     | outcome, depth, breaker_point                                  | Ladder chase outcome                |
| `WeakGroup`        | stones, liberties, status                                      | Group with ≤2 liberties             |
| `GroupStatus`      | Enum: ALIVE, DEAD, CRITICAL, UNSETTLED                         | Life/death assessment               |
| `CaptureType`      | Enum: NONE, TRIVIAL, FORCED, NET                               | Capture classification              |
| `InstinctType`     | Enum: NONE, EXTEND_FROM_ATARI, CONNECT, HANE_HEAD_OF_TWO       | Instinct move types                 |

---

## Future Work (Phase 2-4)

- **Hint integration**: Feed `generate_tactical_hint()` into `core/hints.py` for YH property
- **Quality scoring**: Use `compute_tactical_complexity()` as input to YQ metrics
- **Classifier enhancement**: Feed tactical patterns into difficulty classification
