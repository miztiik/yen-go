# Research Brief — KataGo .cfg Audit

**Initiative**: 20260320-2200-feature-katago-cfg-audit-fix
**Date**: 2026-03-20
**Planning Confidence Score**: 80
**Risk Level**: medium

---

## Sources Consulted

| R-ID | Source | Type | Key Finding |
|------|--------|------|-------------|
| R-1 | KataGo diagnostic logs (`.lab-runtime/diagnostics/`) | Internal evidence | 4 unused key warnings confirmed: `allowSelfAtari`, `analysisWideRootNoise`, `cpuctExplorationAtRoot`, `scoreUtilityFactor` |
| R-2 | External expert audit (user-provided) | External analysis | 8 problematic parameters flagged, 4 unused keys identified, priority-ordered fix list |
| R-3 | KataGo-Engine-Expert agent (Dr. David Wu persona) | Agent consultation | 12-parameter assessment, visit budget coherence, thread analysis for Intel Iris Xe |
| R-4 | KataGo-Tsumego-Expert agent (Dr. Shin Jinseo 9p persona) | Agent consultation | 8-parameter tsumego correctness assessment, 5 coherence issues, 4 concrete scenarios, 2-phase rollout proposal |

## Expert Consensus Matrix

| Parameter | External Audit | Engine Expert | Tsumego Expert | Consensus |
|-----------|:-------------:|:-------------:|:--------------:|:---------:|
| **Remove `allowSelfAtari`** | REMOVE | REMOVE (P-1) | REMOVE (U-1) | **3/3 REMOVE** |
| **Remove `analysisWideRootNoise`** | REMOVE | REMOVE (P-2) | REMOVE (U-2) | **3/3 REMOVE** |
| **Remove `cpuctExplorationAtRoot`** | REMOVE | REMOVE (P-3) | REMOVE (U-3) | **3/3 REMOVE** |
| **Remove `scoreUtilityFactor`** | REMOVE | REMOVE (P-4) | RENAME to `staticScoreUtilityFactor=0.1` (U-4/P-4) | **3/3 FIX** (2 remove, 1 rename) |
| **`wideRootNoise` 0.02→0.0** | 0.0 | **No change** (0.02 appropriate) | **No change** (0.02 appropriate) | **2/3 keep 0.02** |
| **`rootPolicyTemperature` 0.7→?** | 1.0 | 1.0 (P-6) | 1.0 (P-2) | **3/3 → 1.0** |
| **`rootPolicyTemperatureEarly` 0.7→?** | 1.0 | 1.0 (P-7, match base) | **1.5** (P-3, boost early discovery) | **2/3 → 1.0** vs 1/3 → 1.5 |
| **`cpuctExploration` 0.7→?** | 0.9 | 1.0 (P-8) | 1.0 (P-5) | **2/3 → 1.0**, 1/3 → 0.9 |
| **`maxVisits` 5000→?** | 20000 | **No change** (P-9, pipeline overrides) | **No change** (P-8, tier system) | **2/3 keep 5000** |
| **`ignorePreRootHistory`** | true | **No change** false (P-10, ko puzzles) | **No change** false (P-6, ko puzzles) | **2/3 keep false** |
| **Thread config (2×8)** | 1×14 | **No change** (P-11, Iris Xe batch) | Not evaluated | **1/2 keep 2×8** |
| **`subtreeValueBiasFactor` 0.4→?** | 0.15 | 0.3 (P-12, low priority) | 0.25 (P-7) | **3/3 lower** (range 0.15-0.3) |

## Key Disagreements

| D-ID | Parameter | Disagreement | Resolution Recommendation |
|------|-----------|-------------|---------------------------|
| D-1 | `scoreUtilityFactor` | External: remove / Engine: remove / Tsumego: rename to `staticScoreUtilityFactor=0.1` | **Rename** — Tsumego Expert explains this controls seki detection sensitivity. Removing it entirely uses KataGo's compiled default which may not be 0.1. |
| D-2 | `rootPolicyTemperatureEarly` | External+Engine: 1.0 / Tsumego: 1.5 | **User decision needed (Q2)** — Tsumego Expert's scenario (under-the-stones, 0.8% policy) is compelling. |
| D-3 | `subtreeValueBiasFactor` | External: 0.15 / Engine: 0.3 / Tsumego: 0.25 | **0.25** — Middle ground. Engine Expert notes low priority. |
| D-4 | `wideRootNoise` | External: 0.0 / Experts: keep 0.02 | **Keep 0.02** — Both experts explain it serves a different purpose than Dirichlet noise. Already overridden to 0.08 for refutations. |

## New Finding: `staticScoreUtilityFactor` Seki Impact

The Tsumego Expert identified a critical finding not in the external audit: `scoreUtilityFactor` being ignored means seki detection has been running on KataGo's compiled default for `staticScoreUtilityFactor` (typically 0.1-0.3). If the default was 0.3, seki positions would show winrate shifts of ~0.05-0.10 outside the seki detection band (`winrate_band_low=0.45, winrate_band_high=0.55`). Adding `staticScoreUtilityFactor = 0.1` explicitly controls this.

## Research Invocation Justification

Research was invoked because:
1. Two specialized KataGo expert agents were available (repository-defined custom agents)
2. External expert audit required validation against engine-specific and tsumego-specific knowledge
3. Multiple viable parameter values existed with unknown tradeoffs (rootPolicyTemperatureEarly, subtreeValueBiasFactor)
4. Impact on 9,000+ puzzle library correctness required domain expert confidence
