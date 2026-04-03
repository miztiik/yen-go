# Options: Backend Test Remediation

## Option OPT-1: Test-Only Fix (Recommended)

**Approach:** Fix all 91 failures purely by updating/deleting tests. One small production fix for publish `failed` metric accumulation (identified as genuine bug by CR-ALPHA).

| Aspect | Details |
|--------|---------|
| Scope | 91 test failures across 21 files |
| Production changes | 1 line fix in `update_stage_metrics()` for publish failed accumulation |
| Test deletions | ~32 tests (stale/dead/duplicated) |
| Test updates | ~57 tests (fixture + assertion modernization) |
| Test investigations | 2 tests (selective recompute — may need test setup fix) |
| Risk | Low — all changes verified against production code |
| Rollback | Git revert of test changes |

**Benefits:** Fast, focused, minimal blast radius  
**Drawbacks:** Doesn't address broader DRY violations (CR-BETA findings)

## Option OPT-2: Test Fix + Consolidation

**Approach:** Same as OPT-1, plus consolidation of duplicate test files and shared fixture extraction (CR-BETA findings CRB-1, CRB-2, CRB-6, CRB-7).

| Aspect | Details |
|--------|---------|
| Additional scope | Merge 6-8 duplicate inventory test files, extract shared fixtures to conftest |
| Test count reduction | ~15 additional redundant tests eliminated |
| Risk | Medium — file merges could miss edge cases |
| Extra effort | ~40% more work |

**Benefits:** Cleaner test suite, reduced maintenance  
**Drawbacks:** Larger change set, higher review burden

## Recommendation

**OPT-1** for this initiative. Consolidation (OPT-2 extras) deferred to a follow-up initiative since it's additive and doesn't affect the pass/fail fix goal.

_Last updated: 2026-03-24_
