# Plan: enrich_single.py SRP Refactor — OPT-1 Stage Runner Pattern

**Initiative ID:** 20260313-1400-refactor-enrich-single-srp  
**Selected Option:** OPT-1  
**Last Updated:** 2026-03-13

---

## Overview

Decompose `analyzers/enrich_single.py` (~1,726 lines) into 12 files using the Stage Runner pattern. Each enrichment step becomes a stage class implementing `EnrichmentStage` protocol, auto-wrapped by `StageRunner` for notify/timing/error handling.

**Target:** `enrich_single.py` ≤ 150 lines (thin orchestrator).

---

## Phase 1: Foundation (Prerequisites)

### 1a. Create `analyzers/stages/` sub-package

Create directory structure:
```
analyzers/stages/__init__.py
```

### 1b. Define protocols (`analyzers/stages/protocols.py`)

**New file ~100 lines.** Contains:

- `SgfMetadata` TypedDict — typed dictionary for parsed SGF metadata keys (`puzzle_id: str`, `tags: list[int]`, `corner: str`, `move_order: str`, `ko_type: str`, `collection: str`, etc.)
- `PipelineContext` dataclass — typed state flowing through pipeline
- `StageResult` dataclass — per-stage outcome (success/failure/degraded)
- `ErrorPolicy` enum — `FAIL_FAST` | `DEGRADE`
- `EnrichmentStage` Protocol — `name`, `error_policy`, `async run(ctx) → ctx`

### 1c. Extract result builders (`analyzers/result_builders.py`)

**Move from enrich_single.py lines 141–270 (~130 lines).** Pure functions:
- `_build_refutation_entries()` → `build_refutation_entries()`
- `_build_difficulty_snapshot()` → `build_difficulty_snapshot()`
- `_compute_config_hash()` → `compute_config_hash()`
- `_make_error_result()` → `make_error_result()`
- `_build_partial_result()` → `build_partial_result()`

**Transforms:** Remove underscore prefix (these become public module functions).

### 1d. Create stage runner (`analyzers/stages/stage_runner.py`)

**New file ~70 lines.** Implements:
- `StageRunner.run_stage(stage, ctx, notify_fn, timings)` — auto-wraps with notify/timing/error policy
- `StageRunner.run_pipeline(stages, ctx, notify_fn)` — runs ordered stage list

---

## Phase 2: Extract Stage Modules

### 2a. Parse stage (`analyzers/stages/parse_stage.py`)

**Extract from enrich_single.py Steps 1-2 (lines 793–860, ~70 lines).**
- Parse SGF, extract metadata, puzzle_id fallback
- Extract correct first move + solution tree
- **Error policy:** FAIL_FAST (can't continue without parsed SGF)
- **Reads:** `ctx.sgf_text`, `ctx.source_file`
- **Writes:** `ctx.root`, `ctx.metadata`, `ctx.position`, `ctx.correct_move_sgf`

### 2b. Solve paths (`analyzers/stages/solve_paths.py`)

**Move from enrich_single.py lines 276–720 (~445 lines).**
- `_run_position_only_path()`, `_run_has_solution_path()`, `_run_standard_path()`
- Already parameter-injected — cleanest extraction
- **Error policy:** DEGRADE (fallback to partial enrichment on failure)
- **Reads:** `ctx.root`, `ctx.position`, `ctx.metadata`, `ctx.correct_move_sgf`, `ctx.engine_manager`, `ctx.config`
- **Writes:** `ctx.state`, `ctx.correct_move_gtp`, `ctx.correct_move_sgf`, `ctx.solution_moves`

### 2c. Query stage (`analyzers/stages/query_stage.py`)

**Extract from enrich_single.py Steps 3-4 (lines 935–1085, ~150 lines).**
- Build analysis query (crop + frame), run engine analysis, uncrop response
- Board state GUI notifications
- **Error policy:** FAIL_FAST (can't continue without analysis)
- **Reads:** `ctx.sgf_text`, `ctx.position`, `ctx.config`, `ctx.engine_manager`
- **Writes:** `ctx.response`, `ctx.cropped`, `ctx.engine_model`, `ctx.engine_visits`, `ctx.effective_visits`

### 2d. Validation stage (`analyzers/stages/validation_stage.py`)

**Extract from enrich_single.py Steps 5-5.5 (lines 1086–1245, ~160 lines).**
- Validate correct move (tag-aware), tree validation, curated wrongs, nearby moves
- **Error policy:** DEGRADE (validation failure shouldn't block enrichment)
- **Reads:** `ctx.response`, `ctx.correct_move_gtp`, `ctx.metadata`, `ctx.position`, `ctx.solution_moves`, `ctx.config`, `ctx.engine_manager`
- **Writes:** `ctx.validation_result`, `ctx.curated_wrongs`, `ctx.nearby_moves`

### 2e. Refutation stage (`analyzers/stages/refutation_stage.py`)

**Extract from enrich_single.py Step 6 (lines 1246–1392, ~147 lines).**
- Generate refutations + escalation logic
- **Error policy:** DEGRADE (zero refutations is acceptable)
- **Reads:** `ctx.position`, `ctx.correct_move_gtp`, `ctx.response`, `ctx.config`, `ctx.engine_manager`, `ctx.nearby_moves`, `ctx.curated_wrongs`
- **Writes:** `ctx.refutation_result`

### 2f. Difficulty stage (`analyzers/stages/difficulty_stage.py`)

**Extract from enrich_single.py Step 7 (lines 1393–1452, ~60 lines).**
- Estimate difficulty (structural + policy-only fallback)
- **Error policy:** DEGRADE (fallback to policy-only)
- **Reads:** `ctx.validation_result`, `ctx.refutation_result`, `ctx.solution_moves`, `ctx.metadata`, `ctx.state`, `ctx.root`, `ctx.nearby_moves`
- **Writes:** `ctx.difficulty_estimate`

### 2g. Assembly stage (`analyzers/stages/assembly_stage.py`)

**Extract from enrich_single.py Step 8 (lines 1453–1600, ~148 lines).**
- Assemble AiAnalysisResult, AC level decision matrix, goal inference, field wiring
- **Error policy:** FAIL_FAST (assembly failure = no result)
- **Reads:** all upstream context fields
- **Writes:** `ctx.result`

### 2h. Teaching stage (`analyzers/stages/teaching_stage.py`)

**Extract from enrich_single.py Steps 9-10 (lines 1601–1726, ~126 lines).**
- Technique classification, teaching comments, hints, SGF writeback, final logging
- **Error policy:** DEGRADE (teaching enrichment is optional)
- **Reads:** `ctx.result`, `ctx.sgf_text`, `ctx.metadata`
- **Writes:** `ctx.result.technique_tags`, `ctx.result.teaching_comments`, `ctx.result.hints`, `ctx.result.enriched_sgf`

---

## Phase 3: Rewrite Orchestrator

### 3a. Rewrite `enrich_single.py` as thin orchestrator

**Target: ~120-150 lines.** Contains only:
1. Config init + trace_id generation
2. `PipelineContext` construction
3. Solve-path dispatch (position-only vs has-solution vs standard)
4. `StageRunner.run_pipeline()` call with stage list
5. Timing finalization + return result

### 3b. Update imports across lab

Update all files that import from `enrich_single`:
- `cli.py` / `bridge.py` — update `enrich_single_puzzle` import
- `tests/test_enrich_single.py` — update to new signature
- Any other test files that reference internal helpers

### 3c. Delete dead code

Remove any residual functions from `enrich_single.py` that were extracted to other modules. Verify via grep that no imports reference removed symbols.

---

## Phase 4: Documentation + Cleanup

### 4a. Update lab README

Add architecture section describing the stage runner pattern and new module map.

### 4b. Verify test suite passes

Run full lab test suite. No new tests required (Q9:B), but all existing tests must pass.

---

## PipelineContext Field Ownership Table (RC-2)

| Field | Type | Written by | Read by |
|-------|------|-----------|---------|
| `sgf_text` | `str` | init | parse, query |
| `config` | `EnrichmentConfig` | init | all stages |
| `engine_manager` | `SingleEngineManager` | init | solve_paths, query, validation, refutation |
| `source_file` | `str` | init | parse, assembly |
| `run_id` | `str` | init | assembly |
| `trace_id` | `str` | init | assembly |
| `config_hash` | `str` | init | assembly |
| `root` | `SGFNode` | parse | solve_paths, validation, difficulty, assembly |
| `metadata` | `SgfMetadata` (TypedDict) | parse | solve_paths, validation, refutation, difficulty, assembly, teaching |
| `position` | `Position` | parse | solve_paths, query, validation, refutation |
| `correct_move_sgf` | `str \| None` | parse → solve_paths | query, validation |
| `correct_move_gtp` | `str \| None` | solve_paths | validation, refutation, difficulty, assembly |
| `solution_moves` | `list[str]` | solve_paths | validation, difficulty |
| `state` | `EnrichmentRunState` | solve_paths | difficulty, assembly |
| `response` | `AnalysisResponse \| None` | query | validation, refutation, assembly |
| `cropped` | `CroppedResult \| None` | query | (logged only) |
| `engine_model` | `str \| None` | query | assembly |
| `engine_visits` | `int` | query | difficulty, assembly |
| `effective_visits` | `int` | query | (logged only) |
| `validation_result` | `CorrectMoveResult \| None` | validation | refutation, difficulty, assembly |
| `curated_wrongs` | `list[dict] \| None` | validation | refutation |
| `nearby_moves` | `list[str] \| None` | validation | refutation, difficulty |
| `refutation_result` | `RefutationResult \| None` | refutation | difficulty, assembly |
| `difficulty_estimate` | `DifficultyEstimate \| None` | difficulty | assembly |
| `result` | `AiAnalysisResult \| None` | assembly | teaching |

---

## Runner Sunset Criteria (RC-1)

If the backend merger initiative (refactoring `core/__init__.py` for lazy imports) has not started by **September 2026** (6 months):

1. Evaluate whether the runner pattern has provided value beyond the initial decomposition
2. If no additional stages have been added and no merger work is planned, consider simplifying to OPT-3 (direct function calls with PipelineContext, no runner)
3. The Protocol ABCs should be retained regardless — they document the interface contract

---

## Risks and Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| PipelineContext becomes God object | Medium | Field ownership table enforced; typed fields only |
| Test breakage from signature change | Low | Mechanical update of call-sites; existing suite covers behavior |
| Import cycles in stages/ | Low | Each stage imports from analyzers/ (not from sibling stages) |
| Solve paths extraction complexity | Medium | 445 lines are already parameter-injected; test coverage exists |
| Timing anomaly regression | Low | Runner auto-wrapping eliminates manual timing; anomalies fixed by design |

## Rollback Strategy

Each phase is committed to a feature branch. If a phase breaks tests:
1. Revert the phase commit
2. Investigate the specific extraction that broke
3. Fix and re-apply

No destructive git operations. No force-push.

---

## Documentation Plan

| doc_action | file | why_updated |
|-----------|------|-------------|
| files_to_update | `tools/puzzle-enrichment-lab/README.md` | Add architecture section with stage runner description and module map |
| files_to_create | `analyzers/stages/README.md` | Brief description of stage pattern, how to add new stages |
| cross_references | `docs/concepts/snapshot-shard-terminology.md` | N/A — this refactor doesn't affect concepts docs |

---

## SOLID/DRY/KISS/YAGNI Mapping

| Principle | How this plan delivers |
|-----------|----------------------|
| **S (SRP)** | Each stage module has exactly one reason to change |
| **O (Open/Closed)** | New stages added by implementing protocol, not modifying runner |
| **L (Liskov)** | All stages substitutable via `EnrichmentStage` protocol |
| **I (Interface Segregation)** | Single focused `EnrichmentStage` protocol |
| **D (Dependency Inversion)** | Orchestrator depends on protocol, not concrete stages |
| **DRY** | Notify/timing/error logic in runner only; result builders in one module |
| **KISS** | Runner is ~70 lines; protocol is ~100 lines; each stage is focused |
| **YAGNI** | Protocol mirrors proven backend pattern (not speculative) |
