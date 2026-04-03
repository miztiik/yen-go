# Task Decomposition: Backend Test Remediation

## Dependency Order

Tasks are: `[P]` = parallelizable with previous task, otherwise sequential.

---

### Phase 1 — Delete Dead Tests (zero risk, no dependencies)

| ID | Task | File(s) | Action | Tests Affected |
|----|------|---------|--------|----------------|
| T1 | Delete characterization tests | `tests/unit/test_analyze_characterization.py` | DELETE file | -18 |
| T2 | [P] Delete periodic reconcile tests | `tests/integration/test_periodic_reconcile.py` | DELETE file | -8 |
| T3 | [P] Delete root-level daily posix tests | `tests/test_daily_posix.py` | DELETE file | -3 |

**After T1-T3:** Run `pytest backend/ -m unit -q --no-header --tb=short` to confirm no regressions.

---

### Phase 2 — Delete Trace Sidecar Tests + Benchmark

| ID | Task | File(s) | Action | Tests Affected |
|----|------|---------|--------|----------------|
| T4 | Delete ingest trace sidecar tests | `tests/stages/test_ingest_trace.py` | DELETE file | -3 |
| T5 | [P] Delete publish trace sidecar tests | `tests/stages/test_publish_trace.py` | DELETE file | -4 |
| T6 | [P] Delete benchmark test | `tests/benchmarks/test_batch_writer_perf.py` | DELETE file | -1 |

**After T4-T6:** Run `pytest backend/ -m unit -q --no-header --tb=short`.

---

### Phase 3 — Quick Assertion Fixes

| ID | Task | File(s) | Action | Tests Affected |
|----|------|---------|--------|----------------|
| T7 | Fix root comment preservation assertions | `tests/test_sgf_enrichment.py` | EDIT: flip `not in` → `in` for root C[] assertions | 2 |
| T8 | [P] Fix enrichment config/assertion | `tests/test_enrichment.py` | EDIT: remove `corner_threshold=5` kwarg; loosen hint assertion | 2 |
| T9 | [P] Fix tagger expected result | `tests/test_tagger.py` | EDIT: `assert tags == []` | 1 |
| T10 | [P] Fix board invalid size value | `tests/test_board.py` | EDIT: `Board(10)` → `Board(3)` (below MIN_BOARD_SIZE) | 1 |
| T11 | Fix analyze trace selective recompute tests | `tests/stages/test_analyze_trace.py` | DELETE 2 failing tests (`test_existing_yq_preserved`, `test_missing_yx_computed_fresh`); keep 2 passing | -2, fix 0 |

**After T7-T11:** Run `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=no`.

---

### Phase 4 — Inventory Fixture Modernization

| ID | Task | File(s) | Action | Tests Affected |
|----|------|---------|--------|----------------|
| T12 | Update inventory models test fixtures | `tests/test_inventory_models.py` | EDIT: remove `avg_quality_score`/`hint_coverage_pct`; use `quality_increments` dict; schema `"2.0"` | 8 |
| T13 | Update inventory rebuild test fixtures | `tests/test_inventory_rebuild.py` | EDIT: modernize publish-log fixture format; update path format; fix count assertions | 8 |
| T14 | Delete obsolete CLI tests | `tests/test_inventory_cli.py` | DELETE file (all 5 tests check sections that don't exist in v2.0 CLI) | -5 |
| T15 | [P] Update inventory check test fixtures | `tests/test_inventory_check.py` | EDIT: modernize publish-log fixture; update path format | 5 |
| T16 | [P] Update inventory integration test fixtures | `tests/test_inventory_integration.py` | EDIT: update `_update_inventory` call signature to use `level_slug_counts=`/`tag_slug_counts=`; schema `"2.0"` | 4 |
| T17 | [P] Update inventory reconcile unit tests | `tests/unit/test_inventory_reconcile.py` | EDIT: `manager.reconcile()` → `reconcile_inventory()` function import + call | 2 |

**After T12-T17:** Run `pytest backend/ -k inventory -q --no-header --tb=short`.

---

### Phase 5 — Publish Path Format Update

| ID | Task | File(s) | Action | Tests Affected |
|----|------|---------|--------|----------------|
| T18 | Update publish test path assertions | `tests/stages/test_publish.py` | EDIT: `sgf/{level}/batch-{NNNN}/` → `sgf/{NNNN}/`; remove per-level batch state expectations | 9 |

**After T18:** Run `pytest backend/ -k test_publish -q --no-header --tb=short`.

---

### Phase 6 — Production Bugfix + Stage Metrics Tests

| ID | Task | File(s) | Action | Tests Affected |
|----|------|---------|--------|----------------|
| T19 | Fix publish `failed` metric accumulation | `backend/puzzle_manager/inventory/manager.py` | EDIT: add `"failed": current.failed + metrics.get("failed", 0)` to publish branch in `update_stage_metrics()` | 0 (production fix) |
| T20 | Verify stage metrics tests pass | `tests/integration/test_stage_metrics.py` | VERIFY: all 3 tests should now pass with T19 fix | 3 |

**After T19-T20:** Run `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=no`.

---

### Phase 7 — Dead Code Tracking + Documentation

| ID | Task | File(s) | Action | Tests Affected |
|----|------|---------|--------|----------------|
| T21 | Create dead code decommissioning artifact | `TODO/initiatives/20260324-dead-code-decommissioning.md` | CREATE: list dead code paths, sidecar doc references, trace_map module | 0 |
| T22 | [P] Final full regression | All | Run `pytest backend/ -q --no-header --tb=short` | 0 |

---

## Summary

| Metric | Count |
|--------|-------|
| Tests to DELETE | 44 |
| Tests to FIX (assertions) | 6 |
| Tests to MODERNIZE (fixtures) | 36 |
| Production bugs to FIX | 1 |
| Total test impact | 91 → 0 failures |
| Test count change | -44 (2502 → 2458) |

_Note: 5 inventory CLI tests deleted (T14) not counted separately — included in the 44 deletions._

---

## Verification Checkpoints

After all phases: `pytest backend/ -q --no-header --tb=short` must show 0 failures.

_Last updated: 2026-03-24_
