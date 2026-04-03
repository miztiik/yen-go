# Research Brief: Stage Boundary Analysis for enrich_single.py Decomposition

**Initiative:** `20260313-1400-refactor-enrich-single-srp`  
**Date:** 2026-03-13  
**Author:** Feature-Researcher agent (read-only analysis)

---

## 1. Research Question and Boundaries

**Primary question:** For `tools/puzzle-enrichment-lab/analyzers/enrich_single.py` (~1,726 lines), what are the precise line boundaries, data dependencies, and cross-cutting concerns for each of the 12 proposed concern groups?

**Success criteria:** A structured map that lets planners correctly size decomposition options, identify shared state, and choose whether TELEMETRY should be a cross-cutting module or inline residue.

**Out of scope:** Code changes, backend imports, DRY analysis (separate research question in this same file previously addressed).

---

## 2. Internal Code Evidence — Stage Boundary Map

### 2.1 Function Definition Line Numbers (verified by grep)

| Symbol | Line |
|--------|------|
| `_build_refutation_entries` | 141 |
| `_build_difficulty_snapshot` | 160 |
| `_compute_config_hash` | 179 |
| `_make_error_result` | 185 |
| `_build_partial_result` | 205 |
| `_run_position_only_path` (async) | 276 |
| `_run_has_solution_path` (async) | 543 |
| `_run_standard_path` | 707 |
| `enrich_single_puzzle` (async) | 729 |

### 2.2 Stage Boundary Table

| Row | Group | Lines | ~Count | Key Functions / Variables Defined | Reads From | Writes To |
|-----|-------|-------|--------|-----------------------------------|-----------|-----------|
| R-1 | **IMPORTS** | 1–139 | 139 | `logger`; dual-path `try/except` imports for all analyzers, models, config | None (stdlib only) | All groups (shared names) |
| R-2 | **RESULT_ASSEMBLY** | 141–270 | 130 | `_build_refutation_entries`, `_build_difficulty_snapshot`, `_compute_config_hash`, `_make_error_result`, `_build_partial_result` | `RefutationResult`, `DifficultyEstimate`, `EnrichmentConfig`, `AiAnalysisResult` | `ASSEMBLY`, `AI_SOLVE` (error/partial early-return paths) |
| R-3 | **AI_SOLVE** | 276–720 | 445 | `_run_position_only_path`, `_run_has_solution_path`, `_run_standard_path` | `EnrichmentRunState`, `SGF root`, `position`, `config`, `engine_manager`, `metadata` dict | `state` (mutated); may return `AiAnalysisResult` early via `_make_error_result`/`_build_partial_result` |
| R-4 | **ORCHESTRATOR_SETUP** | 729–939 | 211 | `enrich_single_puzzle` function def + docstring; `config_hash`, `trace_id`, `effective_run_id`, local `_notify` async helper, `t_total_start`, `timings: dict`; Step 1: `root`, `metadata`, `puzzle_id`, `tags`, `corner`, `move_order`, `ko_type`, `collection`; Step 2: `state`, `position`, `board_size`, `correct_move_sgf`, `correct_move_gtp`, `solution_moves` | `EnrichmentConfig`, `sgf_text`, `engine_manager` | All downstream steps (pipeline context vars) |
| R-5 | **QUERY_ANALYSIS** | 940–1085 | 146 | Step 3: `query_result`, `request`, `cropped`, `effective_visits`, `symmetries_override`; Step 4: `response`, `engine_model`, `engine_visits`; Step 4b: `uncrop_response` | `position`, `ko_type`, `config`, `engine_manager`, `board_size` | `VALIDATION`, `REFUTATIONS`, `ASSEMBLY` (all read `response`) |
| R-6 | **VALIDATION** | 1086–1245 | 160 | Step 5: `correct_move_result: CorrectMoveResult`; Step 5a: `tree_depth`, `tree_status` appended to `correct_move_result.flags`; Step 5.5: `curated_wrongs`, `nearby_moves` | `response`, `correct_move_gtp`, `tags`, `corner`, `move_order`, `ko_type`, `config`, `solution_moves`, `position` | `REFUTATIONS` (`curated_wrongs`, `nearby_moves`, `correct_move_result`), `DIFFICULTY` (`correct_move_result`) |
| R-7 | **REFUTATIONS** | 1246–1392 | 147 | Step 6: `refutation_result: RefutationResult`; escalation logic (may re-assign `refutation_result`) | `position`, `correct_move_gtp`, `response`, `config`, `nearby_moves`, `curated_wrongs`, `engine_manager.engine` | `DIFFICULTY`, `ASSEMBLY` |
| R-8 | **DIFFICULTY** | 1393–1452 | 60 | Step 7: `difficulty_estimate: DifficultyEstimate`; `branch_count`, `local_candidate_count`, `max_resolved_depth` | `correct_move_result`, `refutation_result`, `solution_moves`, `state.solution_tree_completeness` | `ASSEMBLY` |
| R-9 | **ASSEMBLY** | 1453–1600 | 148 | Step 8: `result: AiAnalysisResult` (fully wired); AC-level matrix, goal inference, level mismatch log | `correct_move_result`, `refutation_result`, `difficulty_estimate`, `response`, `state`, `config`, `metadata`, all session vars | `TEACHING`, `SGF_OUTPUT` |
| R-10 | **TEACHING** | 1601–1662 | 62 | Step 9: `result.technique_tags`, `result.teaching_comments`, `result.hints` | `result` (modifies in-place), `board_size` | `SGF_OUTPUT` |
| R-11 | **SGF_OUTPUT** | 1663–1726 | 64 | Step 10: `result.enriched_sgf`; `result.phase_timings`, final `enrichment_end` log, `return result` | `result`, `sgf_text`, `timings` dict | Return value |
| R-12 | **TELEMETRY** _(cross-cutting)_ | Scattered | ~55 stmts | `_notify` helper def (~L789–792); timer starts (`t_parse_start` etc.) × 7; `timings[key]` assignments × 9; `result.phase_timings = timings` (~L1698) | Every group | Every group |

> **Line total check:** 139+130+445+211+146+160+147+60+148+62+64 = **1,712** (matches ~1,726; difference is blank lines and section separators).

---

## 3. Telemetry Inventory (Cross-Cutting)

### 3.1 `await _notify(...)` calls — 14 total

| # | Line | Stage name | Concern group |
|---|------|-----------|---------------|
| 1 | 798 | `"parse_sgf"` | ORCHESTRATOR_SETUP / Step 1 |
| 2 | 846 | `"extract_solution"` | ORCHESTRATOR_SETUP / Step 2 |
| 3 | 913 | `"board_state"` (initial) | ORCHESTRATOR_SETUP / Step 2 |
| 4 | 940 | `"build_query"` | QUERY_ANALYSIS / Step 3 |
| 5 | 994 | `"board_state"` (crop) | QUERY_ANALYSIS / Step 3 |
| 6 | 1041 | `"katago_analysis"` | QUERY_ANALYSIS / Step 4 |
| 7 | 1086 | `"validate_move"` | VALIDATION / Step 5 |
| 8 | 1246 | `"generate_refutations"` | REFUTATIONS / Step 6 |
| 9 | 1393 | `"estimate_difficulty"` | DIFFICULTY / Step 7 |
| 10 | 1453 | `"assemble_result"` | ASSEMBLY / Step 8 |
| 11 | 1601 | `"teaching_enrichment"` | TEACHING / Step 9 |
| 12 | 1663 | `"enriched_sgf"` (start) | SGF_OUTPUT / Step 10 |
| 13 | 1671 | `"enriched_sgf"` (success) | SGF_OUTPUT / Step 10 |
| 14 | 1691 | `"enriched_sgf"` (failure) | SGF_OUTPUT / Step 10 |

> **Note:** Zero `_notify` calls inside the three `_run_*` code-path functions. They are module-level functions without access to the `_notify` closure; they use `state.notify_fn` indirectly via `EnrichmentRunState` (though current usage shows only `logger` calls in those functions).

### 3.2 `timings[key]` assignments — 9 total

| # | Line | Key | Timer started at / covers |
|---|------|-----|--------------------------|
| 1 | 946 | `"parse"` | `t_parse_start` (~L798) → covers **Step 1+2** |
| 2 | 1042 | `"query_build"` | `t_query_start` (~L947) → covers **Step 3** |
| 3 | 1087 | `"analysis"` | `t_analysis_start` (~L1043) → covers **Step 4** |
| 4 | 1251 | `"tree_validation"` | `t_validation_start` (~L1088) → covers **Step 5** |
| 5 | 1394 | `"refutation"` | `t_refutation_start` (~L1252) → covers **Step 6** |
| 6 | 1607 | `"difficulty"` | `t_difficulty_start` (~L1395) → **covers Steps 7+8 combined** ⚠️ |
| 7 | 1696 | `"enrich_sgf"` | `t_enrich_sgf_start` (~L1664) → covers **Step 10** |
| 8 | 1699 | `"teaching"` | `t_teaching_start` (~L1608) → **covers Steps 9+10 combined** ⚠️ |
| 9 | 1700 | `"total"` | `t_total_start` (~L793) → full pipeline |

> **⚠️ Two timing key anomalies:** `timings["difficulty"]` spans steps 7+8 (assembly is untimed separately). `timings["teaching"]` spans steps 9+10. These are imprecision bugs — the two timer starts are in different concern groups than the corresponding `timings[key]` write.

---

## 4. Data Flow Between Groups

The critical variables bridging concern groups inside `enrich_single_puzzle`:

| Bridge Variable | Type | Written By | Read By |
|----------------|------|-----------|---------|
| `root` | SGF node | ORCHESTRATOR_SETUP (parse_sgf) | AI_SOLVE, QUERY_ANALYSIS (via `sgf_text`), ASSEMBLY (level mismatch log), SGF_OUTPUT |
| `metadata` dict | `dict` | ORCHESTRATOR_SETUP | All downstream (puzzle_id, tags, corner, ko_type, move_order, collection) |
| `state` | `EnrichmentRunState` | ORCHESTRATOR_SETUP (initialized), AI_SOLVE (mutated) | ASSEMBLY (ac_level matrix, tree_truncated, queries_used) |
| `position` | `Position` | ORCHESTRATOR_SETUP | QUERY_ANALYSIS, VALIDATION, REFUTATIONS, DIFFICULTY |
| `correct_move_sgf` / `correct_move_gtp` | `str` | AI_SOLVE → set via `state`, bridged to locals in ORCHESTRATOR_SETUP | QUERY_ANALYSIS, VALIDATION, REFUTATIONS, ASSEMBLY |
| `solution_moves` | `list[str]` | AI_SOLVE → state → local | VALIDATION (tree depth), DIFFICULTY |
| `query_result` / `cropped` | `QueryResult` | QUERY_ANALYSIS | QUERY_ANALYSIS (uncrop), VALIDATION (coordinate space) |
| `response` | `AnalysisResponse` | QUERY_ANALYSIS (engine.analyze) | VALIDATION, REFUTATIONS (initial_analysis), DIFFICULTY, ASSEMBLY (goal inference, top_move) |
| `engine_model`, `engine_visits` | `str`, `int` | QUERY_ANALYSIS | ASSEMBLY (AiAnalysisResult.from_validation) |
| `correct_move_result` | `CorrectMoveResult` | VALIDATION | DIFFICULTY (mutated — adds puzzle_id, visits, confidence), ASSEMBLY |
| `curated_wrongs`, `nearby_moves` | `list` | VALIDATION (Step 5.5) | REFUTATIONS |
| `refutation_result` | `RefutationResult` | REFUTATIONS | DIFFICULTY, ASSEMBLY |
| `difficulty_estimate` | `DifficultyEstimate` | DIFFICULTY | ASSEMBLY |
| `result` | `AiAnalysisResult` | ASSEMBLY (created), TEACHING (fields populated) | SGF_OUTPUT (enriched_sgf), return value |
| `timings` | `dict[str, float]` | ORCHESTRATOR_SETUP (init), TELEMETRY (assignments) | SGF_OUTPUT (`result.phase_timings = timings`) |

---

## 5. Risks and Decomposition Observations

| Row | Risk | Severity | Notes |
|-----|------|----------|-------|
| R-1 | **Heavy shared local scope** | High | 20+ local variables live from ORCHESTRATOR_SETUP through SGF_OUTPUT. Decomposing into separate functions/classes requires explicit context carrier evolution. |
| R-2 | **TELEMETRY is fully non-extractable as inline** | Medium | `_notify` is a closure over `progress_cb`. Timer starts/stops straddle every group boundary. Extraction requires a `PipelineContext` or observer object to carry `_notify`, `timings`, and timer state. |
| R-3 | **`timings["difficulty"]` spans steps 7+8** | Low-Medium | If ASSEMBLY is split into its own module, the `t_difficulty_start` → `timings["difficulty"]` arc will cross the module boundary. Requires timer refactoring as part of decomposition (bug fix opportunity). |
| R-4 | **`correct_move_result` is mutated in DIFFICULTY** | Low | `correct_move_result.puzzle_id`, `.visits_used`, `.confidence` are set just before `estimate_difficulty()` call (L1388–1392). This mutation-before-use pattern creates ordering dependency. |
| R-5 | **`_build_partial_result` in R-2 duplicates teaching logic** | Medium | `_build_partial_result` calls `classify_techniques`, `generate_hints`, `generate_teaching_comments` directly — same calls made in TEACHING (Step 9). Any change to TEACHING step must be reflected here. |
| R-6 | **AI_SOLVE code paths are 445 lines but structurally isolated** | Low | The three `_run_*` functions are already module-level. They share no local state with the orchestrator (receive all via parameters). **Cleanest extraction candidate.** |

---

## 6. Planner Recommendations

- **Rec-1 (Extract AI_SOLVE first):** `_run_position_only_path`, `_run_has_solution_path`, `_run_standard_path` (R-3, lines 276–720, 445 lines) are the cleanest extraction. They are already module-level, fully parameter-injected, and have no implicit dependency on orchestrator locals. Move to `analyzers/solve_paths.py`. Reduces `enrich_single.py` by ~26%.

- **Rec-2 (Introduce `PipelineContext` to carry TELEMETRY):** The `_notify` closure and `timings` dict prevent clean decomposition of the orchestrator body without a context carrier. Define a `PipelineContext` dataclass in `models/pipeline_context.py` holding `notify_fn`, `timings`, `trace_id`, `run_id`, `config_hash`. Then each stage function receives `ctx: PipelineContext` rather than 8+ individual kwargs.

- **Rec-3 (Fix timing anomalies during decomposition):** When extracting DIFFICULTY and ASSEMBLY as separate callables, fix `timings["difficulty"]` to cover only Step 7, and add `timings["assembly"]` for Step 8. This resolves the two ⚠️ anomalies noted in §3.2 as a side-effect of the refactor.

- **Rec-4 (Merge `_build_partial_result` teaching calls into TEACHING stage):** The partial-result helper (R-2) duplicates the TEACHING step logic. Extract a `run_teaching_stage(result, board_size, scan_response)` function that both `_build_partial_result` and the Step 9 block call. Eliminates ~12 lines of duplication.

---

## 7. Confidence and Risk Update

| Dimension | Assessment |
|-----------|-----------|
| **Boundary precision** | High — all function line numbers verified by grep; notify/timing lines confirmed by search |
| **Data flow completeness** | High — all 20 bridging variables traced through full pipeline |
| **Decomposition risk** | Medium — heavy shared local scope requires context carrier before clean extraction |
| **Telemetry risk** | Medium — `_notify` closure dependency and timer-boundary anomalies must be resolved in same PR as decomposition |

**post_research_confidence_score:** 92  
**post_research_risk_level:** `medium`

---

## Handoff Summary

```
research_completed: true
initiative_path: TODO/initiatives/20260313-1400-refactor-enrich-single-srp/
artifact: 15-research.md
top_recommendations:
  1. Extract _run_position_only_path / _run_has_solution_path / _run_standard_path
     → analyzers/solve_paths.py  (445 lines, cleanest isolation, no shared scope)
  2. Introduce PipelineContext dataclass to carry _notify + timings —
     prerequisite for decomposing the orchestrator body
  3. Fix timings["difficulty"]/["teaching"] anomalies during Stage 7/8/9 extraction
  4. Extract run_teaching_stage() to eliminate _build_partial_result duplication
open_questions: []
post_research_confidence_score: 92
post_research_risk_level: medium
```

