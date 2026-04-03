# Options — KataGo .cfg Audit & Fix

**Initiative**: 20260320-2200-feature-katago-cfg-audit-fix
**Date**: 2026-03-20

---

## Decision Axis

All three options share the same **P0 (bug fix)** changes — removal of 4 unused keys and addition of `staticScoreUtilityFactor=0.1`. The primary decision axis is the **exploration parameter tuning** (P1/P2) and the **early temperature** value (Q2 disagreement).

---

## Option Comparison

| Dimension | OPT-A: Conservative Restore | OPT-B: Tsumego-Optimized | OPT-C: Minimal (Bugs Only) |
|-----------|:---------------------------:|:-------------------------:|:---------------------------:|
| **Approach** | Restore KataGo defaults for all exploration params | Engine defaults + Tsumego Expert's early-phase boost | Fix only confirmed bugs, don't touch exploration |
| **P0: Remove 4 unused keys** | Yes | Yes | Yes |
| **P0: Add `staticScoreUtilityFactor=0.1`** | Yes | Yes | Yes |
| **P1: `rootPolicyTemperature`** | 0.7 → **1.0** | 0.7 → **1.0** | 0.7 (no change) |
| **P1: `cpuctExploration`** | 0.7 → **1.0** | 0.7 → **1.0** | 0.7 (no change) |
| **P2: `rootPolicyTemperatureEarly`** | 0.7 → **1.0** (match base) | 0.7 → **1.5** (early-phase boost) | 0.7 (no change) |
| **P3: `subtreeValueBiasFactor`** | 0.4 → **0.25** | 0.4 → **0.25** | 0.4 (no change) |
| **Version control header** | Yes | Yes | Yes |
| **Total lines changed** | ~8 edits + header | ~8 edits + header | ~4 deletions + 1 addition + header |

## Detailed Assessment

### OPT-A: Conservative Restore (Engine Expert Aligned)

**Summary**: Restore all exploration parameters to KataGo defaults (1.0). Safe, well-understood baseline.

| Dimension | Assessment |
|-----------|-----------|
| Benefits | All 3 experts agree on temp=1.0, cpuct=1.0. Restoring defaults is zero-innovation risk. |
| Drawbacks | tempEarly=1.0 misses the Tsumego Expert's insight about early-phase tesuji discovery. |
| Risks | Medium: visit allocation changes for all standard queries. Mitigated by test gate + refutation overrides unaffected. |
| Complexity | Low — all values are KataGo defaults. |
| Test impact | test_tsumego_config.py may need 1-2 assertion updates for staticScoreUtilityFactor. |
| Rollback | Trivial — revert .cfg values in git. |
| Architecture compliance | Config-only change, no code. Meets C6 (zero cost). |

### OPT-B: Tsumego-Optimized (Tsumego Expert Aligned)

**Summary**: Same as OPT-A but with `rootPolicyTemperatureEarly=1.5` to boost low-prior tesuji discovery in the critical first ~30 visits.

| Dimension | Assessment |
|-----------|-----------|
| Benefits | Addresses the specific tsumego blind spot: under-the-stones, snapback, throw-in tesuji at <1% policy get ~3x more early visits (effective weight 0.008^(1/1.5)≈0.04 vs 0.008^(1/1.0)≈0.008). |
| Drawbacks | tempEarly=1.5 is a non-default value requiring empirical validation. Engine Expert recommended 1.0 for consistency. |
| Risks | Low-Medium: early-phase affects only first ~30 visits. At T1=500, 30/500=6% of budget. At T2=2000, impact is diluted to 1.5%. At T0=50, 30/50=60% — significant for quick-scan but T0 is always confirmed by T1. |
| Complexity | Same as OPT-A — one line difference. |
| Test impact | Same as OPT-A. |
| Rollback | Trivial — change tempEarly to 1.0 (OPT-A fallback). |
| Architecture compliance | Config-only. Meets C6. |

### OPT-C: Minimal (Bugs Only)

**Summary**: Fix only the 4 confirmed unused key warnings + seki detection fix. Don't touch exploration parameters.

| Dimension | Assessment |
|-----------|-----------|
| Benefits | Lowest risk. Zero behavioral change except seki detection. Eliminates log noise. |
| Drawbacks | Leaves the "double exploration suppression" unfixed. Low-prior tesuji continue to be missed at T0/T1. The intended two-tier CPUCT strategy (cpuctExplorationAtRoot=1.3) remains non-functional. |
| Risks | Very Low change risk. But carries the **ongoing correctness risk** of under-explored standard queries. |
| Complexity | Minimal — 4 deletions + 1 addition. |
| Test impact | Minimal — only staticScoreUtilityFactor test needs updating. |
| Rollback | Trivial. |
| Architecture compliance | Config-only. Meets C6. |

---

## Recommendation

| OPT-ID | Recommendation | Rationale |
|--------|----------------|-----------|
| OPT-A | **Viable** | Safe, all defaults, full expert consensus on core params. |
| OPT-B | **Recommended** | Builds on OPT-A with the Tsumego Expert's insight about early-phase discovery. The risk is minimal (affects only first 30 visits, T0 always confirmed by T1). The upside is meaningful: 3x more early visits for low-prior tesuji. |
| OPT-C | **Not recommended** | Leaves known exploration deficit unfixed. The "double suppression" is well-documented by 3/3 experts. Deferring P1 changes to a future iteration loses the expert consensus momentum. |

---

> **See also**:
>
> - [Research](./15-research.md) — Expert consensus matrix and disagreement analysis
> - [Charter](./00-charter.md) — Goals, non-goals, constraints
> - [Clarifications](./10-clarifications.md) — Q2 (rootPolicyTemperatureEarly) is the key decision
