# Clarifications: Enrichment Lab Log Viewer

> Initiative: `20260321-1800-feature-enrichment-log-viewer`
> Last Updated: 2026-03-21

## Pre-Resolved Decisions (from user request)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q0a | Standalone viewer vs Preact integration? | A: Preact / B: Standalone HTML+JS | B | **B: Standalone HTML+JS** | ✅ resolved |
| Q0b | Location? | A: `tools/log-viewer/` / B: `tools/puzzle-enrichment-lab/log-viewer/` | B | **B: Inside enrichment lab** | ✅ resolved |
| Q0c | Source of truth? | A: Pipeline objects / B: JSONL log file only | B | **B: JSONL log file only** | ✅ resolved |
| Q0d | Python CLI additions needed? | A: Yes / B: No | B | **B: No Python CLI additions** | ✅ resolved |
| Q0e | Charting approach? | A: CSS-only / B: JS charting library | B | **B: Proper JS charting library** | ✅ resolved |
| Q0f | Backward compatibility required? | A: Yes / B: No | B | **B: Not required — new tool** | ✅ resolved |
| Q0g | Remove existing Python report generator? | A: Yes / B: No, keep as-is | B | **B: Keep existing, not removed yet** | ✅ resolved |

## Clarification Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Charting library choice**: Which JS charting library? | A: Chart.js (~60KB) / B: ECharts (~300KB) / D: uPlot (~35KB) | A: Chart.js | **A: Chart.js (~60KB)** | ✅ resolved |
| Q2 | **Pipeline journey chart type**: How should the pipeline stages flow be rendered? | A: Horizontal swim-lane / B: Vertical timeline / C: Sankey/flow | A: Horizontal swim-lane | **A: Horizontal swim-lane** | ✅ resolved |
| Q3 | **Dark mode support**: Should the viewer support dark mode? | A: Light only / C: System-preference auto-detect | C: System-preference | **C: System-preference auto-detect** | ✅ resolved |
| Q4 | **File architecture**: Single HTML file vs multi-file? | A: Single index.html / B: Separate files | B: Separate files | **B: Separate files (index.html + app.js + styles.css)** | ✅ resolved |
| Q5 | **Graceful degradation for missing log data** | A: Placeholder / B: Hide / C: Header + CTA | C: Mix | **C: Show header + "Enrich log to enable" CTA** | ✅ resolved |
| Q6 | **Sample/demo JSONL**: Ship a sample file for testing? | A: Yes / B: No | A: Yes | **A: Yes, include sample.jsonl** | ✅ resolved |
| Q7 | **Performance target**: Max JSONL file size? | A: ~100 puzzles / B: ~1,000 puzzles / C: ~10,000 puzzles | B: 1,000 | **B: ~1,000 puzzles (~5K events)** | ✅ resolved |

## All Clarifications Resolved

No further blocking questions. Ready for options phase.
