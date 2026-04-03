# Clarifications — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Last Updated: 2026-03-25

## Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | New directory vs extend existing golden-calibration? | A: New `instinct-calibration/` / B: Extend existing / C: New parallel | **A** | **A** | ✅ resolved |
| Q2 | Target puzzle count? | A: 60 / B: 72 / C: 75 / D: 90 (15×6 incl null) | B: 72 | **D: 90+** — expand to cover technique/objective diversity. Increase to ~120 if needed. | ✅ resolved |
| Q3 | Include null (no-instinct) category? | A: Yes (12) / B: No / C: Yes (6) | A | **A** | ✅ resolved |
| Q4 | Primary puzzle source? | A: Sakata + Lee + Cho / B: Cho only / C: Mix all | A | **A** | ✅ resolved |
| Q5 | Naming convention? | A: `{instinct}_{level}_{serial}.sgf` / B: `+source` / C: Minimal | B | **A**: `{instinct}_{level}_{serial}.sgf` | ✅ resolved |
| Q6 | Labeling method? | A: Experts label from scratch / B: Classifier bootstrap / C: Sakata auto + expert verify | A | **A** — use ASCII render utility for experts to read SGF positions | ✅ resolved |
| Q7 | Tobi = extend? | A: Auto-include / B: Verify all 10 / C: Exclude | B | **B** | ✅ resolved |
| Q8 | Success criteria? | A: 70% macro only / B: +per-instinct / C: +HIGH-tier precision | C | **C** | ✅ resolved |
| Q9 | Keep or replace existing golden-calibration? | A: Keep, create new / B: Replace / C: Extended | A | **A** | ✅ resolved |
| Q10 | Search/copy utility — permanent or one-time? | A: Permanent tool / B: One-time script / C: Permanent with CLI | A | **A** — two permanent tools: (1) search by technique/objective/tag/instinct, (2) copy and rename | ✅ resolved |

## Round 2

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q11 | Scope of multi-dimensional labels? | A: All 3 full / B: Instinct primary, technique secondary / C: Instinct + top technique + objective | C | **C** | ✅ resolved |
| Q12 | Increase count for technique diversity? | A: 90 enough / B: ~120 for ≥5/technique / C: 90, accept sparse | A | **B: ~120** — technique/instinct/objective/tag calibration is mandatory. Without it, tagging is template guessing, teaching comments are heuristics, KataGo signals are just numbers. | ✅ resolved |
| Q13 | Backward compatibility — old code removal? | A: No removal / B: Remove old threshold path | A | **A** | ✅ resolved |

## Key Design Decision (from Q12 rationale)

**The calibration set is not just for instinct.** It is the ground truth that validates the entire enrichment pipeline:

| Signal | Without calibration | With calibration |
|--------|-------------------|-----------------|
| Technique tags | Template-matched guesses | Verified against human labels |
| Teaching comments | Heuristic text assembly | Grounded in confirmed technique |
| KataGo policy entropy | Just a number | Correlated with human difficulty |
| Instinct classification | Untested geometric detector | Validated ≥70% accuracy |
| Difficulty estimation | Algorithm output | Anchored to professional labels |

This is the **signal-to-words bridge** — the calibration set translates numeric KataGo signals into meaningful pedagogical content.
