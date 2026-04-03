# Charter: Enrichment Lab No-Solution Resilience Refactor

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Type:** Refactor  
**Date:** 2026-03-07

## Problem Statement

The Puzzle Enrichment Lab (`tools/puzzle-enrichment-lab/`) hard-rejects SGFs that lack a correct first move, producing zero enrichment output. This affects two distinct scenarios:

1. **Position-only SGFs (no solution tree at all)** when `ai_solve` is NOT active → immediate `REJECTED` status at `enrich_single.py:546`
2. **AI-Solve finds no correct moves** even when enabled → immediate `REJECTED` at `enrich_single.py:598`

In both cases, the pipeline could still extract valuable partial enrichment: difficulty estimation from position analysis, technique classification from stone patterns, teaching comments, and hints — none of which require a correct first move.

## Goals

1. Eliminate hard-rejection for no-correct-move scenarios; produce partial enrichment instead
2. Ensure correct-moves-only SGFs (no wrong moves) still generate refutation branches via KataGo
3. Introduce a clear enrichment tier system matching D26 architecture decision (Tier 1=Bare, 2=Structural, 3=Full)
4. Design changes for future integration into `backend/puzzle_manager/` pipeline (but do NOT modify backend today)

## Non-Goals

- Modifying `backend/puzzle_manager/` code
- Adding new KataGo engine modes
- Changing the SGF schema version
- Modifying config/katago-enrichment.json thresholds

## In-Scope Files / Symbols

| File                                                       | Symbols                  | Change Type                                                           |
| ---------------------------------------------------------- | ------------------------ | --------------------------------------------------------------------- |
| `tools/puzzle-enrichment-lab/analyzers/enrich_single.py`   | `enrich_single_puzzle()` | Main refactor target: remove hard exits, add partial enrichment paths |
| `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py`    | `enrich_sgf()`           | Accept partial results (no refutations OK)                            |
| `tools/puzzle-enrichment-lab/models/ai_analysis_result.py` | `AiAnalysisResult`       | Add `enrichment_tier` field, partial-result flags                     |
| `tools/puzzle-enrichment-lab/tests/test_enrich_single.py`  | Test class additions     | New tests for partial enrichment scenarios                            |
| `tools/puzzle-enrichment-lab/tests/test_sgf_enricher.py`   | Test additions           | Verify enricher with partial results                                  |

## Out-of-Scope Exclusions

- `backend/puzzle_manager/**` — future integration only, no changes
- `config/` — no config schema changes
- `frontend/` — no frontend changes
- `tools/puzzle-enrichment-lab/analyzers/solve_position.py` — AI-Solve logic is working, not being changed
- `tools/puzzle-enrichment-lab/engine/` — engine layer untouched

## Constraints

1. Lab must continue to emit valid SGF (enriched or original passthrough)
2. `AiAnalysisResult` schema version bump required if model fields change
3. Must be testable without a running KataGo engine (mock-based unit tests)
4. Future pipeline integration: the lab's output SGF must be consumable by `backend/puzzle_manager/core/sgf_parser` without modifications

## Success Criteria

- Position-only SGF without ai_solve → `AiAnalysisResult` with `enrichment_tier=1` AND partial difficulty/technique data
- AI-Solve finds no correct moves → `AiAnalysisResult` with `enrichment_tier=1` AND position-level analysis data
- Correct-moves-only SGF (no wrong branches) → full enrichment with KataGo-generated refutations (verify this path works, no code changes expected)
- All existing tests continue to pass
- New test coverage for all three scenarios above
