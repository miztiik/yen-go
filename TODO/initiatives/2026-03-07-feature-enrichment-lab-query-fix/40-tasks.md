# Tasks

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Last Updated:** 2026-03-07
**Selected Option:** OPT-B

---

## Dependency Order

```
T1 → T2 → T3 → T4 (DRY refactor chain)
T5 [P] (logging fix — independent)
T6 [P] (encoding fix — independent)
T7 (comment cleanup — depends on T6)
T8 (log naming — depends on T5)
T9 (golden fixture — depends on T1-T4)
T10 (documentation — depends on all above)
T11 (validation — depends on all above)
```

`[P]` = parallelizable with other `[P]` tasks.

---

## Task List

| task_id | title                                                                                                           | file(s)                                         | depends_on | parallel | status      |
| ------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------- | -------- | ----------- |
| T1      | Create `TsumegoQueryBundle` dataclass and `prepare_tsumego_query()` function                                    | `analyzers/query_builder.py`                    | —          | —        | not_started |
| T2      | Refactor `build_query_from_sgf()` to call `prepare_tsumego_query()`                                             | `analyzers/query_builder.py`                    | T1         | —        | not_started |
| T3      | Refactor `build_query_from_position()` to call `prepare_tsumego_query()`                                        | `analyzers/query_builder.py`                    | T1         | —        | not_started |
| T4      | Refactor `SyncEngineAdapter.__init__()` to call `prepare_tsumego_query()` and wire `allowed_moves` in `query()` | `analyzers/solve_position.py`                   | T1         | —        | not_started |
| T5      | Fix `_LabNamespaceFilter` to match actual module prefixes                                                       | `log_config.py`                                 | —          | [P]      | not_started |
| T6      | Fix encoding: `.decode("latin-1")` → `.decode("utf-8")` in `_get_node_move_coord()`                             | `analyzers/sgf_enricher.py`                     | —          | [P]      | not_started |
| T7      | Remove diagnostic data from refutation branch C[] comments                                                      | `analyzers/sgf_enricher.py`                     | T6         | —        | not_started |
| T8      | Align `generate_run_id()` and log file naming with KataGo pattern                                               | `models/ai_analysis_result.py`, `log_config.py` | T5         | —        | not_started |
| T9      | Add golden fixture regression test                                                                              | `tests/` (new or existing)                      | T1-T4      | —        | not_started |
| T10     | Update documentation                                                                                            | `README.md` or inline comments                  | T1-T9      | —        | not_started |
| T11     | Full validation: run all tests, verify log output, verify AC-1 through AC-9                                     | all                                             | T1-T10     | —        | not_started |

---

## Task Details

### T1: Create `TsumegoQueryBundle` + `prepare_tsumego_query()`

**File:** `tools/puzzle-enrichment-lab/analyzers/query_builder.py`

**Actions:**

1. Add `TsumegoQueryBundle` dataclass after existing `QueryResult` dataclass
2. Add `prepare_tsumego_query()` pure function that implements:
   - Override komi to 0.0
   - Compute puzzle region moves via `get_puzzle_region_moves(margin)`
   - Apply tsumego frame via `apply_tsumego_frame(position, margin)`
   - Resolve ko-aware rules and PV length from config
3. Export both from module

**Lines added:** ~40
**Lines removed:** 0 (extraction happens in T2/T3)

### T2: Refactor `build_query_from_sgf()`

**File:** `tools/puzzle-enrichment-lab/analyzers/query_builder.py`

**Actions:**

1. After crop step, call `prepare_tsumego_query(eval_position, config=config, ko_type=ko_type, puzzle_region_margin=margin)`
2. Use `bundle.framed_position` for AnalysisRequest position
3. Use `bundle.region_moves` for AnalysisRequest allowed_moves
4. Use `bundle.rules` and `bundle.pv_len` for AnalysisRequest
5. Remove inline komi override, `get_puzzle_region_moves()`, `apply_tsumego_frame()`, ko-aware rules resolution

**Lines added:** ~5
**Lines removed:** ~20

### T3: Refactor `build_query_from_position()`

**File:** `tools/puzzle-enrichment-lab/analyzers/query_builder.py`

**Actions:**

1. Call `prepare_tsumego_query(position, config=config, ko_type=ko_type, puzzle_region_margin=margin)`
2. Use bundle fields for AnalysisRequest construction
3. Remove inline komi override, `get_puzzle_region_moves()`, `apply_tsumego_frame()`, ko-aware rules resolution

**Lines added:** ~5
**Lines removed:** ~25

### T4: Refactor `SyncEngineAdapter` + wire `allowed_moves`

**File:** `tools/puzzle-enrichment-lab/analyzers/solve_position.py`

**Actions:**

1. In `__init__()`: replace inline komi/frame/region logic with call to `prepare_tsumego_query()` from `query_builder`
2. Store `self._bundle` (or `self._position`, `self._region_moves` from bundle)
3. In `query()`: add `allowed_moves=self._region_moves` to `AnalysisRequest`
4. Remove inline imports of `apply_tsumego_frame`, `Position` that are no longer needed

**Lines added:** ~5
**Lines removed:** ~15

### T5: Fix logging namespace filter

**File:** `tools/puzzle-enrichment-lab/log_config.py`

**Actions:**

1. Replace `LOGGER_NAMESPACE = "puzzle_enrichment_lab"` with a tuple of prefixes matching actual module names
2. Update `_LabNamespaceFilter.filter()` to check against the prefix tuple
3. Keep `"puzzle_enrichment_lab"` in the list for backward compatibility

### T6: Fix encoding in sgf_enricher

**File:** `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py`

**Actions:**

1. Change `_get_node_move_coord()`: `.decode("latin-1")` → `.decode("utf-8", errors="replace")`
2. In `_embed_teaching_comments()`: add ASCII-only sanitization for enrichment-added text (strip non-ASCII before embedding)

### T7: Remove diagnostic data from C[] comments

**File:** `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py`

**Actions:**

1. In `_build_refutation_branches()`: change comment from `f"Wrong. Winrate drops by {delta_pct:.0f}%."` to `"Wrong."`
2. Remove refutation line numbering from C[] (`Refutation line N/M.`)
3. Add `logger.info(...)` call with the delta/score data for observability

### T8: Align log file naming

**Files:** `models/ai_analysis_result.py`, `log_config.py`

**Actions:**

1. Update `generate_run_id()`: `f"{now:%Y%m%d}-{secrets.token_hex(4)}"` → `f"{now:%Y%m%d}-{now:%H%M%S}-{secrets.token_hex(4).upper()}"`
2. Update `setup_logging()` file naming pattern if needed
3. Verify test conftest.py generates compatible run_ids

### T9: Golden fixture regression test

**File:** `tests/test_solve_position.py` or new `tests/test_golden_fixture.py`

**Actions:**

1. Add constant for golden puzzle SGF
2. Test `prepare_tsumego_query()` produces correct region_moves
3. Test `SyncEngineAdapter.query()` builds request with `allowed_moves` (mock engine)
4. Test no move in region_moves is outside bounding box + margin
5. Verify no non-ASCII in enrichment-added C[] comments (fixture from BUG-3)

### T10: Documentation

**File:** `tools/puzzle-enrichment-lab/README.md`

**Actions:**

1. Document `prepare_tsumego_query()` as single source of truth for tsumego query prep
2. Document `allowed_moves` requirement
3. Document comment policy (teaching comments only in C[])
4. Document log file naming convention

### T11: Validation

**Actions:**

1. Run `pytest tests/test_enrich_single.py tests/test_solve_position.py`
2. Run `pytest tests/test_query_builder.py`
3. Run `pytest tests/test_log_config.py`
4. Verify enrichment log files contain data (not empty)
5. Verify golden fixture test passes
6. `ruff check analyzers/ models/ tests/`
7. Verify all AC-1 through AC-9

> **See also**:
>
> - [30-plan.md](./30-plan.md) — Technical design
> - [20-analysis.md](./20-analysis.md) — Ripple effects
