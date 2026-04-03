# Tasks — config.py SRP Decomposition (OPT-3)

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14
> Selected Option: OPT-3 (Hybrid, 10 files)

## Symbol → Module Mapping (reference for all tasks)

| Symbol | Target Module |
|--------|---------------|
| `EnrichmentConfig` | `config` (\_\_init\_\_) |
| `load_enrichment_config` | `config` (\_\_init\_\_) |
| `clear_cache` | `config` (\_\_init\_\_) |
| `resolve_path` | `config` (\_\_init\_\_) |
| `load_puzzle_levels`, `get_level_id` | `config` (\_\_init\_\_) |
| `load_tag_ids`, `get_tag_id` | `config` (\_\_init\_\_) |
| `get_effective_max_visits` | `config.helpers` |
| `get_level_category`, `LEVEL_CATEGORY_MAP` | `config.helpers` |
| `DifficultyConfig`, `DifficultyWeights`, `StructuralDifficultyWeights`, `DifficultyNormalizationConfig`, `ValidationConfig`, `CuratedPruningConfig`, `OwnershipThresholds`, `QualityGatesConfig`, `SparsePositionConfig`, `EscalationConfig`, `EscalationLevel`, `ScoreToLevelEntry`, `PolicyToLevelEntry`, `PolicyToLevel`, `MCTSConfig`, `EloAnchorConfig`, `CalibratedRankElo` | `config.difficulty` |
| `RefutationsConfig`, `RefutationEscalationConfig`, `CandidateScoringConfig`, `RefutationOverridesConfig`, `TenukiRejectionConfig` | `config.refutations` |
| `TechniqueDetectionConfig`, `LadderDetectionConfig`, `SnapbackDetectionConfig`, `NetDetectionConfig`, `SekiDetectionConfig`, `DirectCaptureDetectionConfig`, `ThrowInDetectionConfig`, `NakadeDetectionConfig`, `DoubleAtariDetectionConfig`, `SacrificeDetectionConfig`, `EscapeDetectionConfig`, `KoDetectionConfig` | `config.technique` |
| `AiSolveConfig`, `AiSolveThresholds`, `AiSolveConfidenceMetrics`, `AiSolveAlternativesConfig`, `AiSolveCalibrationConfig`, `ObservabilityConfig` | `config.ai_solve` |
| `SolutionTreeConfig`, `DepthProfile`, `BensonGateConfig`, `AiSolveSekiDetectionConfig`, `AiSolveGoalInference`, `EdgeCaseBoosts` | `config.solution_tree` |
| `TeachingConfig`, `TeachingCommentsConfig`, `TeachingCommentEntry`, `WrongMoveTemplate`, `DeltaAnnotation`, `WrongMoveComments`, `SignalTemplates`, `AssemblyRules`, `AnnotationPolicy`, `load_teaching_comments_config` | `config.teaching` |
| `AnalysisDefaultsConfig`, `VisitTierConfig`, `VisitTiersConfig`, `KoAnalysisConfig`, `DeepEnrichConfig`, `ModelEntry`, `ModelsConfig`, `TreeValidationConfig`, `FrameEntropyQualityConfig`, `FrameConfig`, `HumanSLConfig` | `config.analysis` |
| `PathsConfig`, `CalibrationConfig`, `LoggingExtraConfig`, `TestDefaultsConfig` | `config.infrastructure` |

---

## Phase 1: Create config/ package

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T1 | Create `config/difficulty.py` — 17 models from L29-L158, L281-L327, L516-L528, L839-L878 | `config/difficulty.py` | — | [P] |
| T2 | Create `config/refutations.py` — 5 models from L159-L279 | `config/refutations.py` | — | [P] |
| T3 | Create `config/technique.py` — 12 models from L583-L663 | `config/technique.py` | — | [P] |
| T4 | Create `config/solution_tree.py` — 6 models from L761-L774, L823-L837, L878-L1036 | `config/solution_tree.py` | — | [P] |
| T5 | Create `config/ai_solve.py` — 6 models from L776-L821, L1038-L1132. Imports SolutionTreeConfig etc. from solution_tree. | `config/ai_solve.py` | T4 | |
| T6 | Create `config/teaching.py` — 9 models from L665-L673, L1248-L1320 + `load_teaching_comments_config` + `_cached_teaching_comments` | `config/teaching.py` | — | [P] |
| T7 | Create `config/analysis.py` — 11 models from L327-L397, L399-L490, L528-L581, L1134-L1154 | `config/analysis.py` | — | [P] |
| T8 | Create `config/infrastructure.py` — 4 models from L492-L514, L675-L730 | `config/infrastructure.py` | — | [P] |
| T9 | Create `config/helpers.py` — `LEVEL_CATEGORY_MAP`, `get_level_category()`, `get_effective_max_visits()` | `config/helpers.py` | — | [P] |
| T10 | Create `config/__init__.py` — `EnrichmentConfig` + imports from all sub-modules + loader functions + caches + `clear_cache()` + `resolve_path()` | `config/__init__.py` | T1-T9 | |
| T11 | Smoke test: `from config import load_enrichment_config; cfg = load_enrichment_config()` succeeds | — | T10 | |

## Phase 2: Rewrite analyzer imports

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T12 | Rewrite imports in `analyzers/enrich_single.py` | `analyzers/enrich_single.py` | T11 | [P] |
| T13 | Rewrite imports in `analyzers/solve_position.py` | `analyzers/solve_position.py` | T11 | [P] |
| T14 | Rewrite imports in `analyzers/query_builder.py` | `analyzers/query_builder.py` | T11 | [P] |
| T15 | Rewrite imports in `analyzers/validate_correct_move.py` | `analyzers/validate_correct_move.py` | T11 | [P] |
| T16 | Rewrite imports in `analyzers/generate_refutations.py` | `analyzers/generate_refutations.py` | T11 | [P] |
| T17 | Rewrite imports in `analyzers/estimate_difficulty.py` | `analyzers/estimate_difficulty.py` | T11 | [P] |
| T18 | Rewrite imports in `analyzers/technique_classifier.py` | `analyzers/technique_classifier.py` | T11 | [P] |
| T19 | Rewrite imports in `analyzers/teaching_comments.py` | `analyzers/teaching_comments.py` | T11 | [P] |
| T20 | Rewrite imports in `analyzers/comment_assembler.py` | `analyzers/comment_assembler.py` | T11 | [P] |
| T21 | Rewrite imports in `analyzers/hint_generator.py` | `analyzers/hint_generator.py` | T11 | [P] |
| T22 | Rewrite imports in `analyzers/ko_validation.py` | `analyzers/ko_validation.py` | T11 | [P] |
| T23 | Rewrite imports in `analyzers/result_builders.py` | `analyzers/result_builders.py` | T11 | [P] |
| T24 | Rewrite imports in `analyzers/single_engine.py` | `analyzers/single_engine.py` | T11 | [P] |
| T25 | Rewrite imports in `analyzers/humansl_calibration.py` | `analyzers/humansl_calibration.py` | T11 | [P] |
| T26 | Rewrite imports in `analyzers/stages/analyze_stage.py` | `analyzers/stages/analyze_stage.py` | T11 | [P] |
| T27 | Rewrite imports in `analyzers/stages/protocols.py` | `analyzers/stages/protocols.py` | T11 | [P] |
| T27B | Rewrite imports in `analyzers/stages/solve_paths.py` — runtime `from config import AiSolveConfig` → `from config.ai_solve import AiSolveConfig` | `analyzers/stages/solve_paths.py` | T11 | [P] |

## Phase 3: Rewrite detector imports

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T28 | Rewrite imports in all 29 `analyzers/detectors/*.py` files (28 detectors + `__init__.py`). Each imports `EnrichmentConfig` → `from config import EnrichmentConfig`. | `analyzers/detectors/*.py` (29 files) | T11 | [P] |

## Phase 4: Rewrite top-level + engine + script imports

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T29 | Rewrite imports in `bridge.py` | `bridge.py` | T11 | [P] |
| T30 | Rewrite imports in `cli.py` | `cli.py` | T11 | [P] |
| T31 | Rewrite imports in `_model_paths.py` | `_model_paths.py` | T11 | [P] |
| T32 | Rewrite imports in `log_config.py` | `log_config.py` | T11 | [P] |
| T33 | Rewrite imports in `engine/local_subprocess.py` | `engine/local_subprocess.py` | T11 | [P] |
| T34 | Rewrite imports in `scripts/download_models.py` + `scripts/run_calibration.py` | `scripts/*.py` | T11 | [P] |

## Phase 5: Rewrite test imports

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T35 | Rewrite imports in all `tests/test_*.py` files (~38 files). Use the symbol mapping table. | `tests/*.py` | T11 | [P] |
| T36 | Rewrite imports in `tests/generate_review_report.py` + `conftest.py` | `tests/generate_review_report.py`, `conftest.py` | T11 | [P] |

## Phase 6: Delete monolith + verify

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T37 | Delete `config.py` | `config.py` | T12-T36 | |
| T38 | Run full test suite: `python -m pytest tests/ --cache-clear -x` | — | T37 | |
| T39 | Grep verification: `grep -r "from config import" . --include="*.py"` — verify all imports resolve to config/ package | — | T37 | |
| T40 | Verify no file in config/ exceeds 250 lines: `wc -l config/*.py` | — | T37 | |

## Phase 7: Documentation

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T41 | Update `AGENTS.md` — file inventory, model locations, import patterns, config source reference | `AGENTS.md` | T38 | |
| T42 | Update `README.md` if it references `config.py` | `README.md` | T38 | [P] |

---

## Summary

| Phase | Tasks | Parallel? | Description |
|-------|-------|-----------|-------------|
| 1 | T1-T11 | Mostly parallel (T1-T9 parallel, T10 after, T11 after) | Create package |
| 2 | T12-T27 | All parallel | Rewrite analyzer imports |
| 3 | T28 | Single batch | Rewrite detector imports |
| 4 | T29-T34 | All parallel | Rewrite top-level imports |
| 5 | T35-T36 | Parallel | Rewrite test imports |
| 6 | T37-T40 | Sequential | Delete + verify |
| 7 | T41-T42 | Parallel | Documentation |

**Total: 43 tasks across 7 phases.**

## Phase 8: Post-Review RC Fixes (Governance Review Gate 6)

| Task | Description | File(s) | Deps | Parallel |
|------|-------------|---------|------|----------|
| T43 | RC-1: Fix `from config import DepthProfile` → `from config.solution_tree import DepthProfile` in defensive fallback | `analyzers/solve_position.py` | T38 | [P] |
| T44 | RC-2: Add `clear_teaching_cache()` to teaching.py; update `clear_cache()` in `__init__.py` to call it instead of manipulating internal state | `config/teaching.py`, `config/__init__.py` | T38 | [P] |
| T45 | RC-3: Remove dead import `from config.teaching import _cached_teaching_comments` (subsumed by RC-2) | `config/__init__.py` | T44 | |
| T46 | Re-run full test suite after RC fixes | — | T43-T45 | |

**Updated total: 46 tasks across 8 phases.**
