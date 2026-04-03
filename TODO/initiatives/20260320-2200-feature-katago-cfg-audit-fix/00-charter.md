# Charter — KataGo .cfg Audit & Fix

**Initiative ID**: `20260320-2200-feature-katago-cfg-audit-fix`
**Type**: feature
**Created**: 2026-03-20
**Status**: approved (governance Gate 1)

---

## Problem Statement

An expert audit of `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg` identified 8 problematic settings and 4 unused/invalid keys that produce KataGo warnings or suppress search effectiveness for tsumego analysis.

### Audit Findings (8 Issues)

| # | Setting | Issue | Severity |
|---|---------|-------|----------|
| 1 | `analysisWideRootNoise = 0.0` | Deprecated key; use `wideRootNoise` instead | Medium |
| 2 | `scoreUtilityFactor = 0.1` | Deprecated; replaced by `staticScoreUtilityFactor` + `dynamicScoreUtilityFactor` | High |
| 3 | `allowSelfAtari = true` | GTP-only flag; ignored in analysis mode | Low |
| 4 | `cpuctExplorationAtRoot = 1.3` | Not a valid KataGo key; silently ignored | High |
| 5 | `cpuctExploration = 0.7` | Below default 1.0; over-suppresses exploration | Medium |
| 6 | `subtreeValueBiasFactor = 0.4` | Above default 0.25; risks value overestimation | Medium |
| 7 | `rootPolicyTemperature = 0.7` | With cpuctExploration=0.7, double exploration suppression | High |
| 8 | `rootPolicyTemperatureEarly = 0.7` | Under 1.0 suppresses low-prior tesuji discovery | Medium |

### 4 Unused Keys to Remove

- `analysisWideRootNoise` (deprecated)
- `scoreUtilityFactor` (deprecated)
- `allowSelfAtari` (GTP-only, no-op in analysis mode)
- `cpuctExplorationAtRoot` (not a valid KataGo parameter)

## Goals

1. Remove all 4 unused/invalid keys to eliminate KataGo warnings
2. Replace deprecated `scoreUtilityFactor` with explicit `staticScoreUtilityFactor`
3. Fix exploration suppression by restoring KataGo defaults for MCTS parameters
4. Optionally boost early-phase tesuji discovery via `rootPolicyTemperatureEarly`
5. Add version header and changelog to .cfg for auditability
6. Update tests to validate removed keys and new values
7. Update AGENTS.md with gotcha bullet

## Non-Goals

- No changes to the enrichment pipeline Python code
- No changes to visit tier thresholds (T0/T1/T2/T3)
- No changes to model selection (b18c384/b28c512/b10c128)
- No runtime behavior changes outside KataGo engine parameters

## Acceptance Criteria

- [ ] 4 removed keys are absent from .cfg (grep returns empty)
- [ ] `staticScoreUtilityFactor = 0.1` present
- [ ] `cpuctExploration = 1.0` (KataGo default)
- [ ] `subtreeValueBiasFactor = 0.25` (KataGo default)
- [ ] `rootPolicyTemperature = 1.0` (KataGo default)
- [ ] `rootPolicyTemperatureEarly = 1.5` (tsumego-optimized)
- [ ] Version 2 header with changelog present
- [ ] `test_removed_keys_absent` test passes
- [ ] `test_static_score_utility_factor` validates new value
- [ ] No regression in enrichment lab test suite
- [ ] AGENTS.md gotcha bullet documents the change

## Scope

| Item | In Scope | Files |
|------|----------|-------|
| .cfg parameter changes | ✅ | `tools/puzzle-enrichment-lab/katago/tsumego_analysis.cfg` |
| Test updates | ✅ | `tools/puzzle-enrichment-lab/tests/test_tsumego_config.py` |
| AGENTS.md update | ✅ | `tools/puzzle-enrichment-lab/AGENTS.md` |
| Pipeline code | ❌ | — |
| Frontend | ❌ | — |
| Backend pipeline | ❌ | — |

## Correction Level

**Level 2: Medium Single** — 3 files, ~100 lines changed, explicit behavior change (KataGo search parameters). Plan Mode → Approve → Execute.

## Expert Consultation

Two domain expert agents were consulted:
- **KataGo-Engine-Expert**: Validated parameter semantics, deprecated key identification, default values
- **KataGo-Tsumego-Expert**: Validated tsumego-specific tuning rationale for `rootPolicyTemperatureEarly = 1.5`

## Hardware Context

- GPU: Intel Iris Xe (integrated)
- Backend: OpenCL
- Thread config: 2×8=16
- Models: b18c384 (primary), b28c512 (referee), b10c128 (quick/T0)
