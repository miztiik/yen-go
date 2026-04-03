# Plan: HTML Report Redesign

**Initiative**: `20260321-1400-feature-html-report-redesign`
**Selected Option**: OPT-1 (Inline HTML String Builder)
**Date**: 2026-03-21

---

## Architecture Overview

### Current State
- `generator.py`: `LogReportGenerator.generate()` accepts scalar counts (puzzle_count, accepted_count, etc.) → returns markdown string
- `token.py`: `build_report_path()` returns `.md` extension
- `cli.py`: passes counts only; does not pass `AiAnalysisResult` or original SGF text
- `__init__.py`: exports package docstring only

### Target State
- `generator.py`: `LogReportGenerator.generate()` accepts `results: list[AiAnalysisResult]`, `original_sgf_texts: list[str]`, `total_queries: int`, `trace_ids: list[str]` alongside existing params → returns self-contained HTML string
- `token.py`: `build_report_path()` returns `.html` extension
- `index_generator.py` (NEW): `regenerate_index(logs_dir: Path)` → writes `index.html` navigation shell
- `cli.py`: passes full `AiAnalysisResult` list + original SGF texts to generator; calls `regenerate_index()` after report write
- `__init__.py`: exports `LogReportGenerator`, `regenerate_index`

---

## Detailed Design

### 1. Generator Signature Change

```python
def generate(
    self,
    *,
    log_path: Path | str | None = None,
    output_path: Path | str | None = None,
    run_id: str = "",
    puzzle_count: int = 0,
    accepted_count: int = 0,
    flagged_count: int = 0,
    error_count: int = 0,
    duration_s: float = 0.0,
    source_file: str = "",
    # NEW parameters
    results: list[AiAnalysisResult] | None = None,
    original_sgf_texts: list[str] | None = None,
    total_queries: int = 0,
    trace_ids: list[str] | None = None,
) -> str:
```

All new params are optional with safe defaults to maintain backward-compatible call sites during transition.

### 2. HTML Structure (10 Sections + 3 New)

```
<html>
<head>
  <style> /* inline CSS: color scheme, tables, details/summary, badges */ </style>
</head>
<body>
  <h1>Enrichment Report</h1>

  <!-- S1: Run Metadata -->
  <section id="s1-metadata">
    Generated, Run ID, trace_id count (NEW), source file, report mode, source log paths (NEW)
  </section>

  <!-- S2: Log Linkage -->
  <section id="s2-linkage">
    Source log absolute path, relative path from workspace root (NEW)
  </section>

  <!-- S3: Summary Metrics -->
  <section id="s3-summary">
    Total puzzles, accepted/flagged/error, duration, avg KataGo queries/puzzle (NEW)
  </section>

  <!-- S4: Request/Response Correlation -->
  <section id="s4-correlation">
    Table with colored status badges (green=matched, red=unmatched)
  </section>

  <!-- NEW: Per-Puzzle Details (batch = collapsible <details>) -->
  <section id="puzzle-details">
    For each puzzle:
    - Before/After SGF Property Table (D4)
    - Analysis Narrative
  </section>

  <!-- S5: Glossary (versioned, expanded) -->
  <section id="s5-glossary">
    All field definitions, tagged with schema version (NEW: versioned)
  </section>

  <!-- S6: Policy Definitions (with real thresholds) -->
  <section id="s6-policy">
    Active rules with t_good, t_bad, t_hotspot values from config (NEW)
  </section>

  <!-- S7: Win Rate Interpretation -->
  <section id="s7-winrate">
    Threshold values from config alongside prose (NEW: concrete values)
  </section>

  <!-- S8: Category Terms -->
  <section id="s8-categories">
    Go/tsumego domain terminology (expanded)
  </section>

  <!-- S9: Data Quality -->
  <section id="s9-quality">
    Correlated pairs, unmatched, parse warnings, correlation completeness % (NEW)
  </section>

  <!-- S10: Change Magnitude (blocked) -->
  <section id="s10-magnitude">
    Governance-blocked placeholder
  </section>
</body>
</html>
```

### 3. Before/After SGF Property Table

Parse original SGF text to extract `Y*` custom properties using regex:
```python
SGF_PROPS = ["YG", "YT", "YQ", "YX", "YH", "YK", "YO", "YR", "YC"]
_PROP_RE = re.compile(r"(Y[GTQXHKORC])\[([^\]]*)\]")
```

Extract new values from `AiAnalysisResult`:
- YG → `result.difficulty.suggested_level`
- YT → `",".join(result.tag_names)`
- YQ → constructed from `result.ac_level`, `result.enrichment_quality_level`
- YX → constructed from `result.difficulty` fields
- YH → `"|".join(result.hints)`
- YK → from result if available (or original)
- YO → `result.move_order`
- YR → from `result.refutations` wrong moves
- YC → `result.corner`

Render as HTML table:
```html
<table class="before-after">
  <tr><th>Property</th><th>Before</th><th>After</th></tr>
  <tr class="changed"><td>YG</td><td>elementary</td><td>intermediate</td></tr>
  <tr class="unchanged"><td>YK</td><td>none</td><td>none</td></tr>
</table>
```

### 4. Analysis Narrative

Per puzzle, generate human-readable observations from AiAnalysisResult:

| Observation | Source Field |
|-------------|-------------|
| Root winrate | `result.validation.correct_move_winrate` |
| KataGo top move | `result.validation.katago_top_move_gtp` |
| Agreement | `result.validation.katago_agrees` |
| Correct move rank | `result.difficulty.correct_move_rank` |
| Solution depth | `result.difficulty.solution_depth` |
| Refutation count | `len(result.refutations)` |
| Tree truncated | `result.tree_truncated` |
| Queries consumed | `result.queries_used` |
| Phase timings | `result.phase_timings` |
| Human solution confidence | `result.human_solution_confidence` |
| AI solution validated | `result.ai_solution_validated` |
| Goal inference | `result.goal`, `result.goal_confidence` |
| Technique tags | `result.technique_tags` |
| Enrichment tier | `result.enrichment_tier` |

### 5. Navigation Shell

`report/index_generator.py`:
- Scans `logs_dir` for `enrichment-report-*.html` files
- Sorts by mtime descending (most recent first)
- Generates `index.html` with:
  - Left sidebar (20% width): clickable file list with timestamps
  - Right panel (80% width): `<iframe>` loading selected report
  - Embedded CSS/JS for click handling
  - No external dependencies

### 6. K.3 Spec Gap Fixes

| Gap | Section | Fix |
|-----|---------|-----|
| S1 missing trace_id count | S1 | Add `trace_ids` param, render count: `f"Trace IDs: {len(trace_ids)}"` |
| S2 missing relative path | S2 | Compute relative path: `log_path.relative_to(workspace_root)` with fallback to absolute |
| S3 missing avg queries | S3 | Add `total_queries` param, render: `f"Avg queries/puzzle: {total_queries / max(puzzle_count, 1):.1f}"` |
| S5 sparse glossary | S5 | Expand to all report fields, tag with `AI_ANALYSIS_SCHEMA_VERSION` |
| S6 missing real thresholds | S6 | Pull `t_good`, `t_bad`, `t_hotspot` from config; render actual values |
| S9 missing completeness | S9 | Compute `matched / total * 100`, render as `f"Correlation completeness: {pct:.0f}%"` |

### 7. Color Scheme (Inline CSS)

```css
:root {
  --color-accepted: #28a745;   /* green */
  --color-flagged: #ffc107;    /* amber */
  --color-error: #dc3545;      /* red */
  --color-info: #007bff;       /* blue */
  --color-changed: #d4edda;    /* light green bg for changed rows */
  --color-unchanged: #f8f9fa;  /* light gray bg for unchanged rows */
}
```

---

## File Modification List

| File | Action | Scope |
|------|--------|-------|
| `report/generator.py` | REWRITE | Complete rewrite: markdown → HTML, new params, 10+3 sections |
| `report/token.py` | EDIT | `.md` → `.html` in `build_report_path()` docstring and format string |
| `report/index_generator.py` | CREATE | Navigation shell generator (~80 lines) |
| `report/__init__.py` | EDIT | Update docstring, add exports |
| `cli.py` | EDIT | Wire `results`/`original_sgf_texts`/`total_queries`/`trace_ids` in both `run_enrich` and `_run_batch_async` |
| `tests/test_report_generator.py` | REWRITE | Update all assertions: markdown → HTML section checks |
| `tests/test_report_token.py` | EDIT | `.md` → `.html` in path assertions |
| `tests/test_report_autotrigger.py` | VERIFY | Mock-based; should work with signature change (verify) |
| `tests/test_cli_report.py` | VERIFY | CLI flag parsing; no output format assertions (verify) |
| `tests/test_report_correlator.py` | KEEP | No changes needed (pure log parsing) |
| `tests/test_report_toggle.py` | KEEP | No changes needed (toggle logic unchanged) |
| `tests/test_report_index_generator.py` | CREATE | New tests for navigation shell |
| `AGENTS.md` | EDIT | Update `report/` section description |

---

## Risks and Mitigations

| risk_id | risk | level | mitigation |
|---------|------|-------|------------|
| R1 | HTML string building without template engine → readability | low | Structured helper methods per section, thorough tests |
| R2 | Passing full AiAnalysisResult list in batch → memory | low | Results already in memory during batch loop |
| R3 | index.html regeneration on every report → I/O | low | Fast directory scan, no external I/O |
| R4 | SGF property parsing via regex → edge cases | low | Well-known SGF property format `XX[value]`, defensive fallback |
| R5 | Config not available at report time (mock config in tests) | low | All config reads wrapped in getattr with defaults |

---

## Documentation Plan

| action | file | why |
|--------|------|-----|
| files_to_update | `tools/puzzle-enrichment-lab/AGENTS.md` | Update report/ section: HTML generator, index_generator.py |
| files_to_update | Parent initiative `50-execution-log.md` | Log HTML redesign as sub-work completed |
