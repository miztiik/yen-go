# Charter — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Type**: Feature (regression reversal + policy correction)
**Date**: 2026-03-20
**Level**: Level 3 (Multiple Files: enrichment pipeline + config + tests)
**Supersedes**: `20260319-2100-feature-enrichment-quality-regression-fix` — specifically RC-5 (all-almost-skip), plus P2 (spoiler template) and P3 (curated gate)

## Objective

Reverse three defects introduced or exposed by the predecessor initiative's RC-5:

1. **P1 (RC-5 All-Skip)**: The `skipped_all_almost` gate drops ALL wrong branches when every AI-discovered refutation has delta < 0.05 — creating zero-feedback puzzles in Scenarios A and F.
2. **P2 (Spoiler Template)**: The `almost_correct` teaching comment template "Close — {!xy} is slightly better." reveals the correct first move coordinate, defeating the puzzle.
3. **P3 (Curated Gate)**: `_has_existing_refutation_branches()` blocks ALL AI-discovered wrong branches when curated wrongs already exist (Scenario D). User explicitly requested AI wrongs be added **alongside** curated wrongs.

## Enumerated Scenario Table

| ID | Puzzle Comes With | AI Discovers (Wrong) | Current Behavior | Proposed Behavior |
|:--:|:------------------|:--------------------|:-----------------|:------------------|
| **A** | 1 correct, 0 wrong | 1–3 wrongs, ALL almost-correct (δ<0.05) | ALL dropped (P1) | Add to wrong tree, comment: "Wrong. Close, but not the best move." |
| **B** | 1 correct, 0 wrong | 1–3 wrongs, MIXED almost + true wrong | Only true-wrong added | Unchanged (correct) |
| **C** | 1 correct, 0 wrong | 1–3 wrongs, ALL true wrong (δ≥0.05) | All added | Unchanged (correct) |
| **D** | 1 correct, 1+ curated wrong | 1–3 AI wrongs (any delta) | ALL AI blocked (P3) | AI wrongs added alongside curated, capped at max_refutation_root_trees=3 total |
| **E** | 1 correct, 0 wrong | 0 wrongs found | Nothing to add | Unchanged (expected) |
| **F** | 0 correct (position-only) | KataGo discovers correct + wrongs | RC-5 still applies (P1) | Same fix as A — all-skip removed |

## Count Boundaries (Config-Driven)

| Resource | Min | Max | Config Source |
|:---------|:---:|:---:|:-------------|
| Correct root trees | 1 | 2 | `max_correct_root_trees=2` |
| Wrong root trees (total incl. curated + AI) | 0 | 3 | `max_refutation_root_trees=3` |
| Refutation PV depth | 1 | 4–10 | `max_pv_length` (level-dependent) |

## Success Criteria

1. **SC-1**: Scenario A puzzles get 1–3 wrong branches with non-spoiler "Wrong. Close, but not the best move." comment
2. **SC-2**: Scenario D puzzles get AI wrongs alongside curated wrongs, total capped at 3
3. **SC-3**: `almost_correct` template contains no `{!xy}` coordinate token (no spoiler)
4. **SC-4**: No hardcoded `0.05` threshold remains in `sgf_enricher.py` — all thresholds from config
5. **SC-5**: Scenarios B, C, E unchanged (regression-free)
6. **SC-6**: All existing tests pass; new tests cover Scenarios A, D, F

## Scope

### In Scope
- `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` — remove `skipped_all_almost`, remove curated gate, add cap logic
- `config/teaching-comments.json` — fix `almost_correct` template (remove `{!xy}`)
- `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` — stop passing `correct_first_coord` for `almost_correct`
- Tests covering all 6 scenarios
- `tools/puzzle-enrichment-lab/AGENTS.md` update

### Out of Scope
- Retroactive re-enrichment of existing SGFs (tracked as follow-up)
- Frontend changes
- RC-1 through RC-4 from predecessor initiative (those are correct and remain)
- Threshold tuning (t_good, t_bad, almost_correct_threshold) — config-driven, no code change needed

## Constraints
- Forward-only (no retroactive re-enrichment)
- No new dependencies
- Backward compatible with existing enriched SGFs
- Config-driven thresholds — no hardcoded magic numbers
- Template voice: ≤15 words, "Wrong." prefix, no coordinate leak

## Non-Goals
- Changing co_correct logic or max_correct_root_trees
- Changing refutation candidate selection (delta_threshold=0.08)
- Re-enrichment campaign (separate initiative)
- Frontend puzzle rendering changes

> **See also**:
> - [Predecessor initiative](../20260319-2100-feature-enrichment-quality-regression-fix/00-charter.md) — RC-5 that introduced the regression
> - [Teaching comments concept](../../docs/concepts/) — Comment template system
> - [Enrichment Lab AGENTS.md](../../tools/puzzle-enrichment-lab/AGENTS.md) — Module architecture

Last Updated: 2026-03-20
