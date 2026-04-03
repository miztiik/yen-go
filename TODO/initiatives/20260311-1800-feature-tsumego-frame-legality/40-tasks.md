# Tasks: Tsumego Frame Legality & Correctness

**Last Updated**: 2026-03-12
**Selected Option**: OPT-1 (Inline Validation)

---

## Task Graph

| Task | Title | File(s) | Depends On | [P]arallel | Status |
|------|-------|---------|------------|------------|--------|
| T1 | Data audit script | `scripts/frame_audit.py` | — | [P] with T2 | deferred (D4) |
| T2 | Add `count_group_liberties()` helper | `analyzers/liberty.py` | — | [P] with T1 | ✅ completed |
| T3 | Add `would_harm_puzzle_stones()` helper | `analyzers/liberty.py` | T2 | | ✅ completed |
| T4 | Add `is_eye()` helper (single + two-point) | `analyzers/liberty.py` | T2 | [P] with T3 | ✅ completed |
| T5 | Add `has_frameable_space()` helper | `analyzers/liberty.py` | — | [P] with T2 | ✅ completed |
| T6 | Add skip counters + density to `FrameResult` | `tsumego_frame.py` | — | [P] with T2 | ✅ completed |
| T7 | Wire validation guards into `fill_territory()` | `tsumego_frame.py` | T2, T3, T4, T6 | | ✅ completed |
| T8 | Wire validation guards into `place_border()` | `tsumego_frame.py` | T7 | | ✅ completed |
| T9 | Wire `has_frameable_space()` into `build_frame()` early return | `tsumego_frame.py` | T5 | | ✅ completed |
| T10 | Add PL tie-breaker to `guess_attacker()` | `tsumego_frame.py` | — | [P] with T2 | ✅ completed |
| T11 | Add inviolate rule comment to `build_frame()` | `tsumego_frame.py` | — | [P] with T10 | ✅ completed |
| T12 | Wire density metric logging in `build_frame()` | `tsumego_frame.py` | T6, T9 | | ✅ completed |
| T13 | Unit tests: liberty counting | `tests/test_tsumego_frame.py` | T2 | | ✅ completed (existing tests cover) |
| T14 | Unit tests: puzzle protection | `tests/test_tsumego_frame.py` | T3, T7 | | not-started |
| T15 | Unit tests: eye detection | `tests/test_tsumego_frame.py` | T4, T7 | | not-started |
| T16 | Unit tests: PL tie-breaker + disagreement log | `tests/test_tsumego_frame.py` | T10 | | not-started |
| T17 | Unit tests: full-board skip + density metric | `tests/test_tsumego_frame.py` | T9, T12 | | not-started |
| T18 | Unit tests: skip counters in FrameResult | `tests/test_tsumego_frame.py` | T6, T7 | | not-started |
| T19 | Run data audit on fixtures, record in 15-research.md | `scripts/frame_audit.py`, `15-research.md` | T1, T7 | | deferred (D4) |
| T20 | Regression: run existing frame tests + regression tests | — | T7, T8, T9, T10 | | ✅ completed |
| T21 | Line count check (MH-1): extract to `liberty.py` | `analyzers/liberty.py` | T7, T8, T9 | | ✅ completed (D1) |
| T22 | Update `docs/concepts/tsumego-frame.md` | `docs/concepts/tsumego-frame.md` | T20 | | ✅ completed |

---

## Test Remediation Tasks (added 2026-03-12, post-implementation review)

Gov review RC-1 identified 9 planned tests not implemented. These are the remaining test tasks.

| Task | Title | File(s) | [P]arallel | Status |
|------|-------|---------|------------|--------|
| T14a | Test fill skips illegal placement (F1/F8) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T14b | Test fill protects puzzle stones (F2/F10) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T15a | Test fill respects single-point eye (F20) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T15b | Test fill respects two-point eye (F20) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T16a | Test guess_attacker PL tie-breaker (F25) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T16b | Test guess_attacker PL disagreement logged (MH-3) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T17a | Test full-board early return (F11) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T17b | Test density metric in FrameResult (MH-4) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |
| T18a | Test skip counters in FrameResult (MH-2) | `tests/test_tsumego_frame.py` | [P] | ✅ completed |

---

## Task Details

### T1: Data Audit Script
Create `tools/puzzle-enrichment-lab/scripts/frame_audit.py`:
- Parse all SGF files from `tests/fixtures/scale/` (scale-100, scale-1k, scale-10k) and `tests/fixtures/calibration/`
- For each: parse to Position, run `build_frame()`, collect skip counters, density metrics, PL-heuristic disagreements
- Output summary table: total, illegals, puzzle-protects, eyes, PL disagreements, density stats

### T2: Liberty Counting
Add `_count_group_liberties(coord, color, occupied, board_size) -> int`:
- BFS from `coord` through same-color stones
- Count empty adjacent intersections (unique)
- `occupied: dict[(x,y), Color]` for O(1) lookup

### T3: Puzzle Stone Protection
Add `_would_harm_puzzle_stones(coord, candidate_color, puzzle_stones, occupied, board_size) -> bool`:
- Hypothetically add candidate at `coord`
- For each puzzle stone group adjacent to `coord`, check liberties
- Return True if any puzzle group would have 0 liberties

### T4: Eye Detection
Add `_is_eye(coord, color, occupied, board_size) -> bool`:
- Single-point: all neighbors same color or off-board; ≥3/4 diagonals (≥all for edge/corner)
- Two-point: both points empty, share a neighbor, all non-shared neighbors same color

### T5: Full-Board Check
Add `_has_frameable_space(regions, board_size, min_ratio=0.05) -> bool`:
- `frameable = board_size² - len(regions.occupied) - len(regions.puzzle_region)`
- Return `frameable / (board_size²) >= min_ratio`

### T6: FrameResult Extension
Add `stones_skipped_illegal`, `stones_skipped_puzzle_protect`, `stones_skipped_eye`, `fill_density` fields.

### T7-T8: Wire Validation Guards
In `fill_territory()` and `place_border()`, before each `stones.append()`:
1. Build occupied dict from all placed stones + existing stones
2. Check liberty, puzzle-protect, eye guards
3. Track skip counters

### T9: Full-board early return
In `build_frame()`, check `_has_frameable_space()` before computing regions. If False→ return with empty frame.

### T10: PL Tie-Breaker
In `guess_attacker()`, replace `return Color.BLACK` (line ~168) with:
```python
# PL tie-breaker: in tsumego, player_to_move = defender
if position.player_to_move:
    pl_attacker = _opposite(position.player_to_move)
    heuristic_attacker = Color.BLACK  # would have been the arbitrary fallback
    if pl_attacker != heuristic_attacker:
        logger.info(
            "Attacker heuristic tie-break (BLACK) disagrees with PL-based inference (%s)",
            pl_attacker.value,
        )
    return pl_attacker
return Color.BLACK
```

### T11: Inviolate Rule Comment
Add comment above `player_to_move=norm.position.player_to_move` in `build_frame()`:
```python
# INVIOLATE RULE: player_to_move is preserved from the original SGF PL property.
# It must NEVER be altered by the framing process. KataGo's policy head
# conditions on player_to_move; altering it changes the AI's move recommendations.
```

### T19: Data Audit Execution
Run the audit script, record results in `15-research.md`:
- Total puzzles scanned
- Illegal placements found (before fix, if any)
- Puzzle-protections triggered
- Eye detections
- PL-heuristic disagreements
- Density distribution

### T21: Line Count Check
After all implementation tasks, count new lines added. If > 120, extract to `analyzers/liberty.py`.

---

## Test Remediation Details

### T14a: Test Fill Skips Illegal Placement (F1/F8)
**File:** `tests/test_tsumego_frame.py`
**Class:** `TestFillTerritory` or new `TestLegalityGuards`

Construct a position where a frame placement would leave the stone with 0 liberties (e.g., a surrounded intersection). Call `fill_territory()` and verify `skip_stats["illegal"] > 0` in the returned tuple. Also verify the illegal coordinate is NOT in the output stones.

```python
def test_fill_skips_illegal_placement(self):
    # Position with a single hole surrounded by opponent stones — filling it is suicide
    pos = Position(board_size=9, stones=[...], player_to_move=Color.BLACK)
    regions = compute_regions(pos, FrameConfig(board_size=9))
    stones, skip_stats = fill_territory(pos, regions, Color.WHITE)
    assert skip_stats["illegal"] > 0
    coords = {(s.x, s.y) for s in stones}
    assert (trapped_x, trapped_y) not in coords  # no suicide stone placed
```

### T14b: Test Fill Protects Puzzle Stones (F2/F10)
**File:** `tests/test_tsumego_frame.py`

Construct a position where placing a frame stone would capture adjacent puzzle stones by removing their last liberty. Call `fill_territory()` with `puzzle_stone_coords` set, verify `skip_stats["puzzle_protect"] > 0`.

### T15a: Test Fill Respects Single-Point Eye (F20)
**File:** `tests/test_tsumego_frame.py`

Construct a position with a single-point defender eye in the fill region. Call `fill_territory()`, verify `skip_stats["eye"] > 0` and the eye coordinate is not filled.

### T15b: Test Fill Respects Two-Point Eye (F20)
Same as T15a but construct a two-point eye pattern. Verify both eye points are skipped.

### T16a: Test PL Tie-Breaker (F25)
**File:** `tests/test_tsumego_frame.py`

Construct a symmetric position where stone-count, edge-distance, and cover-side heuristics all tie. Set `player_to_move=Color.WHITE`. Call `guess_attacker()`. Assert returns `Color.BLACK` (opposite of PL). Then test with `player_to_move=Color.BLACK`, assert `Color.WHITE`.

Note: existing tests `test_no_stones_returns_pl_based` and `test_no_stones_white_to_move` partially cover this. T16a should test the **tie-break path specifically** (equal stones on both sides, equal edge distance).

### T16b: Test PL Disagreement Logged (MH-3)
**File:** `tests/test_tsumego_frame.py`

Same symmetric position as T16a with `player_to_move=Color.WHITE` (so PL-based attacker = BLACK, which matches the default `Color.BLACK` fallback → no log). Then construct with `player_to_move=Color.BLACK` (PL-based attacker = WHITE, disagrees with BLACK fallback → log). Use `caplog` to assert `"disagrees"` appears in log output.

### T17a: Test Full-Board Early Return (F11)
**File:** `tests/test_tsumego_frame.py`

Construct a position that covers >95% of the board (e.g., 17x17+ stones on a 19x19). Call `build_frame()`. Assert `result.frame_stones_added == 0` (early return). Use `caplog` to verify warning logged.

### T17b: Test Density Metric in FrameResult (MH-4)
**File:** `tests/test_tsumego_frame.py`

Call `build_frame()` on a standard corner position. Assert `result.fill_density > 0.0` and `result.fill_density <= 1.0`.

### T18a: Test Skip Counters in FrameResult (MH-2)
**File:** `tests/test_tsumego_frame.py`

Call `build_frame()` on a standard corner position. Assert the skip counter fields exist and are `>= 0`: `result.stones_skipped_illegal`, `result.stones_skipped_puzzle_protect`, `result.stones_skipped_eye`. With a standard corner puzzle, most should be 0 — the test verifies the fields are populated, not that they trigger.
