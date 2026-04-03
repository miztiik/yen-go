# Tasks: Enrichment Lab Log Viewer

> Initiative: `20260321-1800-feature-enrichment-log-viewer`
> Selected Option: **OPT-1 — Module-Per-Section Architecture**
> Last Updated: 2026-03-21

---

## Dependency Graph

```
T1 (scaffold) ──→ T2 (parser) ──→ T3 (header+summary) ──→ T6 (search)
                       │                    │
                       ├─→ T4 (timing) ─────┤
                       │                    │
                       ├─→ T5 (pipeline) ───┤
                       │                    │
                       └─→ T7 (puzzles) ────┘
                                            │
T8 (reference) ────────────────────────────→┤  [P] parallel with T3-T7
                                            │
T9 (sample.jsonl) ─────────────────────────→┤  [P] parallel with T3-T8
                                            │
                                            ↓
                                     T10 (integration)
                                            │
                                            ↓
                                     T11 (dark mode)
                                            │
                                            ↓
                                     T12 (docs)
                                            │
                                            ↓
                                     T13 (manual test)
```

---

## Task List

### T1: Scaffold — Create directory structure and HTML shell
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/index.html`
- **Scope**:
  - Create `log-viewer/` directory
  - Create `index.html` with:
    - `<meta charset="utf-8">`, viewport meta
    - CSP meta tag: `default-src 'self'; script-src 'self' https://cdn.jsdelivr.net cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'`
    - Chart.js CDN `<script>` tag with SRI integrity hash
    - `<link rel="stylesheet" href="styles.css">`
    - `<script src="app.js" defer></script>`
    - Drop zone container `<div id="drop-zone">`
    - Section containers: `<div id="s1-header">`, `<div id="s2-summary">`, etc.
    - Hidden file input `<input type="file" accept=".jsonl,.log,.txt">`
    - "Load sample" button
  - Create empty `app.js` with module structure skeleton (IIFE + section function stubs)
  - Create `styles.css` with:
    - CSS custom properties for colors (light theme)
    - Drop zone styles (border, drag-over highlight)
    - Section container base styles
    - Badge styles (green/amber/red/blue)
    - Responsive layout basics
- **Dependencies**: None
- **Level**: 2

---

### T2: JSONL Parser + EventStore
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`
- **Scope**:
  - `parseJSONL(text)` → array of event objects (line-by-line JSON.parse, skip invalid lines)
  - `buildEventStore(events)` → EventStore object:
    - Index puzzles by `trace_id` (group session_start → enrichment_begin → enrichment_complete → enrichment_end)
    - Compute aggregate stats: status counts, level distribution, tag distribution, tier distribution
    - Compute timing aggregates: per-stage totals, averages, max
    - Extract run metadata: `run_id`, first/last timestamps
  - `escapeHtml(str)` utility function
  - `formatDuration(seconds)` utility function
  - File drop zone event handlers: `dragover`, `dragleave`, `drop`, click-to-browse, "Load sample" fetch
  - On file load: parse → build store → call `renderDashboard(store)`
- **Dependencies**: T1
- **Level**: 2

---

### T3: S1 Header + S2 Summary Sections
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`
- **Scope**:
  - `renderHeader(store, container)`:
    - File name, run ID, timestamp
    - Total puzzle count badge
    - Total duration
  - `renderSummary(store, container)`:
    - Status distribution: doughnut Chart.js chart (accepted/flagged/rejected/error)
    - Level distribution: horizontal bar chart
    - Tag frequency: horizontal bar chart (top 15 tags)
    - Tier distribution: small doughnut chart with tier descriptions
    - Total/average KataGo queries
  - Graceful degradation: if `level` missing → omit level chart, show CTA
- **Dependencies**: T2
- **Level**: 2

---

### T4: S3 Timing Section [P]
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`, `tools/puzzle-enrichment-lab/log-viewer/styles.css`
- **Scope**:
  - `renderTiming(store, container)`:
    - Aggregate stacked bar chart: all stages, proportional timing (Chart.js stacked bar)
    - Per-stage average timing: bar chart with thermal coloring
    - Table fallback: stage name, total time, avg time, max time, % of total
  - Graceful degradation: if no `phase_timings` in any puzzle → show CTA
- **Dependencies**: T2
- **Level**: 2
- **[P]** parallel with T3, T5, T7

---

### T5: S4 Pipeline Journey Swim-Lane [P]
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`, `tools/puzzle-enrichment-lab/log-viewer/styles.css`
- **Scope**:
  - `renderPipelineJourney(store, container)`:
    - Create SVG element with horizontal node layout
    - 11 fixed stages: Parse, Solve-Path, Analyze, Validate, Refutation, Difficulty, Assembly, Technique, Instinct, Teaching, SGF-Writeback
    - Each node: rounded rect + stage name + status icon (✓/✗/⊘/—)
    - Connecting lines between nodes (solid for executed, dotted for skipped)
    - Color coding: green=completed, red=failed, gray=skipped, light-gray=no data
    - If batch mode: show aggregate (% of puzzles that passed each stage)
    - Tooltip on hover: stage name, timing, pass/fail count
  - Derive stage status from `phase_timings` keys and puzzle `status`
  - Graceful degradation: if no stage data → show all nodes as "no data" with CTA
- **Dependencies**: T2
- **Level**: 3 (custom SVG rendering)
- **[P]** parallel with T3, T4, T7

---

### T6: S6 Search Section
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`, `tools/puzzle-enrichment-lab/log-viewer/styles.css`
- **Scope**:
  - `renderSearch(store, container)`:
    - Text input with debounced handler (300ms)
    - `searchLog(query, events)` → SearchResult[]
    - Case-insensitive substring match across all JSON fields (stringified)
    - Display: line number, matched field highlighted, surrounding context
    - Max 200 results with "showing X of Y matches" counter
    - Result click → expand/highlight corresponding puzzle in S5
  - Styles: search input, result list, match highlighting
- **Dependencies**: T2, T3 (needs S5 puzzle detail IDs for click-to-expand)
- **Level**: 2

---

### T7: S5 Puzzle Details Section [P]
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`, `tools/puzzle-enrichment-lab/log-viewer/styles.css`
- **Scope**:
  - `renderPuzzleDetails(store, container)`:
    - Batch mode: collapsible `<details>` per puzzle, sorted by trace_id
    - Single mode: expanded card
    - Per puzzle:
      - Header: puzzle_id + status badge + level badge + tier badge
      - Phase timing: inline stacked bar (Chart.js small bar or CSS bar)
      - Tags: tag chips
      - Hints count, refutation count, queries used
      - Enrichment tier with human-readable description tooltip
      - Per-stage query count (if available)
    - Lazy rendering: detail content created on first `<details>` toggle event
  - Styles: puzzle card, tag chips, tier badges with tooltips
- **Dependencies**: T2
- **Level**: 2
- **[P]** parallel with T3, T4, T5

---

### T8: S7 Reference Section [P]
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`
- **Scope**:
  - `renderReference(container)`:
    - Glossary terms with `id` anchors (for hyperlinks from other sections)
    - Terms: Accepted, Flagged, Rejected, Error, Enrichment Tier (1/2/3), Phase Timing, Policy Prior, Policy Entropy, Composite Score, Solution Depth, Refutation, Co-correct, Technique Tags, Trace ID, Run ID
    - Enrichment tier detailed descriptions with examples
    - Status legend with color badges
    - JSONL event format quick reference
  - Hyperlink integration: other sections use `<a href="#ref-term">` to link to glossary
- **Dependencies**: None (static content)
- **Level**: 1
- **[P]** parallel with T3-T7

---

### T9: Sample JSONL File [P]
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/sample.jsonl`
- **Scope**:
  - 4-5 puzzles covering:
    - 1 accepted (full data with all `phase_timings`)
    - 1 flagged (partial data, KataGo disagrees)
    - 1 rejected (high delta_wr)
    - 1 error (parse failure)
    - 1 accepted with minimal data (testing graceful degradation)
  - Each puzzle: session_start → enrichment_begin → enrichment_complete → enrichment_end
  - Realistic `phase_timings`, `technique_tags`, `level` values
  - Valid JSONL format (one JSON object per line)
- **Dependencies**: None
- **Level**: 1
- **[P]** parallel with T3-T8

---

### T10: Integration — Wire All Sections + Polish
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/app.js`, `tools/puzzle-enrichment-lab/log-viewer/index.html`
- **Scope**:
  - `renderDashboard(store)` orchestrator: calls all section renderers in order
  - Drop zone collapse after load (show filename + "Load another" link)
  - Chart.js CDN fallback: detect if `Chart` is undefined → show table fallbacks
  - Error handling: show user-friendly error for invalid JSONL
  - Section navigation: sticky header with section links
  - Glossary hyperlinks: wire `<a href="#ref-term">` across all sections
  - Performance: verify 1K-puzzle JSONL loads in <2s on modern browser
- **Dependencies**: T3, T4, T5, T6, T7, T8, T9
- **Level**: 2

---

### T11: Dark Mode CSS
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/styles.css`
- **Scope**:
  - `@media (prefers-color-scheme: dark)` block
  - Override all CSS custom properties for dark palette
  - Chart.js color scheme: read colors from CSS custom properties at chart creation time
  - SVG pipeline journey: inherit colors from CSS custom properties
  - Test: toggle OS dark mode, verify all sections readable
- **Dependencies**: T10
- **Level**: 1

---

### T12: Documentation
- **Files**: `tools/puzzle-enrichment-lab/log-viewer/README.md`, `tools/puzzle-enrichment-lab/AGENTS.md`
- **Scope**:
  - `README.md`:
    - Quick start: "Open index.html in a browser, drop a .jsonl file"
    - "Load sample" quick start alternative
    - JSONL event format reference table
    - Dashboard section descriptions
    - Known limitations (missing data, CDN dependency)
    - Vendoring Chart.js for offline use instructions
  - `AGENTS.md` update:
    - Add `log-viewer/` to directory structure section
    - Brief description: "Standalone HTML+JS JSONL log viewer"
- **Dependencies**: T10
- **Level**: 1

---

### T13: Manual Test Pass
- **Files**: None (verification only)
- **Scope**:
  - Open `index.html` in Chrome and Firefox
  - Drop `sample.jsonl` → verify all 7 sections render
  - Drop empty file → verify error message
  - Drop non-JSONL → verify error message
  - Click "Load sample" → verify loads demo data
  - Test search with known string → verify highlighting
  - Expand/collapse puzzle details → verify lazy rendering
  - Verify dark mode (toggle OS setting)
  - Verify `file://` protocol works (no CORS errors)
  - Verify Chart.js loads from CDN and renders correctly
  - Performance: drop 1K-puzzle JSONL, verify <2s load
- **Dependencies**: T11, T12
- **Level**: 0

---

## Summary

| Task | Description | Dependencies | Parallel | Level |
|------|------------|-------------|----------|-------|
| T1 | Scaffold: directory + HTML shell + empty JS/CSS | — | — | 2 |
| T2 | JSONL parser + EventStore + file handling | T1 | — | 2 |
| T3 | S1 Header + S2 Summary charts | T2 | — | 2 |
| T4 | S3 Timing charts | T2 | [P] with T3,T5,T7 | 2 |
| T5 | S4 Pipeline Journey SVG | T2 | [P] with T3,T4,T7 | 3 |
| T6 | S6 Search | T2, T3 | — | 2 |
| T7 | S5 Puzzle Details | T2 | [P] with T3,T4,T5 | 2 |
| T8 | S7 Reference glossary | — | [P] with T3-T7 | 1 |
| T9 | Sample JSONL file | — | [P] with T3-T8 | 1 |
| T10 | Integration + polish | T3-T9 | — | 2 |
| T11 | Dark mode CSS | T10 | — | 1 |
| T12 | Documentation (README + AGENTS.md) | T10 | — | 1 |
| T13 | Manual test pass | T11, T12 | — | 0 |

**Execution order**: T1 → T2 → [T3, T4, T5, T7] parallel + [T8, T9] parallel → T6 → T10 → T11 → T12 → T13
