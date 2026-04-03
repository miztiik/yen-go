# Analysis: HTML Report Redesign

**Initiative**: `20260321-1400-feature-html-report-redesign`
**Date**: 2026-03-21
**Planning Confidence Score**: 92
**Risk Level**: medium
**Research Invoked**: No (score ≥ 70, all extension points clear)

---

## Coverage Map

| K.3 spec gap | task_id | status |
|-------------|---------|--------|
| S1: trace_id count | T-HR-5 | ✅ addressed |
| S2: relative path | T-HR-6 | ✅ addressed |
| S3: avg queries | T-HR-7 | ✅ addressed |
| S5: versioned glossary | T-HR-9 | ✅ addressed |
| S6: real thresholds | T-HR-10 | ✅ addressed |
| S9: completeness | T-HR-12 | ✅ addressed |

## New Feature Coverage

| feature | task_id(s) | status |
|---------|-----------|--------|
| Before/after SGF property table | T-HR-14, T-HR-15, T-HR-16 | ✅ addressed |
| Analysis narrative | T-HR-17 | ✅ addressed |
| Per-puzzle collapsible sections | T-HR-18 | ✅ addressed |
| Navigation shell | T-HR-20, T-HR-21 | ✅ addressed |
| HTML format + inline CSS | T-HR-4 | ✅ addressed |
| Token .md → .html | T-HR-19 | ✅ addressed |

## Constraint Coverage

| constraint | task_id | status |
|-----------|---------|--------|
| C1: All code in tools/puzzle-enrichment-lab/ | All | ✅ verified |
| C2: Non-blocking try/except | T-HR-2, T-HR-3, T-HR-21 | ✅ preserved |
| C3: Production OFF by default | N/A (toggle unchanged) | ✅ preserved |
| C4: No external JS/CSS | T-HR-4, T-HR-20 | ✅ inline only |
| C5: Toggle precedence unchanged | N/A (toggle.py untouched) | ✅ preserved |
| C6: AGENTS.md updated | T-HR-28 | ✅ addressed |

## Test Coverage

| test file | task_id | action |
|-----------|---------|--------|
| test_report_generator.py | T-HR-23 | Rewrite assertions |
| test_report_token.py | T-HR-24 | Update .md → .html |
| test_report_autotrigger.py | T-HR-25 | Verify (mock-based) |
| test_cli_report.py | T-HR-26 | Verify (argparse only) |
| test_report_correlator.py | N/A | No changes |
| test_report_toggle.py | N/A | No changes |
| test_report_index_generator.py | T-HR-27 | New file |

---

## Ripple Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | CLI `run_enrich` — new params passed to generator | low | All new params optional with defaults | T-HR-2 | ✅ addressed |
| RE-2 | downstream | CLI `_run_batch_async` — accumulates results during loop | low | Append to list, no behavior change to loop | T-HR-3 | ✅ addressed |
| RE-3 | lateral | `build_report_path()` consumers — extension change .md → .html | medium | Only called from cli.py report blocks; already wrapped in try/except | T-HR-19 | ✅ addressed |
| RE-4 | downstream | Test assertions — all markdown checks become HTML checks | medium | Systematic test rewrite in T-HR-23 | T-HR-23 | ✅ addressed |
| RE-5 | lateral | AGENTS.md — must reflect new architecture | low | Updated in same commit | T-HR-28 | ✅ addressed |
| RE-6 | upstream | `report/correlator.py` — unchanged, generator still calls it | none | No changes needed | N/A | ✅ no action |
| RE-7 | upstream | `report/toggle.py` — unchanged, CLI still calls it | none | No changes needed | N/A | ✅ no action |
| RE-8 | lateral | Parent initiative status.json — sub-work completed | low | Update execution log | N/A | ✅ addressed |
| RE-9 | downstream | .lab-runtime/logs/ directory — now contains .html + index.html | low | index.html regenerated each run, old .md files ignored | T-HR-20 | ✅ addressed |

---

## Findings

| finding_id | severity | description | resolution |
|------------|----------|-------------|------------|
| F1 | low | Old `.md` report files in `.lab-runtime/logs/` will remain alongside new `.html` files | Acceptable — stale files, operator can clean up manually. Not worth adding cleanup logic. |
| F2 | low | `AiAnalysisResult` doesn't have a direct `ko_context` field for YK property | Extract from original SGF; if not in result, keep original value. T-HR-15 handles this. |
| F3 | info | All 6 K.3 gaps traced to specific tasks with clear implementation approach | No action needed. |
| F4 | info | No new dependencies introduced (OPT-1 constraint satisfied) | No action needed. |
| F5 | low | Batch mode accumulates `list[AiAnalysisResult]` in memory | Results already in memory during batch loop; no additional peak memory. |

---

## Unmapped Tasks Check

All charter goals and acceptance criteria are mapped to tasks:
- AC-1 (K.3 gaps): T-HR-5, T-HR-6, T-HR-7, T-HR-9, T-HR-10, T-HR-12
- AC-2 (before/after): T-HR-14, T-HR-15, T-HR-16, T-HR-18
- AC-3 (narrative): T-HR-17, T-HR-18
- AC-4 (navigation shell): T-HR-20, T-HR-21
- AC-5 (tests pass): T-HR-23, T-HR-24, T-HR-25, T-HR-26, T-HR-27, T-HR-29
- AC-6 (browser rendering): T-HR-4 (CSS), manual verification
- AC-7 (AGENTS.md): T-HR-28

No unmapped tasks or acceptance criteria found.
