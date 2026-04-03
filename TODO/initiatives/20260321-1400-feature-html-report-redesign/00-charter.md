# Charter: HTML Report Redesign

**Initiative**: `20260321-1400-feature-html-report-redesign`
**Parent**: `20260318-1400-feature-enrichment-lab-production-readiness` (Work Stream K)
**Date**: 2026-03-21

## Goals

1. Replace markdown report generator with self-contained HTML report
2. Close all 6 K.3 spec gaps (S1 trace_id, S2 relative path, S3 avg queries, S5 versioned glossary, S6 real thresholds, S9 correlation completeness)
3. Add before/after SGF property comparison table per puzzle
4. Add per-puzzle analysis narrative with real AiAnalysisResult data
5. Create navigation shell (`index.html`) for log directory browsing
6. Update all existing report tests (78+ tests, 201 regression)

## Non-Goals

- No dual-format (markdown + HTML) support
- No external JS/CSS dependencies
- No changes to toggle precedence logic
- No changes to correlator logic
- No changes to production boundary (D14 remains OFF by default)

## Constraints

| C-ID | Constraint |
|------|-----------|
| C1 | All code inside `tools/puzzle-enrichment-lab/` |
| C2 | Non-blocking try/except in CLI wiring preserved |
| C3 | Production profile → report OFF by default (D14) |
| C4 | No external JS/CSS dependencies (self-contained HTML) |
| C5 | Toggle precedence (4-level: CLI→env→profile→config) unchanged |
| C6 | AGENTS.md updated in same commit as structural changes |

## Acceptance Criteria

- AC-1: All 6 K.3 spec gaps closed (S1, S2, S3, S5, S6, S9)
- AC-2: Before/after table renders for single and batch enrichment
- AC-3: Analysis narrative populated from `AiAnalysisResult` fields
- AC-4: Navigation shell discovers and lists all `enrichment-report-*.html` files
- AC-5: All existing report tests pass with updated assertions
- AC-6: HTML opens in browser with correct colors and layout
- AC-7: AGENTS.md report/ section reflects new architecture
