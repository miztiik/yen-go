# Charter — Enrichment Lab Test Suite Deep Audit & Consolidation (Phase 2)

> Last Updated: 2026-03-24
> Initiative ID: 20260324-2200-feature-enrichment-lab-test-audit
> Correction Level: **Level 3 (Multiple Files)** — 4 files deleted, ~12 files consolidated, .vscode/tasks.json updated
> Prior Initiative: 20260322-1400-refactor-enrichment-lab-test-consolidation (completed — handled sprint files, sys.path DRY, remediation rename)

## Problem Statement

After the prior consolidation initiative (20260322-1400), the enrichment lab test suite still has 84 test files (~27,400 lines, ~1,700+ test functions). A deep audit identified:

1. **4 fully duplicated detector test files** (2,238 lines) — the old frequency-based naming (`_common`, `_high_frequency`, `_intermediate`, `_lower_frequency`) was not deleted when renamed to priority-based (`_priority1`, `_priority2`, `_priority3`, `_priority4_5_6`). Both copies run every time, doubling detector test execution.
2. **52 YAGNI config snapshot tests** in `test_feature_activation.py` that assert hardcoded config default values, breaking on every intentional config change.
3. **7 config test files** with overlapping Pydantic validation tests that the framework already guarantees.
4. **4 refutation quality phase files** (A/B/C/D) sharing identical boilerplate that could be one file.
5. **Stale `.vscode/tasks.json` references** to individual phase files.

## Goals

| ID | Goal | Measurable Outcome |
|----|------|--------------------|
| G1 | Delete 4 duplicate detector test files | 2,238 lines removed, 87 duplicate test executions eliminated |
| G2 | Consolidate config snapshot tests | `test_feature_activation.py` reduced to ~5 critical threshold guards (C9 invariants) |
| G3 | Merge refutation quality phases A-D | 4 files → 1 file, ~250 lines boilerplate saved |
| G4 | Consolidate config test files | 6 config test files → 2 files |
| G5 | Update .vscode/tasks.json references | All task references point to valid files |
| G6 | Zero test regressions | Same test pass count before and after |

## Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Merge perf test files (perf_smoke/100/1k/10k) | Governance panel ruled: keep separate for CI tier selection |
| NG2 | Reorganize into subdirectories | Prior initiative excluded; still too disruptive |
| NG3 | Modify test assertions or logic | Pure consolidation — no behavioral changes |
| NG4 | Change teaching comment test organization | Already well-layered per prior initiative |
| NG5 | Redistribute test_implementation_review.py | Medium risk, low reward — defer to future initiative |

## Constraints

| ID | Constraint |
|----|------------|
| C1 | Zero test regressions — `pytest --co -q` count must match minus exact duplicate count |
| C2 | Zero assertion changes — only file merges, imports, and deletions |
| C3 | `TestThresholdConservation` (C9 invariants: t_good=0.05, t_bad=0.15, t_hotspot=0.30) MUST be preserved |
| C4 | `.vscode/tasks.json` updated in same commit as file renames/deletions |
| C5 | AGENTS.md test section updated |
| C6 | All `@pytest.mark` markers preserved |

## Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC1 | 4 frequency-named detector files deleted | `test_detectors_{common,high_frequency,intermediate,lower_frequency}.py` gone |
| AC2 | `test_feature_activation.py` deleted entirely | File no longer exists (per Q2=A) |
| AC3 | `test_refutation_quality.py` exists as merged file | Single file with Phases A-D classes preserved |
| AC4 | No duplicate test IDs in pytest collection | `pytest --co -q` has no duplicate test names |
| AC5 | `.vscode/tasks.json` references valid files | All referenced test file paths exist |
| AC6 | All enrichment lab tests pass | `pytest tests/ -m "not slow"` green |
| AC7 | AGENTS.md test section updated | Reflects new file names |

> **See also**:
> - [Prior initiative](../20260322-1400-refactor-enrichment-lab-test-consolidation/00-charter.md) — Sprint files, sys.path DRY
> - [Research brief](../20260324-research-enrichment-lab-test-audit/15-research.md) — Full 84-file audit
