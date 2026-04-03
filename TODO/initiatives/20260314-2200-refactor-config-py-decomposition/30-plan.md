# Plan — config.py SRP Decomposition (OPT-3 Hybrid)

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14
> Selected Option: **OPT-3 (Hybrid, 10 files)**

## Architecture

### Target Package Structure

```
tools/puzzle-enrichment-lab/
  config.py              ← DELETED
  config/                ← NEW PACKAGE
    __init__.py          # EnrichmentConfig + loaders + caches + re-exports (~246 lines)
    helpers.py           # get_effective_max_visits, get_level_category, LEVEL_CATEGORY_MAP (~70 lines)
    difficulty.py        # DifficultyConfig + ValidationConfig + OwnershipThresholds + ... (~225 lines)
    refutations.py       # RefutationsConfig + RefutationEscalationConfig + ... (~132 lines)
    technique.py         # TechniqueDetectionConfig + 10 detector configs + KoDetectionConfig (~85 lines)
    ai_solve.py          # AiSolveConfig + Thresholds + Confidence + Alternatives + Observability (~157 lines)
    solution_tree.py     # SolutionTreeConfig + DepthProfile + BensonGateConfig + ... (~200 lines)
    teaching.py          # TeachingConfig + TeachingCommentsConfig + loader (~159 lines)
    analysis.py          # AnalysisDefaultsConfig + VisitTiers + DeepEnrich + Models + ... (~246 lines)
    infrastructure.py    # PathsConfig + CalibrationConfig + LoggingExtraConfig + TestDefaultsConfig (~92 lines)
```

### Model-to-Module Assignment

| Module | Models (count) | Source Lines |
|--------|---------------|-------------|
| `__init__.py` | EnrichmentConfig (1) | L1156-L1246 |
| `helpers.py` | — (functions only) | L733-L759, L1490-L1522 |
| `difficulty.py` | OwnershipThresholds, CuratedPruningConfig, ValidationConfig, DifficultyWeights, StructuralDifficultyWeights, ScoreToLevelEntry, PolicyToLevelEntry, PolicyToLevel, MCTSConfig, DifficultyConfig, DifficultyNormalizationConfig, QualityGatesConfig, SparsePositionConfig, EscalationLevel, EscalationConfig, EloAnchorConfig, CalibratedRankElo (17) | L29-L158, L281-L327, L516-L528, L839-L878 |
| `refutations.py` | CandidateScoringConfig, RefutationOverridesConfig, TenukiRejectionConfig, RefutationsConfig, RefutationEscalationConfig (5) | L159-L279 |
| `technique.py` | LadderDetectionConfig, SnapbackDetectionConfig, NetDetectionConfig, SekiDetectionConfig, DirectCaptureDetectionConfig, ThrowInDetectionConfig, NakadeDetectionConfig, DoubleAtariDetectionConfig, SacrificeDetectionConfig, EscapeDetectionConfig, TechniqueDetectionConfig, KoDetectionConfig (12) | L583-L663 |
| `ai_solve.py` | AiSolveThresholds, AiSolveConfidenceMetrics, AiSolveAlternativesConfig, AiSolveCalibrationConfig, ObservabilityConfig, AiSolveConfig (6) | L776-L821, L1038-L1132 |
| `solution_tree.py` | DepthProfile, BensonGateConfig, SolutionTreeConfig, AiSolveSekiDetectionConfig, AiSolveGoalInference, EdgeCaseBoosts (6) | L761-L774, L823-L837, L878-L1036 |
| `teaching.py` | TeachingConfig, TeachingCommentEntry, WrongMoveTemplate, DeltaAnnotation, WrongMoveComments, SignalTemplates, AssemblyRules, AnnotationPolicy, TeachingCommentsConfig (9) | L665-L673, L1248-L1320 |
| `analysis.py` | AnalysisDefaultsConfig, VisitTierConfig, VisitTiersConfig, KoAnalysisConfig, DeepEnrichConfig, ModelEntry, ModelsConfig, TreeValidationConfig, FrameEntropyQualityConfig, FrameConfig, HumanSLConfig (11) | L327-L397, L399-L490, L528-L581, L1134-L1154 |
| `infrastructure.py` | PathsConfig, CalibrationConfig, LoggingExtraConfig, TestDefaultsConfig (4) | L492-L514, L675-L730 |

### Dependency Direction

```
pydantic.BaseModel  ←  difficulty.py
                    ←  refutations.py
                    ←  technique.py
                    ←  solution_tree.py
                    ←  teaching.py
                    ←  analysis.py
                    ←  infrastructure.py
                    ←  ai_solve.py  →  solution_tree.py  (AiSolveConfig composes SolutionTreeConfig)

config/__init__.py  ←  ALL sub-modules (composition root for EnrichmentConfig)
config/helpers.py   ←  __init__.py (needs EnrichmentConfig for get_effective_max_visits signature)
```

No circular imports. AC-8 verified.

### `__init__.py` Design

The `__init__.py` serves two roles:
1. **Composition root**: `EnrichmentConfig` imports and composes models from all sub-modules.
2. **Loader hub**: `load_enrichment_config()`, `load_puzzle_levels()`, `load_tag_ids()`, `get_level_id()`, `get_tag_id()`, `clear_cache()`, `resolve_path()` + their `_cached_*` globals.

Consumers that only need `EnrichmentConfig` or loaders: `from config import load_enrichment_config, EnrichmentConfig`.
Consumers that need specific models: `from config.difficulty import DifficultyConfig`.

## Execution Strategy

### Phase 1: Create config/ package (8 domain sub-modules)

1. Create `config/` directory with all 10 files.
2. Each sub-module: module docstring + `from __future__ import annotations` + pydantic imports + models cut from config.py.
3. `__init__.py`: imports from all sub-modules, defines `EnrichmentConfig`, contains all loader functions.
4. `helpers.py`: `LEVEL_CATEGORY_MAP`, `get_level_category()`, `get_effective_max_visits()`.
5. Verify: `python -c "from config import load_enrichment_config; cfg = load_enrichment_config(); print(cfg.version)"` works.

### Phase 2: Rewrite all import sites

1. Systematic file-by-file import rewrite across:
   - `analyzers/` (16 files)
   - `analyzers/detectors/` (26 files)
   - `analyzers/stages/` (2 files)
   - Top-level files: `bridge.py`, `cli.py`, `_model_paths.py`, `log_config.py`
   - `engine/` (1 file)
   - `scripts/` (2 files)
2. Pattern: find current `from config import X, Y, Z` → map each symbol to its new sub-module → rewrite.
3. Symbol mapping table drives mechanical rewrite (no judgment calls).

### Phase 3: Rewrite test imports

1. All `tests/test_*.py` files that import from config (~30 files).
2. Same mechanical mapping as Phase 2.
3. Add `clear_cache()` import from `config` (unchanged path) where needed.

### Phase 4: Delete monolith + verify

1. Delete `config.py`.
2. Run full test suite: `python -m pytest tests/ --cache-clear -x`.
3. Verify no remaining `from config import` that references non-existent monolith patterns.

### Phase 5: Documentation

1. Update `AGENTS.md` — file inventory, model locations, import patterns.
2. Update `README.md` if it references config.py.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Missed import site | Medium | Test failure | grep verification after Phase 2+3; full test suite (AC-5) |
| Circular import | Low | Import error | Dependency direction verified. Only one cross-module edge (ai_solve→solution_tree). |
| Name collision with config/ directory | Low | Import resolution | Python package (config/) takes precedence over module (config.py). Delete monolith first. |
| `__init__.py` exceeds 250 lines | Low | AC-6 violation | Estimated at ~246. EnrichmentConfig is 91 lines — structural, not reducible. |
| Teaching loader in wrong module | Low | Confusion | `load_teaching_comments_config` moves to `teaching.py` — matches its domain. |

## Rollback Strategy

If tests fail after Phase 4:
1. Restore `config.py` from git (the file is tracked).
2. Revert all import changes.
3. Delete `config/` directory.

Simple `git checkout -- tools/puzzle-enrichment-lab/config.py` + `git checkout -- tools/puzzle-enrichment-lab/analyzers/` etc.

## Documentation Plan

| Action | File | Why |
|--------|------|-----|
| Update | `tools/puzzle-enrichment-lab/AGENTS.md` | File inventory changes: config.py → config/ package. New sub-module descriptions. |
| Update | `tools/puzzle-enrichment-lab/README.md` | If references config.py, update to config/ package. |
| No change | `docs/how-to/backend/enrichment-lab.md` | References config JSON, not Python module. |
| No change | `.github/instructions/puzzle-enrichment-lab.instructions.md` | References entry points, not config internals. |
