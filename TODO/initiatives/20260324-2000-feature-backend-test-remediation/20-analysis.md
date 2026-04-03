# Analysis: Backend Test Remediation

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 85/100 |
| Risk Level | low |
| Research Invoked | Yes (Code-Reviewer-Alpha, Code-Reviewer-Beta) |

**Score breakdown:** Started at 100; -10 for fixture modernization scope (moderate uncertainty on exact fixture shape); -5 for production bug side-effect risk (mitigated by isolated single-field change).

---

## Findings

| ID | Severity | Category | Finding | Resolution |
|----|----------|----------|---------|------------|
| F1 | High | Stale tests | 18 characterization tests call removed `_inject_yengo_props()` — pure dead weight | Delete (T1) |
| F2 | High | Stale tests | 8 periodic reconcile tests for descoped feature | Delete (T2) |
| F3 | Medium | Duplicate | `tests/test_daily_posix.py` duplicates `tests/integration/test_daily_posix.py` with wrong imports | Delete root copy (T3) |
| F4 | Medium | Dead code | `core/trace_map.py` — `write_trace_map()` and `read_trace_map()` have zero callers | Track for decommissioning (T21) |
| F5 | Medium | Stale tests | 7 trace sidecar tests for dead mechanism (ingest/publish no longer write sidecars) | Delete (T4, T5) |
| F6 | Low | Env-dependent | Benchmark test `test_batch_writer_perf.py` fails on non-standard environments | Delete (T6) |
| F7 | High | Schema drift | 34 inventory tests use v1.0 fixtures (`avg_quality_score`, `hint_coverage_pct`, `quality_scores`) against v2.0 models | Modernize fixtures (T12-T17) |
| F8 | Medium | Schema drift | 5 CLI tests assert sections (`Stage Metrics:`, `Error Rates:`, `Audit:`) not in v2.0 output | Delete (T14) |
| F9 | Medium | Path drift | 9 publish tests use old hierarchical format `sgf/{level}/batch-{NNNN}/` vs flat `sgf/{NNNN}/` | Update assertions (T18) |
| F10 | High | Production bug | `update_stage_metrics()` publish branch doesn't accumulate `failed` count | Fix production code (T19) |
| F11 | Low | Assertion drift | 2 enrichment tests expect root comment removal (production preserves by default) | Fix assertions (T7) |
| F12 | Low | Assertion drift | 1 tagger test expects `life-and-death` fallback (production returns empty: precision-over-recall) | Fix assertion (T9) |
| F13 | Low | Assertion drift | 1 board test uses `Board(10)` as invalid (valid range is 5-19) | Fix value (T10) |
| F14 | Low | Config drift | 2 enrichment tests reference removed `corner_threshold` parameter | Fix config construction (T8) |
| F15 | Medium | Selective recompute | 2 analyze-trace tests fail due to test setup not triggering policy gates properly | Delete 2 failing, keep 2 passing (T11) |

---

## Coverage Map

| Category | Failures | Delete | Fix | Modernize | Production Fix |
|----------|----------|--------|-----|-----------|----------------|
| A: Characterization | 18 | 18 | — | — | — |
| B: Inventory schema | 34 | 5 | — | 29 | — |
| C: Periodic reconcile + Stage metrics | 11 | 8 | — | — | 3 (T19 enables) |
| D: Publish paths | 9 | — | — | 9 | — |
| E: Trace sidecars | 9 | 7 | — | — | — |
| F: Assertion drift | 6 | — | 6 | — | — |
| G: Environment/duplicates | 4 | 4 | — | — | — |
| **Total** | **91** | **42** | **6** | **38** | **3** (+1 prod fix) |

*Note: 2 selective recompute tests counted under E (trace). 5 CLI tests counted under B (inventory).*

---

## Ripple-Effects Table

| ID | Direction | Area | Risk | Mitigation | Owner Task | Status |
|----|-----------|------|------|------------|------------|--------|
| R1 | Downstream | Test count reduction (-44) | Low | All deleted tests verified as testing dead/descoped features | T1-T6, T14 | ✅ addressed |
| R2 | Lateral | Inventory manager production fix | Low | Single field addition; no consumers depend on `failed` being 0 | T19 | ✅ addressed |
| R3 | Downstream | Dead code (trace_map.py) still importable | Low | Tracked for decommissioning initiative; no runtime impact | T21 | ✅ addressed |
| R4 | Lateral | Docs reference trace map sidecars | Low | Tracked for decommissioning; docs are informational only | T21 | ✅ addressed |
| R5 | Upstream | Schema v2.0 fixture updates must match production models | Medium | Each fixture validated against `inventory/models.py` Pydantic types | T12-T17 | ✅ addressed |
| R6 | Lateral | Publish path tests must match `BatchWriter._write_batch()` format | Medium | Cross-reference `stages/publish.py` format strings during T18 | T18 | ✅ addressed |

---

## Dead Code Inventory (for decommissioning initiative)

| ID | Path | Type | Evidence | Risk if Deleted |
|----|------|------|----------|----------------|
| DC1 | `backend/puzzle_manager/core/trace_map.py` | Module (full file) | No imports in `stages/ingest.py`, `stages/publish.py`, `stages/analyze.py` | None — no callers |
| DC2 | `docs/architecture/backend/integrity.md` | Doc section | References sidecar trace map architecture | None — informational only |
| DC3 | `docs/architecture/backend/inventory-operations.md` | Doc section | May reference trace map reconciliation | None — informational only |
| DC4 | `backend/puzzle_manager/core/trace_map.py::read_trace_map()` | Function | Zero callers | None |
| DC5 | `backend/puzzle_manager/core/trace_map.py::write_trace_map()` | Function | Zero callers | None |

---

## Code Reviewer Findings Integration

### CR-ALPHA

| ID | Finding | Accepted | Impact |
|----|---------|----------|--------|
| CRA-1 | Phase order correct | ✅ | None |
| CRA-2 | Cat B scope verified | ✅ | None |
| CRA-3 | `test_stage_metrics` misdiagnosis corrected — tests call `update_stage_metrics()` not `_update_inventory` | ✅ | Reclassified to production bug + test verification (T19-T20) |
| CRA-4 | Cat F scope confirmed | ✅ | None |
| CRA-5 | Cat G count corrected (4 not 5; 3 daily_posix + 1 benchmark) | ✅ | Fixed in task count |

### CR-BETA

| ID | Finding | Accepted | Impact |
|----|---------|----------|--------|
| CRB-1 | DRY violation: duplicate test files in root `tests/` vs `tests/unit/`+`tests/integration/` | ✅ | `test_daily_posix.py` handled (T3); broader consolidation deferred |
| CRB-2 | `trace_map.py` confirmed safe to decommission | ✅ | Tracked (T21) |
| CRB-3 | Inventory test files could consolidate | Deferred | Out of scope for this initiative |
| CRB-4 | Publish log fixture format needs careful alignment | ✅ | Noted in T13, T15 |
| CRB-5 | Test marker coverage gaps | Deferred | Tracked but not remediated here |

---

## Unmapped Tasks

None — all 91 failures are traced to specific tasks T1-T22.

---

## User Decision Record

| Question | Answer | Impact |
|----------|--------|--------|
| Q1: Periodic reconcile | A: Delete 8 tests | T2 |
| Q2: Trace map sidecars | B: Delete tests + track dead code | T4, T5, T21 |
| Q3: Consolidation scope | A: Same initiative | All tasks |
| Q4: Schema version | A: Remove v1.0, update to v2.0 | T12-T17 |
| Q5: CLI stage metrics | Delete 5 tests — sections don't exist in v2.0 CLI | T14 |
| Q6: Selective recompute | Delete 2 failing tests (setup issue), keep 2 passing | T11 |
| Category A | Delete completely | T1 |
| Category B | Fix schema drift | T12-T17 |
| Category C | Fix as needed | T2, T19-T20 |
| Category D | Update path assertions | T18 |
| Category E | Delete sidecar tests + track dead code | T4, T5, T21 |
| Category F | Update assertions | T7-T10 |
| Category G | Drop benchmark; delete daily_posix dupe | T3, T6 |

_Last updated: 2026-03-24_
