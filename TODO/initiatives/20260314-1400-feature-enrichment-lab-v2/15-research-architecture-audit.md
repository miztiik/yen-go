# Architecture Audit — Enrichment Lab V2 Dependency Analysis

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Research Type**: READ-ONLY architecture verification  
**Last Updated**: 2026-03-14

---

## 1. Research Question and Boundaries

**Question**: Do the planned V2 modules have clean interfaces, no circular/inverse dependencies, and are they architecturally sound?

**Scope**: Import dependency graph of `tools/puzzle-enrichment-lab/` — current state and planned V2 state. No code changes.

**Dependency Direction Rules (enforced)**:

| Layer | May Import | Must NOT Import |
|-------|-----------|-----------------|
| `models/` | stdlib, pydantic, other models | analyzers, stages, config |
| `config.py` | stdlib, pydantic, pathlib | analyzers, models, stages |
| `analyzers/detectors/` (new) | models, config, liberty.py | stages, enrich_single, other analyzers |
| `analyzers/stages/` | analyzers, models, config | other stages |
| `analyzers/` (non-stage) | models, config | stages |
| `entropy_roi.py` (new) | models, math/numpy | stages, detectors |
| `humansl_calibration.py` (new) | models, config | stages |

---

## 2. Current Import Dependency Graph (Adjacency List)

Each entry: `module → [dependencies]`. Only project-internal imports shown (stdlib/pydantic excluded). `core/` = `core/tsumego_analysis`, `core/sgf_parser`.

### 2.1 Models Layer

| R-ID | Module | Imports |
|------|--------|---------|
| R-1 | `models/position.py` | *(none — pydantic only)* |
| R-2 | `models/analysis_request.py` | `models/position` |
| R-3 | `models/analysis_response.py` | *(none — pydantic only)* |
| R-4 | `models/refutation_result.py` | *(none — pydantic only)* |
| R-5 | `models/difficulty_estimate.py` | *(none — pydantic only)* |
| R-6 | `models/solve_result.py` | *(none — stdlib only)* |
| R-7 | `models/enrichment_state.py` | *(none — stdlib only)* |
| R-8 | **`models/ai_analysis_result.py`** | **`analyzers/validate_correct_move`** ⚠️ |

### 2.2 Config Layer

| R-ID | Module | Imports |
|------|--------|---------|
| R-9 | `config.py` | *(none — stdlib, pydantic, pathlib only)* ✅ |

### 2.3 Analyzers Layer (non-stage, non-detector)

| R-ID | Module | Imports |
|------|--------|---------|
| R-10 | `analyzers/query_builder.py` | `core/tsumego_analysis`, `analyzers/frame_adapter`, `models/analysis_request`, `models/analysis_response`, `models/position`, `config` |
| R-11 | `analyzers/validate_correct_move.py` | `config`, `models/analysis_response`, `models/position` |
| R-12 | `analyzers/estimate_difficulty.py` | `analyzers/validate_correct_move`, `models/refutation_result`, `models/difficulty_estimate`, `config` |
| R-13 | `analyzers/generate_refutations.py` | `config`, `models/position`, `models/analysis_request`, `models/analysis_response`, `models/refutation_result`, `engine/local_subprocess` |
| R-14 | `analyzers/technique_classifier.py` | `config` |
| R-15 | `analyzers/teaching_comments.py` | `config`, `analyzers/vital_move`, `analyzers/hint_generator`, `analyzers/refutation_classifier`, `analyzers/comment_assembler` |
| R-16 | `analyzers/hint_generator.py` | `config` |
| R-17 | `analyzers/sgf_enricher.py` | `core/tsumego_analysis`, `core/sgf_parser`, `analyzers/validate_correct_move`, `analyzers/property_policy`, `analyzers/config_lookup`, `analyzers/hint_generator`, `models/ai_analysis_result` |
| R-18 | `analyzers/result_builders.py` | `analyzers/validate_correct_move`, `analyzers/technique_classifier`, `analyzers/teaching_comments`, `analyzers/hint_generator`, `analyzers/config_lookup`, `models/ai_analysis_result` |
| R-19 | `analyzers/frame_adapter.py` | `models/position`, `analyzers/tsumego_frame_gp` |
| R-20 | `analyzers/solve_position.py` | `config`, `models/solve_result`, `core/sgf_parser` |
| R-21 | `analyzers/liberty.py` | `models/position` |
| R-22 | `analyzers/config_lookup.py` | *(stdlib, json, pathlib only)* ✅ |
| R-23 | `analyzers/property_policy.py` | *(stdlib, json, pathlib only)* ✅ |
| R-24 | `analyzers/ko_validation.py` | `config`, `models/analysis_response`, `analyzers/validate_correct_move` |
| R-25 | `analyzers/vital_move.py` | *(none — stdlib only)* |
| R-26 | `analyzers/refutation_classifier.py` | *(none — stdlib only)* |
| R-27 | `analyzers/comment_assembler.py` | `config` |
| R-28 | `analyzers/frame_utils.py` | `models/position` |
| R-29 | `analyzers/tsumego_frame_gp.py` | (see `frame_adapter.py`) |
| R-30 | `analyzers/tsumego_frame.py` | `models/position` |
| R-31 | `analyzers/single_engine.py` | `engine/config`, `engine/local_subprocess`, `models/analysis_request`, `models/analysis_response`, `config` |
| R-32 | `analyzers/observability.py` | `models/solve_result` |

### 2.4 Stages Layer

| R-ID | Module | Imports |
|------|--------|---------|
| R-33 | `stages/protocols.py` | *(TYPE_CHECKING only: core, analyzers, config, models)* ✅ |
| R-34 | `stages/stage_runner.py` | `stages/protocols` |
| R-35 | `stages/parse_stage.py` | `core/tsumego_analysis`, `analyzers/config_lookup`, `stages/protocols` |
| R-36 | `stages/query_stage.py` | `analyzers/query_builder`, `stages/protocols`, `models/analysis_response`, `config` |
| R-37 | `stages/validation_stage.py` | `core/tsumego_analysis`, `analyzers/validate_correct_move`, `analyzers/config_lookup`, `stages/protocols`, `models/analysis_response` |
| R-38 | `stages/refutation_stage.py` | `analyzers/generate_refutations`, `stages/protocols`, `models/refutation_result` |
| R-39 | `stages/difficulty_stage.py` | `core/tsumego_analysis`, `analyzers/estimate_difficulty`, `stages/protocols` |
| R-40 | `stages/assembly_stage.py` | `analyzers/config_lookup`, `analyzers/result_builders`, `stages/protocols`, `models/ai_analysis_result` |
| R-41 | `stages/teaching_stage.py` | `analyzers/technique_classifier`, `analyzers/teaching_comments`, `analyzers/hint_generator`, `analyzers/sgf_enricher`, `stages/protocols` |
| R-42 | `stages/solve_paths.py` | `core/tsumego_analysis`, `analyzers/config_lookup`, `analyzers/estimate_difficulty`, `analyzers/result_builders`, `models/analysis_response` |

### 2.5 Orchestrator

| R-ID | Module | Imports |
|------|--------|---------|
| R-43 | `analyzers/enrich_single.py` | `analyzers/single_engine`, `analyzers/result_builders`, `stages/protocols`, `stages/stage_runner`, `stages/parse_stage`, `stages/solve_paths`, `stages/query_stage`, `stages/validation_stage`, `stages/refutation_stage`, `stages/difficulty_stage`, `stages/assembly_stage`, `stages/teaching_stage`, `models/ai_analysis_result`, `models/enrichment_state`, `config`, `log_config` |

---

## 3. EXISTING Violations Found

### V-1: Model imports Analyzer (**INVERSE DEPENDENCY**) ⛔

**File**: `models/ai_analysis_result.py` (R-8)  
**Imports**: `analyzers.validate_correct_move.ValidationStatus`, `CorrectMoveResult`

**Severity**: HIGH — This is a runtime import (not TYPE_CHECKING), creating a hard dependency from the model layer up to the analyzer layer.

**Impact**: Any change to `validate_correct_move.py` can break the model. Creates potential circular paths if any analyzer imports `AiAnalysisResult` and also imports other modules that depend on `validate_correct_move`.

**Actual circular path today**: `models/ai_analysis_result` → `analyzers/validate_correct_move` → `models/position` → *(stops, no circle)* — No true circular dependency exists currently, but it's one step away. If `validate_correct_move` ever imported `AiAnalysisResult`, it would be circular.

### V-2: Cross-analyzer imports (design smell, not rule violation)

Several analyzers import other analyzers:
- `estimate_difficulty` → `validate_correct_move` (for `CorrectMoveResult` type)
- `teaching_comments` → `vital_move`, `hint_generator`, `refutation_classifier`, `comment_assembler`
- `sgf_enricher` → `validate_correct_move`, `property_policy`, `config_lookup`, `hint_generator`
- `result_builders` → `validate_correct_move`, `technique_classifier`, `teaching_comments`, `hint_generator`, `config_lookup`
- `ko_validation` → `validate_correct_move`

These are all in the same layer so technically allowed, but `result_builders` is a "hub" with 6 analyzer dependencies.

### V-3: `stages/solve_paths.py` is not a stage class

`solve_paths.py` imports from `analyzers/` and `models/` but lives in `stages/`. It doesn't import other stage modules, so no inter-stage violation. It acts as a utility used by the orchestrator, not a stage. Acceptable but architecturally ambiguous.

---

## 4. Planned V2 Dependency Graph (Changes Only)

### 4.1 New Modules

| R-ID | Module (new) | Planned Imports | Rule Check |
|------|-------------|-----------------|------------|
| R-50 | `analyzers/entropy_roi.py` | `models/position`, math | ✅ Clean |
| R-51 | `analyzers/stages/solve_path_stage.py` | `stages/protocols`, current `stages/solve_paths.py` functions | ✅ (imports solve_paths utility, not another stage) |
| R-52 | `analyzers/stages/technique_stage.py` | `analyzers/technique_classifier`, `stages/protocols` | ✅ Clean |
| R-53 | `analyzers/stages/sgf_writeback_stage.py` | `analyzers/sgf_enricher`, `stages/protocols` | ✅ Clean |
| R-54 | `analyzers/stages/analyze_stage.py` | `analyzers/query_builder` (stripped), `stages/protocols`, `models/position`, `config` | ✅ Clean |
| R-55 | `analyzers/detectors/__init__.py` | `models/position`, `models/analysis_response` | ✅ Clean |
| R-56 | `analyzers/detectors/ladder_detector.py` | `models/position`, `analyzers/liberty`, `config`, `analyzers/detectors/__init__` | ✅ Clean |
| R-57 | `analyzers/detectors/<all_28>.py` | Same pattern as ladder_detector | ✅ Clean (if pattern holds) |
| R-58 | `analyzers/humansl_calibration.py` | `models`, `config` | ✅ Clean |
| R-59 | `models/entropy_roi.py` (or inline) | *(pydantic/dataclass only)* | ✅ Clean |
| R-60 | `models/technique_result.py` | *(pydantic only, references DetectionResult from detectors)* | ⚠️ See V-4 |

### 4.2 Modified Modules

| R-ID | Module | Change | Rule Check |
|------|--------|--------|------------|
| R-36' | `stages/analyze_stage.py` (renamed from query_stage) | Remove `uncrop_response` import, accept `Position` directly | ✅ Simplifies |
| R-41' | `stages/teaching_stage.py` | Remove `technique_classifier`, `sgf_enricher` imports (moved to separate stages) | ✅ Reduces coupling |
| R-10' | `analyzers/query_builder.py` | Remove `CroppedPosition` import, remove crop logic | ✅ Simplifies |
| R-13' | `analyzers/generate_refutations.py` | Add `overrideSettings` from config, use framed position | ✅ Same layer |
| R-14' | `analyzers/technique_classifier.py` | Import from `analyzers/detectors/`, call each detector | ✅ (detectors are same layer as analyzers) |
| R-12' | `analyzers/estimate_difficulty.py` | Add complexity metric field access | ✅ No new imports |
| R-15' | `analyzers/teaching_comments.py` | Add ownership settledness delta | ✅ Uses existing data |

---

## 5. V2 Violations / Concerns Found

### V-4: `models/technique_result.py` may import from `analyzers/detectors/` ⚠️

**Plan says**: `TechniqueDetectionResult` aggregates `DetectionResult` instances.

**Problem**: If `DetectionResult` lives in `analyzers/detectors/__init__.py` and `TechniqueDetectionResult` lives in `models/technique_result.py`, the model imports from the analyzer layer.

**Recommendation**: Move `DetectionResult` dataclass to `models/technique_result.py` (or a shared `models/detection.py`) and have `analyzers/detectors/__init__.py` import it FROM models. This preserves the dependency direction: detectors → models.

**Severity**: MEDIUM — same anti-pattern as existing V-1.

### V-5: `result_builders.py` remains a "god module" hub ⚠️

**Current**: R-18 imports 6 analyzer modules.
**After V2**: Technique classification moves out (to `TechniqueStage`), but `result_builders` likely still imports `validate_correct_move`, `config_lookup`, and `models/ai_analysis_result`.

**Assessment**: Improved from 6→~4 dependencies. Still a hub but within acceptable bounds since it's a pure assembly module.

### V-6: Pre-existing V-1 (`models/ai_analysis_result` → `analyzers/validate_correct_move`) persists

The V2 plan does not mention fixing this inverse dependency. It should be addressed in Phase 1 as part of pipeline cleanup.

**Recommendation**: Extract `ValidationStatus` and `CorrectMoveResult` into `models/validation.py`. Have both `models/ai_analysis_result.py` and `analyzers/validate_correct_move.py` import from this new model file.

### V-7: Detector ↔ Classifier potential coupling

**Plan**: `technique_classifier.py` becomes a dispatcher that calls all 28 detectors.

**Risk**: If detectors need to know about each other (e.g., "if ladder detected, skip net"), the dispatcher pattern prevents that. Each detector receives `position + analysis + solution_tree + config` and returns independently.

**Assessment**: LOW risk. The plan explicitly states independent detectors with priority-based merging in the dispatcher. No inter-detector imports needed.

### V-8: `solve_paths.py` as stage-layer utility

**Current**: Lives in `stages/` but doesn't implement `EnrichmentStage` protocol.
**Planned**: New `SolvePathStage` will formalize this.

**Assessment**: V2 plan correctly addresses this. `solve_paths.py` functions will be consumed by `SolvePathStage`, which is a proper stage.

---

## 6. No Circular Dependencies Found ✅

**Method**: Traced all import paths looking for A → B → ... → A cycles.

**Closest near-cycle**: 
```
models/ai_analysis_result → analyzers/validate_correct_move → models/position → (stops)
                                                               models/analysis_response → (stops)
```
No complete cycle exists. The inverse dependency (V-1) is one-directional.

**V2 additions**: All new modules follow clean dependency directions. No new cycles introduced.

---

## 7. Interface Cleanliness Assessment

| R-ID | Module | Dependencies | Responsibility | Verdict |
|------|--------|-------------|----------------|---------|
| R-50 | `entropy_roi.py` | 1 (models/position) + math | Entropy computation | ✅ Very clean |
| R-51 | `solve_path_stage.py` | 2 (protocols, solve_paths) | Solve path dispatch | ✅ Clean |
| R-52 | `technique_stage.py` | 2 (technique_classifier, protocols) | Technique detection | ✅ Clean |
| R-53 | `sgf_writeback_stage.py` | 2 (sgf_enricher, protocols) | SGF property writing | ✅ Clean |
| R-54 | `analyze_stage.py` | 4 (query_builder, protocols, models/position, config) | Engine analysis | ✅ Acceptable |
| R-55 | `detectors/__init__.py` | 2 (models/position, models/analysis_response) | Protocol + result model | ✅ Clean |
| R-56 | `detectors/ladder_detector.py` | 4 (models/position, liberty, config, detectors init) | Ladder detection | ✅ Acceptable |
| R-58 | `humansl_calibration.py` | 2 (models, config) | HumanSL query builder | ✅ Clean |

**No module exceeds 4 internal dependencies.** All new modules have clear single responsibilities.

---

## 8. Architectural Smell Check

### 8.1 "God module" — Everything depends on?

**`config.py`**: 11 modules import `config.py`. This is expected and acceptable — config is a leaf dependency (imports nothing from the project).

**`models/position.py`**: 10+ modules import Position. Also expected — it's the core domain model.

**`stages/protocols.py`**: All stages import it. Expected — it's the stage interface contract. Uses TYPE_CHECKING for heavy imports, so no real coupling.

### 8.2 Tight coupling between previously independent modules?

**V2 change**: `technique_classifier.py` will now import from 28 `detectors/*.py` files. This is a planned architectural expansion, not tight coupling — detectors don't import back.

**No unexpected new couplings found.**

### 8.3 DetectionResult protocol — unnecessary coupling?

The `DetectionResult` dataclass is a simple 4-field return value. It's lighter than requiring each detector to return a dict. Having 28 detectors share a return type is **good design** (Interface Segregation, LSP). No unnecessary coupling.

---

## 9. Planner Recommendations

1. **FIX V-1 in Phase 1**: Extract `ValidationStatus` enum and `CorrectMoveResult` model from `analyzers/validate_correct_move.py` into `models/validation.py`. Update imports in both `ai_analysis_result.py` and `validate_correct_move.py`. This removes the only inverse dependency in the codebase. **Estimated: 3 files, ~30 lines moved, Level 2 correction.**

2. **Place `DetectionResult` in models layer** (prevents V-4): Define `DetectionResult` in `models/technique_result.py` alongside `TechniqueDetectionResult`. Have `analyzers/detectors/__init__.py` re-export it for convenience. This prevents the same models→analyzers violation pattern.

3. **Proceed with V2 plan as architected**: All 10 new modules pass dependency direction checks. No circular dependencies introduced. Interface cleanliness is excellent (max 4 internal deps per new module). Stage isolation is maintained — no inter-stage imports.

4. **Add architecture test in Phase 1**: Create a `tests/test_architecture.py` that asserts the dependency rules (models never import analyzers, stages never import stages, config imports nothing internal). This prevents future regressions. Pattern: parse `.py` files for `from`/`import` statements, validate against allowlist.

---

## 10. Overall Architectural Soundness Verdict

### **PASS — with 2 Required Fixes**

| Check | Status | Details |
|-------|--------|---------|
| No circular dependencies | ✅ PASS | No cycles in current or planned graph |
| No inter-stage imports | ✅ PASS | Stages import analyzers + protocols only |
| Models don't import analyzers | ⚠️ CONDITIONAL | V-1 exists today (pre-V2), V-4 would add another. Both fixable. |
| Detectors don't import stages | ✅ PASS | Plan specifies correct direction |
| Config is a leaf | ✅ PASS | No project-internal imports |
| Interface cleanliness | ✅ PASS | All new modules ≤ 4 dependencies |
| No god modules | ✅ PASS | `config.py` is appropriately central; `result_builders` improves with V2 |
| SRP per module | ✅ PASS | Split of TeachingStage into 3 is well-motivated |

**Required fixes before/during Phase 1**:
1. Extract `ValidationStatus` + `CorrectMoveResult` to `models/` (fixes V-1)
2. Place `DetectionResult` in `models/` (prevents V-4)

**Confidence**: 92/100 — High confidence in analysis completeness; 8% uncertainty from not reading every line of 28 planned detector files (only the interface contract was verified).

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260314-1400-feature-enrichment-lab-v2/
artifact: 15-research-architecture-audit.md
top_recommendations:
  - Fix V-1: Extract ValidationStatus to models/validation.py (Phase 1 prerequisite)
  - Fix V-4: Place DetectionResult in models/technique_result.py (Phase 2 prerequisite)
  - Proceed with V2 plan — architecture is sound
  - Add tests/test_architecture.py dependency guard
open_questions:
  - Q1: Should solve_paths.py remain in stages/ as a utility, or move to analyzers/? (Low priority)
post_research_confidence_score: 92
post_research_risk_level: low
```
