# Tasks — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Date**: 2026-03-20

## Task List

| task_id | title | files | depends | parallel | est_lines |
|---------|-------|-------|---------|----------|-----------|
| T1 | Remove `skipped_all_almost` all-skip gate (P1) | `sgf_enricher.py` | — | [P] | ~15 removed |
| T2 | Replace curated gate with count + cap (P3) | `sgf_enricher.py` | T1 (same file) | — | ~20 modified |
| T3 | Fix `almost_correct` template (P2) | `config/teaching-comments.json` | — | [P] | ~1 |
| T4 | Stop passing `correct_first_coord` for almost_correct | `teaching_comments.py` | — | [P] | ~4 |
| T5 | Add dedup: skip AI branch if coord already curated | `sgf_enricher.py` | T2 | — | ~5 |
| T6 | Remove dead `_has_existing_refutation_branches` if no other callers | `sgf_enricher.py` | T2 | — | ~25 removed |
| T7 | Tests: Scenario A (all-almost, now gets branches) | `tests/` | T1, T3, T4 | — | ~30 |
| T8 | Tests: Scenario D (curated + AI coexist, capped) | `tests/` | T2, T5 | — | ~40 |
| T9 | Tests: Scenario B/C (unchanged, regression check) | `tests/` | T1 | — | ~20 |
| T10 | Tests: Template has no `{!xy}`, no coordinate leak | `tests/` | T3, T4 | — | ~15 |
| T11 | Tests: Cap logic (2 curated + 3 AI → 1 AI added) | `tests/` | T2 | — | ~20 |
| T12 | Run regression test suite | — | T7-T11 | — | 0 |
| T13 | Update AGENTS.md | `tools/puzzle-enrichment-lab/AGENTS.md` | T1-T6 | — | ~10 |

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1, T2, T5, T6 | `sgf_enricher.py` | Sequential within lane (same file) | not_started |
| L2 | T3 | `config/teaching-comments.json` | none — [P] with L1 | not_started |
| L3 | T4 | `teaching_comments.py` | none — [P] with L1, L2 | not_started |
| L4 | T7, T8, T9, T10, T11 | `tests/` | L1, L2, L3 complete | not_started |
| L5 | T12 | — | L4 complete | not_started |
| L6 | T13 | `AGENTS.md` | L1, L2, L3 complete | not_started |

## Detailed Task Descriptions

### T1: Remove `skipped_all_almost` all-skip gate
- Delete `skipped_all_almost = False` (line 414)
- Delete `all_almost` check block (lines 420–430)
- Remove `and not skipped_all_almost` from YR fallback condition (line 459)
- Verify: the `else` branch that calls `_build_refutation_branches()` becomes the only path

### T2: Replace curated gate with count + cap
- Remove `not _has_existing_refutation_branches(root)` from condition (line 416)
- Add new helper `_count_existing_refutation_branches(root) -> int`
- Load `max_refutation_root_trees` from `katago-enrichment.json` config
- Compute `budget = max(0, max_total - existing_count)`
- Slice: `refutation_branches = _build_refutation_branches(...)[:budget]`

### T3: Fix `almost_correct` template
- In `config/teaching-comments.json`, change:
  `"Close — {!xy} is slightly better."` → `"Close, but not the best move."`

### T4: Stop passing `correct_first_coord` for almost_correct
- In `teaching_comments.py`, for both `classification.causal` and `classification.default_moves` loops:
  change `coord=correct_first_coord` to `coord=""` when condition is `almost_correct`

### T5: Add dedup for AI branches vs curated
- Before adding AI branches, collect coordinates of existing curated wrong branches
- Filter: skip any AI branch whose `wrong_move` coordinate already exists in curated set

### T6: Remove dead `_has_existing_refutation_branches`
- Grep for callers. If none remain, delete the function (~25 lines).
- If callers exist elsewhere (e.g., observability, tests), keep.

### T7–T11: Tests (see per-task descriptions above)

### T12: Regression suite
- Run: `pytest tools/puzzle-enrichment-lab/tests/ --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -m "not slow" -q --no-header --tb=short`
- Verify: 0 failures

### T13: Update AGENTS.md
- Remove mention of "curated gate blocks AI wrongs" if present
- Update enrichment flow description to reflect direct branch building with cap

Last Updated: 2026-03-20
