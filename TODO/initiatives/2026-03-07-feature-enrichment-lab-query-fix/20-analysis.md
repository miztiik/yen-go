# Analysis

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Last Updated:** 2026-03-07

---

## Planning Confidence

| Metric                    | Value                             |
| ------------------------- | --------------------------------- |
| Planning Confidence Score | 85                                |
| Risk level                | medium                            |
| Research invoked          | No (codebase evidence sufficient) |

**Score breakdown:**

- Start at 100
- -0: Architecture seams are clear (query_builder.py → models/, solve_position.py → engine/)
- -0: Approach is clear (OPT-B, extraction)
- -0: No external precedent needed
- -5: Quality impact slightly uncertain (need to verify ko-puzzle behavior after refactor)
- -5: Test strategy needs golden fixture design
- -5: Rollout: `generate_run_id()` format change affects multiple consumers

---

## Ripple Effects

| impact_id | direction  | area                                                         | risk   | mitigation                                                                                                                                                                       | owner_task | status       |
| --------- | ---------- | ------------------------------------------------------------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------ |
| RE-1      | downstream | `build_query_from_sgf()` callers (enrich_single.py)          | Low    | Function returns same `QueryResult` type — callers unchanged                                                                                                                     | T2         | needs action |
| RE-2      | downstream | `build_query_from_position()` callers (enrich_single.py)     | Low    | Function returns same `QueryResult` type — callers unchanged                                                                                                                     | T3         | needs action |
| RE-3      | downstream | `SyncEngineAdapter` callers (enrich_single.py, tree builder) | Low    | `.query()` API unchanged — only internal implementation changes                                                                                                                  | T4         | needs action |
| RE-4      | downstream | `generate_run_id()` format consumers                         | Medium | Search for all format consumers: `cli.py` (L411), `conftest.py` (L50), `log_config.py`. Format is only used for file naming and JSON metadata — no parsing on the format itself. | T8         | needs action |
| RE-5      | lateral    | Test files that assert log file names                        | Medium | `test_log_config.py`, `test_sprint5_fixes.py` may assert on `{run_id}-enrichment.log` pattern. Update assertions.                                                                | T8         | needs action |
| RE-6      | lateral    | Tests that mock `SyncEngineAdapter` internals                | Low    | If any test patches `_region_moves` or `_position` directly, it may need updating. Search test files.                                                                            | T4         | needs action |
| RE-7      | upstream   | `config/katago-enrichment.json`                              | None   | Config file is read-only; shared function reads same config. No config changes needed.                                                                                           | —          | addressed    |
| RE-8      | lateral    | `sgf_enricher.py` encoding change                            | Low    | Only affects how SGF node properties are decoded. Existing SGFs with only ASCII are unaffected. Non-ASCII original C[] are preserved.                                            | T6         | needs action |
| RE-9      | lateral    | Comment text change in `_build_refutation_branches()`        | Low    | Tests that assert on exact comment text (e.g., "Wrong. Winrate drops by X%.") will need updating.                                                                                | T7         | needs action |
| RE-10     | downstream | `observability.py` — may log via enrichment lab namespace    | Low    | If `observability.py` uses `logging.getLogger(__name__)`, it already produces `analyzers.observability` which is now covered by T5 filter fix.                                   | T5         | addressed    |

---

## Cross-Artifact Consistency

| finding_id | severity | finding                                                                                                                                                                                                 | resolution                              |
| ---------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| F-1        | Low      | Charter AC-7 ("Only ONE code path prepares tsumego queries") requires verification after T1-T4.                                                                                                         | T11 validates.                          |
| F-2        | Low      | Charter AC-6 ("log naming matches YYYYMMDD-HHMMSS-HASH.log") requires T8 format update propagation to conftest.py.                                                                                      | RE-5 covers.                            |
| F-3        | None     | Tasks T2 and T3 are both in query_builder.py and could be done as single edit.                                                                                                                          | Marked parallel-eligible in task graph. |
| F-4        | Low      | The existing `2026-03-06-fix-enrichment-lab-logging-scope` initiative (research only) partially overlaps with T5. That initiative was never executed — only research done. This initiative subsumes it. | Note in 70-governance-decisions.md.     |

---

## Coverage Map

| Acceptance Criteria                    | Covered by Task(s) | Status  |
| -------------------------------------- | ------------------ | ------- |
| AC-1: Correct branch after enrichment  | T4, T9             | covered |
| AC-2: No out-of-area moves             | T1, T4, T9         | covered |
| AC-3: No garbled non-ASCII             | T6, T9             | covered |
| AC-4: No diagnostic data in C[]        | T7                 | covered |
| AC-5: Log files contain data           | T5                 | covered |
| AC-6: Log naming matches pattern       | T8                 | covered |
| AC-7: Single query prep path (DRY)     | T1, T2, T3, T4     | covered |
| AC-8: All existing tests pass          | T11                | covered |
| AC-9: Golden fixture exists and passes | T9                 | covered |

All acceptance criteria are covered. No unmapped tasks. No gaps.

> **See also**:
>
> - [40-tasks.md](./40-tasks.md) — Task details
> - [30-plan.md](./30-plan.md) — Technical plan
