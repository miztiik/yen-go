# Options — KaTrain Trap Density + Elo-Anchor Level Gate

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`

---

## Overview

Two features are locked in scope (P-1: score-based trap density, P-2: Elo-anchor level gate). The options below address the **implementation strategy** — specifically how to combine them and handle the open Q6 decision (adj_weight pattern).

---

## Option Comparison

### OPT-1: Full KaTrain Alignment (Score + adj_weight Floor + Elo Hard Gate)

**Approach**: Port the full KaTrain trap density pattern including the `adj_weight` floor mechanism. The Elo-anchor operates as a hard gate on level assignment.

**Trap density formula**:
```python
# Per-refutation weight (KaTrain-style)
weight = min(1.0, sum(score_delta_i * prior_i) / sum(prior_i))
adj_weight = max(0.05, min(1.0, max(weight, score_delta / 4)))
# Final trap_density = mean(adj_weight) across refutations
```

**Elo-anchor gate**:
```python
elo_level = elo_to_yengo_level(policy_prior)  # via CALIBRATED_RANK_ELO
if elo_level is not None and abs(composite_level_id - elo_level_id) > threshold:
    final_level = elo_level  # override
```

| Aspect | Assessment |
|--------|-----------|
| **Benefits** | Closest to KaTrain = borrowing battle-tested calibration. Floor prevents zero-trap-density for obvious-but-dangerous moves. |
| **Drawbacks** | `adj_weight` adds complexity: the per-refutation floor (`score_delta / 4`) was designed for game-review (hundreds of moves), not puzzle enrichment (1-3 refutations). May over-inflate trap density for simple puzzles. |
| **Risks** | RK-OPT1-1: Floor of 0.05 means trap density is never < 0.05 even when refutations are benign → novice puzzles get inflated difficulty. RK-OPT1-2: `score_delta / 4` fallback is arbitrary for tsumego context (derived from game analysis). |
| **Complexity** | Medium — ~120 lines changed across 5 files |
| **Test impact** | All `test_difficulty.py` trap density tests need updating. New Elo-anchor tests. |
| **Rollback** | Easy — revert formula changes, remove Elo config keys |
| **Architecture compliance** | ✅ Config-driven, within tools/, no backend imports |

---

### OPT-2: Minimal KaTrain Adaptation (Score Numerator Only + Elo Hard Gate)

**Approach**: Switch the trap density numerator from `|winrate_delta|` to `score_delta` but keep the existing simple ratio formula (no `adj_weight` floor). Elo-anchor as hard gate.

**Trap density formula**:
```python
# Simple replacement: |winrate_delta| → |score_delta|, normalized
for ref in refutations:
    prior = ref.wrong_move_policy
    points_lost = abs(ref.score_delta)
    # Normalize score_delta: KataGo score is in points, not [0,1]
    # Cap at 30 points (beyond this = totally lost anyway)
    normalized_loss = min(points_lost / 30.0, 1.0)
    weighted_sum += normalized_loss * prior
    prior_sum += prior
trap_density = min(weighted_sum / prior_sum, 1.0)
```

**Elo-anchor gate**: Same as OPT-1.

| Aspect | Assessment |
|--------|-----------|
| **Benefits** | Minimal change to existing formula structure. Easy to understand and test. Score-based signal provides better endgame differentiation. Normalization ceiling (30 points) is tunable via config. |
| **Drawbacks** | Doesn't adopt KaTrain's adj_weight floor → trap density CAN be 0.0 for benign refutations (same as current behavior). Diverges from KaTrain's full pattern. |
| **Risks** | RK-OPT2-1: Score normalization ceiling (30 points) needs calibration — too low inflates, too high deflates. RK-OPT2-2: Without floor, puzzles with low-policy refutations get near-zero trap density even if the score loss is large. |
| **Complexity** | Low — ~80 lines changed across 5 files |
| **Test impact** | All `test_difficulty.py` trap density tests need updating. New Elo-anchor tests. |
| **Rollback** | Easy — same as OPT-1 |
| **Architecture compliance** | ✅ Same |

---

### OPT-3: KaTrain Score + Configurable Floor + Elo Hard Gate

**Approach**: Switch to score-based trap density AND add a configurable floor, but use a simpler floor than KaTrain's `adj_weight`. The floor is a single config value (not the complex `max(0.05, max(weight, loss/4))` pattern).

**Trap density formula**:
```python
for ref in refutations:
    prior = ref.wrong_move_policy
    points_lost = abs(ref.score_delta)
    normalized_loss = min(points_lost / score_normalization_cap, 1.0)
    weighted_sum += normalized_loss * prior
    prior_sum += prior

raw_density = weighted_sum / prior_sum if prior_sum > 1e-9 else 0.0
# Configurable floor: minimum trap density when ANY refutation exists
trap_density = max(raw_density, trap_density_floor) if refutations else 0.0
trap_density = min(trap_density, 1.0)
```

Config additions:
```json
"difficulty": {
  "trap_density_floor": 0.05,
  "score_normalization_cap": 30.0
}
```

**Elo-anchor gate**: Same as OPT-1.

| Aspect | Assessment |
|--------|-----------|
| **Benefits** | Score-based (KaTrain-aligned). Floor prevents zero-density for puzzles with refutations (KaTrain-inspired). Simpler than OPT-1's per-refutation adj_weight. Fully config-driven — floor and cap tunable without code changes. |
| **Drawbacks** | Not a direct port of KaTrain's formula — adapted for tsumego context. Floor is per-puzzle not per-refutation (different granularity from KaTrain). |
| **Risks** | RK-OPT3-1: Need to calibrate `score_normalization_cap` and `trap_density_floor`. But both are config-driven, so calibration is fast. |
| **Complexity** | Low-Medium — ~90 lines changed across 5 files |
| **Test impact** | Same as others. Floor adds one extra test dimension. |
| **Rollback** | Easy — same as others |
| **Architecture compliance** | ✅ Config-driven, tunable |

---

## Comparison Matrix

| Criterion | OPT-1 (Full KaTrain) | OPT-2 (Score Only) | OPT-3 (Score + Config Floor) |
|-----------|----------------------|--------------------|-----------------------------|
| KaTrain alignment | ⬛⬛⬛⬛⬛ Exact | ⬛⬛⬛⬜⬜ Partial | ⬛⬛⬛⬛⬜ Close |
| Simplicity | ⬛⬛⬜⬜⬜ | ⬛⬛⬛⬛⬛ | ⬛⬛⬛⬛⬜ |
| Config-driven tuning | ⬛⬛⬜⬜⬜ No (hardcoded 0.05, /4) | ⬛⬛⬛⬜⬜ Cap only | ⬛⬛⬛⬛⬛ Both floor + cap |
| Tsumego-appropriate | ⬛⬛⬜⬜⬜ Game-review pattern | ⬛⬛⬛⬛⬜ | ⬛⬛⬛⬛⬛ Adapted |
| Risk of over-inflation | ⬛⬛⬛⬜⬜ High (floor always fires) | ⬛⬜⬜⬜⬜ None | ⬛⬛⬜⬜⬜ Low (config-gated) |
| Zero-density protection | ⬛⬛⬛⬛⬛ | ⬛⬜⬜⬜⬜ None | ⬛⬛⬛⬛⬛ |
| Files changed | 5 | 5 | 5 |
| Lines changed | ~120 | ~80 | ~90 |

---

## Recommendation

**OPT-3** — Score-based with configurable floor.

**Rationale**: 
1. **Closest to KaTrain's intent** without importing its game-review-specific `adj_weight` pattern verbatim. KaTrain's floor exists to prevent zero-complexity for obvious moves — OPT-3 achieves the same goal with a simpler, config-driven mechanism.
2. **Config-driven** — both `score_normalization_cap` and `trap_density_floor` are tunable in `katago-enrichment.json`, making calibration fast without code changes.
3. **Tsumego-appropriate** — KaTrain's `adj_weight = max(0.05, max(weight, loss/4))` was designed for per-move game analysis where hundreds of moves are averaged. For puzzles with 1-3 refutations, a per-puzzle floor is more appropriate and less likely to over-inflate.
4. **User alignment** — User said "align with KaTrain" (Q6). OPT-3 adopts KaTrain's core insight (score > winrate, floor > zero) while adapting the mechanism for the domain.

---

## Elo-Anchor Design (Common to All Options)

### KaTrain Elo Table (embedded as config)

The `CALIBRATED_RANK_ELO` table maps Elo→kyu rank. For the Elo-anchor, we need policy_prior→approximate rank→Yen-Go level.

**Mapping chain**:
```
policy_prior → difficulty_Elo (via table lookup) → kyu_rank → Yen-Go level
```

**Implementation**: Add `elo_anchor` section to `katago-enrichment.json`:
```json
"elo_anchor": {
  "enabled": true,
  "override_threshold_levels": 2,
  "calibrated_rank_elo": [...],  // KaTrain table
  "policy_to_elo_mapping": "interpolated"
}
```

**Override logic**: After `_score_to_level()` assigns a composite level, check if Elo-derived level differs by ≥ `override_threshold_levels`. If so, use the Elo-derived level. Skip for uncovered ranges.

> **See also**:
> - [Charter](./00-charter.md)
> - [Research](./15-research.md)
> - [Clarifications](./10-clarifications.md)
