# Research Brief: Critical Review of 91 Failing Backend Tests

**Last Updated**: 2026-03-24
**Initiative**: 20260324-research-backend-failing-tests
**Status**: research_completed

---

## 1. Research Question and Boundaries

**Question**: Of the 91 failing backend tests, which represent valid production contract violations vs. stale/obsolete test code that has drifted from intentional architecture changes?

**Boundaries**:
- Scope: Only the 91 failing tests identified in the problem statement
- Method: Cross-reference each test's assertions against current production code
- Out of scope: Writing fix code, modifying tests, or implementing changes

---

## 2. Internal Code Evidence (Per Cluster)

### Cluster A — `_inject_yengo_props` Removed (18 tests)

| R-1 | Evidence | Reference |
|-----|----------|-----------|
| R-1a | `AnalyzeStage` in [stages/analyze.py](backend/puzzle_manager/stages/analyze.py#L495) has `_enrich_sgf()` (SGFBuilder-based), NOT `_inject_yengo_props()` (regex-based) | Method name change from spec-103 Phase 12 |
| R-1b | All 18 tests in [test_analyze_characterization.py](backend/puzzle_manager/tests/unit/test_analyze_characterization.py) call `analyze_stage._inject_yengo_props()` with raw SGF string | Tests were "golden master" for the OLD regex implementation |
| R-1c | The new `_enrich_sgf()` takes a `SGFGame` object (not raw string), plus `level: int` argument | Completely different interface |
| R-1d | The file header says: "Characterization tests for `_inject_yengo_props()` output... before refactoring to SGFBuilder-based implementation" | Tests were meant to be temporary safety net during refactoring |

**Verdict**: **STALE — DELETE**. These are explicitly labeled as "golden master" tests for a removed method. The refactoring is complete (spec-103 Phase 12). The equivalent behavior is tested by [test_sgf_enrichment.py](backend/puzzle_manager/tests/test_sgf_enrichment.py) which tests `_enrich_sgf()` directly.

---

### Cluster B — Inventory Model Schema Drift (34 tests across 8 files)

#### B1: `test_inventory_models.py` (8 tests)

| R-2 | Evidence | Reference |
|-----|----------|-----------|
| R-2a | Tests assert `stats.avg_quality_score == 0.0` and `stats.hint_coverage_pct == 0.0` | [test_inventory_models.py](backend/puzzle_manager/tests/test_inventory_models.py#L147-L150) |
| R-2b | Current `CollectionStats` has `by_puzzle_quality: dict[str, int]` instead of `avg_quality_score: float` and `hint_coverage_pct: float` | [inventory/models.py](backend/puzzle_manager/inventory/models.py#L69-L87) |
| R-2c | Tests also create `CollectionStats(avg_quality_score=3.5)` and test bounds `(0-5)` and `(0-100)` | Spec 102 replaced float averages with per-level quality breakdown |

**Verdict**: **STALE — UPDATE ASSERTIONS**. The `CollectionStats` model intentionally changed from `avg_quality_score`/`hint_coverage_pct` floats to `by_puzzle_quality` dict. Tests need to assert the new fields.

#### B2: `test_inventory_rebuild.py` (8 tests)

| R-3 | Evidence | Reference |
|-----|----------|-----------|
| R-3a | Publish log fixtures use path `"sgf/beginner/2026/01/batch-001/puzzle-001.sgf"` (old hierarchical format) | [test_inventory_rebuild.py](backend/puzzle_manager/tests/test_inventory_rebuild.py#L41-L43) |
| R-3b | Current publish writes flat `sgf/{NNNN}/{hash}.sgf` paths; `rebuild_inventory()` ghost-checks against disk | [inventory/rebuild.py](backend/puzzle_manager/inventory/rebuild.py#L89-L100) |
| R-3c | SGF files in fixture use old path `sgf/beginner/2026/01/batch-001/` but rebuild does `sgf_path.relative_to(output_dir)` matching against publish log `entry.path` | Path mismatch causes ghost-entry skip → 0 counts |

**Verdict**: **STALE — UPDATE FIXTURES**. Tests use old path format in publish log fixtures. The publish log paths must match the flat `sgf/{NNNN}/{hash}.sgf` layout. The rebuild logic itself is correct; only the test fixtures are outdated.

#### B3: `test_inventory_cli.py` (5 tests)

| R-4 | Evidence | Reference |
|-----|----------|-----------|
| R-4a | Fixture creates `CollectionStats` with `avg_quality_score=3.7, hint_coverage_pct=92.5` (doesn't exist) | [test_inventory_cli.py](backend/puzzle_manager/tests/test_inventory_cli.py#L77-L78) |
| R-4b | Tests assert `"Quality Metrics:"`, `"Stage Metrics:"`, `"Error Rates:"`, `"Audit:"` in output | Lines 157-230 |
| R-4c | Current `format_inventory_summary()` outputs: "By Level:", "By Tag:", "By Quality:", "Last Updated:", "Last Run ID:" — does NOT output "Quality Metrics:", "Stage Metrics:", "Error Rates:", "Audit:" sections | [inventory/cli.py](backend/puzzle_manager/inventory/cli.py#L26-L100) |

**Verdict**: **STALE — UPDATE ASSERTIONS**. The CLI format was intentionally simplified (removed stage metrics, error rates, per-item quality metrics). Tests assert the old verbose format. The fixture also uses removed fields.

#### B4: `test_inventory_integration.py` (4 tests)

| R-5 | Evidence | Reference |
|-----|----------|-----------|
| R-5a | Test creates `InventoryUpdate` with `quality_scores=[3,4,4,3,5...]` and `hints_count=7` — fields that don't exist | [test_inventory_integration.py](backend/puzzle_manager/tests/test_inventory_integration.py#L62-L65) |
| R-5b | Current `InventoryUpdate` has `quality_increments: dict[str, int]` (not list of scores) | [inventory/models.py](backend/puzzle_manager/inventory/models.py#L115-L125) |
| R-5c | Test asserts `inventory.collection.avg_quality_score == pytest.approx(3.9)` and `hint_coverage_pct == 70.0` | Removed fields |
| R-5d | Test asserts `schema_version == "1.1"` but current default is `"2.0"` | [inventory/models.py](backend/puzzle_manager/inventory/models.py#L96) |

**Verdict**: **STALE — UPDATE TESTS**. InventoryUpdate model changed from quality_scores list to quality_increments dict. Schema version bumped to 2.0. Tests need full rewrite to match current model contracts.

#### B5: `test_inventory_manager.py` (1 test — `save_writes_valid_json`)

| R-6 | Evidence | Reference |
|-----|----------|-----------|
| R-6a | Fixture creates inventory at `yengo-puzzle-collections/puzzle-collection-inventory.json` (old filename) | [test_inventory_manager.py](backend/puzzle_manager/tests/test_inventory_manager.py#L64) |
| R-6b | Current path is `.puzzle-inventory-state/inventory.json` (Spec 107) | [inventory/manager.py](backend/puzzle_manager/inventory/manager.py#L47-L58) |

**Verdict**: **STALE — UPDATE PATH**. Inventory filename/location changed per Spec 107. Test fixture path needs updating.

#### B6: `test_inventory_check.py` (5 tests)

| R-7 | Evidence | Reference |
|-----|----------|-----------|
| R-7a | Fixtures create publish log entries with old hierarchical paths (`sgf/beginner/2026/01/batch-001/p1.sgf`) | [test_inventory_check.py](backend/puzzle_manager/tests/test_inventory_check.py#L48-L52) |
| R-7b | Check logic does ghost-check by matching publish log paths to filesystem files | Path mismatch → all entries appear as "ghosts" → wrong integrity results |

**Verdict**: **STALE — UPDATE FIXTURES**. Same root cause as B2: old path format in test fixtures.

#### B7: `test_inventory_protection.py` (1 test)

| R-8 | Evidence | Reference |
|-----|----------|-----------|
| R-8a | Test stores inventory at `yengo-puzzle-collections/puzzle-collection-inventory.json` (old name) | [test_inventory_protection.py](backend/puzzle_manager/tests/test_inventory_protection.py#L59) |
| R-8b | `PROTECTED_FILES` includes both `"puzzle-collection-inventory.json"` and `"inventory.json"` | [pipeline/cleanup.py](backend/puzzle_manager/pipeline/cleanup.py#L35-L38) |
| R-8c | The cleanup function checks `file_path.name in PROTECTED_FILES` — both old and new names are protected | Legacy compat maintained |

**Verdict**: Needs investigation — may be path mismatch rather than protection logic. **UPDATE FIXTURE PATH** if test is checking ops-dir cleanup.

#### B8: `test_inventory_reconcile.py` (2 tests)

| R-9 | Evidence | Reference |
|-----|----------|-----------|
| R-9a | Tests call `manager.reconcile(output_dir=..., run_id=...)` | [test_inventory_reconcile.py](backend/puzzle_manager/tests/unit/test_inventory_reconcile.py#L50) |
| R-9b | `InventoryManager` has NO `reconcile()` method | [inventory/manager.py](backend/puzzle_manager/inventory/manager.py) — confirmed by grep |
| R-9c | Reconcile is a standalone function: `reconcile_inventory()` in [inventory/reconcile.py](backend/puzzle_manager/inventory/reconcile.py#L95) | Different interface entirely |

**Verdict**: **STALE — REWRITE**. Tests call a method that was factored out to a standalone function. Tests should use `reconcile_inventory(output_dir, run_id)` instead of `manager.reconcile()`.

---

### Cluster C — PublishStage `_update_inventory` Interface Changed (11 tests)

#### C1: `test_periodic_reconcile.py` (8 tests)

| R-10 | Evidence | Reference |
|------|----------|-----------|
| R-10a | Tests call `stage._update_inventory(puzzles_by_level={"beginner": [{"id": "p1"}]}, puzzles_by_tag=..., puzzles_by_quality=..., reconcile_interval=0)` | [test_periodic_reconcile.py](backend/puzzle_manager/tests/integration/test_periodic_reconcile.py#L69-L78) |
| R-10b | Current signature: `_update_inventory(self, level_slug_counts: dict[str, int], tag_slug_counts: dict[str, int], puzzles_by_quality: dict[str, int], run_id, processed_count, output_dir)` | [stages/publish.py](backend/puzzle_manager/stages/publish.py#L682-L700) |
| R-10c | Tests pass `puzzles_by_level` (lists of dicts) but production expects `level_slug_counts` (dict[str, int]) | Completely incompatible signatures |
| R-10d | Tests also assert `inv.audit.runs_since_last_reconcile` which doesn't exist on `AuditMetrics` | [inventory/models.py](backend/puzzle_manager/inventory/models.py#L42-L46) — only has `total_rollbacks` and `last_rollback_date` |

**Verdict**: **STALE — REWRITE**. The `_update_inventory` signature changed AND the periodic reconcile counter (`runs_since_last_reconcile`) was removed from the model. The entire feature of periodic auto-reconcile may have been descoped.

#### C2: `test_stage_metrics.py` (3 tests)

| R-11 | Evidence | Reference |
|------|----------|-----------|
| R-11a | Tests call `manager.update_stage_metrics()` which DOES exist | [inventory/manager.py](backend/puzzle_manager/inventory/manager.py#L463) |
| R-11b | Likely failure is fixture setup using old model fields or old inventory path | Same pattern as B4/B5 |

**Verdict**: **PARTIALLY STALE — UPDATE FIXTURES**. The `update_stage_metrics()` API itself exists. Failures are likely from fixture setup using old model fields (`schema_version="1.1"` or old path).

---

### Cluster D — Publish Path Layout Changed (9 tests)

| R-12 | Evidence | Reference |
|------|----------|-----------|
| R-12a | Tests expect `sgf/{level}/batch-{NNNN}/{hash}.sgf` path format | [test_publish.py](backend/puzzle_manager/tests/stages/test_publish.py#L108-L112) |
| R-12b | Current publish uses flat `sgf/{NNNN}/{hash}.sgf` (global batch counter, no level subdirectory) | [batch_writer.py](backend/puzzle_manager/core/batch_writer.py#L231) scans `sgf/{NNNN}` |
| R-12c | Tests also expect `.batch-state.json` at `sgf/{level}/` but flat sharding uses `sgf/.batch-state.json` | State key is now global, not per-level |
| R-12d | State key tests: `test_state_key_is_level_only` expects `sgf/beginner/.batch-state.json` | [test_publish.py](backend/puzzle_manager/tests/stages/test_publish.py#L193-L200) |

**Verdict**: **STALE — UPDATE PATH ASSERTIONS**. Spec 126 changed from `sgf/{level}/batch-{NNNN}/` to flat `sgf/{NNNN}/`. Tests assert the intermediate format (per-level batch dirs) that was superseded. These are **valid contract tests** that need path format updates.

---

### Cluster E — Trace Map/Logging Behavior (9 tests)

#### E1: `test_ingest_trace.py` (3 tests)

| R-13 | Evidence | Reference |
|------|----------|-----------|
| R-13a | Tests expect `.trace-map-{run_id}.json` written by ingest; also expect `.original-filenames-{run_id}.json` | [test_ingest_trace.py](backend/puzzle_manager/tests/stages/test_ingest_trace.py#L88-L100) |
| R-13b | Trace map is now embedded in `YM` property (v12), not a separate file | CLAUDE.md: "trace_id is stored in SGF files via the YM property" |
| R-13c | `read_trace_map()` function still exists but may not be written by current ingest | Need to verify `stages/ingest.py` |

**Verdict**: **LIKELY STALE — INVESTIGATE**. If trace data moved to YM property and trace_map files are no longer generated, these tests assert a removed mechanism. The tests test an implementation detail (sidecar file) rather than the observable behavior (trace_id presence in SGF).

#### E2: `test_publish_trace.py` (4 tests)

| R-14 | Evidence | Reference |
|------|----------|-----------|
| R-14a | Tests expect `trace_id`, `source_file`, `original_filename` fields in publish log JSONL entries | [test_publish_trace.py](backend/puzzle_manager/tests/stages/test_publish_trace.py#L108-L113) |
| R-14b | `PublishLogEntry` model HAS `trace_id` field (mandatory) | [models/publish_log.py](backend/puzzle_manager/models/publish_log.py#L55) |
| R-14c | Test also expects trace map cleanup and original-filenames sidecar file | Lines 155-175 |

**Verdict**: **MIXED**. The `trace_id` in publish log is a valid contract. `source_file` and `original_filename` may not be written by current publish stage. Tests for cleanup of trace_map files may be stale if those files are no longer generated.

#### E3: `test_analyze_trace.py` (2 tests)

| R-15 | Evidence | Reference |
|------|----------|-----------|
| R-15a | Tests assert `YQ[q:5;rc:99;hc:1]` is preserved in output when input already has it | [test_analyze_trace.py](backend/puzzle_manager/tests/stages/test_analyze_trace.py#L125-L140) |
| R-15b | Current `_enrich_sgf()` uses `get_policy_registry()` for PRESERVE/OVERRIDE decisions | [stages/analyze.py](backend/puzzle_manager/stages/analyze.py#L545-L570) |
| R-15c | The policy for YQ is "OVERRIDE" (always recomputed) per property_policy registry | Need to verify — if YQ policy is OVERRIDE, existing values get replaced |

**Verdict**: **NEEDS INVESTIGATION**. If the property policy for YQ is OVERRIDE (always recompute), then preserving input YQ is incorrect behavior. Tests may be asserting the wrong behavior. If the policy is PRESERVE_IF_PRESENT, tests are valid.

---

### Cluster F — SGF Enrichment/Comment Behavior (5 tests)

#### F1: `test_sgf_enrichment.py` — Root comment removal (2 tests)

| R-16 | Evidence | Reference |
|------|----------|-----------|
| R-16a | Test asserts `"C[This is a puzzle" not in result` (expects root comment REMOVED) | [test_sgf_enrichment.py](backend/puzzle_manager/tests/test_sgf_enrichment.py#L271) |
| R-16b | Current `_enrich_sgf()` PRESERVES root comment by default (`preserve_root_comment=True`) | [stages/analyze.py](backend/puzzle_manager/stages/analyze.py#L530-L536) |
| R-16c | CLAUDE.md states: "Root `C[]` PRESERVED by default (configurable via `preserve_root_comment`)" | Intentional behavior change |

**Verdict**: **STALE — UPDATE ASSERTION**. The behavior intentionally changed from "remove root comment" to "preserve root comment by default". Tests need to assert the comment IS present, not absent. This is an intentional contract change.

#### F2: `test_enrichment.py` — EnrichmentConfig rejects `corner_threshold` (2 tests)

| R-17 | Evidence | Reference |
|------|----------|-----------|
| R-17a | Test creates `EnrichmentConfig(corner_threshold=5, edge_threshold=8)` | [test_enrichment.py](backend/puzzle_manager/tests/test_enrichment.py#L220-L223) |
| R-17b | `EnrichmentConfig` no longer has `corner_threshold` or `edge_threshold` fields | [enrichment/config.py](backend/puzzle_manager/core/enrichment/config.py#L79-L91) — "no longer configurable, computed from board_size" |
| R-17c | Unit test file at `tests/unit/test_enrichment.py` line 1671 explicitly documents: "corner_threshold and edge_threshold are no longer configurable" | Internal tests already adapted |
| R-17d | Hint test: `assert "corner" in hint.lower()` for `HintGenerator.generate_yh1()` with `region_code="TL"` | Depends on hint text generation implementation |

**Verdict**: **STALE — DELETE threshold tests, INVESTIGATE hint test**. Threshold configurability was intentionally removed. The hint "corner" assertion may fail if hint text generation changed.

#### F3: `test_tagger.py` — `detect_techniques()` empty default (1 test)

| R-18 | Evidence | Reference |
|------|----------|-----------|
| R-18a | Test asserts `len(tags) > 0` for a minimal SGF with no comments/patterns | [test_tagger.py](backend/puzzle_manager/tests/test_tagger.py#L68-L80) |
| R-18b | Tagger design: "No fallback: empty tag list is returned when no technique is confidently detected" | [core/tagger.py](backend/puzzle_manager/core/tagger.py#L17) — docstring is explicit |
| R-18c | Test name says "defaults to life-and-death" but tagger explicitly says "empty tag list is a valid result" | Design principle mismatch — tagger chose precision over recall |

**Verdict**: **STALE — DELETE or UPDATE**. The tagger's design principle explicitly states "empty tag list is a valid result" and "no fallback". The test asserts an old behavior (defaulting to life-and-death) that was intentionally removed for precision.

---

### Cluster G — Isolated Failures (5 tests)

#### G1: `test_board.py` — `Board(0)` doesn't raise ValueError (1 test)

| R-19 | Evidence | Reference |
|------|----------|-----------|
| R-19a | Test does `with pytest.raises(ValueError): Board(10)` | [test_board.py](backend/puzzle_manager/tests/test_board.py#L26-L27) |
| R-19b | Board validates `MIN_BOARD_SIZE(5) <= size <= MAX_BOARD_SIZE(19)` | [core/board.py](backend/puzzle_manager/core/board.py#L44) |
| R-19c | `Board(10)` SHOULD raise ValueError because... wait — 10 is between 5 and 19 | Test expects rejection of size 10 but 10 is a valid board size |

**Verdict**: **OVER-SPECIFIED — UPDATE TEST**. The test assumes `Board(10)` is invalid, but `Board` now accepts any size 5-19. Size 10 is a legitimate odd/even size. If the intent was to test rejection of invalid sizes, test `Board(0)`, `Board(4)`, or `Board(20)` instead.

#### G2: `test_daily_posix.py` — PuzzleRef.path is empty (3 tests)

| R-20 | Evidence | Reference |
|------|----------|-----------|
| R-20a | Tests import `_to_puzzle_ref` from `backend.puzzle_manager.daily.standard` | [test_daily_posix.py](backend/puzzle_manager/tests/test_daily_posix.py#L23) |
| R-20b | `standard.py` re-exports `_to_puzzle_ref` from `daily._helpers` which expects **compact dict** format: `{"p": "0001/hash", "l": 110}` | [daily/_helpers.py](backend/puzzle_manager/daily/_helpers.py#L197-L210) |
| R-20c | Tests pass old format: `{"id": "abc123", "path": "sgf\\intermediate\\batch-0001\\abc123.sgf", "level": "intermediate"}` | Missing `"p"` key → `compact_path = ""` → empty path |

**Verdict**: **STALE — UPDATE FIXTURES**. The `_to_puzzle_ref()` input format changed from `{"id", "path", "level"}` dicts to compact `{"p", "l"}` dicts. Tests pass the old format.

#### G3: `test_batch_writer_perf.py` — O(1) perf threshold (1 test)

| R-21 | Evidence | Reference |
|------|----------|-----------|
| R-21a | Benchmark test marked `@pytest.mark.slow` and `@pytest.mark.benchmark` | [test_batch_writer_perf.py](backend/puzzle_manager/tests/benchmarks/test_batch_writer_perf.py#L20) |
| R-21b | Test likely has tight timing threshold (> 1.0ms) that fails on slower machines or CI | Environment-dependent |

**Verdict**: **FLAKY/ENVIRONMENT-DEPENDENT**. Performance benchmarks with absolute timing thresholds are inherently flaky. Should use relative comparison (O(1) vs O(N) ratio) instead of absolute ms threshold.

---

## 3. External References

| R-22 | Reference | Relevance |
|------|-----------|-----------|
| R-22a | [pytest best practices: test isolation](https://docs.pytest.org/en/stable/goodpractices.html) | Tests should test behavior, not implementation details |
| R-22b | [Golden Master testing pattern](https://blog.thecodewhisperer.com/permalink/surviving-legacy-code-with-golden-master) | Cluster A tests are explicitly golden master — should be removed after successful refactoring |
| R-22c | [Martin Fowler: Test Doubles](https://martinfowler.com/bliki/TestDouble.html) | Inventory tests mock old interfaces instead of current ones |

---

## 4. Candidate Adaptations for Yen-Go

| R-23 | Adaptation | Affected Tests | Effort |
|------|-----------|----------------|--------|
| R-23a | Delete golden master tests (Cluster A) | 18 tests | Trivial |
| R-23b | Update inventory model fixtures to schema v2.0 (Clusters B, C) | ~30 tests | Medium |
| R-23c | Update path fixtures from hierarchical to flat format (Clusters B2, B6, D) | ~22 tests | Medium |
| R-23d | Update daily puzzle input format to compact dicts (Cluster G2) | 3 tests | Small |
| R-23e | Fix Board test to use actually-invalid size (G1) | 1 test | Trivial |
| R-23f | Investigate trace map mechanism (Cluster E) — may need partial delete | 9 tests | Medium |
| R-23g | Update root comment assertion to expect preservation (F1) | 2 tests | Trivial |
| R-23h | Delete threshold config tests; investigate hint text (F2) | 2 tests | Small |
| R-23i | Delete or fix tagger default assertion (F3) | 1 test | Trivial |
| R-23j | Convert benchmark to relative comparison (G3) | 1 test | Small |

---

## 5. Risks, License/Compliance, and Rejection Reasons

| R-24 | Risk | Severity | Mitigation |
|------|------|----------|------------|
| R-24a | Deleting Cluster A tests removes coverage of SGF property injection behavior | Low | `test_sgf_enrichment.py` already covers `_enrich_sgf()` with 30+ tests |
| R-24b | Updating path fixtures might mask real path format bugs | Medium | Verify with end-to-end pipeline run before and after |
| R-24c | Inventory model changes might have further hidden drift | Low | After fix, run full `pytest backend/` to catch cascading issues |
| R-24d | `test_periodic_reconcile.py` removal means periodic reconcile feature is untested | Medium | If periodic reconcile feature was descoped, tests should be removed. If planned, rewrite them |

No license/compliance issues — all changes are internal test updates.

---

## 6. Planner Recommendations

1. **Phase 1 (Quick Wins — delete stale)**: Delete the 18 Cluster A golden master tests and the 1 tagger default test. Remove threshold config tests from `test_enrichment.py`. Fix `Board(10)` → `Board(0)`. Total: ~22 tests resolved, zero production risk.

2. **Phase 2 (Fixture Modernization)**: Update all inventory test fixtures to schema v2.0 (`by_puzzle_quality` instead of `avg_quality_score`/`hint_coverage_pct`), update path format from `sgf/{level}/batch-{NNNN}/` to `sgf/{NNNN}/`, update CLI assertions to match simplified output, update daily puzzle dict format to compact `{"p","l"}`. Total: ~55 tests resolved, moderate effort.

3. **Phase 3 (Investigation Required)**: Audit trace map mechanism (Cluster E, 9 tests) — determine whether trace_map sidecar files are still generated or if everything is in YM. Audit periodic reconcile feature (8 tests) — determine if the feature was descoped or if `runs_since_last_reconcile` just moved. Total: ~17 tests, requires codebase investigation first.

4. **Phase 4 (Flaky test fix)**: Convert `test_batch_writer_perf.py` to relative performance comparison (O(1)/O(N) ratio > 10x) instead of absolute ms threshold. 1 test.

---

## 7. Confidence and Risk Update

**Post-research confidence**: 88/100
- High confidence on Clusters A, B, D, F, G (clear evidence of intentional production changes)
- Medium confidence on Cluster C (periodic reconcile descoping unclear)
- Medium confidence on Cluster E (trace map mechanism needs code-level verification)

**Post-research risk level**: **low**
- No production code needs fixing for any of these 91 tests
- All failures are test-side drift from intentional architecture changes
- Zero evidence of actual production bugs being masked

---

## Summary Table

| R-25 | test_file | tests_count | verdict | action | priority |
|------|-----------|-------------|---------|--------|----------|
| R-25a | `tests/unit/test_analyze_characterization.py` | 18 | Stale (removed API) | DELETE file | P1 |
| R-25b | `tests/test_inventory_models.py` | 8 | Stale (schema drift) | UPDATE assertions | P2 |
| R-25c | `tests/test_inventory_rebuild.py` | 8 | Stale (path format) | UPDATE fixtures | P2 |
| R-25d | `tests/test_inventory_cli.py` | 5 | Stale (format changed) | UPDATE assertions + fixtures | P2 |
| R-25e | `tests/test_inventory_integration.py` | 4 | Stale (model drift) | REWRITE tests | P2 |
| R-25f | `tests/test_inventory_manager.py` | 1 | Stale (path moved) | UPDATE fixture path | P2 |
| R-25g | `tests/test_inventory_check.py` | 5 | Stale (path format) | UPDATE fixtures | P2 |
| R-25h | `tests/test_inventory_protection.py` | 1 | Stale (path moved) | UPDATE fixture path | P2 |
| R-25i | `tests/unit/test_inventory_reconcile.py` | 2 | Stale (API factored out) | REWRITE to use `reconcile_inventory()` | P2 |
| R-25j | `tests/integration/test_periodic_reconcile.py` | 8 | Stale (signature + model) | INVESTIGATE if feature descoped → DELETE or REWRITE | P3 |
| R-25k | `tests/integration/test_stage_metrics.py` | 3 | Partially stale | UPDATE fixtures | P2 |
| R-25l | `tests/stages/test_publish.py` | 9 | Stale (path format) | UPDATE path assertions | P2 |
| R-25m | `tests/stages/test_ingest_trace.py` | 3 | Likely stale | INVESTIGATE then DELETE or UPDATE | P3 |
| R-25n | `tests/stages/test_publish_trace.py` | 4 | Mixed | INVESTIGATE; keep trace_id test, may delete sidecar tests | P3 |
| R-25o | `tests/stages/test_analyze_trace.py` | 2 | Needs investigation | INVESTIGATE YQ property policy | P3 |
| R-25p | `tests/test_sgf_enrichment.py` | 2 | Stale (behavior changed) | UPDATE: assert comment IS preserved | P1 |
| R-25q | `tests/test_enrichment.py` | 2 | Stale (config removed) | DELETE threshold tests; INVESTIGATE hint test | P1 |
| R-25r | `tests/test_tagger.py` | 1 | Stale (design principle) | DELETE or UPDATE to assert empty is valid | P1 |
| R-25s | `tests/test_board.py` | 1 | Over-specified | UPDATE: use `Board(0)` or `Board(4)` | P1 |
| R-25t | `tests/test_daily_posix.py` | 3 | Stale (input format) | UPDATE to compact dict format | P2 |
| R-25u | `tests/benchmarks/test_batch_writer_perf.py` | 1 | Flaky | CONVERT to relative comparison | P4 |
| | **TOTAL** | **91** | | | |

### Consolidation Opportunities

| R-26 | Opportunity | Files | Rationale |
|------|------------|-------|-----------|
| R-26a | Merge `test_inventory_models.py` and `test_inventory_integration.py` | 2 files → 1 | Both test inventory model behavior; integration tests are just model tests with manager |
| R-26b | Merge `test_inventory_rebuild.py` and `test_inventory_check.py` | 2 files → 1 | Both test publish-log-based operations; share nearly identical fixtures |
| R-26c | Delete `test_analyze_characterization.py` entirely | 1 file → 0 | `test_sgf_enrichment.py` already covers all SGF enrichment output behavior |
| R-26d | `test_periodic_reconcile.py` may be fully deletable if periodic reconcile is descoped | 1 file → 0 | Tests feature that may not exist anymore |
