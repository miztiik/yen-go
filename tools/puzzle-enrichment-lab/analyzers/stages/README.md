# Enrichment Stages

Stage runner pipeline for single-puzzle enrichment.

## Pattern

Each stage implements the `EnrichmentStage` protocol from `protocols.py`:
- `name` property — stage identifier for logging/timing
- `error_policy` property — `FAIL_FAST` or `DEGRADE`
- `async run(ctx) → ctx` — stage logic operating on `PipelineContext`

`StageRunner` auto-wraps stages with timing, notifications, and error handling.

## Stage Execution Order

| # | Stage | Error Policy | Purpose |
|---|-------|-------------|---------|
| 1-2 | `ParseStage` | FAIL_FAST | Parse SGF, extract metadata + correct first move |
| 2b | `SolvePathStage` | DEGRADE | Dispatch: position-only / has-solution / standard |
| 3-4 | `AnalyzeStage` | FAIL_FAST | Build query (frame + ROI), run KataGo analysis |
| 5 | `ValidationStage` | DEGRADE | Validate correct move, tree validation |
| 6 | `RefutationStage` | DEGRADE | Generate wrong-move refutations + escalation |
| 7 | `DifficultyStage` | DEGRADE | Estimate difficulty (structural + policy fallback) |
| 8 | `AssemblyStage` | FAIL_FAST | Assemble AiAnalysisResult, AC level, goal inference |
| 9-10 | `TeachingStage` | DEGRADE | Technique, comments, hints, SGF writeback |

## Adding a New Stage

1. Create `analyzers/stages/my_stage.py`
2. Implement `EnrichmentStage` protocol (name, error_policy, async run)
3. Add to the stage list in `enrich_single.py`
4. Document field ownership in the plan's PipelineContext table

## Key Types

- **`PipelineContext`** — mutable dataclass flowing through all stages
- **`SgfMetadata`** — typed container for parsed SGF metadata (replaces bare dict)
- **`StageResult`** — per-stage outcome (success/failure/degraded)
- **`ErrorPolicy`** — `FAIL_FAST` | `DEGRADE`

Last Updated: 2026-03-13
