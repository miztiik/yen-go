# Plan: Tsumego Frame Legality & Correctness

**Last Updated**: 2026-03-11
**Selected Option**: OPT-1 (Inline Validation)

---

## 1. Architecture & Design

### 1.1 Approach: Validate-and-Skip

All frame stone placements (fill, border, ko-threat) pass through validation guards before being added. If a placement would create an illegal position or harm puzzle stones, it is silently skipped. This is a conservative approach — the frame may have slightly fewer stones in edge cases, but KataGo's ownership head is robust to minor stone count variations.

### 1.2 New Private Functions in `tsumego_frame.py`

**Liberty counting** (~30 lines):

```python
def _count_group_liberties(
    coord: tuple[int, int],
    color: Color,
    occupied: dict[tuple[int, int], Color],
    board_size: int,
) -> int:
```

Standard BFS/flood-fill to find the connected group containing `coord` and count its liberties (empty adjacent intersections). `occupied` is a dict mapping `(x, y) → Color` for all stones on the board.

**Puzzle stone protection** (~15 lines):

```python
def _would_harm_puzzle_stones(
    coord: tuple[int, int],
    candidate_color: Color,
    puzzle_stones: frozenset[tuple[int, int]],
    occupied: dict[tuple[int, int], Color],
    board_size: int,
) -> bool:
```

After hypothetically adding the candidate stone, check each puzzle stone group's liberties. Returns True if any puzzle group would have zero liberties.

**Eye detection** (~30 lines):

```python
def _is_eye(
    coord: tuple[int, int],
    color: Color,
    occupied: dict[tuple[int, int], Color],
    board_size: int,
) -> bool:
```

Returns True if `coord` is a single-point or two-point eye of `color`. A single-point eye: all 4 (or 2-3 for edge/corner) neighbours are same-color stones, and at least 3/4 (or all for edge/corner) diagonals are same-color or off-board. A two-point eye: both points are empty, all non-shared neighbours are same-color, shared neighbours exist.

**Full-board check** (~5 lines):

```python
def _has_frameable_space(
    regions: FrameRegions,
    board_size: int,
    min_ratio: float = 0.05,
) -> bool:
```

Returns False when frameable area is less than `min_ratio` of total board.

### 1.3 Modifications to Existing Functions

**`fill_territory()`** (line ~328):
- Build `occupied` dict from `regions.occupied` at start of function
- Before each `stones.append()`, run 3 guards:
  1. Check `_count_group_liberties()` > 0 for the candidate stone
  2. Check `_would_harm_puzzle_stones()` returns False
  3. Check `_is_eye()` returns False (for defender color eyes)
- Track skip counters (illegal, puzzle-protect, eye)
- Return tuple `(stones, skip_stats)` or add stats to a separate tracking mechanism

**`place_border()`** (line ~382):
- Same guards before each `stones.append()`

**`build_frame()`** (line ~568):
- If `_has_frameable_space()` returns False, return early with minimal or no frame
- Pass skip counters to `FrameResult`
- Compute and log density metric: `len(all_frame_stones) / frameable_count`

**`guess_attacker()`** (line ~125):
- Replace `return Color.BLACK` tie-breaker with PL-based tie-breaker
- Add `logger.info` when heuristic result disagrees with PL

### 1.4 Data Model Changes

**`FrameResult`** — add fields:
```python
@dataclass
class FrameResult:
    position: Position
    frame_stones_added: int
    attacker_color: Color
    normalized: bool
    stones_skipped_illegal: int = 0
    stones_skipped_puzzle_protect: int = 0
    stones_skipped_eye: int = 0
    fill_density: float = 0.0
```

### 1.5 Data Audit Script

Create `tools/puzzle-enrichment-lab/scripts/frame_audit.py` that:
1. Loads all SGF files from `tests/fixtures/scale/` and `tests/fixtures/calibration/`
2. Parses each into a Position
3. Runs `build_frame()` with default FrameConfig
4. Reports: total puzzles, illegal placements skipped, puzzle protections triggered, eyes detected, PL-heuristic disagreements, density stats (min/max/mean/median)
5. Outputs a summary table

### 1.6 Inviolate Rule Comment

Add code comment to `build_frame()` documenting the `player_to_move` preservation as an inviolate rule.

---

## 2. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Liberty counting BFS has performance regression | Low | Low | Frame is offline; BFS on 19x19 is <1ms. Only called for frame stones. |
| Skip-heavy frames produce poor KataGo input | Low | Medium | Data audit validates on real corpus. If >20% of placements skipped, investigate. |
| Eye detection false positives | Low | Low | Conservative: only skip if all neighbours are same color. Under-detection is safe. |
| 120-line threshold (MH-1) exceeded | Low | Low | Liberty+puzzle-protect+eye+fullboard helpers estimated at ~80-100 lines. Extract if exceeded. |

---

## 3. Must-Hold Constraints (from Governance)

| MH-ID | Constraint | Implementation |
|-------|-----------|----------------|
| MH-1 | Extract to `liberty.py` if helpers > 120 lines | Measure after implementation. Estimated ~80-100 lines. |
| MH-2 | Skip counters in FrameResult | New fields: `stones_skipped_illegal`, `stones_skipped_puzzle_protect`, `stones_skipped_eye` |
| MH-3 | PL disagreement logging | `logger.info("Attacker heuristic (%s) disagrees with PL-based inference (%s)", ...)` |
| MH-4 | Density metric logged | `fill_density = stones_added / frameable_area` in FrameResult + `logger.debug` |

---

## 4. Documentation Plan

| doc_action | file | why_updated |
|-----------|------|-------------|
| update | `docs/concepts/tsumego-frame.md` | Document legality validation, eye detection, PL tie-breaker, density metric |

---

## 5. Test Strategy

### Unit Tests (in existing `tests/test_tsumego_frame.py`)

| Test | Finding |
|------|---------|
| `test_fill_skips_illegal_placement` | F1/F8 — frame stone that would have 0 liberties is skipped |
| `test_fill_protects_puzzle_stones` | F2/F10 — frame stone that would capture puzzle stones is skipped |
| `test_fill_respects_single_eye` | F20 — single-point eye of defender is not filled |
| `test_fill_respects_two_point_eye` | F20 — two-point eye formation is not filled |
| `test_guess_attacker_pl_tiebreaker` | F25 — when heuristics tie, PL determines attacker |
| `test_guess_attacker_pl_disagreement_logged` | F25/MH-3 — logger.info emitted on disagreement |
| `test_frame_result_skip_counters` | MH-2 — FrameResult contains correct skip counts |
| `test_full_board_skips_fill` | F11 — nearly-full board returns early |
| `test_density_metric_computed` | MH-4 — fill_density field populated |

### Data Audit (one-time script)

- Run `frame_audit.py` on all fixtures
- Record results in `15-research.md`
- If 0 illegal/puzzle-capture triggers found on the full corpus, the legality engine is a safety net (no regression, correct by construction)
