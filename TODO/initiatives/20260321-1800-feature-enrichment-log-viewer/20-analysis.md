# Analysis: Enrichment Lab Log Viewer

> Initiative: `20260321-1800-feature-enrichment-log-viewer`
> Last Updated: 2026-03-21

---

## Planning Confidence

| Metric | Value | Notes |
|--------|-------|-------|
| Planning Confidence Score | 85 | Post-clarification, all decisions resolved |
| Risk Level | medium | New greenfield tool, but JSONL data gaps are real |
| Research Invoked | No | Score ≥ 70, charting decision resolved via clarification |

---

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|-----------|------------|--------|
| RE-1 | upstream | JSONL log format (log_config.py, enrich_single.py) | Low | Viewer reads whatever is present; graceful degradation for missing fields. No log format changes required. | T2 (parser handles missing fields) | ✅ addressed |
| RE-2 | upstream | Chart.js CDN (cdn.jsdelivr.net) | Low | SRI integrity hash + table fallback if CDN unavailable | T1 (SRI hash), T10 (fallback) | ✅ addressed |
| RE-3 | downstream | AGENTS.md (enrichment lab architecture map) | Low | Must update AGENTS.md with log-viewer directory entry | T12 | ✅ addressed |
| RE-4 | lateral | Existing Python report generator (report/generator.py) | None | No changes to Python report. Viewer is additive. Both coexist. | N/A | ✅ addressed |
| RE-5 | lateral | Frontend Preact app | None | No imports. No shared code. Complete isolation per C5. | N/A | ✅ addressed |
| RE-6 | lateral | Backend pipeline (puzzle_manager/) | None | No imports. Log file is only interface. Per C5, C6. | N/A | ✅ addressed |
| RE-7 | downstream | Future JSONL enrichment initiative | Low | Viewer CTAs identify which fields would unlock more features. This creates implicit requirements for a future JSONL enrichment initiative. | T2 (CTA messages list specific fields) | ✅ addressed |
| RE-8 | lateral | Test infrastructure | None | Manual testing only. No impact on pytest or vitest suites. | T13 | ✅ addressed |

---

## Charter ↔ Plan Coverage

| Charter Item | Plan Coverage | Task Coverage | Status |
|-------------|--------------|--------------|--------|
| G1: Standalone HTML+JS viewer | OPT-1 architecture, 4-file structure | T1 (scaffold) | ✅ |
| G2: Proper charting (not CSS hacks) | Chart.js integration (D1) | T3, T4, T7 | ✅ |
| G3: Pipeline journey flow | SVG swim-lane (S4 section) | T5 | ✅ |
| G4: Batch mode with collapsible details | `<details>` per puzzle, lazy render (D4) | T7 | ✅ |
| G5: Pure-JS text search | Search section (S6) | T6 | ✅ |
| G6: Glossary/reference with hyperlinks | Reference section (S7) + anchor links | T8, T10 | ✅ |
| G7: Human-readable tier descriptions | Tier description table + tooltip badges | T7, T8 | ✅ |
| G8: Per-stage query usage | Stage breakdown in S3 + per-puzzle in S5 | T4, T7 | ✅ |
| C1: Zero runtime backend | Static HTML+JS | All | ✅ |
| C2: No build step | Direct index.html open | T1 | ✅ |
| C3: File drop zone | D3 design | T2 | ✅ |
| C4: Self-contained | CDN chart lib | T1 | ✅ |
| C5: No backend/frontend imports | Isolated directory | All | ✅ |
| C6: Log file only input | D6, EventStore from JSONL only | T2 | ✅ |
| C7: Location in enrichment lab | `tools/puzzle-enrichment-lab/log-viewer/` | T1 | ✅ |
| AC1: Drop file → dashboard | End-to-end flow | T1→T10 | ✅ |
| AC2: Proper charting | Chart.js | T3, T4 | ✅ |
| AC3: Gate-by-gate flow | SVG swim-lane | T5 | ✅ |
| AC4: Batch mode | Collapsible `<details>` + stats | T7, T3 | ✅ |
| AC5: Search function | Text search with highlighting | T6 | ✅ |
| AC6: Tier descriptions | Tooltips + badges | T7, T8 | ✅ |
| AC7: Glossary hyperlinks | Anchor links from sections to S7 | T8, T10 | ✅ |
| AC8: Per-stage query counts | Timing section + puzzle details | T4, T7 | ✅ |
| AC9: Works with known events | Parser handles all 4 event types | T2, T9 | ✅ |
| AC10: 1K puzzles without freezing | Lazy rendering + debounced search | T7, T6, T10 | ✅ |

---

## Constraint ↔ Task Traceability

| Constraint | Implementing Tasks | Verification |
|-----------|-------------------|-------------|
| XSS prevention (must-hold #4) | T2 (escapeHtml), T5 (createElementNS), T7 (textContent) | T13 (manual inspection) |
| file:// compatibility (must-hold #1) | T1 (no ES modules), T2 (no fetch for data) | T13 (open via file://) |
| Chart.js CDN + SRI (must-hold #2-3) | T1 (script tag + integrity) | T13 (verify load) |
| Dark mode (Q3) | T11 | T13 (toggle OS) |
| Sample JSONL (Q6) | T9 | T13 (load sample) |
| 1K puzzle performance (Q7) | T7 (lazy render), T6 (debounce), T10 (verify) | T13 (perf test) |

---

## Findings

| ID | Severity | Finding | Recommendation |
|----|----------|---------|---------------|
| F1 | Info | JSONL logs currently lack per-stage query counts (`queries_used` is puzzle-level only). T4/T7 per-stage query display will show CTA for missing data. | Accept: viewer degrades gracefully. Future JSONL enrichment initiative can add stage-level query tracking. |
| F2 | Info | `phase_timings` keys may vary across enrichment lab versions (stages renamed/added). Parser should treat stage names as dynamic, not hardcoded. | T2: EventStore should discover stage names from data, not from a static list. T5 pipeline journey has a fixed expected list but handles unknown stages. |
| F3 | Info | "Load sample" button uses `fetch('sample.jsonl')` which fails on `file://` protocol in some browsers (CORS on local files). | T2: Use XMLHttpRequest as fallback, or read sample inline as a JS variable. Recommend inline approach for guaranteed `file://` compatibility. |
| F4 | Low | Chart.js v4 CDN URL must use UMD build (not ESM) since we're loading via `<script>` tag. The correct URL is `chart.umd.min.js`, not `chart.min.js`. | T1: Verify CDN URL uses UMD build. |
| F5 | Info | The `sample.jsonl` "Load sample" feature has a design tension with `file://` constraint (F3). Inlining sample data as a JS constant is the safest approach but increases `app.js` size by ~2KB. | T9: Embed sample data as `const SAMPLE_DATA = '...'` in `app.js` rather than separate file. Keep `sample.jsonl` for documentation but load inline. |
| F6 | Info | No automated tests planned. Acceptable for v1 greenfield dev tool, but if the viewer grows, OPT-2 refactor would enable unit testing. | Documented in plan as future upgrade path. |

---

## Unmapped Items

None. All charter goals, non-goals, constraints, and acceptance criteria are traced to tasks.
