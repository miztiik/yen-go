# Tasks: Remove Dormant Dedup Infrastructure

**Feature:** Remove Dormant Dedup Infrastructure  
**Source:** [30-plan.md](30-plan.md) (architecture), [20-analysis.md](20-analysis.md) (blast radius)  
**Correction Level:** 3 (Multiple Files) — 5 files deleted, 8 files edited  
**Backward Compatibility:** NOT required (user decision: republish = reset)  
**Rollback Dependency:** NONE (verified — `rollback.py` has zero dedup references)  
**Last Updated:** 2026-03-05

---

## Phase 1 — Setup & Delete Dormant Modules

> **Goal:** Remove all dormant dedup source files. Zero production imports — safe to delete.

- [ ] T001 [P] Delete dormant dedup registry module at backend/puzzle_manager/core/dedup_registry.py
- [ ] T002 [P] Delete dormant position fingerprint module at backend/puzzle_manager/core/position_fingerprint.py
- [ ] T003 [P] Delete dedup registry unit tests at backend/puzzle_manager/tests/unit/test_dedup_registry.py
- [ ] T004 [P] Delete dedup metadata merge unit tests at backend/puzzle_manager/tests/unit/test_dedup_metadata_merge.py
- [ ] T005 [P] Delete position fingerprint unit tests at backend/puzzle_manager/tests/unit/test_position_fingerprint.py

---

## Phase 2 — Foundational Production Code Edits

> **Goal:** Remove fingerprint infrastructure from production code that other files depend on. Must complete before Phase 3+.

- [ ] T006 Remove all fingerprint support from trace_utils in backend/puzzle_manager/core/trace_utils.py
  - Remove `fingerprint: str = ""` parameter from `build_pipeline_meta()` signature and docstring Args
  - Remove `if fingerprint: meta["fp"] = fingerprint` block
  - Remove `fingerprint: str = ""` field from `PipelineMeta` dataclass and "dedup fingerprints" from docstring
  - Remove `fingerprint=data.get("fp", "")` from `parse_pipeline_meta_extended()` return statement

- [ ] T007 Remove fingerprint kwarg from analyze stage in backend/puzzle_manager/stages/analyze.py (depends on T006)
  - Remove `fingerprint=existing.fingerprint` from `build_pipeline_meta()` call at line 592

- [ ] T008 [P] Remove dedup-registry cleanup block from backend/puzzle_manager/pipeline/cleanup.py
  - Remove dedup-registry.json deletion block (lines 424-436)
  - Remove `"dedup-registry.json"` from `paths_cleared` list (line 469)

---

## Phase 3 — Test File Edits (depends on Phase 2)

> **Goal:** Remove test assertions and methods that reference removed fingerprint/dedup infrastructure.

- [ ] T009 [P] Remove fingerprint test methods and assertions from backend/puzzle_manager/tests/unit/test_pipeline_meta_extended.py
  - Remove `test_fingerprint_included` test method (line 22)
  - Remove `test_fingerprint_empty_omitted` test method (line 52)
  - Remove `fingerprint=` args from builder calls and `assert meta.fingerprint` assertions in roundtrip tests
  - Update module docstring to remove "fingerprint" mention (line 4)

- [ ] T010 [P] Remove dedup-registry test methods and fixture data from backend/puzzle_manager/tests/integration/test_cleanup.py
  - Remove `test_cleanup_clears_dedup_registry` test method (line 432)
  - Remove `test_cleanup_dedup_registry_dry_run` test method (line 458)
  - Remove dedup-registry.json creation from `populated_collection` fixture (lines 302-303)

---

## Phase 4 — Config, Docs & Log Messages (parallel with Phase 3)

> **Goal:** Clean documentation and config references to removed infrastructure.

- [ ] T011 [P] Remove fp(fingerprint) from YM description in config/sgf-property-policies.json
  - Change `"Sub-fields: t(trace_id), f(filename), i(run_id), fp(fingerprint), ct(content_type 1-3), tc(trivial_capture)"` to `"Sub-fields: t(trace_id), f(filename), i(run_id), ct(content_type 1-3), tc(trivial_capture)"`

- [ ] T012 [P] Remove phantom dedup log references from docs/architecture/backend/logging.md
  - Line 24: Remove ", dedup aggregate stats" from INFO level Usage column
  - Line 48: Remove `Dedup: skipping {file}` bullet entirely
  - Line 83: Remove dedup grep pattern from the command example

- [ ] T013 [P] Rename misleading log message in backend/puzzle_manager/stages/publish.py
  - Line 212: Change `"Skipping duplicate SGF content {content_hash}"` to `"Skipping already-published SGF {content_hash}"`

---

## Phase 5 — Verification (depends on all prior phases)

> **Goal:** Validate that all changes are clean, no stale references remain, and all tests pass.

- [ ] T014 Run pytest validation: `pytest -m "not (cli or slow)"` — all tests must pass
- [ ] T015 Run stale reference grep across backend/ for `dedup_registry|position_fingerprint|DedupRegistry|DedupEntry|DedupResult|DedupStats` — must return zero matches
- [ ] T016 Run stale reference grep across config/ and docs/ for `fp(fingerprint)` — must return zero matches

---

## Dependencies

```
Phase 1 (T001-T005)  ──► Phase 2 (T006-T008)  ──► Phase 3 (T009-T010) ──► Phase 5 (T014-T016)
                                                 \                        /
                                                  ► Phase 4 (T011-T013) ─╯
```

| Dependency          | Reason                                                                                                               |
| ------------------- | -------------------------------------------------------------------------------------------------------------------- |
| T007 → T006         | T007 removes `fingerprint=existing.fingerprint` kwarg; T006 removes the parameter from `build_pipeline_meta()`       |
| T009 → T006         | T009 removes test assertions that reference `PipelineMeta.fingerprint` field and `build_pipeline_meta(fingerprint=)` |
| T010 → T008         | T010 removes test methods that exercise the deleted dedup-registry cleanup block                                     |
| T011-T013 → Phase 2 | Docs/config edits only depend on design decision, not code; parallel with Phase 3                                    |
| T014-T016 → \*      | Final verification depends on all code and doc changes being complete                                                |

## Parallel Execution Batches

| Batch | Tasks                        | Parallelizable | Notes                                          |
| ----- | ---------------------------- | -------------- | ---------------------------------------------- |
| 1     | T001, T002, T003, T004, T005 | All [P]        | Independent file deletions                     |
| 2     | T006, T008                   | Both [P]       | Independent production edits (different files) |
| 3     | T007                         | Sequential     | Must follow T006 (parameter removed)           |
| 4     | T009, T010, T011, T012, T013 | All [P]        | Independent test/config/doc edits              |
| 5     | T014, T015, T016             | Sequential     | Verification must run after all changes        |

## Implementation Strategy

- **MVP scope:** Phases 1-2 (delete dormant modules + production code edits) — immediately reduces dead code
- **Incremental delivery:** Each phase is independently testable via `pytest -m unit`
- **Rollback:** Git revert of the commit(s) restores all files; zero data migration needed
- **Risk:** Low — all removed code has zero production callers (verified by grep)

## Summary

| Metric                    | Value                                                           |
| ------------------------- | --------------------------------------------------------------- |
| Total tasks               | 16                                                              |
| Files deleted             | 5                                                               |
| Files edited              | 8                                                               |
| Parallel batches          | 5                                                               |
| Parallel opportunities    | 13 of 16 tasks are [P]-eligible                                 |
| Independent test criteria | `pytest -m "not (cli or slow)"` passes + grep returns 0 matches |
| Suggested MVP             | Phases 1-2 (T001-T008)                                          |
| Test command              | `pytest -m "not (cli or slow)"`                                 |
