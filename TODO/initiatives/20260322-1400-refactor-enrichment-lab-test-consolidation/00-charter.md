# Charter — Enrichment Lab Test Suite Consolidation

> Last Updated: 2026-03-22
> Initiative ID: 20260322-1400-refactor-enrichment-lab-test-consolidation
> Correction Level: **Level 3 (Multiple Files)** — 5+ files migrated, 60+ files touched for sys.path cleanup

## Problem Statement

The `tools/puzzle-enrichment-lab/tests/` directory (79 test files, 600+ tests) has accumulated organizational debt:

1. **5 sprint-named files** (`test_sprint[1-5]_fixes.py`) whose names reference development process rather than the subsystem under test — making discoverability poor
2. **`test_remediation_sprints.py`** has a process-oriented name that confusingly suggests overlap with the sprint files (they are actually disjoint — different gap ID namespaces)
3. **61 files contain identical `sys.path.insert(0, str(_LAB_DIR))` boilerplate** — a DRY violation since conftest.py already handles this
4. **Perf test files** (`test_perf_100.py`, `test_perf_1k.py`, `test_perf_10k.py`) duplicate utility functions (`_prepare_input`, `_get_referee_model`, `_parse_statuses`)

## Goals

| ID | Goal | Measurable Outcome |
|----|------|--------------------|
| G1 | Migrate sprint file tests to domain-specific files | 18 test classes from 5 sprint files relocated to 13 target files by domain |
| G2 | Delete empty sprint files after migration | 5 fewer files in tests/ directory |
| G3 | Rename `test_remediation_sprints.py` | Renamed to `test_ai_solve_remediation.py` — clarifies scope |
| G4 | Eliminate sys.path boilerplate DRY violation | Zero `sys.path.insert` calls in individual test files |
| G5 | Extract shared perf utilities | Duplicated helpers consolidated into conftest.py or shared module |
| G6 | Zero test regressions | Exact same test count before and after; zero assertion changes |

## Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Merge refutation quality phase files (A/B/C/D) | Distinct PI improvement sets — no overlap |
| NG2 | Reorganize into subdirectories | Too disruptive; naming improvement is sufficient |
| NG3 | Modify test assertions or logic | Pure relocation — no behavioral changes |
| NG4 | Delete perf 100/1K/10K files | They are real implementations, not placeholders (CR-ALPHA finding) |
| NG5 | Change teaching comment test organization | Already well-layered (unit/integration/embedding/config) |

## Constraints

| ID | Constraint |
|----|------------|
| C1 | Zero test regressions — `pytest --co -q` count must be identical before and after |
| C2 | Zero assertion changes — only file location, imports, and sys.path boilerplate change |
| C3 | Docstring/gap-ID provenance preserved in migrated test classes |
| C4 | No interaction with DRY initiative (20260321-2100) artifacts beyond acknowledging conftest.py |
| C5 | AGENTS.md updated if test infrastructure changes |
| C6 | One commit per sprint file migration (5 atomic commits for Lane 1) |

## Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC1 | `test_sprint[1-5]_fixes.py` no longer exist | `ls tests/test_sprint*.py` returns empty |
| AC2 | `test_remediation_sprints.py` renamed to `test_ai_solve_remediation.py` | File exists at new path |
| AC3 | Test count unchanged | `pytest --co -q` output identical before/after |
| AC4 | No `sys.path.insert` in any test file except conftest.py | `grep -r "sys.path.insert" tests/ \| grep -v conftest` returns empty |
| AC5 | All migrated test classes retain original docstrings with gap IDs | Manual review of migrated classes |
| AC6 | Zero assertion changes in migrated tests | Diff shows only import/location changes |
| AC7 | Shared perf utilities in one location | `_prepare_input` defined in exactly 1 file |
| AC8 | All tests pass | `pytest tests/ -m "not slow" -q` green |
