# Analysis — Backend Dead Code Cleanup Post-Recovery

**Initiative**: 20260324-1500-feature-backend-dead-code-cleanup  
**Selected Option**: OPT-1 (3-Phase Risk-Layered)  
**Last Updated**: 2026-03-24

---

## 1. Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | **95** |
| Risk Level | **medium** (broad deletion scope, but all dead code verified) |
| Research Invoked | Yes — 2 passes (code audit + docs audit) |
| Research Required | Yes — planning confidence <70 before first pass resolved to 95 after both passes |

### Confidence Score Breakdown

| Factor | Deduction | Notes |
|--------|-----------|-------|
| Architecture seams unclear | -0 | Fully mapped via AGENTS.md + 2 research passes |
| Viable approaches with unknown tradeoffs | -0 | Options clearly differentiated |
| External precedent needed | -0 | Pure deletion, no external patterns |
| Quality/performance/security impact uncertain | -0 | Zero runtime change — deletion only |
| Test strategy unclear | -0 | Pytest gates with markers verified |
| Rollout/rollback impact unclear | -5 | Broad scope (48 files) warrants caution |

**Final Score**: 100 - 5 = **95**

---

## 2. Cross-Artifact Consistency

| Check ID | Artifact Pair | Finding | Status |
|----------|---------------|---------|--------|
| CC-1 | Charter AC-1..AC-13 ↔ Tasks T1..T34 | All 13 acceptance criteria mapped to specific tasks and verification gates | ✅ |
| CC-2 | Charter §5 Scope ↔ Plan §1-§3 | All scope items present in plan phases. 21 orphan tests (updated from ~18 estimate) | ✅ |
| CC-3 | Charter §6 Phasing ↔ Plan phases | 3-phase structure matches. Phase 2 updated with `__init__.py` edit per RC-1 | ✅ |
| CC-4 | Clarifications Q1-Q12 ↔ Plan decisions | All answers reflected in plan (delete aggressively, no compat, argparse fix, etc.) | ✅ |
| CC-5 | Options OPT-1 ↔ Plan structure | Plan implements OPT-1 exactly: core→adapters→docs | ✅ |
| CC-6 | Governance must-hold ↔ Tasks | (1) T7-T14 co-delete with T1-T6 ✅ (2) T21 atomic with T17 ✅ (3) T15/T22/T31 pytest gates ✅ (4) T22 sources cmd ✅ | ✅ |
| CC-7 | Research R-1..R-15 ↔ Plan scope | All research findings assigned to specific plan sections | ✅ |
| CC-8 | Research D-1..D-23 ↔ Tasks T24-T30 | All doc findings mapped to Phase 3 tasks | ✅ |
| CC-9 | `status.json` ↔ actual state | Phase states, decisions, governance gates all current | ✅ |

---

## 3. Ripple Effects Analysis

### 3.1 Upstream Dependencies (What deleted code depends on)

| Impact ID | Direction | Area | Risk | Mitigation | Owner Task | Status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | `core/trace_map.py` — trace_registry.py depends on it | None | trace_registry is being deleted, not trace_map | T3 | ✅ addressed |
| RE-2 | upstream | `core/content_db.py` — dedup_registry depends on it | None | dedup_registry is being deleted, not content_db | T2 | ✅ addressed |
| RE-3 | upstream | `paths.py` — runtime.py depends on it | None | runtime.py is being deleted, not paths.py | T5 | ✅ addressed |
| RE-4 | upstream | `pm_logging.py` — logging.py depends on it | None | logging.py is being deleted, not pm_logging | T5 | ✅ addressed |
| RE-5 | upstream | `core/classifier.py` — level_mapper depends on it | None | level_mapper is being deleted, not classifier | T6 | ✅ addressed |
| RE-6 | upstream | `_base.py`, `_registry.py` — dead adapters import from `base.py`, `registry.py` | None | Dead adapters AND old infra both deleted | T16, T17 | ✅ addressed |

### 3.2 Downstream Consumers (What depends on deleted code)

| Impact ID | Direction | Area | Risk | Mitigation | Owner Task | Status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-7 | downstream | `adapters/__init__.py` imports `UrlAdapter` from `url.py` | **HIGH** | Edit `__init__.py` to remove import in same phase (RC-1) | T21 | ✅ addressed |
| RE-8 | downstream | 21 orphan test files import dead modules | Medium | Co-delete all orphan tests with source in Phase 1 | T7-T14 | ✅ addressed |
| RE-9 | downstream | `maintenance/__init__.py` exists but directory becomes empty | Low | Delete entire `maintenance/` directory | T4 | ✅ addressed |
| RE-10 | downstream | `tests/models/__init__.py` exists but directory becomes empty | Low | Delete entire `tests/models/` directory | T10 | ✅ addressed |
| RE-11 | downstream | `stages/protocol.py` has `views_dir` referencing dead views system | Low | Remove property in Phase 3 | T23 | ✅ addressed |
| RE-12 | downstream | AGENTS.md references dead modules, wrong CLI framework | Low | Fix in Phase 3 | T26 | ✅ addressed |
| RE-13 | downstream | 18 docs reference dead systems | Low | Fix in Phase 3 | T24-T30 | ✅ addressed |

### 3.3 Lateral/Cross-Module Effects

| Impact ID | Direction | Area | Risk | Mitigation | Owner Task | Status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-14 | lateral | Python package-vs-module resolution: `local.py` + `local/` package | Very Low | Verified: Python resolves package first. Deleting flat file is transparent. | T19 | ✅ addressed |
| RE-15 | lateral | Python package-vs-module resolution: `sanderland.py` + `sanderland/` | Very Low | Same as RE-14. Verified. | T19 | ✅ addressed |
| RE-16 | lateral | Python package-vs-module resolution: `travisgk.py` + `travisgk/` | Very Low | Same as RE-14. Verified. | T19 | ✅ addressed |
| RE-17 | lateral | Python package-vs-module resolution: `kisvadim.py` + `kisvadim/` | Very Low | Same as RE-14. Verified. | T19 | ✅ addressed |
| RE-18 | lateral | `core/__init__.py` exports — dead modules NOT exported | None | Verified: `core/__init__.py` does not re-export any dead modules | — | ✅ addressed |
| RE-19 | lateral | `models/__init__.py` — does NOT import `models/trace.py` | None | Verified: safe to delete `trace.py` without editing `models/__init__.py` | T3 | ✅ addressed |
| RE-20 | lateral | `test_adapters.py` (T14) imports dead adapter base/registry but is in tests/ not in `tests/adapters/` | None | File correctly identified as orphan, deleted in Phase 1 | T14 | ✅ addressed |
| RE-21 | lateral | CI/CD pipeline — test count will decrease | None | Expected behavior. Test gates verify zero failures, not constant count. | T15, T22, T31 | ✅ addressed |

---

## 4. Coverage Map

### 4.1 Acceptance Criteria → Task Traceability

| AC-ID | Criterion | Task(s) | Status |
|-------|-----------|---------|--------|
| AC-1 | All 13 dead production modules deleted | T1-T6 | ✅ mapped |
| AC-2 | All orphan test files deleted | T7-T14 | ✅ mapped |
| AC-3 | Old adapter infrastructure deleted | T16 | ✅ mapped |
| AC-4 | Orphaned flat-file adapters deleted | T17-T19 | ✅ mapped |
| AC-5 | `adapters/ogs/` ghost directory deleted | T20 | ✅ mapped |
| AC-6 | 5 obsolete docs deleted/archived | T24, T25 | ✅ mapped |
| AC-7 | Critical + medium stale docs fixed | T26-T30 | ✅ mapped |
| AC-8 | AGENTS.md says argparse, not Typer | T26 | ✅ mapped |
| AC-9 | `views_dir` property removed | T23 | ✅ mapped |
| AC-10 | pytest passes with 0 failures | T15, T22, T31, T32 | ✅ mapped |
| AC-11 | ruff passes with 0 errors | T15, T22, T31, T33 | ✅ mapped |
| AC-12 | No production behavior change | T15, T22, T31 (gates) | ✅ mapped |
| AC-13 | `adapters/__init__.py` UrlAdapter removed | T21 | ✅ mapped |

**Unmapped ACs**: None.

### 4.2 Governance Must-Hold Constraints → Task Traceability

| Constraint | Task(s) | Status |
|------------|---------|--------|
| MH-1: Orphan test co-deletion | T7-T14 (same phase as T1-T6) | ✅ |
| MH-2: `__init__.py` edit atomic with `url.py` | T21 depends on T17 (same phase) | ✅ |
| MH-3: Pytest gate each phase | T15, T22, T31 | ✅ |
| MH-4: `sources` command in Phase 2 | T22 | ✅ |

### 4.3 Research Findings → Task Traceability

| Finding | Category | Task(s) |
|---------|----------|---------|
| R-1..R-13: Dead production modules | Code | T1-T6 |
| R-14: Dual adapter registry | Code | T16-T21 |
| R-15: 4 duplicate adapters | Code | T19 |
| R-16: Ghost `ogs/` dir | Code | T20 |
| D-1..D-5: Obsolete docs | Docs | T24, T25 |
| D-6..D-8: AGENTS.md errors | Docs | T26 |
| D-9..D-14: Stale doc content | Docs | T27-T30 |

---

## 5. Severity-Based Findings

| Finding ID | Severity | Description | Mitigation | Status |
|------------|----------|-------------|------------|--------|
| F1 | **Critical** | `adapters/__init__.py` line 27 imports `UrlAdapter` from dead `url.py`. Deletion without edit causes ImportError at pipeline startup. | T21 edits `__init__.py` in same phase as T17 `url.py` deletion (RC-1). | ✅ addressed |
| F2 | **High** | `maintenance/` directory becomes empty after dead file deletion. Leaving empty `__init__.py` is misleading. | T4 deletes entire directory. Zero production imports verified. | ✅ addressed |
| F3 | **High** | `tests/models/` directory becomes empty after orphan test deletion. | T10 deletes entire directory. | ✅ addressed |
| F4 | **Medium** | AGENTS.md claims "Typer CLI" but code uses `argparse`. Misleads AI agents working in the codebase. | T26 fixes all 3 occurrences (lines 26, 175, dep table). | ✅ addressed |
| F5 | **Medium** | 4 flat-file adapters shadow their package counterparts. Python resolves packages first, but dual presence is confusing. | T19 deletes flat files. Package resolution verified for all 4. | ✅ addressed |
| F6 | **Low** | `StageContext.views_dir` property references dead views system. | T23 removes 4-line property. | ✅ addressed |
| F7 | **Low** | 18 docs have stale content referencing dead systems. | T24-T30 fix in Phase 3. | ✅ addressed |
| F8 | **Info** | `validation_stats.py` is NOT dead — it's actively imported by `stages/ingest.py` and `core/__init__.py`. Correctly excluded from scope. | N/A — correctly excluded. | ✅ verified |
| F9 | **Info** | Trace-related test files (`test_trace_map.py`, `test_trace_e2e.py`, etc.) test LIVE modules (`core.trace_map`, `core.trace_utils`). Correctly excluded from orphan list. | N/A — correctly excluded. | ✅ verified |

---

## 6. Unmapped Tasks

All tasks in `40-tasks.md` are mapped to at least one acceptance criterion or governance constraint. No orphan tasks.

---

## 7. Test Impact Summary

| Phase | Tests Deleted | Tests Modified | Tests Added | Expected Net Change |
|-------|---------------|---------------|-------------|---------------------|
| Phase 1 | 21 test files (~5,163 lines) | 0 | 0 | Decrease in collected tests |
| Phase 2 | 0 | 0 | 0 | No change |
| Phase 3 | 0 | 0 | 0 | No change |

**Key insight**: No new tests needed because this initiative only deletes dead code. The remaining test suite already covers all live production code.

---

## 8. Documentation Impact Summary

| Phase | Docs Deleted | Docs Archived | Docs Fixed | Docs Created |
|-------|-------------|---------------|------------|-------------|
| Phase 1 | 0 | 0 | 0 | 0 |
| Phase 2 | 0 | 0 | 0 | 0 |
| Phase 3 | 2 | 3 | ~9 | 0 |
