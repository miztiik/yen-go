# Research: KaTrain Constants & Config vs Yen-Go Enrichment Config

**Last Updated**: 2026-03-13
**Initiative**: `20260313-research-katrain-config-comparison`
**Source**: [katrain/core/constants.py](https://github.com/sanderland/katrain/blob/master/katrain/core/constants.py) + [katrain/core/ai.py](https://github.com/sanderland/katrain/blob/master/katrain/core/ai.py)

---

## 1. Research Question & Boundaries

**Question**: What can Yen-Go learn from KaTrain's configuration and constants when compared to our `config/katago-enrichment.json` and related enrichment lab code?

**Scope**: Configuration patterns, difficulty estimation, move classification, ownership/analysis thresholds, AI strategy parameters. Excludes UI/rendering code, networking, and game-management logistics.

**Success Criteria**: Identify concrete gaps, borrowed-but-divergent patterns, and opportunities for calibration improvement.

---

## 2. Internal Code Evidence

### R-1: Yen-Go Difficulty Estimation

| ID  | Signal | Config Key | Value | Notes |
|-----|--------|-----------|-------|-------|
| R-1a | Policy rank | `difficulty.weights.policy_rank` | 15% | Reduced from 40% after PUCT collinearity discovery |
| R-1b | Visits to solve | `difficulty.weights.visits_to_solve` | 15% | Per-move visits, not total (C1 fix) |
| R-1c | Trap density | `difficulty.weights.trap_density` | 25% | KaTrain-style formula (see R-3) |
| R-1d | Structural | `difficulty.weights.structural` | 45% | 5-signal blend: depth/branch/local/refutation/proof |

**File**: `tools/puzzle-enrichment-lab/engine/estimate_difficulty.py`

### R-2: Yen-Go Move Classification (DD-2 Delta-Based)

| ID  | Classification | Threshold | Config Key |
|-----|------|-----------|------------|
| R-2a | TE (Correct) | Δwr ≤ 0.05 | `ai_solve.thresholds.t_good` |
| R-2b | NEUTRAL | 0.05 < Δwr < 0.15 | Between t_good and t_bad |
| R-2c | BM (Wrong) | 0.15 ≤ Δwr < 0.30 | `ai_solve.thresholds.t_bad` |
| R-2d | BM_HO (Blunder Hotspot) | Δwr ≥ 0.30 | `ai_solve.thresholds.t_hotspot` |

**File**: `tools/puzzle-enrichment-lab/engine/solve_position.py`

### R-3: Yen-Go Trap Density Formula (already inspired by KaTrain)

```python
# From estimate_difficulty.py — already documented as "KaTrain-style"
density = sum(|winrate_delta| × refutation_policy) / sum(refutation_policy)
```

This is directly adapted from KaTrain's `game_report()` complexity metric — see R-5 below.

### R-4: Yen-Go Ownership Thresholds

| ID  | Threshold | Value | Config Key |
|-----|-----------|-------|------------|
| R-4a | Alive | 0.7 | `ownership_thresholds.alive` |
| R-4b | Dead | -0.7 | `ownership_thresholds.dead` |
| R-4c | Seki low | -0.3 | `ownership_thresholds.seki_low` |
| R-4d | Seki high | 0.3 | `ownership_thresholds.seki_high` |
| R-4e | Center alive | 0.5 | `ownership_thresholds.center_alive` |

**File**: `config/katago-enrichment.json`

---

## 3. External Evidence: KaTrain Constants & AI Strategies

### R-5: KaTrain Complexity / "Trap Density" (game_report in ai.py)

```python
weight = min(
    1.0,
    sum([max(d["pointsLost"], 0) * d["prior"] for d in filtered_cands])
    / (sum(d["prior"] for d in filtered_cands) or 1e-6),
)
# adj_weight between 0.05 - 1, dependent on difficulty and points lost
adj_weight = max(0.05, min(1.0, max(weight, points_lost / 4)))
```

**Key insight**: KaTrain blends `pointsLost × prior` (score-weighted policy) with a floor of `points_lost / 4`. This is more nuanced than Yen-Go's current `|winrate_delta| × refutation_policy` formula because:
1. It uses **score** (points lost) not winrate delta — more granular in endgame
2. It has the `adj_weight` floor (`max(0.05, ...)`) preventing near-zero complexity for obvious moves
3. The `points_lost / 4` fallback catches moves where prior is low but loss is high

### R-6: KaTrain Accuracy Formula

```python
accuracy = 100 * 0.75 ** weighted_ptloss
```

Exponential decay: each point lost multiplies accuracy by 0.75. Yen-Go has no equivalent per-puzzle accuracy metric — our quality is heuristic-based (`YQ` property).

### R-7: KaTrain Calibrated Rank ↔ Elo Table

```python
CALIBRATED_RANK_ELO = [
    (-21.679, 18),    # 18k ≈ -22 Elo
    (42.602, 17),     # 17k ≈ 43 Elo
    ...
    (1135.395, 0),    # 1d ≈ 1135 Elo
    (1263.959, -2),   # 3d ≈ 1264 Elo
    (1700, -4),       # 5d ≈ 1700 Elo
]
```

**Comparison with Yen-Go**: Yen-Go uses 9 **named buckets** (novice 30k-26k through expert 7d-9d) mapped via composite difficulty scores. KaTrain has a continuous Elo ↔ kyu/dan mapping covering 18k to 5d with calibrated interpolation. KaTrain's range stops at ~5d; Yen-Go extends to 9d (expert).

### R-8: KaTrain AI Strategy Elo Grids

| ID  | Strategy | Parameters | Elo Range |
|-----|----------|-----------|-----------|
| R-8a | AI_WEIGHTED | `weaken_fac` | 219–1592 Elo |
| R-8b | AI_SCORELOSS | `strength` | 539–1386 Elo |
| R-8c | AI_LOCAL | `pick_frac × pick_n` | -204–1700 Elo (2D grid) |
| R-8d | AI_TENUKI | `pick_frac × pick_n` | 47–1700 Elo (2D grid) |
| R-8e | AI_TERRITORY | `pick_frac × pick_n` | 34–1700 Elo (2D grid) |
| R-8f | AI_INFLUENCE | `pick_frac × pick_n` | 217–1623 Elo (2D grid) |
| R-8g | AI_PICK | `pick_frac × pick_n` | -533–1700 Elo (2D grid) |

**Key insight**: These are experimentally calibrated (not theoretical). Each strategy has a known Elo mapping. Yen-Go has no such calibration for its difficulty estimates — our thresholds were tuned via expert panel (Phase S.0) and iterative cycles (v1.4, v1.10), not against a known Elo baseline.

### R-9: KaTrain Rank Strategy (ai.py — RankStrategy)

The `RankStrategy` uses a complex calibrated formula to compute `n_moves` based on player rank:

```python
orig_calib_avemodrank = 0.063015 + 0.7624 * board_squares / (
    10 ** (-0.05737 * kyu_rank + 1.9482)
)
```

This derives from empirical calibration against actual rank data. It models how many moves a player at a given rank would realistically consider — useful context for "how difficult is this for a Nk player?"

### R-10: KaTrain Ownership-Based Move Scoring

KaTrain's `SimpleOwnershipStrategy` and `SettleStonesStrategy` compute per-move ownership settledness:

```python
score = (points_lost
    + attach_penalty * is_attach
    + tenuki_penalty * is_tenuki
    - settled_weight * (own_settledness + opponent_fac * opp_settledness))
```

**Comparison**: Yen-Go uses ownership for life/death validation (alive > 0.7, dead < -0.7) but doesn't compute **per-move settledness deltas**. KaTrain's approach could enrich our refutation annotation: wrong moves that _look_ locally settled but globally lose territory could get richer teaching comments.

### R-11: KaTrain Ko Rules & PV Length

KaTrain's constants don't explicitly show ko-aware rule switching. Yen-Go (Phase S.4, ADR D31) already has a more advanced ko-analysis config:
- `tromp-taylor` rules for ko puzzles (avoids superko blocking ko sequences)
- PV length extended to 30 for ko puzzles

This is a Yen-Go innovation not present in KaTrain's constants.

### R-12: KaTrain Version & Config Constants

```python
PROGRAM_NAME = "KaTrain"
VERSION = "1.17.1"
CONFIG_MIN_VERSION = "1.17.0"
ANALYSIS_FORMAT_VERSION = "1.0"
DATA_FOLDER = "~/.katrain"
```

Yen-Go's config uses `version` field with semantic versioning per-config-file (katago-enrichment.json is at v1.16). Both approaches are config-versioned; KaTrain's `CONFIG_MIN_VERSION` pattern (minimum compatible version) is more defensive for upgrades.

---

## 4. Candidate Adaptations for Yen-Go

### A-1: Score-Based Trap Density (from R-5)

**Current**: Yen-Go uses `|winrate_delta| × refutation_policy` for trap density.
**Adaptation**: Use `pointsLost × prior` (KaTrain-style) with the `adj_weight` floor pattern.

| Aspect | Current Yen-Go | KaTrain-Inspired |
|--------|-------------|------------------|
| Signal | winrate delta | score (points lost) |
| Floor | None | `max(0.05, points_lost / 4)` |
| Granularity | Binary (wr > threshold) | Continuous score |

**Impact**: Better differentiation of endgame-heavy vs opening-trap puzzles. Score-based signals are more stable than winrate for close positions.

**Risk**: Requires generating `pointsLost` per candidate move in analysis — currently available via KataGo `moveInfos` but not stored in Yen-Go's per-puzzle output.

### A-2: Elo-Calibrated Difficulty Anchors (from R-7, R-8)

**Current**: Yen-Go maps composite scores to 9 level buckets via hand-tuned thresholds.
**Adaptation**: Use KaTrain's `CALIBRATED_RANK_ELO` table as an independent validation signal. For each puzzle, compute the approximate Elo of a player who would find the correct move ~50% of the time, then cross-reference with our level assignment.

**Impact**: Objective calibration anchor. Could identify systematic over/under-rating in specific level ranges.

**Risk**: KaTrain's calibration covers 18k–5d (≈ Yen-Go novice→advanced). No data for our low-dan/high-dan/expert tiers.

### A-3: Per-Move Accuracy Metric (from R-6)

**Current**: Yen-Go's `YQ` property is quality metadata (hc/ac counters), not a per-move accuracy score.
**Adaptation**: Compute `accuracy = 100 × 0.75^(weighted_ptloss)` for the correct-move path. Store as a signal in enrichment output for downstream puzzle quality scoring.

**Impact**: Enables "how forgiving is this puzzle?" metric. High-accuracy puzzles have clear best moves; low-accuracy ones have many reasonable alternatives.

**Risk**: Low — additive metric, doesn't change existing behavior.

### A-4: CONFIG_MIN_VERSION Pattern (from R-12)

**Current**: Yen-Go configs have `version` but no minimum-compatible-version field.
**Adaptation**: Add `min_compatible_version` to config schema. Code refuses to load configs below minimum version, preventing silent misconfiguration during upgrades.

**Impact**: Defensive upgrade safety. Especially useful for `katago-enrichment.json` which has changed significantly (16 versions).

**Risk**: Low — additive schema field.

### A-5: Ownership Settledness for Teaching Comments (from R-10)

**Current**: Yen-Go generates teaching comments based on winrate/score deltas and technique detection.
**Adaptation**: Compute per-move ownership settledness delta (KaTrain-style). When a wrong move increases local settledness but decreases global score, generate teaching comments like "This move secures the local group but loses the fight elsewhere."

**Impact**: Richer, more instructive teaching comments for intermediate+ puzzles where global/local tradeoffs matter.

**Risk**: Medium — requires per-move ownership in KataGo response (already requested via `include_ownership: true`), but needs new comment templates in `config/teaching-comments.json`.

---

## 5. Risks, License/Compliance, and Rejection Reasons

| ID | Item | Assessment |
|----|------|-----------|
| R-L1 | KaTrain License | MIT License — fully compatible. Attribution required. |
| R-L2 | Elo calibration data | Empirically derived, not copyrightable data. Safe to reference. |
| R-L3 | Formula adaptation | Mathematical formulas are not copyrightable. Safe to adapt `adj_weight` pattern. |
| R-R1 | Elo table range | Only covers 18k–5d. Yen-Go's expert tier (7d–9d) has no KaTrain calibration data. |
| R-R2 | Score vs winrate | Switching trap density from winrate-based to score-based changes all existing difficulty estimates. Requires re-calibration of `score_to_level_thresholds`. |
| R-R3 | pointsLost availability | KataGo's `moveInfos` includes `scoreLead` per candidate, from which `pointsLost` can be derived. Already in analysis response but not persisted per-puzzle. |
| R-REJ1 | AI strategy system | KaTrain's full AI strategy system (16+ strategies with ELO grids) is designed for **live play opponent simulation**. Yen-Go is a static-puzzle platform — this entire subsystem is out of scope. We analyze puzzles, not simulate opponents. |
| R-REJ2 | Rank-based n_moves formula | The `RankStrategy.get_n_moves()` calibration is for predicting **candidate exploration width** during live play. Not applicable to offline puzzle analysis with fixed visit budgets. |
| R-REJ3 | Pondering / report intervals | `PONDERING_REPORT_DT = 0.25`, `REPORT_DT = 1` — real-time UI feedback timing. Irrelevant for batch enrichment pipeline. |

---

## 6. Planner Recommendations

### P-1: Adopt score-based trap density (A-1) — MEDIUM PRIORITY

Replace `|winrate_delta| × refutation_policy` with `pointsLost × prior` in `estimate_difficulty.py`. Add `adj_weight` floor of `max(0.05, points_lost / 4)`. This is the highest-value KaTrain insight because trap density carries 25% of difficulty weight and the current formula misses endgame nuance. **Requires re-calibration cycle.**

### P-2: Add Elo-anchor validation signal (A-2) — LOW PRIORITY, HIGH INSIGHT

Use `CALIBRATED_RANK_ELO` table to compute expected-Elo for each puzzle's correct-move policy. Compare with assigned level bucket. Output as observability metric in enrichment logs without changing assignment logic. Useful diagnostic, minimal risk.

### P-3: Add per-move accuracy metric (A-3) — LOW PRIORITY

Compute `100 × 0.75^(wt_ptloss)` as an enrichment output field. Cheap additive metric that feeds into future puzzle-quality scoring without changing existing behavior.

### P-4: Add min_compatible_version to config schema (A-4) — LOW PRIORITY, QUICK WIN

Add `min_compatible_version` field to `katago-enrichment.json` schema. Implement version-gate check in `EnrichmentConfig.from_file()`. Prevents configuration drift during upgrades.

---

## 7. Confidence & Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 82 |
| `post_research_risk_level` | low |

**Rationale**: KaTrain is a mature, well-documented reference. The comparison surfaces specific, actionable insights rather than speculative ideas. Main uncertainty is whether P-1 (score-based trap density) justifies the recalibration cost. All other recommendations are additive/observability-only with zero breaking-change risk.

---

## Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should we pursue P-1 (score-based trap density) given it requires full recalibration of `score_to_level_thresholds`? | A: Yes, as a planned calibration cycle / B: No, current formula is sufficient / C: Yes, but run both in parallel (shadow mode) and compare | C | | ✅ resolved — implemented in `20260313-2000-feature-katrain-trap-density-elo-anchor` |
| Q2 | Should P-2 (Elo-anchor) be a log-only diagnostic or should it influence level assignment confidence? | A: Log-only / B: Soft influence (warning when diverges) / C: Hard gate (block if >2 levels off) | B | | ✅ resolved — implemented as hard gate (option C) in `20260313-2000-feature-katrain-trap-density-elo-anchor` |
| Q3 | Is there interest in porting the `CONFIG_MIN_VERSION` pattern (P-4) to other config files beyond `katago-enrichment.json`? | A: Only katago-enrichment / B: All config files / C: Skip entirely | A | | ❌ pending |

---

## Implementation Cross-Reference

> **See also**: [Feature Initiative: KaTrain Trap Density + Elo-Anchor](../20260313-2000-feature-katrain-trap-density-elo-anchor/30-plan.md) — Implements A-1 (score-based trap density) and A-2 (Elo-anchor gate) from this research.
