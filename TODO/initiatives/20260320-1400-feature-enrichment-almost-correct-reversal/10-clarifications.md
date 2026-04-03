# Clarifications — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Date**: 2026-03-20

## Clarification Rounds

### Round 1 (Conversation-derived)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should almost-correct moves (δ<0.05) be added to the correct tree or the wrong tree? | A: Wrong tree / B: Correct tree / C: Drop entirely | A: Wrong tree — preserves single-answer pedagogy, no frontend changes needed | A: Wrong tree | ✅ resolved |
| Q2 | What should the `almost_correct` teaching comment template say? | A: "Close, but not the best move." / B: "Close — there's a slightly better option." / C: Remove condition, use default | A: Concise, no spoiler, fits 15-word voice constraint | Governance: A (6/7), Lee Sedol prefers B | ✅ resolved |
| Q3 | Should AI wrongs be added alongside curated wrongs? | A: Remove gate entirely / B: Remove gate, cap at 3 / C: Keep gate | B: Cap prevents branch explosion, AI enriches curated puzzles | User explicit: add alongside. Governance: B (7/7) | ✅ resolved |
| Q4 | How should the RC-5 all-skip logic be fixed? | A: Remove entirely / B: Change to per-move skip | A: Minimal change, existing per-move evaluation handles it | Governance: A (7/7) | ✅ resolved |
| Q5 | Is backward compatibility required? Should old code be removed? | A: Forward-only, remove old code / B: Requires re-enrichment | A: Forward-only, remove old code | User: forward-only. Governance: A (7/7) | ✅ resolved |

### Round 2 (Governance-derived clarifications)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q-CL1 | Does "Wrong." prefix (RC-1) need to remain for `almost_correct` branches? | A: Keep prefix / B: Skip prefix, use BM property | A: "Wrong." prefix is the detection mechanism for `infer_correctness_from_comment()` | Inferred: A | ✅ resolved |
| Q-CL2 | When removing curated gate, is `max_refutation_root_trees=3` enforced at enricher level? | A: Yes / B: No, only in solve_position | B confirmed by code trace. Must add explicit cap at enricher level. | Code-verified: B | ✅ resolved |
| Q-CL3 | Would adding to correct tree (Q1:B) require frontend changes? | A: Yes / B: No | A: Frontend expects single correct path from root. Eliminates Q1:B. | Code-verified: A | ✅ resolved |
| Q-CL4 | Is hardcoded 0.05 in sgf_enricher.py same as config `almost_correct_threshold`? | Same / Different source | Mismatch: enricher hardcodes 0.05, teaching_comments.py reads from config. Fix removes the hardcoded block entirely. | Code-verified: mismatch, removed by fix | ✅ resolved |

## Backward Compatibility Decision

**Decision**: Forward-only. No retroactive re-enrichment. Old code removed.
**Rationale**: Pipeline is stateless per run. Next enrichment run applies the new logic. Existing enriched SGFs are unchanged.

Last Updated: 2026-03-20
