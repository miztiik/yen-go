# Plan: Layered SRP Extraction (OPT-1)

**Last Updated:** 2026-03-07  
**Selected Option:** OPT-1 — Layered SRP Extraction  
**Governance Status:** GOV-OPTIONS-APPROVED (unanimous)

---

## Overview

4-phase extraction of `enrich_single.py` (1,593 lines → ~200-line orchestrator + purpose-built modules). Each phase is independently committable and revertible.

---

## Phase 1: Config Lookup Consolidation (DRY fix)

**Responsibility:** Centralize tag/level config loading into a single shared module. Eliminate 4-file duplication.

### Target Files

| File                                  | Transformation                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **NEW** `analyzers/config_lookup.py`  | Create. Contains: `load_tag_slug_map()`, `load_tag_id_to_name()`, `load_level_id_map()`, `resolve_tag_names()`, `resolve_level_info()`, `parse_tag_ids()`, `extract_metadata()`, `extract_level_slug()`, module-level caches, `clear_config_caches()`. Uses project root detection via `Path(__file__).resolve().parents[2]` to find `config/` (consistent, not fragile). |
| `analyzers/enrich_single.py`          | Remove: `_extract_metadata`, `_parse_tag_ids`, `_load_tag_slug_map`, `_load_tag_id_to_name`, `_load_level_id_map`, `_resolve_tag_names`, `_resolve_level_info`, `_extract_level_slug`, module-level caches (`_TAG_SLUG_TO_ID`, `_TAG_ID_TO_NAME`, `_LEVEL_ID_MAP`). Replace with imports from `config_lookup`. (~180 lines removed)                                       |
| `analyzers/estimate_difficulty.py`    | Remove `_load_levels_from_config()`. Import `load_level_id_map()` from `config_lookup`.                                                                                                                                                                                                                                                                                   |
| `analyzers/sgf_enricher.py`           | Remove `_load_level_ids()`. Import `load_level_id_map()` from `config_lookup`.                                                                                                                                                                                                                                                                                            |
| `analyzers/validate_correct_move.py`  | Remove `_get_tag_consts()` lazy loader. Import `load_tag_slug_map()` from `config_lookup`.                                                                                                                                                                                                                                                                                |
| `tests/test_enrich_single.py`         | Update imports: `_parse_tag_ids` → from `config_lookup`. Update `autouse` fixture: call `clear_config_caches()`. Move `TestParseTagIds` and `TestExtractMetadataYK` imports to `config_lookup`.                                                                                                                                                                           |
| **NEW** `tests/test_config_lookup.py` | Create. Test path resolution, caching, `clear_config_caches()`, tag slug parsing. (MH-1, MH-2 compliance)                                                                                                                                                                                                                                                                 |

### Invariants

- All existing tests pass (MH-6)
- No functional behavior changes
- `config/tags.json` and `config/puzzle-levels.json` paths resolved correctly (MH-2)

### Risks & Mitigations

| Risk                                                          | Probability | Impact | Mitigation                                                                              |
| ------------------------------------------------------------- | ----------- | ------ | --------------------------------------------------------------------------------------- |
| Different `Path.parents[N]` depths produce different paths    | Medium      | High   | Use a single `_find_project_root()` function that walks up until it finds `config/` dir |
| Cache invalidation in tests breaks                            | High        | Low    | `clear_config_caches()` exposed as public API (MH-1)                                    |
| Subtle differences in error handling across 4 implementations | Low         | Medium | Unit tests cover each loader independently                                              |

### Rollback

`git revert <phase-1-commit>` — single commit, no dependencies.

---

## Phase 2: EnrichmentRunState Dataclass

**Responsibility:** Replace 9+ mutable local tracking variables with a typed state carrier.

### Target Files

| File                                 | Transformation                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **NEW** `models/enrichment_state.py` | Create `EnrichmentRunState` dataclass with fields: `has_solution_path`, `position_only_path`, `ai_solve_failed`, `solution_tree_completeness`, `budget_exhausted`, `queries_used`, `co_correct_detected`, `human_solution_confidence`, `ai_solution_validated`, `correct_move_gtp`, `solution_moves`, `ai_solve_active`, `notify_fn`. All fields have sensible defaults. |
| `analyzers/enrich_single.py`         | Replace 9 bare variable declarations (L620–631) with `state = EnrichmentRunState(...)`. Update all `_foo = value` assignments to `state.foo = value`. Update all reads of `_foo` to `state.foo`. (~30 lines changed, net zero)                                                                                                                                           |

### Invariants

- `state.ai_solve_failed` set in `except` block and consumed in result assembly — exact same fall-through semantics (MH-5)
- Must be `@dataclass` not dict (MH-3)
- All existing tests pass (MH-6)

### Risks & Mitigations

| Risk                                               | Probability | Impact | Mitigation                                                                                     |
| -------------------------------------------------- | ----------- | ------ | ---------------------------------------------------------------------------------------------- |
| `_ai_solve_failed` set-in-except semantics changed | Medium      | High   | Test specifically for the partial-failure state: assert `state.ai_solve_failed` → `ac_level=0` |
| Attribute access slower than local variable        | Negligible  | None   | Negligible overhead vs. 0.5s+ KataGo calls                                                     |

### Rollback

`git revert <phase-2-commit>` — no downstream dependencies.

---

## Phase 3: Extract Code Paths as Private Async Functions

**Responsibility:** Each of the 3 AI-Solve routing branches becomes a single-responsibility async function.

### Target Files

| File                         | Transformation                     |
| ---------------------------- | ---------------------------------- |
| `analyzers/enrich_single.py` | Extract 3 private async functions: |

**Extractions:**

| Function                                                                                                | Lines Extracted       | Responsibility                                                                              | State Flow                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_run_position_only_path(state, root, position, engine_manager, config, metadata) → EnrichmentRunState` | ~190 lines (L633–823) | AI-Solve when no solution exists. Builds solution tree, injects into SGF, handles fallback. | Writes: `position_only_path`, `solution_tree_completeness`, `budget_exhausted`, `queries_used`, `correct_move_gtp`, `solution_moves`                          |
| `_run_has_solution_path(state, root, position, engine_manager, config, metadata) → EnrichmentRunState`  | ~150 lines (L824–975) | AI validation + alternative discovery when existing solution present.                       | Writes: `has_solution_path`, `human_solution_confidence`, `ai_solution_validated`, `queries_used`, `co_correct_detected`, `ai_solve_failed`, `solution_moves` |
| `_run_standard_path(state, root, board_size) → EnrichmentRunState`                                      | ~15 lines (L976–990)  | Simple GTP conversion when no AI-Solve is active.                                           | Writes: `correct_move_gtp`, `solution_moves`                                                                                                                  |

**Orchestrator after extraction (~200 lines):**

```
parse → metadata → route to path → query build → engine analysis → uncrop → validate → tree_validate → refute → difficulty → assemble → goal_infer → teach → timing
```

The orchestrator is now a sequential pipeline of `await` calls and delegations to existing modules (`validate_correct_move`, `generate_refutations`, `estimate_difficulty`, etc.). Each step is 5–15 lines of delegation code.

### Invariants

- Each extracted function returns `EnrichmentRunState` — caller reads state fields for downstream steps
- `_notify` travels via `state.notify_fn`
- Early returns (error results) from position-only path preserved — extracted function returns the error result directly, orchestrator checks and returns early
- All existing tests pass (MH-6)

### Risks & Mitigations

| Risk                                                                                                    | Probability | Impact | Mitigation                                                                                   |
| ------------------------------------------------------------------------------------------------------- | ----------- | ------ | -------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `_notify` calls from within extracted path functions                                                    | Medium      | Low    | `state.notify_fn` carries the closure; extracted functions call `await state.notify_fn(...)` |
| Early-return error results from position-only path need special handling                                | Medium      | Medium | Extracted function returns `(state, AiAnalysisResult                                         | None)` tuple; orchestrator checks for error result |
| Lazy imports inside code paths (`from analyzers.solve_position import ...`) must move to function scope | Low         | Low    | Keep lazy imports inside extracted functions (identical behavior)                            |

### Rollback

`git revert <phase-3-commit>` — orchestrator structure reverts, Phase 2 dataclass still works standalone.

---

## Phase 4: Move `_uncrop_response` to `query_builder.py`

**Responsibility:** Collocate coordinate forward-transform (crop) and reverse-transform (uncrop) in the same module.

### Target Files

| File                         | Transformation                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `analyzers/query_builder.py` | Add `uncrop_response(response, cropped) → AnalysisResponse` as public function. Imports `MoveAnalysis` from models. |
| `analyzers/enrich_single.py` | Remove `_uncrop_response` (55 lines). Import `uncrop_response` from `query_builder`.                                |

### Invariants

- Identical behavior, identical return type
- All existing tests pass (MH-6)

### Risks & Mitigations

| Risk                                                                                      | Probability | Impact | Mitigation                                                          |
| ----------------------------------------------------------------------------------------- | ----------- | ------ | ------------------------------------------------------------------- |
| `query_builder.py` has no existing dependency on `MoveAnalysis`                           | Low         | Low    | Already imported indirectly; add direct import                      |
| Circular import if `enrich_single` imports from `query_builder` which imports from models | None        | None   | No circular path: `enrich_single → query_builder → models` is a DAG |

### Rollback

`git revert <phase-4-commit>` — trivial, single function move.

---

## SOLID/DRY/KISS/YAGNI Mapping

| Principle                     | How This Plan Achieves It                                                                                                     |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **S (Single Responsibility)** | Config lookup → 1 module. State carrier → 1 dataclass. Each code path → 1 function. Orchestrator → routing + delegation only. |
| **O (Open/Closed)**           | New code paths can be added as new functions without modifying orchestrator routing logic.                                    |
| **I (Interface Segregation)** | `EnrichmentRunState` carries only fields needed by all paths. No God object.                                                  |
| **D (Dependency Inversion)**  | All modules depend on `config_lookup` abstraction, not on manual path resolution.                                             |
| **DRY**                       | Config loading consolidated from 4 files → 1.                                                                                 |
| **KISS**                      | One dataclass + one shared module. No protocols, no factories, no registries.                                                 |
| **YAGNI**                     | No async stage protocol. No stage registry. No future-proofing abstractions.                                                  |

---

## Test Strategy (TDD-first per phase)

| Phase | Test Approach                                                                                                                                                                  |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| P1    | Write `test_config_lookup.py` BEFORE extraction. Verify: path resolution, caching, `clear_config_caches()`, tag parsing. Then extract and ensure all existing tests pass.      |
| P2    | Write `test_enrichment_state.py` BEFORE wiring. Verify: default field values, field mutation, `ai_solve_failed` fall-through scenario. Then wire into orchestrator.            |
| P3    | Run existing integration tests as oracle BEFORE extraction. Extract functions. Re-run — must produce identical results. Add unit test per extracted function with mock engine. |
| P4    | Move function, run existing tests. Add `test_uncrop_response` in `test_query_builder.py` if not already present.                                                               |

## Validation Matrix

| Phase | Lint (`ruff check .`) | Tests (`pytest`) | Type check  | Behavior  |
| ----- | --------------------- | ---------------- | ----------- | --------- |
| P1    | Pass                  | All pass         | Types valid | Identical |
| P2    | Pass                  | All pass         | Types valid | Identical |
| P3    | Pass                  | All pass         | Types valid | Identical |
| P4    | Pass                  | All pass         | Types valid | Identical |

> **See also:**
>
> - [Options](./25-options.md) — OPT-1 description
> - [Research](./15-research.md) — Responsibility catalog, state graph
> - [Governance](./70-governance-decisions.md) — Must-hold constraints
