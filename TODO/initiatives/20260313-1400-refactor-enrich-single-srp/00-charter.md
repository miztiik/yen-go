# Charter: enrich_single.py SRP Refactor

**Initiative ID:** 20260313-1400-refactor-enrich-single-srp  
**Type:** Refactor  
**Last Updated:** 2026-03-13

---

## Prior Art

Initiative `2026-03-07-refactor-enrich-single-decomposition` (fully closed out) performed a first-pass decomposition:
- **Extracted:** `config_lookup.py` (metadata/level helpers), `enrichment_state.py` (@dataclass state carrier), moved `_uncrop_response` to `query_builder.py`
- **Reduced:** file from ~1,593 to ~1,500 lines at completion
- **Left intact:** The three major code paths (`_run_position_only_path`, `_run_has_solution_path`, `_run_standard_path`) and the 10-step orchestrator body
- **Post-decomposition growth:** New features (teaching comments, SGF writeback, goal inference, tree completeness tracking) added after that initiative grew the file back to ~1,726 lines

This initiative targets the **orchestrator body itself** — the part the prior initiative deliberately left intact. The prior extracted periphery; this extracts the core.

## Problem Statement

`tools/puzzle-enrichment-lab/analyzers/enrich_single.py` is **~1,726 lines** acting as:
1. **Workflow coordinator** (10-step pipeline sequencing)
2. **Policy engine** (tree-validation skip, refutation escalation, AC-level matrix)
3. **Telemetry adapter** (progress callbacks, phase timings, structured logs)
4. **Result assembler** (DTO mapping, field wiring, partial result construction)
5. **Error policy handler** (fail-fast vs degrade-graceful per stage)

Every new feature lands in this one function, causing merge conflicts, regression risk, and cognitive overload.

## Goals

1. **SRP decomposition**: Each extracted module has exactly one reason to change.
2. **DRY elimination**: Remove duplication between lab modules and backend `core/enrichment/` where functionality overlaps (property_policy, region, ko, move_order, refutation extraction, hints, technique tagging).
3. **Interface-first design**: Define contracts (protocols/ABCs) that the production backend can implement, enabling future swap-in without lab reimplementation.
4. **Pipeline-ready interfaces**: The lab's AI-powered enrichment stages should be pluggable into the backend's `stages/analyze.py` flow via shared protocols.
5. **All changes stay within `tools/puzzle-enrichment-lab/`** — no backend code modified.

## Non-Goals

- Actually integrating into the backend pipeline (this is interface prep only).
- Modifying `backend/puzzle_manager/` code.
- Adding new enrichment features.
- Changing the KataGo engine interface.

## Scope

### In-Scope Files (enrichment lab)
- `analyzers/enrich_single.py` (primary target — decompose)
- `models/enrichment_state.py` (evolve into pipeline context)
- `analyzers/property_policy.py` (DRY candidate — overlaps `backend/core/property_policy.py`)
- `analyzers/config_lookup.py` (result assembly helpers to extract)
- `analyzers/technique_classifier.py` (DRY candidate — overlaps `backend/core/tagger.py`)
- `analyzers/hint_generator.py` (DRY candidate — overlaps `backend/core/enrichment/hints.py`)
- `analyzers/sgf_enricher.py` (SGF writeback stage)
- `analyzers/observability.py` (already extracted — telemetry sink)
- New files for extracted stages/protocols

### Out-of-Scope
- `backend/puzzle_manager/` (read-only reference for interface design)
- `deprecated_generator/`
- `frontend/`
- Engine/KataGo internals (`analyzers/single_engine.py`, `engine/`)
- GUI bridge (`bridge.py`, `gui/`)

## Overlap Map (Lab ↔ Backend)

| Concern | Lab Module | Backend Module | Overlap Type |
|---------|-----------|---------------|-------------|
| Property policy | `analyzers/property_policy.py` | `core/property_policy.py` | Parallel impl of same JSON config |
| Region detection | (inline in enrich_single) | `core/enrichment/region.py` | Same concept, different data types |
| Ko detection | (from sgf_parser metadata) | `core/enrichment/ko.py` | Same concept, different entry points |
| Move order | (from sgf_parser metadata) | `core/enrichment/move_order.py` | Same concept, different entry points |
| Refutation extraction | `analyzers/generate_refutations.py` | `core/enrichment/refutation.py` | Different: lab=AI-powered, backend=tree-structural |
| Technique tagging | `analyzers/technique_classifier.py` | `core/tagger.py` | Different: lab=AI-analysis-based, backend=comment/board-based |
| Hint generation | `analyzers/hint_generator.py` | `core/enrichment/hints.py` | Different: lab=AI-analysis-based, backend=tag+solution-based |
| Difficulty classification | `analyzers/estimate_difficulty.py` | `core/classifier.py` | Different: lab=structural+MCTS formula, backend=heuristic |
| Teaching comments | `analyzers/teaching_comments.py` | (none) | Lab-only feature |
| SGF enricher | `analyzers/sgf_enricher.py` | `stages/analyze.py` (inline) | Different entry points, same output properties |
| Solution tree building | `analyzers/solve_position.py` | (none) | Lab-only feature (AI-Solve) |

## Integration Interface Vision

The backend pipeline follows: `StageContext → Stage.run() → StageResult`.
The lab should expose enrichment capabilities via **protocols** that the backend can consume:

```python
# Shared protocol (can live in lab, importable by backend later)
class EnrichmentStageProtocol(Protocol):
    async def enrich(self, context: EnrichmentContext) -> EnrichmentStageResult: ...
```

## Success Criteria

1. `enrich_single.py` reduced to < 200 lines (thin orchestrator only)
2. Each extracted module is independently testable *by design* (seams exist for per-stage unit tests; writing those tests is deferred to follow-on work)
3. Zero behavioral change (existing tests pass unchanged)
4. Protocols defined that backend `stages/analyze.py` could implement
5. No new imports from `backend/` in any lab module
