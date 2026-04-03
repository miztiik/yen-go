# Validation Report: GP Frame Swap

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Last Updated**: 2026-03-13

---

## 1. Test Results

| val_id | test suite | command | result | exit_code |
|--------|-----------|---------|--------|-----------|
| VAL-1 | Frame utils unit tests | `pytest tests/test_frame_utils.py` | 12/12 passed | 0 |
| VAL-2 | Frame adapter unit tests | `pytest tests/test_frame_adapter.py` | 10/10 passed | 0 |
| VAL-3 | GP frame tests (existing) | `pytest tests/test_frames_gp.py` | 40/40 passed | 0 |
| VAL-4 | BFS frame tests (skipped) | `pytest tests/test_tsumego_frame.py` | 87 skipped | 0 |
| VAL-5 | Consumer tests (enrich_single, query_builder, sgf_enricher, sprint1_fixes) | `pytest tests/test_enrich_single.py tests/test_query_builder.py tests/test_sgf_enricher.py tests/test_sprint1_fixes.py` | 114 passed, 1 skipped | 0 |
| VAL-6 | Golden Five integration suite | `pytest tests/test_golden5.py -v --tb=short` | 6/6 passed (285s) | 0 |
| VAL-7 | Import chain verification | `python -c "from analyzers.frame_adapter import apply_frame..."` | frame_adapter OK, frame_utils OK | 0 |

## 2. Constraint Verification

| val_id | constraint | verification | status |
|--------|-----------|--------------|--------|
| VAL-8 | C1 — GP algorithm purity | `frame_adapter.py` wraps `apply_gp_frame()` without modifying GP internals. GP module only changed to add `GPFrameConfig` (backward-compatible). | ✅ verified |
| VAL-9 | C2 — `player_to_move` preservation | `test_frame_adapter::TestApplyFrame::test_player_to_move_preserved_c2` — explicit assertion. Also `test_white_to_move`. | ✅ verified |
| VAL-10 | C3 — Consumer stability | `query_builder.py` and `enrich_single.py` rewired via adapter/utils. 114 consumer tests pass. | ✅ verified |
| VAL-11 | C4 — `puzzle_region` frozenset type | `test_frame_utils::TestComputeRegions::test_puzzle_region_is_frozenset_rc2` — explicit isinstance check. | ✅ verified |
| VAL-12 | C5 — Single-file rollback | `frame_adapter.py` is the sole adapter layer. Rollback = change 1 import + 1 call in `frame_adapter.py`. | ✅ verified |
| VAL-13 | RC-1 — FrameConfig distinct from BFS | No shared FrameConfig. GP uses `GPFrameConfig`. BFS `FrameConfig` untouched in archived `tsumego_frame.py`. | ✅ verified |
| VAL-14 | RC-2 — puzzle_region type preserved | `FrameRegions.puzzle_region` typed as `frozenset[tuple[int, int]]`. Test assertion confirms. | ✅ verified |

## 3. Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|---------------|--------|
| VAL-15 | query_builder uses frame_adapter.apply_frame | Import changed, 114 consumer tests pass, Golden Five 6/6 | Match | None | ✅ verified |
| VAL-16 | enrich_single uses frame_utils.compute_regions | Import changed, 2 callsites simplified, consumer tests pass | Match | None | ✅ verified |
| VAL-17 | liberty.py dead import removed | TYPE_CHECKING block removed, no runtime impact | Match | None | ✅ verified |
| VAL-18 | show_frame.py simplified CLI | --ko/--color removed, uses frame_adapter | Match | None | ✅ verified |
| VAL-19 | BFS tests skipped | 87 tests properly skipped with reason message | Match | None | ✅ verified |
| VAL-20 | test_frames_gp import fixed | Changed from `analyzers.frames_gp` to `analyzers.tsumego_frame_gp`, 40/40 pass | Match | None | ✅ verified |
| VAL-21 | tsumego_frame.py (BFS) untouched | File preserved at 1130 lines, still importable for rollback | Match | None | ✅ verified |
| VAL-22 | Golden Five integration with GP frame | KataGo engine starts, frames applied via GP, all 6 puzzles solved correctly | Match | None | ✅ verified |

## 4. Documentation Verification

| val_id | file | update | status |
|--------|------|--------|--------|
| VAL-23 | `docs/concepts/tsumego-frame.md` | Updated: date, GP active notice, "Adopted"→"Active", diagnostic tooling | ✅ verified |

## 5. Summary

All validations pass. No regressions detected. All 19 tasks completed. Golden Five integration suite confirms GP frame swap works end-to-end with KataGo.
