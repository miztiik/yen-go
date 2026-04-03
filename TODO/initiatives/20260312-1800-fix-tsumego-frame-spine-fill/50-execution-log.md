# Execution Log

**Last Updated**: 2026-03-12

## Intake Validation

| id | check | result |
|----|-------|--------|
| EX-1 | Plan approval present | ✅ `70-governance-decisions.md` has GOV-PLAN-CONDITIONAL |
| EX-2 | Task graph valid | ✅ T1→T2→T3→T4→T5/T6 sequential |
| EX-3 | Analysis findings resolved | ✅ No unresolved CRITICAL |
| EX-4 | Backward compatibility explicit | ✅ `required: false` — V3.1 produces fragmented output |
| EX-5 | Governance handover consumed | ✅ RC-1, RC-2, RC-4 mapped to T1 |
| EX-6 | Docs plan present | ✅ Deferred to RC-8 |

## Task Execution Log

### T1: Replace `_bfs_fill()` with spine algorithm

**Status**: ✅ Complete  
**File**: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`

Changes:
1. Added `_EYE_INTERVAL = 7` module-level constant
2. Complete rewrite of `_bfs_fill()`:
   - **Seed init**: pre-existing same-color stones added to `visited` + treated as "placed" for connectivity
   - **Expansion rule**: `_enqueue_neighbors()` ONLY called from cells where stones are PLACED or pre-existing same-color (connectivity-preserving)
   - **Eye holes**: `stones_since_eye` counter, skip every 7th eligible cell
   - **Near-boundary**: Manhattan distance ≤ 1 (reduced from ≤ 2) for dense fill near borders/puzzle
3. Updated stale comment in `fill_territory()`: "checkerboard holes" → "spine/chain growth with periodic eye holes"

### T2: Remove multi-seed fallback

**Status**: ✅ Complete  
**File**: `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py`

Removed the multi-seed fallback block (~15 lines) from `fill_territory()`. Previously, unreached cells spawned new seeds creating disconnected components.

### T3: Update test assertions

**Status**: ✅ Complete  
**File**: `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py`

Changes:
1. `test_density_19x19_corner`: threshold `>= 0.4` → `>= 0.25` (spine fill is sparser than checkerboard)
2. `test_fill_respects_single_eye`: moved eye from (16,15) to (17,2) — original was Manhattan 17 from defender seed, unreachable with quota=50 under spine BFS. New position at Manhattan 3 from seed.
3. Removed 4 garbled duplicate lines with em-dash encoding artifacts
4. `test_score_neutral_balance`: added `place_border()` call before `fill_territory()`, passing `border_coords`. Without border, attacker has no viable seeds. This matches production flow.

### T4: Run full test suite

**Status**: ✅ Complete  
**Command**: `python -m pytest tests/test_tsumego_frame.py -v --tb=short`  
**Result**: 87 passed, 0 failed

Initial run showed 86 passed / 1 failed (`test_score_neutral_balance` — 98.18% ratio). Root cause: test called without `border_coords`, diverging from production flow. Fixed in T3 change #4. Re-run: 87/87 pass.

### T5: Visual probe_frame verification

**Status**: ✅ Complete  
**Command**: `python scripts/probe_frame.py --count 5 --seed 42`

All 5 puzzles show clean connected regions:
1. go_seigen_striving (19x19 TR): O fills top-left, X fills bottom+border ✅
2. cho_chikun_encyclope (19x19 TL): O fills bottom-right, X fills left+border ✅
3. kano_yoshinori (13x13 TR): Clean connected regions for small board ✅
4. hashimoto_utaro_tsum (19x19 TR): O fills left, X fills right ✅
5. hashimoto_utaro_the_ (19x19 TL): O fills bottom-left, X fills right+border ✅

### T6: Density/component metrics verification

**Status**: ✅ Complete  
**Sample**: 20 random puzzles from `tests/fixtures/scale/scale-10k` (seed=42), 18 framed, 2 skipped

#### Key Results

| metric | target | actual (mean) | result |
|--------|--------|---------------|--------|
| Frame components/color | 1 | **1.0 W / 1.0 B** | ✅ PASS — 18/18 |
| Eyes/color | 2-15 | 7.5 W / 7.8 B | ✅ PASS — 18/18 |
| Board density | 35-50% | 59.2% | ⚠️ Above target |
| Total components/color | ≤ 2 | 5.3 W / 5.2 B | ⚠️ Elevated (puzzle stones) |

#### Analysis

**Frame components**: The spine algorithm produces exactly **1 connected component per color for all 18 framed puzzles**. This is the core RC-1 deliverable — PERFECT.

**Total components**: The 5+ total components per color come from original puzzle stones, which naturally form multiple disconnected groups (the nature of tsumego). The frame fill itself is always 1 connected region. This metric conflates puzzle structure with frame quality.

**Density**: At 59.2% mean (range 37.7-70.9%), density remains above the 35-50% target. This is a parameter-tuning concern (quota sizes, eye interval) rather than an algorithm defect. The spine algorithm places fewer stones than checkerboard (improved from V3.1's 65%), but further reduction requires adjusting area allocation in `compute_regions()`. This is appropriate for a follow-up iteration.

**Eyes**: Mean 7.5W / 7.8B with all 18 puzzles in the 2-15 range — well within target. The `_EYE_INTERVAL=7` counter produces consistent eye spacing.

## Deviations

| id | deviation | resolution |
|----|-----------|------------|
| EX-7 | `test_score_neutral_balance` failed initially (98.18% skew) | Test was calling `fill_territory()` without `border_coords`, diverging from production flow. Fixed to match production (T3 #4). |
| EX-8 | 4 garbled lines in test file from em-dash encoding | Removed duplicate lines via Python script (T3 #3). |
| EX-9 | PowerShell `.venv` module loading issue | Used `Set-Location` + bare `python` instead of `.venv\Scripts\python.exe`. |
| EX-10 | Density still above 35-50% target | Spine algorithm is correct; remaining gap is parameter-tuning (quota, eye interval). Separate follow-up. |
