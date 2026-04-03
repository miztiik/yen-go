# Enrichment Log Viewer

> Standalone HTML+JS diagnostic dashboard for puzzle-enrichment-lab JSONL log files.

**Last Updated**: 2026-03-21

---

## Quick Start

1. Open `index.html` in any modern browser (Chrome, Firefox, Edge)
2. Drop a `.jsonl` log file onto the page — or click **Load sample data** for a demo

No build step, no server, no dependencies to install. Works with `file://` protocol.

## What It Shows

| Section | Content |
|---------|---------|
| **Header** | File name, run ID, session timestamp, puzzle count, total/avg duration, query counts, model configuration (arch, visit budgets, escalations, config hash) |
| **Summary** | Status distribution (doughnut), level distribution (bar), top tags (bar), enrichment tier breakdown |
| **Timing** | Per-stage average timing (bar chart), timing table with total/avg/max/% |
| **Pipeline Journey** | SVG swim-lane showing 11 pipeline stages with pass/fail/skip indicators per stage. Collapsed with health digest for batch runs (>1 puzzle), expanded for single puzzles |
| **Puzzle Details** | Collapsible per-puzzle cards with metadata, tags, phase timing bars, tier descriptions |
| **Search** | Full-text search across all log events with match highlighting and click-to-expand |
| **Reference** | Glossary of statuses, enrichment tiers, pipeline stages, key metrics, and JSONL event format |

## JSONL Event Format

The viewer expects JSONL files (one JSON object per line) with these event types:

| Event | Key Fields | Description |
|-------|-----------|-------------|
| `session_start` | `trace_id`, `run_id`, `source_file`, `config_hash` | Emitted when enrichment begins for a puzzle |
| `enrichment_begin` | `puzzle_id`, `trace_id`, `source_file` | Marks start of pipeline processing |
| `katago_analysis` | `stage`, `model`, `visits`, `winrate`, `top_move` | KataGo engine analysis result (model and visit data extracted for header) |
| `enrichment_complete` | `status`, `level`, `technique_tags`, `phase_timings`, `refutations`, `hints_count`, `enrichment_tier`, `queries_used` | Full analysis results |
| `enrichment_end` | `trace_id`, `puzzle_id`, `status`, `elapsed_s` | Final event per puzzle with total duration |

### Generating Logs

```bash
# Run enrichment with JSONL logging enabled
cd tools/puzzle-enrichment-lab
python -m cli enrich --input path/to/puzzles/ --verbose 2>&1 | tee enrichment.jsonl
```

The JSONL log file is produced by the enrichment lab's structured logging system. Check `.lab-runtime/logs/` for recent runs.

## Features

- **Graceful degradation**: Missing fields show informative CTAs instead of blank sections
- **Dark mode**: Follows OS preference via `prefers-color-scheme: dark`
- **Chart.js 4.x**: Loaded from CDN; if unavailable, falls back to HTML tables
- **Performance**: Lazy-renders puzzle details on expand; handles 1000+ puzzles
- **Search**: Debounced full-text search with click-to-expand puzzle cards

## Known Limitations

- Requires internet connection for Chart.js CDN (see "Offline Use" below)
- CSP meta tag has limited enforcement on `file://` protocol
- No streaming parser for very large files (>50MB may be slow)

## Offline Use (Vendoring Chart.js)

To use without CDN access:

1. Download `chart.umd.min.js` from https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js
2. Save it to `log-viewer/chart.umd.min.js`
3. Edit `index.html`: change the `<script>` src to `chart.umd.min.js`

## File Structure

```
log-viewer/
├── index.html      # HTML shell with drop zone and section containers
├── app.js          # All application logic (IIFE, no modules)
├── styles.css      # All styles including dark mode
├── sample.jsonl    # Demo data (5 puzzles with varied statuses)
└── README.md       # This file
```

> **See also**:
> - [AGENTS.md](../AGENTS.md) — Enrichment lab architecture map
