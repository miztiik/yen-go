# Options — config.py Decomposition (Rev 2)

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14
> Revision: **Rev 2** — corrected line estimates per GOV-OPTIONS-REVISE (RC-1..RC-5)

## Context

Research identified 71 Pydantic models clustering into 9 natural semantic domains + 10 functions. File is ~1,550 lines (not 1,003 as initially estimated — classes span L29 to L1319 + functions through ~L1550).

**Rev 2 corrections**: Line estimates now computed from actual class line spans via `grep`. ai_solve split into `ai_solve.py` + `solution_tree.py` (RC-2). Infrastructure models extracted from `analysis.py` (RC-3). OPT-2 eliminated — fails AC-6 (RC-4). Dependency direction verified (RC-5).

All options share these invariants:
- Delete monolith `config.py` → create `config/` package
- Rewrite all 120+ import sites (Q1=B)
- `config/__init__.py` exports loader functions + `EnrichmentConfig`
- `config/helpers.py` contains business logic functions
- Zero runtime behavior change

---

## OPT-2: ~~Coarse-Grained~~ — ELIMINATED

OPT-2 combined Difficulty+Validation+Refutation+Escalation+Analysis into a single `enrichment.py` (~450 lines). **Fails AC-6 (≤250 lines)** and recreates the monolith problem at smaller scale. Eliminated per governance RC-4.

---

## OPT-1: Fine-Grained (10 files)

Separates difficulty and validation into distinct files. Otherwise identical to OPT-3.

### Module Layout

| File | Models | Body Lines | Total ~Lines | Key Consumers |
|------|--------|------------|--------------|---------------|
| `config/__init__.py` | `EnrichmentConfig` (91) + loaders + caches + re-exports | 155 + 91 | ~246 | Everyone |
| `config/helpers.py` | `get_effective_max_visits`, `get_level_category`, `LEVEL_CATEGORY_MAP` | 60 | ~70 | solve_position, analyze_stage |
| `config/difficulty.py` | `DifficultyConfig`, `DifficultyWeights`, `StructuralDifficultyWeights`, `DifficultyNormalizationConfig`, `ScoreToLevelEntry`, `PolicyToLevel*`, `MCTSConfig`, `EloAnchorConfig`, `CalibratedRankElo` (11 models) | 155 | ~170 | estimate_difficulty |
| `config/validation.py` | `ValidationConfig`, `CuratedPruningConfig`, `OwnershipThresholds`, `EscalationConfig`, `EscalationLevel`, `QualityGatesConfig`, `SparsePositionConfig` (7 models) | 63 | ~78 | validate_correct_move |
| `config/refutations.py` | `RefutationsConfig`, `RefutationEscalationConfig`, `CandidateScoringConfig`, `RefutationOverridesConfig`, `TenukiRejectionConfig` (5 models) | 117 | ~132 | generate_refutations |
| `config/technique.py` | `TechniqueDetectionConfig` + 10 detector configs + `KoDetectionConfig` (12 models) | 70 | ~85 | technique_classifier, detectors |
| `config/ai_solve.py` | `AiSolveConfig`, `AiSolveThresholds`, `AiSolveConfidenceMetrics`, `AiSolveAlternativesConfig`, `AiSolveCalibrationConfig`, `ObservabilityConfig` (6 models) | 137 | ~157 | solve_position |
| `config/solution_tree.py` | `SolutionTreeConfig`, `DepthProfile`, `BensonGateConfig`, `AiSolveSekiDetectionConfig`, `AiSolveGoalInference`, `EdgeCaseBoosts` (6 models) | 185 | ~200 | solve_position, ai_solve tests |
| `config/teaching.py` | `TeachingConfig` + `TeachingCommentsConfig` + all sub-models + `load_teaching_comments_config` (9 models + 1 loader) | 109 | ~159 | comment_assembler, hint_generator |
| `config/analysis.py` | `AnalysisDefaultsConfig`, `VisitTiers`, `KoAnalysisConfig`, `DeepEnrichConfig`, `ModelsConfig`, `ModelEntry`, `TreeValidationConfig`, `FrameConfig`, `HumanSLConfig` (11 models) | 231 | ~246 | cli, engine, stage_runner |
| `config/infrastructure.py` | `PathsConfig`, `CalibrationConfig`, `LoggingExtraConfig`, `TestDefaultsConfig` (4 models) | 77 | ~92 | cli, log_config, calibration |

**Total: 11 files. Max: ~246 (analysis.py). All ≤250. ✅**

### Tradeoffs

| Dimension | Assessment |
|-----------|------------|
| SRP | ✅ Excellent — every file owns exactly one domain |
| ISP | ✅ Strong — narrow imports per consumer |
| Module count | 11 files — higher cognitive overhead |
| Max file size | ~246 lines (analysis.py) ✅ |
| AC-6 compliance | ✅ All files ≤250 |
| Circular import risk | Low |
| Difficulty-Validation split | ⚠️ These two domains are frequently co-consumed by validate_correct_move — separate files means two imports |

---

## OPT-3: Hybrid (10 files) — RECOMMENDED

Combines difficulty + validation (natural pair), otherwise identical to OPT-1. Governance-mandated sub-splits applied.

### Module Layout

| File | Models | Body Lines | Total ~Lines | Key Consumers |
|------|--------|------------|--------------|---------------|
| `config/__init__.py` | `EnrichmentConfig` (91) + loaders + caches + re-exports | 155 + 91 | ~246 | Everyone |
| `config/helpers.py` | `get_effective_max_visits`, `get_level_category`, `LEVEL_CATEGORY_MAP` | 60 | ~70 | solve_position, analyze_stage |
| `config/difficulty.py` | `DifficultyConfig`, Weights, `DifficultyNormalizationConfig`, `ValidationConfig`, `CuratedPruningConfig`, `OwnershipThresholds`, `EscalationConfig`, `EscalationLevel`, `QualityGatesConfig`, `SparsePositionConfig`, ScoreToLevel*, PolicyToLevel*, MCTSConfig, `EloAnchorConfig`, `CalibratedRankElo` (17 models) | 210 | ~225 | estimate_difficulty, validate_correct_move |
| `config/refutations.py` | `RefutationsConfig`, `RefutationEscalationConfig`, `CandidateScoringConfig`, `RefutationOverridesConfig`, `TenukiRejectionConfig` (5 models) | 117 | ~132 | generate_refutations |
| `config/technique.py` | `TechniqueDetectionConfig` + 10 detector configs + `KoDetectionConfig` (12 models) | 70 | ~85 | technique_classifier, detectors |
| `config/ai_solve.py` | `AiSolveConfig`, `AiSolveThresholds`, `AiSolveConfidenceMetrics`, `AiSolveAlternativesConfig`, `AiSolveCalibrationConfig`, `ObservabilityConfig` (6 models) | 137 | ~157 | solve_position |
| `config/solution_tree.py` | `SolutionTreeConfig`, `DepthProfile`, `BensonGateConfig`, `AiSolveSekiDetectionConfig`, `AiSolveGoalInference`, `EdgeCaseBoosts` (6 models) | 185 | ~200 | solve_position, ai_solve tests |
| `config/teaching.py` | `TeachingConfig` + `TeachingCommentsConfig` + all sub-models + `load_teaching_comments_config` (9 models + 1 loader) | 109 | ~159 | comment_assembler, hint_generator |
| `config/analysis.py` | `AnalysisDefaultsConfig`, `VisitTiers`, `KoAnalysisConfig`, `DeepEnrichConfig`, `ModelsConfig`, `ModelEntry`, `TreeValidationConfig`, `FrameConfig`, `HumanSLConfig` (11 models) | 231 | ~246 | cli, engine, stage_runner |
| `config/infrastructure.py` | `PathsConfig`, `CalibrationConfig`, `LoggingExtraConfig`, `TestDefaultsConfig` (4 models) | 77 | ~92 | cli, log_config, calibration |

**Total: 10 files. Max: ~246 (analysis.py). All ≤250. ✅**

### Import Path Examples

```python
# Most common pattern (detectors, analyzers)
from config import load_enrichment_config, EnrichmentConfig, clear_cache

# Domain-specific
from config.difficulty import DifficultyConfig, ValidationConfig, DifficultyNormalizationConfig
from config.refutations import RefutationsConfig
from config.ai_solve import AiSolveConfig
from config.solution_tree import SolutionTreeConfig, DepthProfile
from config.technique import TechniqueDetectionConfig
from config.teaching import TeachingCommentsConfig, load_teaching_comments_config
from config.analysis import DeepEnrichConfig, ModelsConfig, TreeValidationConfig
from config.infrastructure import PathsConfig, TestDefaultsConfig

# Business logic helpers
from config.helpers import get_effective_max_visits, get_level_category
```

### Tradeoffs

| Dimension | Assessment |
|-----------|------------|
| SRP | ✅ Good — each file owns one or two closely-related domains |
| ISP | ✅ Good — consumers import relevant domain module |
| Module count | 10 files — balanced |
| Max file size | ~246 lines (analysis.py) ✅ |
| AC-6 compliance | ✅ All files ≤250 |
| Circular import risk | Low — verified (see dependency table) |
| Difficulty-Validation grouping | ✅ Natural pair — frequently co-consumed |

---

## Dependency Direction Table (RC-5)

All sub-modules import **only** from `pydantic` (external) — no cross-sub-module imports among domain files. The dependency tree is:

```
pydantic.BaseModel  ←  config/difficulty.py
                    ←  config/refutations.py
                    ←  config/technique.py
                    ←  config/solution_tree.py
                    ←  config/ai_solve.py         ← imports SolutionTreeConfig, EdgeCaseBoosts etc. from solution_tree
                    ←  config/teaching.py
                    ←  config/analysis.py
                    ←  config/infrastructure.py

config/*            ←  config/__init__.py  (imports from ALL sub-modules to compose EnrichmentConfig)
config/*            ←  config/helpers.py    (imports EnrichmentConfig for get_effective_max_visits signature)
```

**Key dependency**: `ai_solve.py` → `solution_tree.py` (AiSolveConfig composes SolutionTreeConfig). No reverse dependency. No cycles.

**EnrichmentConfig** in `__init__.py` imports all sub-module root models for field composition. This is the composition root — expected one-way dependency.

---

## Revised Comparison Matrix

| Criterion | OPT-1 (Fine) | OPT-3 (Hybrid) |
|-----------|:---:|:---:|
| File count | 11 | 10 |
| Max file lines | ~246 ✅ | ~246 ✅ |
| SRP compliance | ✅ Excellent | ✅ Good |
| ISP compliance | ✅ Strong | ✅ Good |
| AC-6 (≤250 lines) | ✅ Pass | ✅ Pass |
| AC-8 (no circular imports) | ✅ Pass | ✅ Pass |
| Cognitive overhead | Slightly higher (11 files) | Balanced (10 files) |
| Import rewrite effort | 8 domain targets | 8 domain targets |
| Difficulty-Validation coupling | Separated (extra import) | Combined (natural pair) ✅ |
| Future extensibility | ✅ Fine-grained slots | ✅ Good |

## Recommendation

**OPT-3 (Hybrid)** — groups the naturally-coupled difficulty+validation domain, keeps every file under 250 lines, maintains clean dependency direction, and balances SRP with navigability. The only difference from OPT-1 is combining 2 closely-related domains into one 225-line file, saving one file while preserving all ACs.
