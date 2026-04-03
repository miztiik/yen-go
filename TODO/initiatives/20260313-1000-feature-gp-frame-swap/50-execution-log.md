# Execution Log: GP Frame Swap

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Last Updated**: 2026-03-13

---

## Phase 1: Shared Utility Extraction

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-1 | T1 — Create `frame_utils.py` with `FrameRegions` dataclass | ✅ completed | `analyzers/frame_utils.py` (97 lines). Frozen dataclass with `puzzle_bbox`, `puzzle_region` (frozenset), `occupied`, `board_edge_sides`. No `defense_area`/`offense_area` per Q6. |
| EX-2 | T2 — Extract `detect_board_edge_sides()` | ✅ completed | In `frame_utils.py`. Pure geometry, takes stones + board_size + margin → frozenset of edge names. |
| EX-3 | T3 — Extract `compute_regions()` | ✅ completed | In `frame_utils.py`. Signature: `(position, *, margin=2, board_size=None) → FrameRegions`. Plain args, no FrameConfig. |
| EX-4 | T4 — Write `tests/test_frame_utils.py` | ✅ completed | 12 tests. Covers: FrameRegions frozen, no defense/offense, detect_board_edge_sides (corner/center/full), compute_regions (empty/single/frozenset-type/margin/board_size/edge). All 12/12 passed. |

## Phase 2: GP Module Enhancement

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-5 | T5 — Add `GPFrameConfig` frozen dataclass | ✅ completed | In `tsumego_frame_gp.py`. Fields: `margin`, `komi`, `ko`, `offence_to_win`. Distinct name from BFS `FrameConfig` (RC-1). |
| EX-6 | T6 — Add optional `config` param to `apply_gp_frame()` | ✅ completed | Optional `config: GPFrameConfig | None = None`. If provided, overrides keyword defaults. Backward compatible. |

### Deviation: Syntax Error Fix

During T11 test execution, a `SyntaxError: invalid decimal literal` at line 221 was discovered in `tsumego_frame_gp.py`. Root cause: a prior session's edit left a stale duplicate `Returns: / GPFrameResult with the framed position. / """` docstring fragment (lines 124-126). Fixed by removing the 3 stale lines.

## Phase 3: Adapter Layer

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-7 | T7 — Create `frame_adapter.py` with `FrameResult` | ✅ completed | `analyzers/frame_adapter.py` (180 lines). `FrameResult` dataclass: `position`, `frame_stones_added`, `attacker_color`. |
| EX-8 | T8 — Implement `apply_frame()` | ✅ completed | Wraps `apply_gp_frame()`, maps `GPFrameResult` → `FrameResult`. Preserves `player_to_move` (C2). |
| EX-9 | T9 — Implement `remove_frame()` | ✅ completed | One-liner: `return original.model_copy(deep=True)`. |
| EX-10 | T10 — Implement `validate_frame()` | ✅ completed | Algorithm-agnostic BFS connectivity + dead stone check. ~80 lines ported from `tsumego_frame.py`. |
| EX-11 | T11 — Write `tests/test_frame_adapter.py` | ✅ completed | 10 tests. Covers: FrameResult fields, apply_frame (returns FrameResult, adds stones, player_to_move preserved C2, white-to-move, ko flag), remove_frame (returns original copy, identity preservation), validate_frame (valid frame, empty frame stones). All 10/10 passed. |

## Phase 4: Consumer Rewiring

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-12 | T12 — Rewire `query_builder.py` | ✅ completed | Both try/except import blocks changed from `tsumego_frame.apply_tsumego_frame` to `frame_adapter.apply_frame`. Call site: `ko_type` str → `ko` bool, extract `.position` from `FrameResult`. |
| EX-13 | T13 — Rewire `enrich_single.py` | ✅ completed | 2 callsites changed from `tsumego_frame.compute_regions, FrameConfig` → `frame_utils.compute_regions`. Removed `FrameConfig` construction, passes `margin` directly. |
| EX-14 | T19 — Simplify `scripts/show_frame.py` | ✅ completed | Removed `--ko`/`--color` CLI flags, dropped `Color` import, rewired to `frame_adapter.apply_frame`, uses `result.frame_stones_added`. |

## Phase 5: Cleanup

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-15 | T14 — Remove dead imports from `liberty.py` | ✅ completed | Removed `TYPE_CHECKING` import and `if TYPE_CHECKING: from analyzers.tsumego_frame import FrameRegions` block. |
| EX-16 | T15 — Skip BFS tests | ✅ completed | Added `pytestmark = pytest.mark.skip(reason="BFS frame archived — GP frame is active (20260313-1000-feature-gp-frame-swap)")` to `test_tsumego_frame.py`. 87 tests correctly skipped. |
| EX-17 | T16 — Fix `test_frames_gp.py` import | ✅ completed | Changed `from analyzers.frames_gp import` to `from analyzers.tsumego_frame_gp import`. 40 tests pass. |

## Phase 6: Documentation & Verification

| ex_id | task | status | evidence |
|-------|------|--------|----------|
| EX-18 | T17 — Update `docs/concepts/tsumego-frame.md` | ✅ completed | Updated Last Updated to 2026-03-13. Added GP Frame Swap notice. Changed "Adopted" → "Active". Updated diagnostic tooling (removed --ko/--color). |
| EX-19 | T18 — Golden Five test suite | ✅ completed | `python -m pytest tests/test_golden5.py`: **6/6 passed** in 285s. KataGo engine started successfully. All 6 puzzle integration tests passed with GP frame active. |

## Summary

| Metric | Value |
|--------|-------|
| Tasks completed | 19/19 |
| New files created | 4 (`frame_utils.py`, `frame_adapter.py`, `test_frame_utils.py`, `test_frame_adapter.py`) |
| Files modified | 8 (`tsumego_frame_gp.py`, `query_builder.py`, `enrich_single.py`, `liberty.py`, `show_frame.py`, `test_tsumego_frame.py`, `test_frames_gp.py`, `docs/concepts/tsumego-frame.md`) |
| Deviations | 1 — syntax error fix in `tsumego_frame_gp.py` (stale docstring from prior edit) |
| Total new test count | 22 (12 frame_utils + 10 frame_adapter) |
| Golden Five | 6/6 passed |
| Consumer tests | 114 passed, 1 skipped |
| GP frame tests | 40/40 passed |
| BFS tests | 87 skipped (intentional) |
