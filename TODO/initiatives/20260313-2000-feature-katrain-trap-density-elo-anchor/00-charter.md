# Charter — KaTrain-Aligned Trap Density + Elo-Anchor Level Gate

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`  
**Type**: Feature  
**Correction Level**: 3 (Multiple Files — 2-3 files logic + model + config + tests)

---

## Goals

| ID | Goal | Acceptance Criteria |
|----|------|-------------------|
| G1 | Replace `\|winrate_delta\| × policy` trap density with KaTrain-aligned `score_delta × policy` formula | `_compute_trap_density()` uses `score_delta` (points lost) instead of `\|winrate_delta\|`. All existing `test_difficulty.py` tests updated. |
| G2 | Thread `score_delta` from KataGo response through `Refutation` model | `Refutation` model has `score_delta` field. `generate_single_refutation()` populates it from KataGo analysis response. |
| G3 | Implement Elo-anchor hard gate for level assignment | When KaTrain Elo-anchor diverges from assigned level by ≥ configurable threshold, level is overridden. Applies to elementary→high-dan only. |
| G4 | Log "no Elo data" for uncovered ranges | Novice, beginner, expert puzzles log "no Elo anchor available" and skip comparison. |
| G5 | Remove legacy trap density formula | Single code path. No configuration branch for old vs new formula. |
| G6 | Update `katago-enrichment.json` config | New config keys for Elo-anchor thresholds and KaTrain calibration table. Bump config version. |

---

## Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Backward compatibility / shadow mode | User decision: full re-enrichment acceptable |
| NG2 | Extrapolate Elo beyond KaTrain's 18k–5d range | No reliable data; better to skip |
| NG3 | Port KaTrain's AI strategy system | Yen-Go is static-puzzle, not live-play |
| NG4 | Accuracy metric (`100 × 0.75^ptloss`) | Lower priority, not in scope for this initiative |
| NG5 | `CONFIG_MIN_VERSION` pattern | Lower priority, separate concern |
| NG6 | Changes to the main `backend/puzzle_manager/` pipeline | Enrichment lab tool only |

---

## Constraints

| ID | Constraint |
|----|-----------|
| C1 | Must stay within `tools/puzzle-enrichment-lab/` directory (tools must NOT import from backend/) |
| C2 | KaTrain `CALIBRATED_RANK_ELO` is MIT licensed — attribution required in code comment |
| C3 | Config changes must follow existing Pydantic validation pattern (no JSON schema file exists) |
| C4 | All existing tests must pass after changes (update, not just add) |
| C5 | `score_delta` data must be available in KataGo analysis response without additional queries |

---

## Acceptance Criteria (End-to-End)

1. `_compute_trap_density()` produces different scores for score-divergent vs winrate-divergent refutations
2. `estimate_difficulty()` uses score-based trap density and produces valid level assignments
3. Elo-anchor overrides level for elementary→high-dan when divergence exceeds threshold
4. Elo-anchor logs "no data" for novice, beginner, expert
5. All `test_difficulty.py` tests updated and passing
6. New tests for Elo-anchor gate (override, skip, edge cases)
7. `katago-enrichment.json` version bumped with new config keys
8. No imports from `backend/puzzle_manager/`

---

## Risk Summary

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| RK1 | Score-based trap density changes all existing difficulty scores | High | Medium | Expected — D1 accepts full re-enrichment |
| RK2 | Elo hard gate overrides correct levels in edge cases | Medium | High | Configurable divergence threshold + level range restriction |
| RK3 | `score_lead` not available in all KataGo response paths | Low | High | Already confirmed: `MoveAnalysis.score_lead` exists in all analysis responses |
| RK4 | KaTrain Elo table covers only 4-6 of 9 levels | Known | Medium | D5: log "no data" for uncovered ranges |

---

> **See also**:
> - [Research: KaTrain Config Comparison](../20260313-research-katrain-config-comparison/15-research.md)
