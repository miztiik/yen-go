# Tasks: Layered SRP Extraction (OPT-1)

**Last Updated:** 2026-03-07  
**Selected Option:** OPT-1  
**Governance Status:** GOV-OPTIONS-APPROVED

---

## Phase 1: Config Lookup Consolidation

| task_id | title                                                                          | depends_on         | parallel        | files                                | definition_of_done                                                                                                                                                                                                                                                                     |
| ------- | ------------------------------------------------------------------------------ | ------------------ | --------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1      | Write `test_config_lookup.py` (TDD: tests first)                               | —                  | —               | `tests/test_config_lookup.py`        | Tests exist for: `load_tag_slug_map()`, `load_tag_id_to_name()`, `load_level_id_map()`, `resolve_tag_names()`, `resolve_level_info()`, `parse_tag_ids()`, `extract_metadata()`, `clear_config_caches()`, and path resolution correctness (MH-2). Tests fail initially (no module yet). |
| T2      | Create `analyzers/config_lookup.py`                                            | T1                 | —               | `analyzers/config_lookup.py`         | Module created with all functions. Uses `_find_project_root()` for path resolution. Exposes `clear_config_caches()` (MH-1). T1 tests pass.                                                                                                                                             |
| T3      | Update `enrich_single.py` — remove config helpers, import from `config_lookup` | T2                 | —               | `analyzers/enrich_single.py`         | Remove ~180 lines of config/metadata helpers. Import from `config_lookup`. Remove module-level caches. All existing tests pass.                                                                                                                                                        |
| T4      | Update `estimate_difficulty.py` — remove `_load_levels_from_config`            | T2                 | [P] with T5, T6 | `analyzers/estimate_difficulty.py`   | Import `load_level_id_map()` from `config_lookup`. Remove local implementation. Tests pass.                                                                                                                                                                                            |
| T5      | Update `sgf_enricher.py` — remove `_load_level_ids`                            | T2                 | [P] with T4, T6 | `analyzers/sgf_enricher.py`          | Import `load_level_id_map()` from `config_lookup`. Remove local implementation. Tests pass.                                                                                                                                                                                            |
| T6      | Update `validate_correct_move.py` — remove `_get_tag_consts`                   | T2                 | [P] with T4, T5 | `analyzers/validate_correct_move.py` | Import `load_tag_slug_map()` from `config_lookup`. Remove local lazy loader. Tests pass.                                                                                                                                                                                               |
| T7      | Update `test_enrich_single.py` — redirect imports                              | T3                 | —               | `tests/test_enrich_single.py`        | Update imports of `_parse_tag_ids`, `_load_tag_slug_map`, `_TAG_SLUG_TO_ID`, `_extract_metadata` to import from `config_lookup`. Update `autouse` fixture to call `clear_config_caches()`. All tests pass.                                                                             |
| T8      | Phase 1 validation: full test suite, lint, verify no regressions               | T3, T4, T5, T6, T7 | —               | all                                  | `pytest` passes. `ruff check .` clean. Behavior identical. Update `tools/puzzle-enrichment-lab/README.md` or `analyzers/` module docstring to mention `config_lookup.py` as the config resolution module (RC-2). Single commit.                                                        |

---

## Phase 2: EnrichmentRunState Dataclass

| task_id | title                                               | depends_on | parallel | files                            | definition_of_done                                                                                                                                                                              |
| ------- | --------------------------------------------------- | ---------- | -------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T9      | Write `test_enrichment_state.py` (TDD: tests first) | T8         | —        | `tests/test_enrichment_state.py` | Tests for: default values, field mutation, `ai_solve_failed` fall-through scenario (MH-5), `notify_fn` attachment. Tests fail initially.                                                        |
| T10     | Create `models/enrichment_state.py`                 | T9         | —        | `models/enrichment_state.py`     | `@dataclass` (MH-3) with 13 fields + defaults. T9 tests pass.                                                                                                                                   |
| T11     | Wire `EnrichmentRunState` into `enrich_single.py`   | T10        | —        | `analyzers/enrich_single.py`     | Replace 9 bare `_*` variable declarations with `state = EnrichmentRunState(...)`. Replace all `_*` reads/writes with `state.*`. Attach `_notify` to `state.notify_fn`. All existing tests pass. |
| T12     | Phase 2 validation: full test suite, lint           | T11        | —        | all                              | `pytest` passes. `ruff check .` clean. Behavior identical. Single commit.                                                                                                                       |

---

## Phase 3: Extract Code Paths

| task_id | title                                                    | depends_on    | parallel     | files                         | definition_of_done                                                                                                                                                                   |
| ------- | -------------------------------------------------------- | ------------- | ------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| T13     | Extract `_run_position_only_path()`                      | T12           | —            | `analyzers/enrich_single.py`  | Private async function (~190 lines). Receives `(state, root, position, engine_manager, config, metadata)`, returns `(EnrichmentRunState, AiAnalysisResult                            | None)`. The `AiAnalysisResult` is non-None only for early-return error/partial results. Lazy imports preserved inside function. |
| T14     | Extract `_run_has_solution_path()`                       | T13           | —            | `analyzers/enrich_single.py`  | Private async function (~150 lines). Receives same signature pattern. Returns `EnrichmentRunState`. Exception handling sets `state.ai_solve_failed = True` and falls through (MH-5). |
| T15     | Extract `_run_standard_path()`                           | T13           | [P] with T14 | `analyzers/enrich_single.py`  | Private async function (~15 lines). Trivial extraction.                                                                                                                              |
| T16     | Refactor orchestrator to dispatch to extracted functions | T13, T14, T15 | —            | `analyzers/enrich_single.py`  | `enrich_single_puzzle()` body reduced to ~200 lines: init → parse → route → query → validate → refute → score → assemble → teach → timing. Clear linear flow.                        |
| T17     | Add unit tests for each extracted path function          | T16           | —            | `tests/test_enrich_single.py` | Mock engine. Test each of 3 paths with representative fixture. Verify state mutations match expectations.                                                                            |
| T18     | Phase 3 validation: full test suite, lint                | T16, T17      | —            | all                           | `pytest` passes. `ruff check .` clean. Behavior identical. Single commit.                                                                                                            |

---

## Phase 4: Move `_uncrop_response`

| task_id | title                                                                | depends_on | parallel | files                                                      | definition_of_done                                                                           |
| ------- | -------------------------------------------------------------------- | ---------- | -------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| T19     | Move `_uncrop_response` to `query_builder.py` as `uncrop_response()` | T18        | —        | `analyzers/query_builder.py`, `analyzers/enrich_single.py` | Function moved. Import added to `enrich_single.py`. `query_builder` now owns crop + uncrop.  |
| T20     | Add test for `uncrop_response` in query_builder tests                | T19        | —        | `tests/test_query_builder.py`                              | Test with mock `CroppedPosition` and `AnalysisResponse`. Verify coordinate back-translation. |
| T21     | Phase 4 validation: full test suite, lint                            | T19, T20   | —        | all                                                        | `pytest` passes. `ruff check .` clean. Behavior identical. Single commit.                    |

---

## Legacy Code Removal (embedded in phases)

| task_id | title                                           | phase | notes                             |
| ------- | ----------------------------------------------- | ----- | --------------------------------- |
| T3      | Remove config helpers from enrich_single.py     | P1    | ~180 lines removed                |
| T4-T6   | Remove duplicate loaders from 3 sibling files   | P1    | ~60 lines removed across 3 files  |
| T11     | Remove bare `_*` variable declarations          | P2    | ~15 lines replaced                |
| T13-T15 | Remove inline code paths from orchestrator body | P3    | ~355 lines extracted to functions |
| T19     | Remove `_uncrop_response` from enrich_single.py | P4    | ~55 lines removed                 |

**Total lines removed from `enrich_single.py`:** ~590 lines (1,593 → ~1,000 with extracted in-file functions; orchestrator body: 1,085 → ~200)

---

## Dependency Graph

```
T1 → T2 → T3 → T7 → T8
             ↘ T4 [P]
             ↘ T5 [P]  → T8
             ↘ T6 [P]

T8 → T9 → T10 → T11 → T12

T12 → T13 → T14 [P with T15]
              ↘ T15 [P with T14]
      T13 + T14 + T15 → T16 → T17 → T18

T18 → T19 → T20 → T21
```

[P] = safe to run in parallel with indicated sibling task.

---

## Completion Checklist

- [ ] Phase 1 committed (T1–T8): Config lookup consolidated, tests updated
- [ ] Phase 2 committed (T9–T12): EnrichmentRunState wired in
- [ ] Phase 3 committed (T13–T18): Code paths extracted, orchestrator is ~200 lines
- [ ] Phase 4 committed (T19–T21): `uncrop_response` in query_builder
- [ ] All 6 must-hold constraints verified
- [ ] `ruff check .` clean after each phase
- [ ] `pytest` passes after each phase

> **See also:**
>
> - [Plan](./30-plan.md) — Phase descriptions, risks, test strategy
> - [Governance](./70-governance-decisions.md) — Must-hold constraints
