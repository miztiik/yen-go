# Charter: Enrichment Lab Log Viewer

> Initiative: `20260321-1800-feature-enrichment-log-viewer`
> Last Updated: 2026-03-21

## Goals

1. **G1**: Build a standalone HTML+JS log viewer that reads JSONL log files from the puzzle-enrichment-lab and renders a rich, interactive diagnostic dashboard
2. **G2**: Replace the crude CSS timing bars with proper charting (flame chart or stacked bar) using an open-source JS library
3. **G3**: Visualize the enrichment pipeline as a "ping-pong ball" flow showing gate-by-gate pass/fail
4. **G4**: Support batch mode with collapsible puzzle details and aggregate statistics
5. **G5**: Provide pure-JS text search across the raw log
6. **G6**: Include a glossary/reference section with hyperlinked terms from analysis sections
7. **G7**: Show human-readable enrichment tier descriptions (not just numbers)
8. **G8**: Show per-stage KataGo query usage (not just totals)

## Non-Goals

- **NG1**: No modifications to the Python enrichment pipeline or CLI
- **NG2**: No integration with the Preact frontend app
- **NG3**: No build step required (works by opening index.html directly)
- **NG4**: No server-side rendering or backend dependency
- **NG5**: No removal of existing Python report generator (stays as-is)
- **NG6**: No enrichment of the JSONL log format (separate initiative if needed)

## Constraints

| ID | Constraint | Rationale |
|----|-----------|-----------|
| C1 | Zero runtime backend — static HTML+JS opened in browser | Holy Law #1 |
| C2 | No build step — `index.html` opens directly, CDN for libs | Developer simplicity |
| C3 | File drop zone — user drags JSONL file onto page | No file picker dialogs, low friction UX |
| C4 | Self-contained — charting library from CDN or vendored | No npm install required |
| C5 | Must NOT import from `backend/` or `frontend/` | Architecture rule 03-architecture-rules.md |
| C6 | Log file is the only input — no additional data sources | Clear separation principle |
| C7 | Location: `tools/puzzle-enrichment-lab/log-viewer/` | Inside enrichment lab, not root tools/ |

## Acceptance Criteria

| ID | Criterion | Verification |
|----|----------|-------------|
| AC1 | Developer can open `log-viewer/index.html`, drop a JSONL file, see full dashboard | Manual test |
| AC2 | Timing visualization uses proper charting library (not CSS hacks) | Visual inspection |
| AC3 | Pipeline journey shows gate-by-gate flow with pass/fail indicators | Visual inspection |
| AC4 | Batch mode: all puzzles with collapsible details + aggregate stats | Drop multi-puzzle JSONL |
| AC5 | Search function finds any string in the log | Type search term, see results |
| AC6 | Enrichment tiers have human-readable descriptions with tooltips | Hover tier number |
| AC7 | References section with hyperlinked glossary terms | Click term → scrolls to definition |
| AC8 | Per-stage query counts visible (not just total) | Check stage breakdown in dashboard |
| AC9 | Works with known JSONL event types: session_start, enrichment_begin, enrichment_complete, enrichment_end | Drop real log file |
| AC10 | Large JSONL files (1000+ puzzles) handled without freezing | Performance test |

## Risk Assessment

| ID | Risk | Probability | Impact | Mitigation |
|----|------|------------|--------|-----------|
| R1 | JSONL log lacks data for some visualizations (gate trace, per-stage queries) | High | Medium | Graceful degradation; show "data not available" |
| R2 | Large JSONL files may cause browser memory pressure | Medium | Medium | Streaming parser, virtualized list for batch mode |
| R3 | CDN dependency for charting library (offline use) | Low | Low | Option to vendor the library locally |
| R4 | Charting library size may slow initial page load | Low | Low | Choose lightweight library (<100KB) |

## Predecessor

- `20260321-1400-feature-html-report-redesign` (closed) — the Python HTML report generator this viewer conceptually supersedes for new development

> **See also**:
> - [AGENTS.md](../../../tools/puzzle-enrichment-lab/AGENTS.md) — Enrichment lab architecture
> - [report/generator.py](../../../tools/puzzle-enrichment-lab/report/generator.py) — Current Python HTML report
> - [report/correlator.py](../../../tools/puzzle-enrichment-lab/report/correlator.py) — JSONL event correlator logic
