# ADR-008: AI-Solve Unified Puzzle Enrichment

**Status**: Accepted (Phases 1-10 implemented; Phase 11 structural tests pass, live KataGo calibration sweep pending; Phase 12 docs partially complete)\n**Date**: 2026-03-04 (updated)
**Context**: KataGo enrichment lab → AI-Solve unified enrichment pipeline
**Source documents**: [007-adr-policy-aligned-enrichment](007-adr-policy-aligned-enrichment.md), [ai-solve-enrichment-plan-v3](../ai-solve-enrichment-plan-v3.md)
**Review Panel**: Cho Chikun (9p), Lee Sedol (9p), Shin Jinseo (9p), Ke Jie (9p), Principal Staff Engineer A, Principal Staff Engineer B

---

## Summary

This ADR captures all architectural design decisions for the AI-Solve unified enrichment feature — building complete solution trees for position-only puzzles and enriching ALL puzzles through AI analysis, whether they already have solutions or not.

## Context

The enrichment lab's `enrich_single_puzzle()` currently rejects any SGF without a child node containing a correct first move. This blocks 900+ position-only puzzles (e.g., tasuki/cho-chikun-elementary) and any future source without solution trees. Additionally, puzzles WITH existing solutions do not benefit from AI-discovered alternative correct paths or deeper solution trees.

## Decisions

### D1: Category-Aware Natural Stopping with Configurable Bounds

**Decision**: Solution tree depth is controlled by natural stopping conditions (winrate stability, ownership convergence, seki detection) with level-category depth profiles (entry/core/strong), not by a single fixed depth pair.

**Rationale**: Different puzzle difficulties have different natural depths. Following review guidance from Cho Chikun and Lee Sedol, entry-level puzzles should terminate quickly, while stronger puzzles should allow deeper tactical expansion. Natural stopping plus category profiles preserves both efficiency and strength coverage.

**Constraints**: Never stop before active profile `solution_min_depth` (`entry=2`, `core=3`, `strong=4`). Never exceed active profile `solution_max_depth` (`entry=10`, `core=16`, `strong=28`). Seki-specific early-exit prevents oscillation.

### D2: Winrate-Primary for Correct Moves, Policy-Primary for Wrong Moves

**Decision**: Two separate ranking systems operate on the same initial analysis. Correct moves are ranked by winrate (finding the best move). Wrong moves are ranked by policy (finding the most tempting traps).

**Rationale**: Winrate reflects truth after search. Policy reflects neural network intuition — precisely what makes a wrong move a good trap for students.

### D3: Recursive Branching at Opponent Decision Points

**Decision**: Solution trees branch at opponent nodes (2-3 responses per opponent move) but not at player nodes (1 correct follow-up). Total queries capped by a required `QueryBudget`.

**Deterministic allocation policy**:

- Build candidate pools once from pre-analysis: `correct_pool` (TE, sort winrate desc then policy desc) and `wrong_pool` (BM/BM_HO, sort policy desc then delta desc).
- Allocate in fixed priority: primary correct root → wrong refutation roots → additional co-correct roots.
- Enforce root-level caps: `max_correct_root_trees=2` (includes primary), `max_refutation_root_trees=3`.
- Apply global per-puzzle query cap: `max_total_tree_queries=50` across all roots/branches.
- If budget is exhausted, skip lower-priority roots and mark entered unfinished lines as truncated.

**Rationale**: Branching at player nodes implies multiple correct answers at each depth — rare in tsumego. Branching at opponent nodes reflects the real structure of solutions. Budget cap prevents runaway computation.

**Review-panel refinement rationale**: Cho Chikun favored deterministic compactness, Lee Sedol favored meaningful tactical breadth, Shin Jinseo/Ke Jie favored stable AI-ordered prioritization, and engineering panel members required explicit caps for reproducible outputs.

**Constraint**: If budget exhausts before active profile `solution_min_depth`, confidence is downgraded and ac:2 is prevented.

### D4: Four-Level AI Correctness (AC) System

**Decision**: `ac:0` (untouched), `ac:1` (enriched), `ac:2` (ai_solved), `ac:3` (human verified). Wire format: `YQ[q:2;rc:0;hc:0;ac:1]`.

**Rationale**: Distinguishes between "AI agreed with existing solution" (ac:1) and "AI built the solution" (ac:2). ac:3 workflow is out of scope — defined for forward compatibility.

### D5: Unified Pipeline — No Opt-In Flag

**Decision**: Every puzzle flows through AI enrichment. Position-only puzzles get solution trees built. Puzzles with solutions get validation + alternative discovery. No `--allow-ai-solve` flag.

**Rationale**: The distinction between "has solution" and "position-only" is just a branching condition inside the same pipeline, not a separate feature. Feature-gating is via `ai_solve.enabled` config (default: false during development).

### D6: Pre/Post Winrate Floors as Confidence Metrics, Not Gates

**Decision**: `pre_winrate_floor` and `post_winrate_ceiling` are confidence annotations, not classification gates. Delta-based classification dominates.

**Rationale**: Many valid tsumego start from positions with root winrate < 0.90. Rejecting them would exclude legitimate puzzles. The delta between pre and post winrate is the teaching signal.

### D7: Co-Correct Detection (Not Miai)

**Decision**: Renamed from "miai" to "co-correct." Detection requires three signals: winrate gap, both moves classify as TE, and score gap below threshold.

**Rationale**: Go-theoretic miai requires moves to be interchangeable in effect — unverifiable from winrate alone. "Co-correct" accurately describes what we detect without false semantic claims.

### D8: Multi-Signal Goal Inference

**Decision**: Score delta is primary signal for kill/live/ko/capture goal inference. Ownership is secondary with variance gate.

**Rationale**: Ownership near edges fluctuates, especially in ko/seki. Score delta (correct move swings score by 15+ points) is more stable for life-and-death detection.

### D9: Stratified, Model-Aware Calibration

**Decision**: Calibration uses held-out fixture set, stratified sampling (≥30 per class), macro-F1 optimization, parameterized by model version and visit count.

**Rationale**: Most moves are neutral — unstratified calibration inflates F1. Thresholds shift between KataGo model versions (b6/b18/b28). Calibration must account for this.

### D10: Human Solution Confidence Metadata

**Decision**: When AI disagrees with existing solution, attach `human_solution_confidence: "strong"|"weak"|"losing"` metadata. Never reorder SGF children.

**Rationale**: Frontend needs a signal to make informed display decisions. Reordering would break backward compatibility. Metadata is the non-invasive approach.

### D11: Batch Summaries + Disagreement Sink

**Decision**: Every batch emits `BatchSummary` as structured JSON. Disagreements written to JSONL sink. Per-collection disagreement rates tracked.

**Rationale**: Per-puzzle logs are insufficient for quality monitoring. Batch aggregates and persistent disagreement records enable quality dashboards and future ac:3 review tooling.

### D12: Edge Case Handling Table

**Decision**: Explicit handling for pass-as-correct (reject), seki (early-exit), bent-four (visit boost), ladder (visit boost + flag), budget exhaustion (confidence downgrade).

**Rationale**: Each edge case has a known failure mode in KataGo. Without explicit handling, they produce silent incorrect results.

## Consequences

- Position-only puzzles (900+) become enrichable.
- All puzzles get AI validation of existing solutions.
- Quality tracking via ac:0-3 enables frontend badges and filtering.
- Disagreement sink enables future human review workflow (ac:3).
- Calibration tests prevent threshold drift across model upgrades.
- Full refactor of enrich_single.py Step 2 — no backward-compatible shims.
- Phase 1 config contract MUST expose deterministic root-cap knobs (`max_correct_root_trees`, `max_refutation_root_trees`) as configuration, not code constants.

## Implementation

12-phase gated implementation tracked in `TODO/ai-solve-enrichment-plan-v3.md`.

## References

- [v3 Implementation Plan](../ai-solve-enrichment-plan-v3.md)
- [v2.1 Plan with Expert Panel Dialogue](../ai-solve-enrichment-plan-v2.md) (archived reference)
- [ADR-007: Policy-Aligned Enrichment](007-adr-policy-aligned-enrichment.md)
