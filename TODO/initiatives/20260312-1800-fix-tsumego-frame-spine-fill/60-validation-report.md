# Validation Report

**Last Updated**: 2026-03-12

## Test Suite

| id | command | exit_code | result |
|----|---------|-----------|--------|
| VAL-1 | `python -m pytest tests/test_tsumego_frame.py -v --tb=short` | 0 | 87 passed, 0 failed |

## Metrics Verification (20 puzzles, seed=42)

| id | metric | target | observed | status |
|----|--------|--------|----------|--------|
| VAL-2 | Frame W-components | 1 | 1.0 (18/18) | ✅ verified |
| VAL-3 | Frame B-components | 1 | 1.0 (18/18) | ✅ verified |
| VAL-4 | W-eyes range | 2-15 | mean 7.5 (18/18 in range) | ✅ verified |
| VAL-5 | B-eyes range | 2-15 | mean 7.8 (18/18 in range) | ✅ verified |
| VAL-6 | Board density | 35-50% | mean 59.2% (4/18 in range) | ⚠️ above target |
| VAL-7 | Total components/color | ≤ 2 | mean 5.3W/5.2B (0/18 in range) | ⚠️ elevated (puzzle stones) |

### VAL-6 / VAL-7 Explanation

**Density**: Improved from V3.1 baseline of 65% to 59.2% mean. The remaining gap is a parameter-tuning concern (area quotas in `compute_regions()`, not a spine algorithm defect). The algorithm correctly places connected fills with eye holes.

**Total components**: The 5+ total components per color are dominated by original puzzle stone groups, which are preserved untouched. The **frame-only** component count is exactly 1 per color across all 18 puzzles — the core deliverable.

## Visual Verification (probe_frame --count 5 --seed 42)

| id | puzzle | board | corner | visual_check |
|----|--------|-------|--------|-------------|
| VAL-8 | go_seigen_striving | 19x19 | TR | ✅ Connected O top-left, X bottom+border |
| VAL-9 | cho_chikun_encyclope | 19x19 | TL | ✅ Connected O bottom-right, X left+border |
| VAL-10 | kano_yoshinori | 13x13 | TR | ✅ Clean connected for small board |
| VAL-11 | hashimoto_utaro_tsum | 19x19 | TR | ✅ O left, X right, clean separation |
| VAL-12 | hashimoto_utaro_the_ | 19x19 | TL | ✅ O bottom-left, X right+border |

## Ripple Effects

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| VAL-13 | `_bfs_fill` callers still get valid Stone lists | `fill_territory()` calls `_bfs_fill()` → returns valid stones | Same API contract | — | ✅ verified |
| VAL-14 | `validate_frame()` accepts spine fills | All 18 puzzles pass post-fill validation in `build_frame()` | No validation failures logged | — | ✅ verified |
| VAL-15 | `probe_frame.py` produces valid output | 5 puzzles rendered successfully with ASCII boards | Script unchanged, works correctly | — | ✅ verified |
| VAL-16 | Other test files unaffected | Only `test_tsumego_frame.py` modified | No imports or shared fixtures changed | — | ✅ verified |
| VAL-17 | Density regression | V3.1=65% → V3.2=59.2% | Improved but still above 35-50% target | Parameter tuning follow-up | ⚠️ deferred |

## RC Item Validation

| rc_id | priority | description | status |
|-------|----------|-------------|--------|
| RC-1 | P0 | Spine fill: only expand from placed cells | ✅ Implemented — 1 frame component/color |
| RC-2 | P0 | Periodic eye holes (counter-based) | ✅ Implemented — `_EYE_INTERVAL=7`, mean 7.5W/7.8B |
| RC-3 | P1 | Narrow zone single-line chain mode | ⬜ Deferred (per plan) |
| RC-4 | P1 | Reduce near-boundary Manhattan≤2→≤1 | ✅ Implemented |
| RC-5 | P1 | Validation hardening | ⬜ Deferred (per plan) |
| RC-6 | P2 | Observability fields | ⬜ Deferred |
| RC-7 | P2 | Config externalization | ⬜ Deferred |
| RC-8 | P2 | Docs update | ⬜ Deferred |
