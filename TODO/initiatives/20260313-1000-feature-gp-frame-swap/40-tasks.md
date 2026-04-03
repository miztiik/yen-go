# Tasks: GP Frame Swap (OPT-1 — Thin Adapter Module)

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Last Updated**: 2026-03-13

---

## Phase 1: Shared Utility Extraction

| Task | Description | File(s) | Depends On | Parallel | Notes |
|------|-------------|---------|-----------|----------|-------|
| T1 | Create `frame_utils.py` with `FrameRegions` dataclass (frozen, no `defense_area`/`offense_area`). Fields: `puzzle_bbox`, `puzzle_region` (`frozenset[tuple[int,int]]` — RC-2), `occupied`, `board_edge_sides`. | `analyzers/frame_utils.py` | — | [P] with T2 | ~20 lines |
| T2 | Extract `detect_board_edge_sides()` to `frame_utils.py`. Pure geometry helper — takes stones + board_size, returns frozenset of edge names. | `analyzers/frame_utils.py` | — | [P] with T1 | ~20 lines. Currently in `tsumego_frame.py` lines 284-301 |
| T3 | Extract `compute_regions()` to `frame_utils.py`. Takes `(position, *, margin=2, board_size=None)` — plain args, NOT `FrameConfig`. Computes bbox, puzzle_region, occupied, board_edge_sides. | `analyzers/frame_utils.py` | → T1, T2 | | ~30-40 lines. Port logic from `tsumego_frame.py` lines 303-352 without `defense_area`/`offense_area` |
| T4 | Write `tests/test_frame_utils.py`. Test: `compute_regions` returns correct bbox, `puzzle_region` is `frozenset[tuple[int,int]]` (RC-2 verification), edge detection, empty position handling. | `tests/test_frame_utils.py` | → T3 | | ~60-80 lines |

## Phase 2: GP Module Enhancement

| Task | Description | File(s) | Depends On | Parallel | Notes |
|------|-------------|---------|-----------|----------|-------|
| T5 | Add `GPFrameConfig` frozen dataclass to `tsumego_frame_gp.py`. Fields: `margin`, `komi`, `ko`, `offence_to_win`. | `analyzers/tsumego_frame_gp.py` | — | [P] with T1-T4 | ~10 lines. Distinct name from BFS `FrameConfig` (RC-1) |
| T6 | Add optional `config: GPFrameConfig | None = None` parameter to `apply_gp_frame()`. If provided, use config fields. If None, use existing keyword arg defaults. | `analyzers/tsumego_frame_gp.py` | → T5 | | ~5 lines. Backward compatible — existing keyword args still work |

## Phase 3: Adapter Layer

| Task | Description | File(s) | Depends On | Parallel | Notes |
|------|-------------|---------|-----------|----------|-------|
| T7 | Create `frame_adapter.py` with `FrameResult` dataclass. Fields: `position`, `frame_stones_added`, `attacker_color`. | `analyzers/frame_adapter.py` | — | [P] with T1-T6 | ~15 lines |
| T8 | Implement `apply_frame(position, *, margin, ko, komi, offence_to_win) → FrameResult`. Wraps `apply_gp_frame()`, maps `GPFrameResult` → `FrameResult`. | `analyzers/frame_adapter.py` | → T7 | | ~20 lines |
| T9 | Implement `remove_frame(framed, original) → Position`. One-liner: `return original.model_copy(deep=True)`. | `analyzers/frame_adapter.py` | → T7 | [P] with T8 | ~3 lines |
| T10 | Implement `validate_frame()` in `frame_adapter.py`. Port from `tsumego_frame.py` lines 777-893. Algorithm-agnostic: connectivity check + dead stone check on any framed `Position`. | `analyzers/frame_adapter.py` | → T7 | [P] with T8 | ~80 lines. Same logic as BFS, but lives in adapter |
| T11 | Write `tests/test_frame_adapter.py`. Tests: `apply_frame` roundtrip, `remove_frame` returns original, `validate_frame` catches dead stones, `player_to_move` preservation (C2), `FrameResult` shape. | `tests/test_frame_adapter.py` | → T8, T9, T10 | | ~80-100 lines |

## Phase 4: Consumer Rewiring

| Task | Description | File(s) | Depends On | Parallel | Notes |
|------|-------------|---------|-----------|----------|-------|
| T12 | Rewire `query_builder.py`: change import from `tsumego_frame.apply_tsumego_frame` to `frame_adapter.apply_frame`. Update call site: `ko_type` str → `ko` bool, extract `.position` from `FrameResult`. | `analyzers/query_builder.py` | → T8 | [P] with T13 | ~6 lines changed. Both try/except import blocks |
| T13 | Rewire `enrich_single.py`: change 2 import sites from `tsumego_frame.compute_regions, FrameConfig` to `frame_utils.compute_regions`. Simplify call: remove `FrameConfig` construction, pass `margin` directly. | `analyzers/enrich_single.py` | → T3 | [P] with T12 | ~8 lines changed (2 callsites × 4 lines each) |

## Phase 4b: Script Updates

| Task | Description | File(s) | Depends On | Parallel | Notes |
|------|-------------|---------|-----------|----------|-------|
| T19 | Simplify `scripts/show_frame.py`: remove `--ko` and `--color` CLI flags, rewire import from `tsumego_frame.apply_tsumego_frame` to `frame_adapter.apply_frame`. Drop `Color` import (no longer needed). Remove `offense_color` variable. Simplify call to `apply_frame(position, margin=args.margin)`. Update `added` count to use `result.frame_stones_added`. Update printed summary to drop ko reference. | `scripts/show_frame.py` | → T8 | [P] with T12, T13 | ~15 lines changed. `probe_frame.py` left as-is (covered by `probe_frame_gp.py`). |

## Phase 5: Cleanup

| Task | Description | File(s) | Depends On | Parallel | Notes |
|------|-------------|---------|-----------|----------|-------|
| T14 | Remove dead `FrameRegions` TYPE_CHECKING import from `liberty.py`. Also remove `from typing import TYPE_CHECKING` if no other TYPE_CHECKING usage. | `analyzers/liberty.py` | — | [P] with T12, T13 | ~3 lines removed |
| T15 | Add `pytestmark = pytest.mark.skip(reason="BFS frame archived")` to `tests/test_tsumego_frame.py`. | `tests/test_tsumego_frame.py` | → T12, T13 | | ~1 line. Tests still exist for reference |
| T16 | Fix `tests/test_frames_gp.py` import: `analyzers.frames_gp` → `analyzers.tsumego_frame_gp`. | `tests/test_frames_gp.py` | — | [P] with T14, T15 | ~1 line |

## Phase 6: Documentation & Verification

| Task | Description | File(s) | Depends On | Parallel | Notes |
|------|-------------|---------|-----------|----------|-------|
| T17 | Update `docs/concepts/tsumego-frame.md`: note GP is now active implementation, BFS archived. Update architecture diagram. | `docs/concepts/tsumego-frame.md` | → T12, T13 | | Doc update |
| T18 | Run full test suite (excluding skipped BFS tests). Verify: new tests pass, existing tests unbroken, no import errors. | — | → T4, T11, T15, T16 | | Regression gate |

---

## Dependency Graph

```
Phase 1 (parallel):
  T1 ──┐
  T2 ──┤
       └── T3 ── T4
  
Phase 2 (parallel with Phase 1):
  T5 ── T6
  
Phase 3 (after T7 base):
  T7 ──┬── T8 ──┐
       ├── T9   ├── T11
       └── T10 ─┘

Phase 4 (after adapter + utils ready):
  T8 ── T12 ──┐
  T3 ── T13 ──┤
  T8 ── T19 ──┤  (show_frame.py simplification)
              └── (Phase 5)

Phase 5 (parallel cleanup):
  T14, T15, T16

Phase 6 (after all):
  T17, T18
```

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 19 |
| New files | 4 (`frame_utils.py`, `frame_adapter.py`, `test_frame_utils.py`, `test_frame_adapter.py`) |
| Modified files | 7 (`tsumego_frame_gp.py`, `query_builder.py`, `enrich_single.py`, `liberty.py`, `show_frame.py`, `test_tsumego_frame.py`, `test_frames_gp.py`) |
| Untouched files | 1 (`tsumego_frame.py` — archived) |
| Doc files | 1 (`docs/concepts/tsumego-frame.md`) |
| Estimated new code | ~250-300 lines (across 4 new files) |
| Estimated changes | ~40 lines changed (across 7 modified files) |
| Total parallel phases | 6 (extensive parallelism in phases 1-3) |
