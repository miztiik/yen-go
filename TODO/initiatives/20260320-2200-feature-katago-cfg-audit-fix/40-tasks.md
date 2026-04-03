# Tasks — KataGo .cfg Audit & Fix

**Initiative ID**: `20260320-2200-feature-katago-cfg-audit-fix`
**Status**: approved (governance Gate 3)

---

## Task Graph

| task_id | title | lane | depends_on | parallel | status |
|---------|-------|------|------------|----------|--------|
| T1 | Add version header & changelog to .cfg | L1 | — | [P] | ✅ done |
| T2 | Delete 4 unused keys from .cfg | L1 | T1 | — | ✅ done |
| T3 | Replace scoreUtilityFactor with staticScoreUtilityFactor | L1 | T2 | — | ✅ done |
| T4 | Restore cpuctExploration to default 1.0 | L1 | T2 | — | ✅ done |
| T5 | Restore subtreeValueBiasFactor to default 0.25 | L1 | T2 | — | ✅ done |
| T6 | Set rootPolicyTemperature=1.0, rootPolicyTemperatureEarly=1.5 | L1 | T2 | — | ✅ done |
| T7 | Update test_tsumego_config.py with new assertions | L2 | L1 | — | ✅ done |
| T8 | Add gotcha bullet to AGENTS.md | L3 | — | [P] | ✅ done |
| T9 | Run config tests (11 tests) | L4 | L2 | — | ✅ done |
| T10 | Run enrichment lab regression + backend unit tests | L4 | L1,L2,L3 | — | ✅ done |

## Task Details

### T1: Add version header & changelog to .cfg

**File**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Change**: Prepend 20-line version header with changelog documenting all v2 changes.

### T2: Delete 4 unused keys from .cfg

**File**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Change**: Remove `analysisWideRootNoise = 0.0`, `allowSelfAtari = true`, `cpuctExplorationAtRoot = 1.3`, and `scoreUtilityFactor = 0.1` lines with surrounding comments.

### T3: Replace scoreUtilityFactor with staticScoreUtilityFactor

**File**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Change**: Add `staticScoreUtilityFactor = 0.1` where `scoreUtilityFactor` was removed. Update inline comment referencing the new key name.

### T4: Restore cpuctExploration to default 1.0

**File**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Change**: `cpuctExploration = 0.7` → `cpuctExploration = 1.0`. Remove invalid `cpuctExplorationAtRoot = 1.3` line. Add explanatory comment.

### T5: Restore subtreeValueBiasFactor to default 0.25

**File**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Change**: `subtreeValueBiasFactor = 0.4` → `subtreeValueBiasFactor = 0.25`. Add explanatory comment.

### T6: Set rootPolicyTemperature=1.0, rootPolicyTemperatureEarly=1.5

**File**: `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg`
**Change**: `rootPolicyTemperature = 0.7` → `1.0`, `rootPolicyTemperatureEarly = 0.7` → `1.5`. Add explanatory comments for both.

### T7: Update test_tsumego_config.py

**File**: `tools/puzzle-enrichment-lab/tests/test_tsumego_config.py`
**Changes**:
1. Update module docstring: replace `staticScoreUtilityFactor NOT in settings` with `staticScoreUtilityFactor = 0.1`
2. Update `test_static_score_utility_factor`: change assertion from "NOT in settings" to `== "0.1"`
3. Add `test_removed_keys_absent`: verify 4 deleted keys are absent from parsed config

### T8: Add gotcha bullet to AGENTS.md

**File**: `tools/puzzle-enrichment-lab/AGENTS.md`
**Change**: Add `.cfg v2 audit (2026-03-20)` bullet in Section 6 documenting removed keys and parameter changes.

### T9: Run config tests

**Command**: `pytest tests/test_tsumego_config.py -v`
**Expected**: 11/11 pass (including new `test_removed_keys_absent`)

### T10: Run regression tests

**Commands**:
- Enrichment lab: `pytest tests/ -m "not slow" --ignore=test_golden5.py --ignore=test_calibration.py --ignore=test_ai_solve_calibration.py`
- Backend unit: `pytest backend/ -m unit -q --no-header --tb=short`
**Expected**: No new failures; pre-existing failures (11) unchanged.
