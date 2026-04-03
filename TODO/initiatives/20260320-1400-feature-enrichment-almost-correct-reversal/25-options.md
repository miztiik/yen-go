# Options — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Date**: 2026-03-20

## Options Table

| OPT-ID | Title | Approach | Benefits | Drawbacks | Risk | Complexity |
|--------|-------|----------|----------|-----------|------|------------|
| OPT-1 | Surgical reversal (selected) | Remove RC-5 all-skip block, remove curated gate + add cap, fix template in config | Minimal code change (~30 lines removed/modified), config-driven, testable per-scenario | Three coordinated changes across 3 files | Low | Low-Medium |
| OPT-2 | Full refutation pipeline rework | Redesign refutation flow to unify curated + AI wrongs from solve_position through enricher | Cleaner long-term architecture, single-path handling | Much larger scope (~200+ lines), higher regression risk, overkill for a 3-point fix | Medium | High |
| OPT-3 | Config-only fix (template + threshold) | Only fix the spoiler template in teaching-comments.json, raise almost_correct_threshold to match delta_threshold | Zero code changes | Does NOT fix P1 (zero-feedback) or P3 (curated gate). Only fixes P2. | Low | Very Low |

## Governance Selection

**Selected**: OPT-1 (Surgical reversal)
**Status**: GOV-OPTIONS-APPROVED (7/7 unanimous)
**Rationale**: Minimal structural change addressing all three problems. OPT-2 is overkill for this scope. OPT-3 only fixes the template, leaving two problems unaddressed.

## Per-Question Governance Decisions

| Question | Selected | Vote | Key Rationale |
|----------|----------|------|---------------|
| Q1: Almost-correct → correct or wrong tree? | **A: Wrong tree** | 7/7 | Single-answer pedagogy. Option B eliminated by frontend architecture constraint (Q-CL3). |
| Q2: Template text? | **A: "Close, but not the best move."** | 6/7 | Non-spoiler, concise. Lee Sedol prefers B — config-tunable post-implementation. |
| Q3: Curated gate? | **B: Remove gate, cap at 3** | 7/7 | Enriches curated puzzles with AI wrongs. Cap prevents explosion. |
| Q4: RC-5 fix? | **A: Remove entirely** | 7/7 | Root cause deletion. Per-move evaluation already works. |
| Q5: Backward compat? | **A: Forward-only** | 7/7 | Pipeline is stateless per run. No migration needed. |

## Required Changes from Governance

| RC-ID | Requirement | Verification |
|-------|-------------|-------------|
| RC-1 | Cap logic: `AI_to_add = min(len(ai_branches), max_refutation_root_trees - existing_curated_count)` | Test: 2 curated + 3 AI → 1 AI added |
| RC-2 | No hardcoded 0.05 threshold in sgf_enricher.py after fix | Grep: no magic `0.05` in enricher |
| RC-3 | Template: "Close, but not the best move." (no `{!xy}`) | Test: almost_correct comment has no coordinate |
| RC-4 | `assemble_wrong_comment()` handles almost_correct without coord | Test: no `{!xy}` residue in output |
| RC-5 | Tests covering Scenarios A, B, C, D, E, F | All scenario tests pass |

Last Updated: 2026-03-20
