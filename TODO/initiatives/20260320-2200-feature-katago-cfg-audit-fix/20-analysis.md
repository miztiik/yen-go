# Analysis — KataGo .cfg Audit & Fix

**Initiative ID**: `20260320-2200-feature-katago-cfg-audit-fix`
**Status**: approved

---

## Findings Summary

| finding_id | severity | description | status |
|------------|----------|-------------|--------|
| F-1 | HIGH | `scoreUtilityFactor` deprecated in modern KataGo; replaced by `staticScoreUtilityFactor` + `dynamicScoreUtilityFactor` | ✅ resolved (v2 adds `staticScoreUtilityFactor=0.1`) |
| F-2 | HIGH | `cpuctExplorationAtRoot` not a valid KataGo parameter; silently ignored | ✅ resolved (removed in v2) |
| F-3 | HIGH | Double exploration suppression: `cpuctExploration=0.7` + `rootPolicyTemperature=0.7` stack | ✅ resolved (both restored to 1.0) |
| F-4 | MEDIUM | `analysisWideRootNoise=0.0` is deprecated; `wideRootNoise` already set | ✅ resolved (removed in v2) |
| F-5 | MEDIUM | `subtreeValueBiasFactor=0.4` above default 0.25; risks value overestimation | ✅ resolved (set to 0.25) |
| F-6 | MEDIUM | `rootPolicyTemperatureEarly=0.7` suppresses low-prior tesuji discovery | ✅ resolved (set to 1.5 for tsumego boost) |
| F-7 | LOW | `allowSelfAtari=true` is GTP-only; no-op in analysis mode | ✅ resolved (removed in v2) |
| F-8 | INFO | No version tracking or changelog in .cfg | ✅ resolved (v2 header added) |

## CRITICAL Findings: 0

No CRITICAL unresolved findings.

## Risk Assessment

| risk_id | risk | probability | impact | mitigation |
|---------|------|-------------|--------|------------|
| R-1 | Changed MCTS params alter enrichment output | Medium | Low | Config changes affect search behavior, not pipeline logic. Re-run on sample to verify. |
| R-2 | `rootPolicyTemperatureEarly=1.5` too aggressive | Low | Low | Can revert to 1.0 if needed. Bounded upside for tesuji discovery. |
| R-3 | File keeps getting reverted | Medium | Medium | Commit to git immediately after applying changes. |

## Options Evaluated

### OPT-A: Conservative (Defaults Only)
- Restore all params to KataGo defaults
- `rootPolicyTemperatureEarly = 1.0`
- Safe but no tsumego-specific optimization

### OPT-B: Tsumego-Optimized (Selected ✅)
- Restore exploration params to KataGo defaults
- `rootPolicyTemperatureEarly = 1.5` (boost low-prior tesuji discovery)
- Bounded risk, meaningful upside for puzzle quality
- **Unanimously selected by Governance-Panel**

### OPT-C: Aggressive Tsumego
- Higher temperature values
- More changes to MCTS params
- Higher risk, diminishing returns

## Dependency Analysis

- No new library dependencies
- No `pyproject.toml` changes
- No frontend impact
- No backend pipeline code changes
- Config-only change with test coverage
