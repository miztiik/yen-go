# Research: Config Panel + Per-Stage Re-Run for Enrichment Lab GUI

**Initiative**: `20260314-feature-enrichment-lab-config-panel`
**Research question**: What is the complete map of pipeline stages, config parameters, PipelineContext fields, bridge API, and GUI layout needed to add a Config Panel with per-stage re-run capability?
**Last Updated**: 2026-03-14

---

## 1. Research Question & Boundaries

| q_id | question | status |
|------|----------|--------|
| RQ-1 | What are all enrichment stages, their names, config reads, inputs/outputs, error policies, and engine usage? | ✅ resolved |
| RQ-2 | What config parameters should be exposed in a GUI panel? Types, ranges, defaults, suggested widgets? | ✅ resolved |
| RQ-3 | What is the complete PipelineContext schema with field ownership per stage? | ✅ resolved |
| RQ-4 | What are the current bridge API endpoints and what would need to change? | ✅ resolved |
| RQ-5 | What is the current GUI layout and where does a config panel fit? | ✅ resolved |
| RQ-6 | Which PipelineContext fields are JSON-serializable and which are not? | ✅ resolved |
| RQ-7 | Can stages be run independently? What are the hard dependencies? | ✅ resolved |

---

## A. Stage Map Table

Pipeline execution order: ParseStage → SolvePathStage → AnalyzeStage → ValidationStage → RefutationStage → DifficultyStage → AssemblyStage → TechniqueStage → TeachingStage → SgfWritebackStage.

The first two (Parse, SolvePath) run individually before the main `StageRunner.run_pipeline()` call. The remaining 8 run as a sequence via `StageRunner.run_pipeline()`.

| R-ID | Stage Class | File | `name` property (SSE event) | Config fields read | PipelineContext reads | PipelineContext writes | ErrorPolicy | Calls KataGo? |
|------|------------|------|----------------------------|-------------------|----------------------|----------------------|-------------|--------------|
| S-1 | `ParseStage` | `analyzers/stages/parse_stage.py` | `parse_sgf` | (none directly — uses `config_lookup.extract_metadata` which reads `config/tags.json`) | `sgf_text`, `source_file` | `root`, `metadata`, `position`, `correct_move_sgf` | FAIL_FAST | No |
| S-2 | `SolvePathStage` | `analyzers/stages/solve_path_stage.py` | `solve_paths` | `config.ai_solve` (entire subtree), `config.ai_solve.solution_tree.*`, `config.ai_solve.thresholds.*`, `config.ai_solve.seki_detection.*` | `root`, `position`, `correct_move_sgf`, `metadata`, `engine_manager`, `config` | `state` (EnrichmentRunState), `correct_move_sgf`, `correct_move_gtp`, `solution_moves`, `result` (early return only) | FAIL_FAST | Yes (1-50+ queries for position-only/has-solution paths) |
| S-3 | `AnalyzeStage` | `analyzers/stages/analyze_stage.py` | `analyze` | `config.visit_tiers.T1.visits`, `config.deep_enrich.visits`, `config.analysis_defaults.default_max_visits`, `config.ko_analysis.rules_by_ko_type`, `config.ko_analysis.pv_len_by_ko_type`, `config.frame.*`, `config.deep_enrich.root_num_symmetries_to_sample` | `position`, `metadata`, `correct_move_sgf`, `correct_move_gtp`, `solution_moves`, `engine_manager`, `config`, `sgf_text`, `trace_id`, `source_file` | `response`, `framed_position`, `engine_model`, `engine_visits`, `effective_visits` | FAIL_FAST | Yes (1 main query) |
| S-4 | `ValidationStage` | `analyzers/stages/validation_stage.py` | `validate_move` | `config.tree_validation.*` (enabled, skip_when_confident, confidence_winrate, confidence_winrate_ko, confidence_winrate_seki, confidence_top_n, visits_per_depth), `config.refutations.locality_max_distance`, `config.validation.curated_pruning.*` | `metadata`, `position`, `response`, `correct_move_gtp`, `solution_moves`, `root`, `engine_manager`, `config` | `validation_result`, `curated_wrongs`, `nearby_moves` | DEGRADE | Maybe (tree validation uses engine if enabled) |
| S-5 | `RefutationStage` | `analyzers/stages/refutation_stage.py` | `generate_refutations` | `config.refutations.*` (candidate_min_policy, candidate_max_count, refutation_max_count, delta_threshold, refutation_visits, locality_max_distance, max_pv_length, pv_mode, pv_extract_min_depth, pv_quality_min_visits, candidate_scoring.*, refutation_overrides.*, tenuki_rejection.*), `config.refutation_escalation.*`, `config.visit_tiers.T2.visits` | `metadata`, `framed_position` (fallback: `position`), `correct_move_gtp`, `solution_moves`, `response`, `engine_manager`, `config`, `nearby_moves`, `curated_wrongs`, `entropy_roi` | `refutation_result` | DEGRADE | Yes (N per candidate + escalation) |
| S-6 | `DifficultyStage` | `analyzers/stages/difficulty_stage.py` | `estimate_difficulty` | `config.difficulty.structural_weights.*`, `config.difficulty.normalization.*`, `config.difficulty.score_to_level_thresholds`, `config.difficulty.score_normalization_cap`, `config.difficulty.trap_density_floor` | `metadata`, `validation_result`, `root`, `nearby_moves`, `state`, `refutation_result`, `solution_moves`, `position`, `engine_visits`, `response`, `config` | `difficulty_estimate` | DEGRADE | No |
| S-7 | `AssemblyStage` | `analyzers/stages/assembly_stage.py` | `assemble_result` | `config.ai_solve.*` (thresholds, goal_inference), `config.elo_anchor.*` | `metadata`, `validation_result`, `engine_model`, `engine_visits`, `config_hash`, `source_file`, `trace_id`, `run_id`, `refutation_result`, `difficulty_estimate`, `state`, `response`, `correct_move_gtp`, `root`, `config` | `result` (AiAnalysisResult) | FAIL_FAST | No |
| S-8 | `TechniqueStage` | `analyzers/stages/technique_stage.py` | `technique_classification` | `config.technique_detection.*` (all 10 detector configs: ladder, snapback, net, seki, direct_capture, throw_in, nakade, double_atari, sacrifice, escape), `config.ko_detection.*` | `result`, `position`, `response`, `config` | `result.technique_tags` | DEGRADE | No |
| S-9 | `TeachingStage` | `analyzers/stages/teaching_stage.py` | `teaching_enrichment` | `config.teaching.*` (non_obvious_policy, ko_delta_threshold, capture_depth_threshold, significant_loss_threshold, moderate_loss_threshold), teaching-comments.json (loaded via `load_teaching_comments_config()`) | `result`, `metadata`, `position` | `result.teaching_comments`, `result.hints` | DEGRADE | No |
| S-10 | `SgfWritebackStage` | `analyzers/stages/sgf_writeback_stage.py` | `sgf_writeback` (SSE: `enriched_sgf`) | sgf-property-policies.json (loaded by `analyzers/property_policy.py`) | `result`, `metadata`, `sgf_text` | `result.enriched_sgf`, `timings["enrich_sgf"]` | DEGRADE | No |

### Stage Dependency Graph (Hard Dependencies)

```
ParseStage (S-1)
  └→ SolvePathStage (S-2) [needs: root, position, correct_move_sgf]
      └→ AnalyzeStage (S-3) [needs: position, metadata, correct_move_gtp]
          ├→ ValidationStage (S-4) [needs: response, correct_move_gtp, position]
          │   └→ RefutationStage (S-5) [needs: framed_position, correct_move_gtp, response, nearby_moves]
          │       └→ DifficultyStage (S-6) [needs: validation_result, refutation_result, solution_moves]
          │           └→ AssemblyStage (S-7) [needs: validation_result, refutation_result, difficulty_estimate, response]
          ├→ TechniqueStage (S-8) [needs: position, response, result (from S-7)]
          │   └→ TeachingStage (S-9) [needs: result.technique_tags (from S-8)]
          │       └→ SgfWritebackStage (S-10) [needs: result (from S-7/S-8/S-9)]
          └→ (S-8 also needs result from S-7)
```

**Critical serial dependency chain**: S-1 → S-2 → S-3 → S-4 → S-5 → S-6 → S-7 → S-8 → S-9 → S-10. All stages are strictly sequential currently.

---

## B. Config Parameter Catalog

Parameters grouped by stage relevance and UI suitability.

### B.1 Analysis & Engine Parameters (High GUI Priority)

| R-ID | Dotted path | Type | Default | Min | Max | Used by stage(s) | Suggested widget | Runtime-safe? |
|------|------------|------|---------|-----|-----|------------------|------------------|---------------|
| C-1 | `visit_tiers.T1.visits` | int | 500 | 1 | 100000 | S-3 (AnalyzeStage) | slider (50-5000 step 50) | Yes |
| C-2 | `visit_tiers.T2.visits` | int | 2000 | 1 | 100000 | S-5 (RefutationStage) | slider (100-10000 step 100) | Yes |
| C-3 | `deep_enrich.visits` | int | 2000 | 100 | 1000000 | S-3 (fallback when visit_tiers absent) | slider (100-10000 step 100) | Yes |
| C-4 | `deep_enrich.root_num_symmetries_to_sample` | int | 4 | 1 | 8 | S-3 (AnalyzeStage) | slider (1-8) | Yes |
| C-5 | `deep_enrich.escalate_to_referee` | bool | True | — | — | S-3 (AnalyzeStage) | toggle | Yes |
| C-6 | `deep_enrich.escalation_winrate_low` | float | 0.3 | 0.0 | 1.0 | S-3 (AnalyzeStage) | slider (0.0-1.0 step 0.05) | Yes |
| C-7 | `deep_enrich.escalation_winrate_high` | float | 0.7 | 0.0 | 1.0 | S-3 (AnalyzeStage) | slider (0.0-1.0 step 0.05) | Yes |
| C-8 | `analysis_defaults.default_max_visits` | int | 200 | 1 | 100000 | S-3 (fallback) | number input | Yes |
| C-9 | `analysis_defaults.puzzle_region_margin` | int | 2 | 0 | 10 | S-3 (query_builder) | slider (0-10) | Yes |

### B.2 Refutation Parameters (Medium GUI Priority)

| R-ID | Dotted path | Type | Default | Min | Max | Used by stage(s) | Suggested widget | Runtime-safe? |
|------|------------|------|---------|-----|-----|------------------|------------------|---------------|
| C-10 | `refutations.delta_threshold` | float | 0.08 | 0.0 | 1.0 | S-5 | slider (0.01-0.5 step 0.01) | Yes |
| C-11 | `refutations.candidate_max_count` | int | 5 | 1 | 20 | S-5 | number input (1-20) | Yes |
| C-12 | `refutations.refutation_max_count` | int | 3 | 1 | 10 | S-5 | number input (1-10) | Yes |
| C-13 | `refutations.refutation_visits` | int | 100 | 10 | 10000 | S-5 | slider (10-5000 step 10) | Yes |
| C-14 | `refutations.locality_max_distance` | int | 2 | 0 | 10 | S-4, S-5 | slider (0-10) | Yes |
| C-15 | `refutations.max_pv_length` | int | 4 | 1 | 20 | S-5 | slider (1-20) | Yes |
| C-16 | `refutations.candidate_scoring.temperature` | float | 1.5 | 0.0 | 10.0 | S-5 | slider (0.0-5.0 step 0.1) | Yes |
| C-17 | `refutations.tenuki_rejection.enabled` | bool | True | — | — | S-5 | toggle | Yes |
| C-18 | `refutations.tenuki_rejection.manhattan_threshold` | float | 4.0 | 0.0 | 38.0 | S-5 | slider (0-20) | Yes |
| C-19 | `refutation_escalation.enabled` | bool | True | — | — | S-5 | toggle | Yes |
| C-20 | `refutation_escalation.escalation_visits` | int | 500 | 100 | 10000 | S-5 | slider (100-5000 step 50) | Yes |
| C-21 | `refutation_escalation.escalation_delta_threshold` | float | 0.03 | 0.0 | 1.0 | S-5 | slider (0.01-0.2 step 0.01) | Yes |

### B.3 AI-Solve / Solution Tree Parameters (Medium GUI Priority)

| R-ID | Dotted path | Type | Default | Min | Max | Used by stage(s) | Suggested widget | Runtime-safe? |
|------|------------|------|---------|-----|-----|------------------|------------------|---------------|
| C-22 | `ai_solve.thresholds.t_good` | float | 0.05 | 0.0 | 1.0 | S-2 (SolvePathStage) | slider (0.01-0.3 step 0.01) | Yes |
| C-23 | `ai_solve.thresholds.t_bad` | float | 0.15 | 0.0 | 1.0 | S-2 | slider (0.05-0.5 step 0.01) | Yes |
| C-24 | `ai_solve.thresholds.t_hotspot` | float | 0.30 | 0.0 | 1.0 | S-2, S-7 | slider (0.1-0.8 step 0.01) | Yes |
| C-25 | `ai_solve.solution_tree.max_total_tree_queries` | int | 50 | 1 | 1000 | S-2 | slider (5-200 step 5) | Yes |
| C-26 | `ai_solve.solution_tree.branch_min_policy` | float | 0.05 | 0.0 | 1.0 | S-2 | slider (0.01-0.3 step 0.01) | Yes |
| C-27 | `ai_solve.solution_tree.max_branch_width` | int | 3 | 1 | 10 | S-2 | slider (1-10) | Yes |
| C-28 | `ai_solve.solution_tree.tree_visits` | int | 500 | 50 | 100000 | S-2 | slider (50-5000 step 50) | Yes |
| C-29 | `ai_solve.solution_tree.confirmation_visits` | int | 500 | 50 | 100000 | S-2 | slider (50-5000 step 50) | Yes |

### B.4 Validation & Tree Validation Parameters (Low GUI Priority)

| R-ID | Dotted path | Type | Default | Min | Max | Used by stage(s) | Suggested widget | Runtime-safe? |
|------|------------|------|---------|-----|-----|------------------|------------------|---------------|
| C-30 | `tree_validation.enabled` | bool | True | — | — | S-4 | toggle | Yes |
| C-31 | `tree_validation.skip_when_confident` | bool | True | — | — | S-4 | toggle | Yes |
| C-32 | `tree_validation.confidence_winrate` | float | 0.85 | 0.0 | 1.0 | S-4 | slider (0.5-1.0 step 0.05) | Yes |
| C-33 | `tree_validation.visits_per_depth` | int | 500 | 50 | 100000 | S-4 | slider (50-5000 step 50) | Yes |

### B.5 Difficulty & Quality Parameters (Low GUI Priority)

| R-ID | Dotted path | Type | Default | Min | Max | Used by stage(s) | Suggested widget | Runtime-safe? |
|------|------------|------|---------|-----|-----|------------------|------------------|---------------|
| C-34 | `difficulty.structural_weights.solution_depth` | float | 35.0 | 0.0 | 100.0 | S-6 | slider (weights must sum to 100) | Yes |
| C-35 | `difficulty.structural_weights.branch_count` | float | 22.0 | 0.0 | 100.0 | S-6 | slider (constrained sum=100) | Yes |
| C-36 | `difficulty.structural_weights.local_candidates` | float | 18.0 | 0.0 | 100.0 | S-6 | slider (constrained sum=100) | Yes |
| C-37 | `difficulty.structural_weights.refutation_count` | float | 15.0 | 0.0 | 100.0 | S-6 | slider (constrained sum=100) | Yes |
| C-38 | `difficulty.structural_weights.proof_depth` | float | 10.0 | 0.0 | 100.0 | S-6 | slider (constrained sum=100) | Yes |
| C-39 | `difficulty.score_normalization_cap` | float | 30.0 | 1.0 | — | S-6 | number input | Yes |
| C-40 | `difficulty.trap_density_floor` | float | 0.05 | 0.0 | 1.0 | S-6 | slider (0.0-0.5 step 0.01) | Yes |

### B.6 Teaching & Comment Parameters (Low GUI Priority)

| R-ID | Dotted path | Type | Default | Min | Max | Used by stage(s) | Suggested widget | Runtime-safe? |
|------|------------|------|---------|-----|-----|------------------|------------------|---------------|
| C-41 | `teaching.non_obvious_policy` | float | 0.10 | 0.0 | 1.0 | S-9 | slider (0.0-0.5) | Yes |
| C-42 | `teaching.ko_delta_threshold` | float | 0.12 | 0.0 | 1.0 | S-9 | slider (0.0-0.5) | Yes |
| C-43 | `teaching.significant_loss_threshold` | float | 0.5 | 0.0 | 1.0 | S-9 | slider (0.0-1.0) | Yes |

### B.7 Ko Analysis Parameters (Low GUI Priority)

| R-ID | Dotted path | Type | Default | Min | Max | Used by stage(s) | Suggested widget | Runtime-safe? |
|------|------------|------|---------|-----|-----|------------------|------------------|---------------|
| C-44 | `ko_analysis.rules_by_ko_type` | dict[str,str] | {"none":"chinese","direct":"tromp-taylor","approach":"tromp-taylor"} | — | — | S-3 | dropdown per ko-type | Yes |
| C-45 | `ko_analysis.pv_len_by_ko_type` | dict[str,int] | {"none":15,"direct":30,"approach":30} | 1 | 100 | S-3 | number input per ko-type | Yes |

**Total exposable parameters**: 45 across 7 groups.

**Recommended MVP subset (first iteration)**: C-1 through C-5, C-10 through C-15, C-22 through C-28 (21 params). Cover analysis, refutations, and AI-solve — the three most useful tuning surfaces.

---

## C. PipelineContext Full Schema

Source: `analyzers/stages/protocols.py` — `PipelineContext` dataclass

| R-ID | Field | Type | Set by | Read by | JSON-serializable? |
|------|-------|------|--------|---------|-------------------|
| F-1 | `sgf_text` | `str` | orchestrator | S-1, S-3, S-10 | ✅ Yes |
| F-2 | `config` | `EnrichmentConfig \| None` | orchestrator | ALL stages | ❌ No (Pydantic model, but `.model_dump()` works) |
| F-3 | `engine_manager` | `SingleEngineManager \| None` | orchestrator | S-2, S-3, S-4, S-5 | ❌ No (subprocess handle) |
| F-4 | `source_file` | `str` | orchestrator | S-1, S-3, S-7 | ✅ Yes |
| F-5 | `run_id` | `str` | orchestrator | S-7 | ✅ Yes |
| F-6 | `trace_id` | `str` | orchestrator | S-3, S-7 | ✅ Yes |
| F-7 | `config_hash` | `str` | orchestrator | S-7 | ✅ Yes |
| F-8 | `root` | `SGFNode \| None` | S-1 | S-2, S-4, S-6, S-7 | ❌ No (tree object with recursive children, properties dict) |
| F-9 | `metadata` | `SgfMetadata \| None` | S-1 | S-2, S-3, S-4, S-5, S-6, S-7, S-9, S-10 | ✅ Yes (has `.to_dict()`) |
| F-10 | `position` | `Position \| None` | S-1 | S-2, S-3, S-4, S-5, S-6, S-8, S-9 | ✅ Yes (Pydantic model, `.model_dump()` works) |
| F-11 | `correct_move_sgf` | `str \| None` | S-1, S-2 | S-2, S-3 | ✅ Yes |
| F-12 | `correct_move_gtp` | `str \| None` | S-2 | S-3, S-4, S-5, S-7 | ✅ Yes |
| F-13 | `solution_moves` | `list[str]` | S-2 | S-4, S-5, S-6 | ✅ Yes |
| F-14 | `state` | `EnrichmentRunState \| None` | S-2 | S-6, S-7 | ✅ Yes (dataclass with simple fields, `.solution_tree_completeness` is `Any`) |
| F-15 | `response` | `AnalysisResponse \| None` | S-3 | S-4, S-5, S-7, S-8 | ✅ Yes (Pydantic model) |
| F-16 | `framed_position` | `Position \| None` | S-3 | S-5 | ✅ Yes (Pydantic model) |
| F-17 | `engine_model` | `str \| None` | S-3 | S-7 | ✅ Yes |
| F-18 | `engine_visits` | `int` | S-3 | S-6, S-7 | ✅ Yes |
| F-19 | `effective_visits` | `int` | S-3 | (logging) | ✅ Yes |
| F-20 | `validation_result` | `CorrectMoveResult \| None` | S-4 | S-5, S-6, S-7 | ✅ Yes (Pydantic-like) |
| F-21 | `curated_wrongs` | `list[dict] \| None` | S-4 | S-5 | ✅ Yes |
| F-22 | `nearby_moves` | `list[str] \| None` | S-4 | S-5, S-6 | ✅ Yes |
| F-23 | `refutation_result` | `RefutationResult \| None` | S-5 | S-6, S-7 | ✅ Yes (Pydantic model) |
| F-24 | `entropy_roi` | `EntropyROI \| None` | (not set by any stage currently) | S-5 | ❌ No (custom class) |
| F-25 | `difficulty_estimate` | `DifficultyEstimate \| None` | S-6 | S-7 | ✅ Yes (Pydantic model) |
| F-26 | `result` | `AiAnalysisResult \| None` | S-2 (early return), S-7 | S-8, S-9, S-10 | ✅ Yes (Pydantic model with `.model_dump()`) |
| F-27 | `notify_fn` | `Callable \| None` | orchestrator | ALL stages | ❌ No (async callback) |
| F-28 | `timings` | `dict[str, float]` | StageRunner | orchestrator | ✅ Yes |

### Serialization Summary

| Category | Count | Fields |
|----------|-------|--------|
| ✅ JSON-safe (primitive or has `.model_dump()`) | 22 | F-1, F-4–F-7, F-9–F-23, F-25–F-26, F-28 |
| ❌ Non-serializable | 6 | F-2 (`config`), F-3 (`engine_manager`), F-8 (`root`/SGFNode), F-24 (`entropy_roi`), F-27 (`notify_fn`), plus F-14.`solution_tree_completeness` is `Any` |

---

## D. Bridge API Analysis

### D.1 Current Endpoints

| R-ID | Method | Path | Request body | Response | Notes |
|------|--------|------|-------------|----------|-------|
| E-1 | POST | `/api/analyze` | `AnalyzeRequest`: `board: list[list[str\|None]]`, `currentPlayer: str`, `moveHistory: list[MoveItem]`, `komi: float=6.5`, `rules: str="chinese"`, `visits: int\|None`, `maxTimeMs: int\|None`, `topK: int\|None`, `analysisPvLen: int\|None`, `includeMovesOwnership: bool`, `ownershipMode: str` | JSON `BridgeAnalyzeResponse` (moves + rootWinRate + ownership) | Interactive single-query analysis |
| E-2 | POST | `/api/enrich` | `EnrichRequest`: `sgf: str` | SSE stream (`text/event-stream`) with stage events → final `complete` event containing `AiAnalysisResult.model_dump()` | Full 10-stage pipeline |
| E-3 | POST | `/api/cancel` | (none) | `{"status": "cancelled"\|"no_task"}` | Cancels running enrichment task |
| E-4 | GET | `/api/health` | (none) | `{"status": str, "backend": str\|null, "modelName": str\|null}` | Engine lifecycle status |

### D.2 Changes Needed for Config Panel

| R-ID | Change | Priority | Rationale |
|------|--------|----------|-----------|
| D-1 | Add `config_overrides: dict \| None` field to `EnrichRequest` | High | Pass GUI config tweaks to `enrich_single_puzzle()`. The overrides dict would contain dotted-path → value pairs (e.g., `{"visit_tiers.T1.visits": 1000}`) |
| D-2 | Add `GET /api/config` endpoint | High | Return current `EnrichmentConfig.model_dump()` so GUI can render default values |
| D-3 | Add `from_stage: str \| None` field to `EnrichRequest` | Medium | For per-stage re-run: specifies which stage to resume from. Requires serialized context (see F section) |
| D-4 | Add `context: dict \| None` field to `EnrichRequest` | Medium | Serialized PipelineContext for per-stage re-run. Only needed if `from_stage` is set |
| D-5 | Add `POST /api/config/preview` endpoint | Low (nice-to-have) | Preview config changes without running pipeline (validate + show effective values) |

### D.3 Config Override Flow

Current flow:
```
EnrichRequest{sgf} → enrich_single_puzzle(sgf, engine, config=None) → loads default config
```

Proposed flow:
```
EnrichRequest{sgf, config_overrides} 
  → bridge.py: base_config = load_enrichment_config()
  → bridge.py: merged_config = apply_overrides(base_config, config_overrides)
  → enrich_single_puzzle(sgf, engine, config=merged_config)
```

**`apply_overrides` implementation**: Pydantic's `model_copy(update=...)` supports nested updates. For dotted paths like `"refutations.delta_threshold"`, split on `.`, traverse the model, and use `model_copy(update={leaf: value})` at the innermost level. This is ~20 lines of utility code.

**Safety**: All config models use Pydantic with `ge`/`le`/`Field()` validators. Invalid overrides will raise `ValidationError` → return 422 to GUI. No extra validation needed.

---

## E. GUI Layout Analysis

### E.1 Current Layout Structure

Source: `gui/index.html`, `gui/css/styles.css`

```
┌─────────────────────────────────────────────────────────┐
│ header#pipeline-bar (stage pills)                        │
├──────────┬──────────────────────┬───────────────────────┤
│ aside    │ main.main-area       │ aside.right-panel     │
│ .sidebar │                      │                       │
│          │ #besogo-container    │ #player-indicator     │
│ #sgf-    │ (Go board + SVG)     │ #solution-tree-panel  │
│ input    │                      │ #policy-priors        │
│          │ #status-bar          │ #analysis-table       │
│ #engine- │                      │                       │
│ status   │                      │                       │
│          │                      │                       │
│ #run-info│                      │                       │
├──────────┴──────────────────────┴───────────────────────┤
│ #log-panel (collapsible, resizable)                      │
└─────────────────────────────────────────────────────────┘
```

### E.2 CSS Layout Details

- **Grid**: `grid-template-columns: minmax(180px, 260px) 1fr minmax(280px, 360px)`
- **Left sidebar**: 180-260px wide, flex-column with `gap: 10px`, overflow-y auto
- **Right panel**: 280-360px wide, flex-column with `gap: 8px`, overflow-y auto
- **Current sidebar contents**: SGF textarea (6 rows), Upload/Download buttons, Enrich/Analyze/Cancel buttons, engine status box, run info box (hidden until enrichment completes)
- **Space below run-info**: **~60-70% of sidebar height is empty** after the controls — plenty of room

### E.3 CSS Patterns Available

| R-ID | Pattern | CSS class | Usage |
|------|---------|-----------|-------|
| P-1 | Panel box | `.status-box` | `background: var(--bg-panel)`, `border: 1px solid var(--border)`, `border-radius: 6px`, `padding: 8px`, `font-size: 12px` |
| P-2 | Button row | `.action-buttons` / `.sgf-buttons` | `display: flex; gap: 6px` |
| P-3 | Primary button | `.btn-primary` | Blue background, white text |
| P-4 | Small button | `.btn-sm` | Compact padding for secondary actions |
| P-5 | Label text | `.sgf-label` | `font-weight: 600; font-size: 13px` |
| P-6 | Hidden toggle | `.hidden` | `display: none !important` |
| P-7 | Log panel (collapsible) | `#log-panel.collapsed` | 28px when collapsed, 180px expanded, drag-resize handle |
| P-8 | Right panel sections | `#solution-tree-panel`, `#analysis-table` | Bordered panel with `max-height` and `overflow-y: auto` |

### E.4 Where Config Panel Fits

**Recommended placement**: Below `#run-info` in the left sidebar, as a new collapsible `<div id="config-panel" class="status-box">`. The sidebar has ample vertical space and already supports `overflow-y: auto`.

**UI pattern**: Collapsible section using `.hidden` toggle on click (same pattern as `#run-info` which starts hidden). Header with "Config ▼" label, expand/collapse on click.

**Alternative**: Below the pipeline bar (`#pipeline-bar`) as a horizontal config strip. This is more visible but takes vertical space from the board. Not recommended for MVP.

### E.5 Widget Patterns Needed (Not Currently in GUI)

| R-ID | Widget | Exists? | Notes |
|------|--------|---------|-------|
| W-1 | Range slider with value label | No | Need to build. Similar pattern used in KaTrain's GUI |
| W-2 | Toggle switch | No | Can use styled checkbox |
| W-3 | Dropdown/select | No | Native `<select>` with dark theme styling |
| W-4 | Number input with min/max | No | Native `<input type="number">` with `.btn-sm` wrapper |
| W-5 | Grouped collapsible section | No (log panel is closest) | Accordion pattern: `.config-group-header` + `.config-group-body` with `.hidden` toggle |
| W-6 | Constrained weight sliders (sum=100) | No | Specialized: linked sliders where adjusting one redistributes others |

---

## F. Per-Stage Re-Run Feasibility

### F.1 Serialization Assessment

To re-run from a specific stage, the PipelineContext must be serialized (after the prior stage) and deserialized (before the target stage).

**Non-serializable fields requiring special handling:**

| R-ID | Field | Type | Solution |
|------|-------|------|----------|
| NS-1 | `config` | `EnrichmentConfig` | ✅ Trivial: `config.model_dump()` → JSON → `EnrichmentConfig(**data)` |
| NS-2 | `engine_manager` | `SingleEngineManager` | ❌ Cannot serialize. Must be re-injected from the running bridge server's singleton |
| NS-3 | `root` | `SGFNode` | ⚠️ Rebuild from `sgf_text` by calling `parse_sgf(ctx.sgf_text)`. ~0ms, lossless |
| NS-4 | `entropy_roi` | `EntropyROI` | ⚠️ Not populated by any stage currently. Can be set to `None` on deserialization |
| NS-5 | `notify_fn` | `Callable` | ❌ Cannot serialize. Re-inject from bridge SSE handler (same as initial run) |
| NS-6 | `state.solution_tree_completeness` | `Any` | ⚠️ If this is a Pydantic model, it serializes via `.model_dump()`. Needs investigation of actual runtime type |

### F.2 Proposed Serialization Strategy

```python
def serialize_context(ctx: PipelineContext) -> dict:
    """Convert PipelineContext to JSON-safe dict."""
    d = {}
    # Primitive fields: copy directly
    for f in ["sgf_text", "source_file", "run_id", "trace_id", "config_hash",
              "correct_move_sgf", "correct_move_gtp", "solution_moves",
              "engine_model", "engine_visits", "effective_visits",
              "curated_wrongs", "nearby_moves"]:
        d[f] = getattr(ctx, f)
    # Pydantic models: .model_dump()
    d["config"] = ctx.config.model_dump() if ctx.config else None
    d["metadata"] = ctx.metadata.to_dict() if ctx.metadata else None
    d["position"] = ctx.position.model_dump() if ctx.position else None
    d["framed_position"] = ctx.framed_position.model_dump() if ctx.framed_position else None
    d["response"] = ctx.response.model_dump() if ctx.response else None
    d["validation_result"] = ctx.validation_result.model_dump() if ctx.validation_result else None
    d["refutation_result"] = ctx.refutation_result.model_dump() if ctx.refutation_result else None
    d["difficulty_estimate"] = ctx.difficulty_estimate.model_dump() if ctx.difficulty_estimate else None
    d["result"] = ctx.result.model_dump() if ctx.result else None
    d["timings"] = ctx.timings
    # EnrichmentRunState: dataclass → dict
    d["state"] = dataclasses.asdict(ctx.state) if ctx.state else None
    return d
```

**Deserialization** reverses: rebuild Pydantic models from dicts, re-inject `engine_manager` and `notify_fn`, rebuild `root` from `sgf_text` via `parse_sgf()`.

**Estimated implementation**: ~80-100 lines for serialize + deserialize utilities.

### F.3 Per-Stage Independence Assessment

| R-ID | Can run from stage X independently? | Hard dependencies | Soft dependencies (degraded OK) |
|------|--------------------------------------|-------------------|-------------------------------|
| I-1 | S-1 (Parse): YES — needs only `sgf_text` | None | None |
| I-2 | S-2 (SolvePath): YES — needs S-1 outputs + engine | S-1 complete | None |
| I-3 | S-3 (Analyze): YES — needs S-1+S-2 outputs + engine | S-1, S-2 complete | None |
| I-4 | S-4 (Validate): YES — needs S-3 output | S-1, S-2, S-3 complete | S-2 (tree validation uses engine optionally) |
| I-5 | S-5 (Refutations): YES — needs S-3, S-4 output + engine | S-1, S-2, S-3 complete | S-4 (nearby_moves, curated_wrongs) |
| I-6 | S-6 (Difficulty): YES — needs S-4, S-5 output | S-1, S-2, S-3, S-4, S-5 complete | None |
| I-7 | S-7 (Assembly): YES — needs S-4, S-5, S-6 output | S-1–S-6 complete | None |
| I-8 | S-8 (Technique): YES — needs S-3, S-7 output | S-1–S-7 complete | None |
| I-9 | S-9 (Teaching): YES — needs S-7, S-8 output | S-1–S-8 complete | None |
| I-10 | S-10 (SgfWriteback): YES — needs S-7–S-9 output | S-1–S-9 complete | None |

**Key finding**: ALL stages can run independently IF their prerequisite context fields are populated. The strict serial chain means you can re-run from any stage N by providing serialized context from after stage N-1.

**Most useful re-run points:**
1. **Re-run from S-3 (Analyze)** — change visit counts. Requires S-1+S-2 context.
2. **Re-run from S-5 (Refutations)** — change refutation params. Requires S-1–S-4 context.
3. **Re-run from S-6 (Difficulty)** — change weight formulas. Requires S-1–S-5 context. No engine needed.
4. **Re-run from S-8+S-9 (Technique+Teaching)** — change detector thresholds. Requires S-1–S-7 context. No engine needed.

### F.4 Engine-Dependent vs Engine-Free Stages

| Category | Stages | Re-run implication |
|----------|--------|--------------------|
| **Requires engine** | S-2, S-3, S-4 (optional), S-5 | Can only re-run if KataGo process is alive. Takes seconds. |
| **Engine-free** | S-1, S-6, S-7, S-8, S-9, S-10 | Instant re-run (~ms). Pure computation on existing data. Config changes take effect immediately. |

---

## 5. Risks and Constraints

| R-ID | Risk | Severity | Mitigation |
|------|------|----------|------------|
| RK-1 | PipelineContext size could be large (AnalysisResponse includes move_infos with PV sequences) | Low | Estimate ~50-200KB JSON. Still reasonable for in-memory transfer. Don't persist to disk. |
| RK-2 | `EnrichmentRunState.solution_tree_completeness` type is `Any` — may contain non-serializable objects | Medium | Audit runtime type during integration testing. If Pydantic model → `.model_dump()`. If custom class → add `to_dict()` method. |
| RK-3 | Re-running from S-5 with different config could produce inconsistent assembly (S-7 uses validation_result from S-4 with old config) | Medium | When re-running from stage N, ALWAYS re-run N through S-10 (not just N). This is the natural approach. |
| RK-4 | Difficulty weight sliders (C-34 to C-38) have sum=100 constraint — complex UI widget | Low | Known UX challenge. Options: (A) linked sliders, (B) normalize-on-blur, (C) 5 independent sliders + validation warning. Option C is simplest for MVP. |
| RK-5 | `SGFNode` rebuild from `sgf_text` after re-parsing may lose modifications made by SolvePathStage (injected solution branches) | High | SolvePathStage modifies `ctx.root` AND `ctx.sgf_text` (via tree injection). If re-running from S-3+, the `sgf_text` already contains injected solution. Use updated `sgf_text` (not original). |
| RK-6 | Config panel adds cognitive load to an already dense sidebar | Medium | Use collapsible accordion sections. Default to collapsed. Show only MVP params initially. |

---

## 6. Planner Recommendations

1. **Start with config override on existing `/api/enrich` endpoint (D-1) + `GET /api/config` (D-2)**. This unblocks the config panel with zero pipeline code changes — only bridge.py routing and a `model_copy(update=...)` utility.

2. **Build config panel as collapsible sidebar section** below the existing controls. Use 3 accordion groups (Analysis, Refutations, AI-Solve) with the MVP parameter subset (C-1 to C-5, C-10 to C-15, C-22 to C-28 = 21 params). Slider + toggle widgets only for MVP.

3. **Defer per-stage re-run to Phase 2**. It requires PipelineContext serialization (~100 lines), a new `from_stage` field on the request model, and UI to select which stage to resume from. The value is high but the effort is medium-high. Config override (without re-run) gives 80% of the benefit.

4. **If implementing per-stage re-run, focus on the engine-free re-run points first** (S-6 Difficulty, S-8+S-9 Technique+Teaching). These give instant feedback for config tuning without waiting for KataGo. Add engine-dependent re-run (S-3, S-5) in a later phase.

---

## 7. Confidence & Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | low |

**Justification**: All internal code has been read completely. Stage dependencies, config models, and serialization feasibility are fully mapped. The only unknowns are (a) `solution_tree_completeness` runtime type (RK-2, minor) and (b) widget implementation effort for constrained weight sliders (RK-4, deferred to Phase 2).

---

## Internal References

| R-ID | Artifact | Relevance |
|------|----------|-----------|
| IR-1 | `tools/puzzle-enrichment-lab/analyzers/stages/protocols.py` | PipelineContext definition (Section C) |
| IR-2 | `tools/puzzle-enrichment-lab/config/__init__.py` | EnrichmentConfig composition root (Section B) |
| IR-3 | `tools/puzzle-enrichment-lab/bridge.py` | Current API endpoints (Section D) |
| IR-4 | `tools/puzzle-enrichment-lab/gui/index.html` + `gui/css/styles.css` | Current layout (Section E) |
| IR-5 | `tools/puzzle-enrichment-lab/analyzers/enrich_single.py` | Orchestrator stage list (Section A) |
| IR-6 | `TODO/initiatives/20260314-1400-feature-enrichment-lab-v2/15-research.md` | Prior research on stage decomposition |
| IR-7 | `tools/puzzle-enrichment-lab/AGENTS.md` | Architecture map |
| IR-8 | All 10 stage files in `analyzers/stages/*.py` | Stage implementations (Section A) |
| IR-9 | All 9 config files in `config/*.py` | Config model definitions (Section B) |

## External References

| R-ID | Source | Relevance |
|------|--------|-----------|
| ER-1 | Pydantic `model_copy(update=...)` — [Pydantic v2 docs](https://docs.pydantic.dev/latest/concepts/serialization/) | Config override strategy (Section D.3). Pydantic v2's `model_copy()` supports deep nested updates, making override application straightforward. |
| ER-2 | KaTrain GUI config panel pattern — [github.com/sanderland/katrain](https://github.com/sanderland/katrain) | KaTrain exposes analysis visits, model selection, and move classification thresholds via a sidebar config panel. This is the closest existing implementation of the same concept for KataGo-based tools. |
| ER-3 | FastAPI SSE + config injection pattern — FastAPI middleware docs | Config can be injected as a dependency or passed via request body. Request body is simpler and avoids global state mutation. |
| ER-4 | LizGoban settings panel — [github.com/kaorahi/lizgoban](https://github.com/kaorahi/lizgoban) | LizGoban uses a modal settings dialog for engine parameters. Not ideal for real-time tuning but shows precedent for exposing engine config to GUI users. |
