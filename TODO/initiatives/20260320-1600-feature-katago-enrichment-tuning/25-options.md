# Options — KataGo Enrichment Threshold Fine-Tuning

**Initiative**: 20260320-1600-feature-katago-enrichment-tuning
**Date**: 2026-03-20

---

## Option A: Full Consensus (14 params + code fix)

Apply all 14 consensus-backed config changes AND the S-1 code fix for adaptive boost compounding.

| Attribute | Value |
|-----------|-------|
| Scope | 14 config values + 1 code fix + tests + docs |
| Compute impact | ~15% increase |
| Risk | Medium — classification changes + behavioral code change |
| Accuracy improvement | High — addresses all identified issues including dead code |
| Files modified | 4 (config, solve_position.py, tests, AGENTS.md) |

**Tradeoffs**: Maximum accuracy improvement. Includes the code fix that reactivates corner/ladder boosts for 90%+ of puzzles. Risk is higher due to combined config+code changes.

## Option B: Conservative Config-Only (thresholds + depths)

Apply only the zero-compute config changes (classification thresholds + depth limits + seki detection). Skip visit budget changes and code fix.

| Attribute | Value |
|-----------|-------|
| Scope | 8 config values only |
| Compute impact | 0% (budget-neutral) |
| Risk | Low — no code changes, no visit budget changes |
| Accuracy improvement | Medium — addresses classification gap and depth issues, but not visit quality or dead code |
| Files modified | 1 (config only) |

**Changes included**: t_good, t_bad, t_disagreement, entry.min_depth, strong.max_depth, score_lead_seki_max, score_delta_ko, curated_pruning.min_depth, branch_disagreement_threshold, calibration.sample_size

**Changes excluded**: refutation_visits, continuation_visits, max_total_tree_queries, candidate_max_count, S-1 code fix

**Tradeoffs**: Lowest risk, zero compute increase. But leaves refutation quality unchanged (100-visit noise issue persists), corner/ladder boosts remain dead code, and the visit hierarchy inversion (S-4) stays unresolved.

## Evaluation Matrix

| Criterion | Weight | Option A | Option B |
|-----------|--------|----------|----------|
| Accuracy improvement | 40% | ★★★★★ | ★★★☆☆ |
| Risk | 25% | ★★★☆☆ | ★★★★★ |
| Compute cost | 15% | ★★★☆☆ | ★★★★★ |
| Dead code resolution | 10% | ★★★★★ | ★☆☆☆☆ |
| Completeness | 10% | ★★★★★ | ★★☆☆☆ |
| **Weighted score** | | **4.0** | **3.4** |

## Recommendation

**Option A (Full Consensus)** — The 4-expert consensus supports all 14 changes plus the code fix. The 15% compute increase is acceptable for an offline pipeline. The dead code fix (S-1) is critical — without it, corner_visit_boost and ladder_visit_boost remain non-functional, undermining the purpose of having edge-case boosts. Option B would leave known quality gaps unresolved.
