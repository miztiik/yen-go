# Plan — Enrichment Lab Tactical Hints & Detection Improvements

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Selected Option**: OPT-2 — New InstinctStage (Parallel Stage Architecture)
**Last Updated**: 2026-03-15

---

## 1. Architecture

### Current Pipeline Stage Order (from `enrich_single.py` L189)

```
Pre-pipeline: ParseStage + SolvePathStage (separate, before stage list)
Pipeline stages (StageRunner.run_pipeline):
  1. AnalyzeStage         — KataGo query + response
  2. ValidationStage      — correct-move existence check
  3. RefutationStage      — wrong-move branch generation
  4. DifficultyStage      — heuristic difficulty estimate
  5. AssemblyStage        — build AiAnalysisResult from stage outputs
  6. TechniqueStage       — 28 detectors → tag list
  7. TeachingStage        — hints + teaching comments
  8. SgfWritebackStage    — write SGF properties
```

### Modified Stage Order (After This Initiative)

```
Pipeline stages:
  1. AnalyzeStage         — unchanged
  2. ValidationStage      — unchanged
  3. RefutationStage      — unchanged
  4. DifficultyStage      — MODIFIED: + entropy feature, + Top-K rank
  5. AssemblyStage        — unchanged
  6. TechniqueStage       — MODIFIED: stores ctx.detection_results (stop discarding)
  7. InstinctStage        — NEW: classify move intent → ctx.instinct_results
  8. TeachingStage        — MODIFIED: reads detection_results + instinct_results + level_category
  9. SgfWritebackStage    — unchanged
```

### Data Flow Changes

```
TechniqueStage (modified):
  ├─ Runs 28 detectors → list[DetectionResult]
  ├─ ctx.detection_results = detection_results     ← NEW (stop discarding)
  └─ ctx.result.technique_tags = [slugs]           (existing)

InstinctStage (new):
  ├─ Reads ctx.position, ctx.response
  ├─ classify_instinct(position, response, config) → list[InstinctResult]
  ├─ ctx.instinct_results = instinct_results       ← NEW
  └─ error_policy = ErrorPolicy.DEGRADE            (failure → empty list, continue)

DifficultyStage (modified):
  ├─ compute_policy_entropy(response) → float      ← NEW
  ├─ find_correct_move_rank(response, correct_move) → int  ← NEW
  ├─ ctx.result.entropy = entropy_value            ← NEW (stored in YX)
  └─ ctx.result.correct_move_rank = rank           ← NEW (stored in BatchSummary)

TeachingStage (modified):
  ├─ Reads ctx.detection_results (evidence for Tier 2)
  ├─ Reads ctx.instinct_results (instinct for Tier 1/comments)
  ├─ Reads get_level_category(ctx.result.level_slug) (level-adaptive)
  └─ generate_hints(analysis, tags, detections, instincts, level_category)
```

### New Modules

| Module | Location | Purpose | Size |
|--------|----------|---------|------|
| `instinct_classifier.py` | `analyzers/` | Classify move intent from KataGo signals | ~100 LOC |
| `instinct_stage.py` | `analyzers/stages/` | Pipeline stage wrapping instinct classifier | ~30 LOC |
| `instinct_result.py` | `models/` | `InstinctResult` dataclass | ~15 LOC |

### Modified Modules

| Module | Change | Size |
|--------|--------|------|
| `analyzers/stages/technique_stage.py` | Store `ctx.detection_results` instead of discarding | ~3 LOC |
| `analyzers/stages/teaching_stage.py` | Pass detection_results + instincts + level to hint/teaching functions | ~10 LOC |
| `analyzers/hint_generator.py` | Accept and use detection evidence, instinct results, level category | ~50 LOC |
| `analyzers/teaching_comments.py` | Add instinct phrase to comment Layer 0 | ~30 LOC |
| `analyzers/comment_assembler.py` | Handle 3-layer composition (instinct + technique + signal) | ~15 LOC |
| `analyzers/estimate_difficulty.py` | Add `compute_policy_entropy()`, `find_correct_move_rank()` | ~20 LOC |
| `analyzers/stages/difficulty_stage.py` | Call entropy/Top-K, store on result | ~10 LOC |
| `analyzers/enrich_single.py` | Insert `InstinctStage()` in stage list after `TechniqueStage()` | 1 LOC |
| `analyzers/stages/protocols.py` | Add `detection_results`, `instinct_results` fields to PipelineContext | ~5 LOC |
| `models/position.py` | Add `rotate(degrees)` and `reflect(axis)` methods | ~30 LOC |
| `config/teaching.py` | Add instinct config + level-adaptive hint template models | ~20 LOC |

### Unchanged Modules

All 28 existing detectors, SGF parser, engine interface, query builder, refutation system, assembly stage, SgfWritebackStage.

---

## 2. Risks and Mitigations

| R-ID | Risk | Likelihood | Impact | Mitigation |
|------|------|-----------|--------|------------|
| R-1 | Instinct accuracy < 70% (AC-4) | Medium | Medium | Config-driven confidence thresholds per instinct; golden set calibration; graceful fallback to technique-only hints |
| R-2 | Multi-orientation tests reveal existing detector bugs | High (intentional) | Low | Fix bugs found; this is the PURPOSE of the testing infrastructure |
| R-3 | PipelineContext field addition breaks serialization | Low | Medium | `PipelineContext` is not serialized — it's an in-memory session object; fields default to None |
| R-4 | 3-layer comment exceeds 15-word cap | Medium | Low | comment_assembler overflow strategy already handles this; instinct phrase ≤3 words |
| R-5 | Level-adaptive hints produce worse hints for some categories | Low | Medium | AC-10: golden set review of 10 samples per level; existing template quality preserved as default |

---

## 3. Documentation Plan

### files_to_update

| File | Why Updated | Cross-Reference |
|------|------------|----------------|
| `tools/puzzle-enrichment-lab/AGENTS.md` | New modules (instinct_classifier, instinct_stage, instinct_result), modified data flow diagram, new stage in pipeline ordering, new PipelineContext fields | Internal architecture map |
| `docs/concepts/hints.md` | Instinct layer added to Tier 1 hints, detection evidence flows to Tier 2, level-adaptive content system — fundamentally changes hint conceptual model | [docs/concepts/](../../docs/concepts/) |
| `docs/how-to/tools/katago-enrichment-lab.md` | New InstinctStage in pipeline, new pipeline capabilities, new config sections for instinct templates and level-adaptive templates | [docs/how-to/tools/](../../docs/how-to/tools/) |
| `config/teaching.py` | New instinct config models, level-adaptive hint template models | Internal config |

### files_to_create

None expected. All new code goes into existing directory structure.

### why_updated

- **hints.md**: The hint system gains 3 new capabilities: (1) instinct classification in Tier 1 ("Push to force a ladder" instead of just "Ladder"), (2) detection evidence in Tier 2 ("12-step ladder chase" instead of generic depth), (3) level-adaptive content (different templates per level category). The conceptual model doc must reflect these structural changes.
- **katago-enrichment-lab.md**: The pipeline gains a new stage (InstinctStage), new config options (instinct confidence thresholds, level-adaptive templates), and new output data (instinct classification, policy entropy). How-to guide must document the new capabilities and configuration.
- **AGENTS.md**: Agent-facing architecture map must reflect new modules, stage ordering, and data flow changes (mandatory per `.github/instructions/puzzle-enrichment-lab.instructions.md`).

> **See also**:
> - [docs/concepts/hints.md](../../docs/concepts/) — Hint system conceptual model
> - [docs/how-to/tools/](../../docs/how-to/tools/) — Enrichment lab how-to guides

---

> **See also**:
> - [25-options.md](./25-options.md) — OPT-2 selected, rationale
> - [00-charter.md](./00-charter.md) — Goals G-1 through G-6
> - [40-tasks.md](./40-tasks.md) — Implementation task breakdown
