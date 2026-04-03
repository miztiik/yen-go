# Execution Log — KaTrain Trap Density + Elo-Anchor

**Last Updated**: 2026-03-13
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`

---

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1 | `models/refutation_result.py` | — | ✅ merged |
| L2 | T2 | `analyzers/generate_refutations.py` | — | ✅ merged |
| L3 | T4 | `config/katago-enrichment.json`, `config.py` | — | ✅ merged |
| L4 | T3, T6 | `analyzers/estimate_difficulty.py` | L1, L2, L3 | ✅ merged |
| L5 | T5, T7 | `tests/test_difficulty.py` | L4 | ✅ merged |
| L6 | T8, T9 | Multiple docs/docstrings | L5 | ✅ merged |

## Per-Task Completion Log

### T1: Add `score_delta` field to Refutation model ✅

- **File**: `tools/puzzle-enrichment-lab/models/refutation_result.py`
- Added `score_delta: float = Field(default=0.0, ...)` to `Refutation`
- Default 0.0 preserves backward compat for deserialization
- **Evidence**: `Refutation(wrong_move='ab', score_delta=-5.2)` → score_delta: -5.2; default: 0.0

### T2: Thread `score_lead` through refutation generation ✅

- **File**: `tools/puzzle-enrichment-lab/analyzers/generate_refutations.py`
- Added `initial_score: float = 0.0` parameter to `generate_single_refutation()`
- Computes `score_after = -opp_best.score_lead` (flip opponent perspective), `score_delta = score_after - initial_score`
- Sets `Refutation(..., score_delta=score_delta)` in return
- In `generate_refutations()`: extracts `initial_score = initial_analysis.root_score`, passes to `generate_single_refutation()`
- In `_enrich_curated_policy()`: builds `score_lookup` from `initial_analysis.move_infos`, computes `score_delta = mi.score_lead - root_score` (no flip — same perspective as existing `winrate_delta = wr - root_wr`)

### T3: Replace trap density formula ✅

- **File**: `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py`
- Rewrote `_compute_trap_density()` with score-based formula
- `normalized_loss = min(|score_delta| / score_normalization_cap, 1.0)` when `score_delta != 0`
- Falls back to `|winrate_delta|` when `score_delta == 0` (legacy compat)
- Applies `max(raw_density, floor)` when refutations exist
- Config-driven: `score_normalization_cap` (30.0) and `trap_density_floor` (0.05)

### T4: Config additions ✅

- **File**: `config/katago-enrichment.json`
  - Bumped version `1.15` → `1.17`
  - Added `difficulty.score_normalization_cap: 30.0`
  - Added `difficulty.trap_density_floor: 0.05`
  - Added `elo_anchor` section with 24-entry `calibrated_rank_elo` table
  - Added v1.17 changelog entry with KaTrain MIT attribution
- **File**: `tools/puzzle-enrichment-lab/config.py`
  - Added `score_normalization_cap` and `trap_density_floor` fields to `DifficultyConfig`
  - Added `CalibratedRankElo` and `EloAnchorConfig` Pydantic models
  - Added `elo_anchor` field to `EnrichmentConfig`
- **Evidence**: Config loads with version=1.17, all new fields accessible

### T5: Update trap density tests ✅

- **File**: `tools/puzzle-enrichment-lab/tests/test_difficulty.py`
- Updated `_make_refutations()` helper to accept `score_delta` parameter
- Added 5 new tests in `TestTrapDensityScoreBased`:
  - Score-divergent vs winrate-divergent → different densities
  - Floor activates when raw < floor but refutations exist
  - Floor does NOT activate with 0 refutations
  - Fallback to |winrate_delta| when score_delta == 0
  - Score normalization cap respected

### T6: Implement Elo-anchor gate ✅

- **File**: `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py`
- Added `_LEVEL_RANK_MIDPOINT` mapping (slug → kyu rank midpoint)
- Added `_RANK_TO_LEVEL` table for reverse mapping
- Implemented `_rank_to_level_slug()` function
- Implemented `_elo_anchor_gate()`: compares composite level vs policy-based level using rank midpoints
- Integrated after `_score_to_level()` in `estimate_difficulty()`
- Handles uncovered ranges (novice, beginner, expert) with log + skip
- MIT attribution for KaTrain CALIBRATED_RANK_ELO in docstring

### T7: Add Elo-anchor gate tests ✅

- **File**: `tools/puzzle-enrichment-lab/tests/test_difficulty.py`
- Added 11 new tests across 7 test classes:
  - Override when divergence >= 2 levels
  - Preserve when divergence < 2
  - Skip novice, beginner, expert (log "no Elo anchor")
  - Parametrized test for all 6 covered levels
  - Threshold config respected
  - Disabled gate returns original

### T8: Legacy code removal ✅

- Updated `estimate_difficulty()` docstring for score-based formula + Elo-anchor
- Updated `_compute_trap_density()` docstring (no more "approximated by |winrate_delta|")

### T9: Documentation updates ✅

- Updated `config/katago-enrichment.json` changelog (v1.17)
- Updated `tools/puzzle-enrichment-lab/README.md` with KaTrain-derived features
- Updated `TODO/initiatives/20260313-research-katrain-config-comparison/15-research.md` with cross-reference
- Updated version assertions in `test_enrichment_config.py` and `test_ai_solve_config.py`

## Deviations

| EX-1 | Version bump | Plan said v1.17, config was at v1.15 (not v1.16). v1.16 changelog was already present from a prior benson_gate initiative. Bumped directly to v1.17. No deviation from plan. |
| EX-2 | Test version fixes | Two test files (`test_enrichment_config.py`, `test_ai_solve_config.py`) had hardcoded `"1.15"` version assertions that needed updating to `"1.17"`. Not in original task list but required for regression. |
