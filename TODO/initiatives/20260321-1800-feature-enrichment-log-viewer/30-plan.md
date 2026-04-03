# Plan: Enrichment Lab Log Viewer

> Initiative: `20260321-1800-feature-enrichment-log-viewer`
> Selected Option: **OPT-1 — Module-Per-Section Architecture**
> Last Updated: 2026-03-21

---

## 1. Architecture Overview

### File Structure

```
tools/puzzle-enrichment-lab/log-viewer/
├── index.html          # HTML shell: drop zone, section containers, CDN script tags
├── app.js              # All application logic (~600-800 LOC)
├── styles.css          # All styles including dark mode via prefers-color-scheme
├── sample.jsonl        # Demo JSONL file (3-5 puzzles with varied statuses)
└── README.md           # Usage instructions, JSONL event format reference
```

### Data Flow

```
User drops .jsonl file
  ↓
FileReader API reads text content
  ↓
parseJSONL(text) → array of event objects
  ↓
buildEventStore(events) → EventStore object
  ↓
renderDashboard(store) → DOM updates per section
  ↓
Interactive: search, collapse/expand, chart tooltips
```

### EventStore Object (in-memory data model)

```javascript
{
  // Raw events
  events: [],              // All parsed JSONL lines

  // Indexed data (derived during buildEventStore)
  puzzles: Map<traceId, {
    traceId, puzzleId, sourceFile, status,
    level, tags, hintsCount, refutations,
    phaseTimings, queriesUsed, enrichmentTier,
    startEvent, completeEvent, endEvent
  }>,

  // Aggregate statistics
  stats: {
    totalPuzzles, accepted, flagged, rejected, errors,
    totalDuration, avgDuration,
    totalQueries, avgQueries,
    levelDistribution: Map<level, count>,
    tagDistribution: Map<tag, count>,
    tierDistribution: Map<tier, count>,
    stageTimingAggregates: Map<stage, {total, avg, max}>
  },

  // Metadata
  runId, sessionStart, sessionEnd,
  fileName    // Original dropped filename
}
```

### Dashboard Sections

| Section | Function | Content | Chart.js Usage |
|---------|----------|---------|---------------|
| S1: Header | `renderHeader(store)` | File name, run ID, timestamp, puzzle count badge | None |
| S2: Summary | `renderSummary(store)` | Status distribution, level distribution, tag frequency | Doughnut chart (status), horizontal bar (levels) |
| S3: Timing | `renderTiming(store)` | Aggregate phase timing breakdown, per-stage averages | Stacked bar chart (phases), bar chart (stage averages) |
| S4: Pipeline Journey | `renderPipelineJourney(store)` | Horizontal swim-lane of pipeline stages with pass/fail | SVG rendered via JS (no Chart.js — custom SVG) |
| S5: Puzzle Details | `renderPuzzleDetails(store)` | Collapsible per-puzzle cards with timing, status, tags | Per-puzzle stacked bar (phase timing) inside `<details>` |
| S6: Search | `renderSearch(store)` | Text input, matching log lines with context highlighting | None |
| S7: Reference | `renderReference()` | Glossary terms, enrichment tier descriptions, status legend | None |

### Pipeline Journey Swim-Lane Design (S4)

```
Parse → Solve-Path → Analyze → Validate → Refutation → Difficulty → Assembly → Technique → Instinct → Teaching → SGF-Writeback
 [✓]      [✓]        [✓]       [✓]        [✓]          [✓]         [✓]        [✓]         [⊘]        [✓]        [✓]

Legend: [✓] = completed  [✗] = failed  [⊘] = skipped  [—] = no data
```

Rendered as horizontal SVG nodes with connecting lines. Each node is clickable (scrolls to relevant data in puzzle details). Color-coded: green=pass, red=fail, gray=skip, dotted=no data.

### Enrichment Tier Descriptions

| Tier | Badge | Human Description |
|------|-------|-------------------|
| 0 | — | **Unknown**: No enrichment data available |
| 1 | Bare | **Tier 1 — Bare Minimum**: Stones and basic structure only |
| 2 | Structural | **Tier 2 — Structural**: Partial KataGo analysis (position + validation) |
| 3 | Full | **Tier 3 — Full Analysis**: Refutations + difficulty + teaching comments |

Rendered as colored badges with tooltip on hover showing the full description.

---

## 2. Key Design Decisions

### D1: Chart.js Integration
- Load Chart.js v4 via CDN `<script>` tag (not ES module)
- `https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js`
- Integrity hash for security (SRI)
- Fallback: show data as tables if Chart.js fails to load

### D2: XSS Prevention
- **All log content** passed through `escapeHtml()` before DOM insertion
- Use `textContent` for plain text, never `innerHTML` with raw log data
- Chart.js handles its own rendering (canvas-based, no injection risk)
- SVG pipeline journey uses `createElementNS` + `textContent` (no innerHTML)

### D3: File Drop Zone
- Full-page drop zone with visual feedback (border highlight on drag-over)
- Also supports click-to-browse (hidden `<input type="file">`)
- "Load sample" button fetches `sample.jsonl` via relative path
- After load: drop zone collapses to header bar with filename and "Load another" link

### D4: Performance for 1K Puzzles
- Puzzle details (S5) uses `<details>` elements — content is lazy-rendered on first expand
- Search (S6) operates on pre-indexed text, debounced input (300ms)
- Charts created once, updated via Chart.js API (not recreated)
- No virtual scrolling needed at 1K puzzle scale

### D5: Dark Mode
- CSS custom properties for all colors
- `@media (prefers-color-scheme: dark)` block overrides custom properties
- Chart.js respects CSS custom properties via `getComputedStyle()` at render time
- SVG pipeline journey reads colors from CSS custom properties

### D6: Graceful Degradation
- Each section checks `store` for required data before rendering
- Missing data: section header + CTA box: "This section requires [field] in the JSONL log. Run enrichment with --verbose to enable."
- `phase_timings` absent → timing section shows CTA
- No `stage` field in events → pipeline journey shows "stage data not available" with all nodes in "no data" state

---

## 3. JSONL Event Mapping

### Known Events → Dashboard Sections

| JSONL `msg` | Key Fields Used | Dashboard Section |
|-------------|----------------|-------------------|
| `session_start` | `trace_id`, `run_id`, `source_file`, `config_hash` | S1: Header |
| `enrichment_begin` | `puzzle_id`, `source_file` | S5: Puzzle start marker |
| `enrichment_complete` | `status`, `refutations`, `level`, `technique_tags`, `hints_count`, `phase_timings` | S2, S3, S4, S5 |
| `enrichment_end` | `trace_id`, `puzzle_id`, `status`, `elapsed_s` | S5: Puzzle end marker |
| Other log events | `stage`, `msg`, `level` | S6: Search corpus |

### Data Gap Handling

| Missing Field | Affected Section | Degradation |
|--------------|-----------------|-------------|
| `phase_timings` | S3 (Timing), S4 (Pipeline) | Show CTA: "Run with --verbose" |
| `stage` field | S4 (Pipeline Journey) | Show all nodes as "no data" |
| `technique_tags` | S2 (tag distribution) | Omit tag chart |
| `level` | S2 (level distribution) | Omit level chart |
| `enrichment_complete` missing (only have `enrichment_end`) | S2, S3 | Use `elapsed_s` from end event; show limited data |

---

## 4. Risks and Mitigations

| ID | Risk | Probability | Impact | Mitigation |
|----|------|------------|--------|-----------|
| R1 | Chart.js CDN unavailable (offline/firewall) | Low | Medium | Graceful fallback to HTML tables; README mentions vendoring option |
| R2 | Large JSONL (>5K events) causes slow parse | Low | Medium | Streaming parse with progress bar; lazy detail rendering |
| R3 | Browser memory with 1K-puzzle EventStore | Low | Low | EventStore stores only indexed summaries, not full events for search |
| R4 | XSS via malicious JSONL content | Low | High | Strict escapeHtml() on all rendered content; CSP meta tag |
| R5 | Pipeline journey SVG complexity for many stages | Low | Low | Fixed 11-stage layout; no dynamic node count |

---

## 5. Contracts / Interfaces

### EventStore Interface (internal)

```javascript
// buildEventStore(events: object[]) → EventStore
// Input: array of parsed JSON objects from JSONL lines
// Output: EventStore object (see data model above)
// Contract: events may be empty, out of order, or missing fields
//           buildEventStore handles all edge cases gracefully
```

### Section Renderer Interface (internal)

```javascript
// Each render function:
//   renderXxx(store: EventStore, container: HTMLElement) → void
// Contract:
//   - Clears container before rendering
//   - Checks store for required data, shows CTA if missing
//   - Uses escapeHtml() for all log-derived content
//   - Chart instances stored for cleanup on re-render
```

### Search Interface (internal)

```javascript
// searchLog(query: string, events: object[]) → SearchResult[]
// SearchResult: { lineNum, event, matchedField, context }
// Contract: case-insensitive substring match across all JSON fields
//           Returns max 200 results (paginated display)
```

---

## 6. Documentation Plan

| ID | Action | File | Why |
|----|--------|------|-----|
| DOC-1 | Create | `tools/puzzle-enrichment-lab/log-viewer/README.md` | Usage instructions, JSONL format reference, screenshots |
| DOC-2 | Update | `tools/puzzle-enrichment-lab/AGENTS.md` | Add log-viewer to directory structure section |
| DOC-3 | Create (content) | `tools/puzzle-enrichment-lab/log-viewer/sample.jsonl` | Demo data file (also serves as format documentation) |

No changes to `docs/` directory needed — this is an internal dev tool, not user-facing documentation.

> **See also**:
> - [00-charter.md](./00-charter.md) — Feature scope and constraints
> - [25-options.md](./25-options.md) — Architecture options evaluated
> - [70-governance-decisions.md](./70-governance-decisions.md) — Option election rationale
