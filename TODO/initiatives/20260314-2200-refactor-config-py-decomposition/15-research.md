# Research — config.py Decomposition

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14

## Planning Confidence

| Metric | Value |
|--------|-------|
| Pre-research confidence | 70 |
| Post-research confidence | 82 |
| Risk level | medium |
| Research invoked | yes (Feature-Researcher subagent) |

## Research Findings

### A. Import Dependency Graph

**Total import sites**: 100+ across the puzzle-enrichment-lab codebase.

**Top-imported symbols** (by frequency):
- `EnrichmentConfig` — ~40 sites (every detector, analyzer, test)
- `load_enrichment_config` — ~35 sites (loaders, tests, scripts)
- `clear_cache` — ~15 sites (tests only)
- `AiSolveConfig` / `SolutionTreeConfig` / `DepthProfile` — ~10 sites (AI-solve analyzers + tests)
- `load_teaching_comments_config` / `TeachingCommentsConfig` — 5 sites (comment assembler, hint generator, tests)
- `TechniqueDetectionConfig` — 2 sites (technique_classifier)
- `get_effective_max_visits` — 1 site (analyze_stage)
- `get_level_category` / `LEVEL_CATEGORY_MAP` — 3 sites (solve_position, tests)
- `DifficultyWeights` / `DifficultyNormalizationConfig` — 3 sites (estimate_difficulty, tests)
- `resolve_path` — 4 sites (cli, log_config, engine, calibration)

**Import pattern**: All use `from config import ...` (bare module name, sys.path-relative).

### B. Existing `models/` Package

10 files with runtime data models (Position, SolveResult, DetectionResult, etc.). **Zero overlap** with config.py's 71 Pydantic config models. Models/ is for inter-module data transfer objects; config.py is for JSON schema binding. Clear conceptual separation.

### C. Existing Initiatives

- `20260314-1400-feature-enrichment-lab-v2` (CLOSED): Declared config decomposition **out of scope**, recommended it as follow-up.
- `20260314-research-enrichment-lab-rewrite`: Explicitly recommended config split.
- `20260313-1400-refactor-enrich-single-srp` (CLOSED): Unrelated (enrich_single decomposition).

### D. No External Consumers

`backend/puzzle_manager/` has its own separate `EnrichmentConfig`. Neither frontend nor gui nor katago sub-packages import from the lab's `config.py`. Blast radius is contained within `tools/puzzle-enrichment-lab/`.

### E. Existing `analyzers/config_lookup.py`

Loads tag/level data from `config/tags.json` and `config/puzzle-levels.json` with its own caching. **Does NOT import from config.py** — completely separate concern. No conflict with decomposition.

### F. Domain Clustering Analysis

Natural clustering of the 71 models into semantic domains:

| Domain | Model Count | Key Classes |
|--------|-------------|-------------|
| **Core / Loading** | 3 | `EnrichmentConfig`, `PathsConfig`, `LoggingExtraConfig` |
| **Difficulty** | 8 | `DifficultyConfig`, `DifficultyWeights`, `StructuralDifficultyWeights`, `ScoreToLevelEntry`, `PolicyToLevel*`, `MCTSConfig`, `DifficultyNormalizationConfig` |
| **Validation / Escalation** | 6 | `ValidationConfig`, `CuratedPruningConfig`, `EscalationConfig`, `EscalationLevel`, `QualityGatesConfig`, `SparsePositionConfig` |
| **Refutations** | 6 | `RefutationsConfig`, `RefutationEscalationConfig`, `CandidateScoringConfig`, `RefutationOverridesConfig`, `TenukiRejectionConfig` |
| **Technique Detection** | 12 | `TechniqueDetectionConfig`, `LadderDetectionConfig`, `SnapbackDetectionConfig`, `NetDetectionConfig`, `SekiDetectionConfig`, `DirectCaptureDetectionConfig`, `ThrowInDetectionConfig`, `NakadeDetectionConfig`, `DoubleAtariDetectionConfig`, `SacrificeDetectionConfig`, `EscapeDetectionConfig`, `KoDetectionConfig` |
| **AI-Solve** | 14 | `AiSolveConfig`, `AiSolveThresholds`, `SolutionTreeConfig`, `DepthProfile`, `BensonGateConfig`, `AiSolveSekiDetectionConfig`, `AiSolveGoalInference`, `EdgeCaseBoosts`, `AiSolveAlternativesConfig`, `AiSolveCalibrationConfig`, `ObservabilityConfig`, `AiSolveConfidenceMetrics` |
| **Teaching** | 8 | `TeachingConfig`, `TeachingCommentsConfig`, `TeachingCommentEntry`, `WrongMoveTemplate`, `DeltaAnnotation`, `WrongMoveComments`, `SignalTemplates`, `AssemblyRules`, `AnnotationPolicy` |
| **Analysis / Engine** | 7 | `AnalysisDefaultsConfig`, `VisitTierConfig`, `VisitTiersConfig`, `KoAnalysisConfig`, `DeepEnrichConfig`, `ModelsConfig`, `ModelEntry`, `TestDefaultsConfig`, `TreeValidationConfig` |
| **Specialized** | 5 | `OwnershipThresholds`, `CalibrationConfig`, `EloAnchorConfig`, `CalibratedRankElo`, `HumanSLConfig`, `FrameConfig`, `FrameEntropyQualityConfig` |
| **Functions** | 10 | `load_enrichment_config`, `load_puzzle_levels`, `load_tag_ids`, `load_teaching_comments_config`, `get_level_id`, `get_tag_id`, `get_level_category`, `get_effective_max_visits`, `clear_cache`, `resolve_path` |
