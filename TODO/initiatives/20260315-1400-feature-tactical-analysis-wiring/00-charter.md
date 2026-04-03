# Charter — Tactical Analysis Pipeline Wiring

> **⚠ ARCHIVED** — This initiative was misdirected at the backend pipeline (`backend/puzzle_manager/`) when the intended target was the puzzle enrichment lab (`tools/puzzle-enrichment-lab/`). Superseded by initiative `20260315-1700-feature-enrichment-lab-tactical-hints`.

**Initiative**: `20260315-1400-feature-tactical-analysis-wiring`
**Type**: Feature
**Status**: ARCHIVED
**Last Updated**: 2026-03-15

---

## Summary

Wire the existing `core/tactical_analyzer.py` (95% built, 50+ tests passing) into the pipeline's downstream consumers: YT auto-tagging, YQ quality scoring, difficulty classification, and hint generation. The core algorithms are already implemented and tested — this initiative completes the integration layer that converts tactical analysis results into puzzle metadata.

## Goals

| G-ID | Goal | Acceptance Criteria |
|------|------|-------------------|
| G-1 | ~~Wire auto-tags into YT~~ **ALREADY IMPLEMENTED** — Validate existing wiring | Auto-tag merge works at `stages/analyze.py` L349-358; add end-to-end integration tests confirming ladder/snapback/seki tags appear in published SGF |
| G-2 | **Feed tactical complexity into quality scoring** | `compute_tactical_complexity()` result consumed by `quality.py`; YQ score reflects tactical depth signal |
| G-3 | **Integrate tactical signals into difficulty classifier** | `classify_difficulty()` accepts tactical pattern presence + weak_group_count as inputs; difficulty estimates improve for tactical puzzles |
| G-4 | **Enhance HintGenerator with tactical detail** — beyond tag-mediated hints (which already work) to include specific tactical context (e.g., "The ladder extends 5 moves", "Recapture 3 stones") | When a ladder/snapback/instinct is detected, YH contains richer context hints than tag-only hints |
| G-5 | **Add structured before/after measurement framework** | Difficulty distribution comparison logged before/after tactical signals are added to classifier |

## Non-Goals

| NG-ID | Exclusion | Rationale |
|-------|-----------|-----------|
| NG-1 | Implement remaining 4 instinct patterns (block-angle, stretch-kosumi, stretch-bump, hane-response) | Low tsumego relevance; can be added later |
| NG-2 | Ladder diagonal-scan optimization or zobrist caching | Performance is already sufficient (~6ms/puzzle) |
| NG-3 | Influence map or territory flood-fill | Not needed for current tag/quality/hint integration |
| NG-4 | compare_moves.py rank-based refutation scoring | Requires KataGo; enrichment-lab-only concern |
| NG-5 | Modify enrichment lab detectors | Separate system with different approach (KataGo-based) |
| NG-6 | Schema changes to YX property format | YAGNI — tactical complexity derivable from YT tags |
| NG-7 | Mistake classification (BLUNDER/MISTAKE/etc.) | Requires AI engine winrate analysis we don't have in pipeline |

## Constraints

| C-ID | Constraint |
|------|-----------|
| C-1 | Zero new dependencies — all algorithms already use existing Board/Group/sgfmill |
| C-2 | ENRICH_IF_ABSENT policy — auto-tags NEVER override manually-assigned or source-provided tags |
| C-3 | Precision-over-recall — only emit auto-tags at HIGH confidence; empty is valid |
| C-4 | Backward compatible for non-tactical puzzles — difficulty scores unchanged for puzzles with no detected tactical patterns; intentionally improved for puzzles with tactical features (this IS the goal, per AC-3) |
| C-5 | All modifications confined to `backend/puzzle_manager/` (pipeline only, not enrichment lab) |
| C-6 | Clean-room adaptation — concepts from GPL-3.0 gogogo adapted independently, no code copying |

## Backward Compatibility

**Required**: No. The current state is that `analyze_tactics()` runs but results are discarded — there are zero existing consumers of tactical analysis output. Wiring the integration creates NEW behavior, it doesn't change existing behavior.

## Acceptance Criteria

| AC-ID | Criterion | Measurement |
|-------|-----------|-------------|
| AC-1 | Existing auto-tag wiring validated end-to-end | Integration test: known-ladder SGF → pipeline run → YT includes `ladder` |
| AC-2 | Position validation flags appear in YQ for broken puzzles | Validation notes recorded; quality score reduced for invalid positions |
| AC-3 | Difficulty classifier uses tactical signals | Paired test: same depth; ladder present → LOWER difficulty (forced sequence, less reading); complex life/death → HIGHER difficulty |
| AC-4 | Tactical-detail hints in YH beyond tag-mediated hints | Ladder puzzle → YH includes chase-specific context (depth, direction); not just "This is a ladder" |
| AC-5 | All existing tests pass (no regression) | `pytest -m "not (cli or slow)"` → 100% pass |
| AC-6 | Before/after difficulty distribution comparison | Log difficulty scores for ≥100 tactical puzzles before and after classifier change; verify pattern-appropriate shifts |
| AC-7 | Round-trip determinism | Same input SGF → same tactical analysis → same output SGF |

---

> **See also**:
> - [15-research.md](./15-research.md) — Full gap analysis with external reference cross-referencing
> - [TODO/puzzle-quality-scorer/implementation-plan.md](../../puzzle-quality-scorer/implementation-plan.md) — Original 4-phase implementation plan
> - [TODO/puzzle-quality-scorer/reference/](../../puzzle-quality-scorer/reference/) — Distilled algorithm references (gogogo, gogamev4)
