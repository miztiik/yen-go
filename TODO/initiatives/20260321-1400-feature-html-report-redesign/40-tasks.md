# Tasks: HTML Report Redesign

**Initiative**: `20260321-1400-feature-html-report-redesign`
**Selected Option**: OPT-1
**Date**: 2026-03-21

---

## Phase 1: Data Wiring (Sequential — foundation for all other phases)

### T-HR-1: Update generator.py signature
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Add new optional parameters to `generate()`:
  - `results: list[AiAnalysisResult] | None = None`
  - `original_sgf_texts: list[str] | None = None`
  - `total_queries: int = 0`
  - `trace_ids: list[str] | None = None`
- **Dependencies**: None
- **Verification**: Existing callers still work (all new params optional with defaults)

### T-HR-2: Wire AiAnalysisResult in single-enrich CLI path
- **File**: `tools/puzzle-enrichment-lab/cli.py` (lines ~235-265, `run_enrich` function)
- **Action**: In the report generation block, pass:
  - `results=[result]`
  - `original_sgf_texts=[sgf_text]`
  - `total_queries=result.queries_used`
  - `trace_ids=[result.trace_id]`
- **Dependencies**: T-HR-1
- **Verification**: `run_enrich` passes result data to generator

### T-HR-3: Wire AiAnalysisResult in batch CLI path
- **File**: `tools/puzzle-enrichment-lab/cli.py` (lines ~600-650, `_run_batch_async` function)
- **Action**:
  1. Before batch loop: initialize `batch_results: list[AiAnalysisResult] = []` and `batch_sgf_texts: list[str] = []` and `batch_total_queries: int = 0` and `batch_trace_ids: list[str] = []`
  2. Inside loop (after each successful enrichment): append result, sgf_text, accumulate queries, collect trace_id
  3. In report generation block: pass accumulated lists to `generator.generate()`
- **Dependencies**: T-HR-1
- **Verification**: Batch mode passes all results to generator

---

## Phase 2: HTML Generator Core (Sequential — depends on Phase 1)

### T-HR-4: Rewrite generator.py — HTML skeleton + CSS
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Replace entire `generate()` body with HTML output:
  1. Build `<html><head><style>...</style></head><body>` wrapper
  2. Inline CSS with color variables (green/amber/red/blue)
  3. Responsive layout with max-width container
  4. Table styling, `.badge` classes, `.changed`/`.unchanged` row classes
  5. `<details><summary>` styling for batch puzzle sections
- **Dependencies**: T-HR-1
- **Verification**: `generate()` returns valid HTML string starting with `<!DOCTYPE html>`

### T-HR-5: Implement S1 — Title and Run Metadata (K.3 gap fix)
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Render S1 section with:
  - Generated timestamp (UTC ISO)
  - Run ID
  - **Trace ID count** (NEW: `len(trace_ids or [])`)
  - Source file or "batch"
  - Report mode: "resolved"
  - Source log path(s)
- **Dependencies**: T-HR-4
- **K.3 Gap**: S1 — adds trace_id count

### T-HR-6: Implement S2 — Log Linkage (K.3 gap fix)
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Render S2 with:
  - Source log absolute path
  - **Relative path from workspace root** (NEW: try `Path.relative_to()` with common parents, fallback to absolute)
  - Token extracted from log path
- **Dependencies**: T-HR-4
- **K.3 Gap**: S2 — adds relative path

### T-HR-7: Implement S3 — Summary Metrics (K.3 gap fix)
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Render S3 with:
  - Total puzzles, accepted/flagged/error with colored badges
  - Duration
  - **Avg KataGo queries per puzzle** (NEW: `total_queries / max(puzzle_count, 1)`)
- **Dependencies**: T-HR-4
- **K.3 Gap**: S3 — adds avg KataGo queries

### T-HR-8: Implement S4 — Correlation Table
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Render correlation table with HTML `<table>` and colored status badges:
  - `matched` → green badge
  - `unmatched_request` → amber badge
  - `unmatched_response` → red badge
- **Dependencies**: T-HR-4

### T-HR-9: Implement S5 — Versioned Glossary (K.3 gap fix)
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Render comprehensive glossary covering ALL report fields:
  - Accepted, Flagged, Error, Run ID (existing 4)
  - **NEW**: Trace ID, Correlation Completeness, Avg Queries, Before/After, Policy Threshold, Win Rate Delta, Enrichment Tier, Solution Depth, Refutation, Solution Confidence, Co-correct, Tree Truncated, Technique Tags
  - **Version tag**: `f"Glossary v{AI_ANALYSIS_SCHEMA_VERSION}"`
- **Dependencies**: T-HR-4
- **K.3 Gap**: S5 — versioned, comprehensive definitions

### T-HR-10: Implement S6 — Policy Definitions with Real Thresholds (K.3 gap fix)
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Render active policy rules with actual config values:
  - Accept: `Δwr ≤ {t_good}` (pull from config or default 0.05)
  - Flag: `{t_good} < Δwr < {t_bad}` (default 0.15)
  - Error: SGF parse failure or engine error
  - Hotspot: `Δwr ≥ {t_hotspot}` (default 0.30)
  - Disagreement: `Δwr gap ≥ {t_disagreement}` (default 0.10)
- **Dependencies**: T-HR-4
- **K.3 Gap**: S6 — real config threshold values

### T-HR-11: Implement S7-S8 — Win Rate Interpretation + Category Terms
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**:
  - S7: Win rate delta interpretation with concrete threshold references from S6
  - S8: Expanded category terms (Tsumego, SGF, KataGo, Solution Tree, Refutation, Co-correct, Policy Prior, Enrichment Tier)
- **Dependencies**: T-HR-4

### T-HR-12: Implement S9 — Data Quality with Completeness (K.3 gap fix)
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Render data quality section with:
  - Correlated pairs count
  - Unmatched requests/responses
  - Parse warnings
  - **Correlation completeness %** (NEW: `matched / max(total, 1) * 100`)
- **Dependencies**: T-HR-4
- **K.3 Gap**: S9 — adds correlation completeness metric

### T-HR-13: Implement S10 — Change Magnitude Placeholder
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Governance-blocked placeholder, same as current (just in HTML format)
- **Dependencies**: T-HR-4

---

## Phase 3: Per-Puzzle Details (Parallel with Phase 2 S5-S10 tasks)

### T-HR-14: SGF property parser helper [P]
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Add private method `_extract_sgf_properties(sgf_text: str) -> dict[str, str]`:
  - Parse `YG[...]`, `YT[...]`, `YQ[...]`, `YX[...]`, `YH[...]`, `YK[...]`, `YO[...]`, `YR[...]`, `YC[...]` from raw SGF text
  - Use regex: `re.findall(r"(Y[GTQXHKORC])\[([^\]]*)\]", sgf_text)`
  - Return dict mapping property name → value
- **Dependencies**: T-HR-1
- **Parallel**: Can be built alongside Phase 2 tasks

### T-HR-15: "After" property extractor from AiAnalysisResult [P]
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Add private method `_extract_result_properties(result: AiAnalysisResult) -> dict[str, str]`:
  - YG → `result.difficulty.suggested_level`
  - YT → `",".join(sorted(result.tag_names))`
  - YQ → `f"q:{result.enrichment_quality_level};ac:{result.ac_level}"`
  - YX → `f"d:{result.difficulty.solution_depth};r:{result.difficulty.refutation_count};u:{result.difficulty.local_candidate_count}"`
  - YH → `"|".join(result.hints)`
  - YK → (not in result directly, keep from original)
  - YO → `result.move_order`
  - YR → `",".join(r.wrong_move for r in result.refutations)`
  - YC → `result.corner`
- **Dependencies**: T-HR-1
- **Parallel**: Can be built alongside Phase 2 tasks

### T-HR-16: Before/after comparison table renderer
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Add private method `_render_before_after_table(before: dict, after: dict) -> str`:
  - HTML table with Property / Before / After columns
  - Row class: `changed` (green bg) if values differ, `unchanged` (gray bg) if same
  - Handle missing properties gracefully (show "—")
- **Dependencies**: T-HR-14, T-HR-15

### T-HR-17: Analysis narrative renderer
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Add private method `_render_analysis_narrative(result: AiAnalysisResult) -> str`:
  - Root winrate + positional assessment sentence
  - Correct move found + KataGo agreement status
  - Solution depth and refutation count
  - Query consumption and phase timing breakdown
  - Human solution confidence assessment
  - Goal inference result
  - Technique tags detected
  - Enrichment tier indicator
- **Dependencies**: T-HR-1

### T-HR-18: Per-puzzle section assembly
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: Integrate before/after table + narrative into the main `generate()` flow:
  - Single puzzle: render inline (no collapsible)
  - Batch: each puzzle in `<details><summary>Puzzle {id} — {status badge}</summary>...</details>`
  - Place between S4 and S5 in section order
- **Dependencies**: T-HR-16, T-HR-17

---

## Phase 4: Token + Index Generator (Parallel with Phase 2-3)

### T-HR-19: Update token.py extension [P]
- **File**: `tools/puzzle-enrichment-lab/report/token.py`
- **Action**:
  - Change `report_name = f"enrichment-report-{token}.md"` → `f"enrichment-report-{token}.html"`
  - Update docstrings: `.md` → `.html`
- **Dependencies**: None
- **Parallel**: Independent of generator work

### T-HR-20: Create index_generator.py [P]
- **File**: `tools/puzzle-enrichment-lab/report/index_generator.py` (NEW)
- **Action**: Create `regenerate_index(logs_dir: Path) -> Path | None`:
  1. Scan `logs_dir` for `enrichment-report-*.html` files
  2. Sort by mtime descending
  3. Generate `index.html` with:
     - Left sidebar (20% width, fixed): file list with dates, clickable links
     - Right panel (80%): `<iframe>` that loads selected report
     - Inline CSS/JS for sidebar click → iframe src change
     - Title: "Enrichment Reports"
  4. Write `logs_dir / index.html`
  5. Return path to index.html (or None if no reports found)
- **Dependencies**: None
- **Parallel**: Fully independent

### T-HR-21: Wire index regeneration in generator [P]
- **File**: `tools/puzzle-enrichment-lab/report/generator.py`
- **Action**: At end of `generate()`, after writing report file, call:
  ```python
  try:
      from report.index_generator import regenerate_index
      if output_path:
          regenerate_index(Path(output_path).parent)
  except Exception as e:
      logger.warning("Index regeneration failed: %s", e)
  ```
- **Dependencies**: T-HR-20, T-HR-4

### T-HR-22: Update __init__.py exports [P]
- **File**: `tools/puzzle-enrichment-lab/report/__init__.py`
- **Action**: Update docstring and add `__all__` with public API:
  ```python
  """Enrichment log-report generation package (Work Stream K).
  Provides automated HTML report generation from enrichment data.
  """
  ```
- **Dependencies**: None
- **Parallel**: Independent

---

## Phase 5: Test Updates (Sequential — depends on Phases 2-4)

### T-HR-23: Rewrite test_report_generator.py
- **File**: `tools/puzzle-enrichment-lab/tests/test_report_generator.py`
- **Action**: Update all assertions from markdown to HTML:
  - `"# Enrichment Log Report"` → `"<h1>"` or `"Enrichment Report"` in HTML
  - `"## Summary"` → `'id="s3-summary"'` or `"<h2>Summary"` 
  - `"## Log Linkage"` → `'id="s2-linkage"'`
  - Section ordering test: check HTML section IDs appear in order
  - File output test: check `.html` extension works
  - **NEW tests**: check trace_id count rendered, relative path rendered, avg queries rendered, glossary versioned, real thresholds rendered, completeness % rendered
  - **NEW tests**: before/after table rendering with mock AiAnalysisResult
  - **NEW tests**: analysis narrative rendering with mock AiAnalysisResult
  - **NEW tests**: batch mode renders `<details>` sections
- **Dependencies**: T-HR-4 through T-HR-18

### T-HR-24: Update test_report_token.py
- **File**: `tools/puzzle-enrichment-lab/tests/test_report_token.py`
- **Action**: Update all `.md` assertions to `.html`:
  - `assert report_path.name == "enrichment-report-20260320-a1b2c3d4.md"` → `.html`
  - `assert report_path.suffix == ".md"` → `.html`
  - Same for `test_override_output_dir`, `test_deterministic_coupling`, `test_fallback_stem`
- **Dependencies**: T-HR-19

### T-HR-25: Verify test_report_autotrigger.py
- **File**: `tools/puzzle-enrichment-lab/tests/test_report_autotrigger.py`
- **Action**: Review mock-based tests. Since they mock `LogReportGenerator` and `build_report_path`, they should work without changes. Verify:
  - `mock_gen.generate.assert_called_once()` still valid (signature change is backward-compatible)
  - No `.md` string assertions
- **Dependencies**: T-HR-2, T-HR-3

### T-HR-26: Verify test_cli_report.py
- **File**: `tools/puzzle-enrichment-lab/tests/test_cli_report.py`
- **Action**: Review CLI flag parsing tests. These test argparse, not output format. Should need no changes. Verify no `.md` assertions.
- **Dependencies**: None

### T-HR-27: Create test_report_index_generator.py
- **File**: `tools/puzzle-enrichment-lab/tests/test_report_index_generator.py` (NEW)
- **Action**: Tests for navigation shell:
  - `test_generates_index_with_reports`: Create temp dir with 3 `.html` report files → verify `index.html` created with all filenames
  - `test_no_reports_returns_none`: Empty dir → returns None, no index.html written
  - `test_index_contains_iframe`: Generated index.html contains `<iframe>`
  - `test_index_sorted_by_mtime`: Reports listed newest-first
  - `test_index_self_contained`: No external CSS/JS references
- **Dependencies**: T-HR-20

---

## Phase 6: AGENTS.md + Final Cleanup (Sequential — last)

### T-HR-28: Update AGENTS.md
- **File**: `tools/puzzle-enrichment-lab/AGENTS.md`
- **Action**: Update `report/` section:
  - `generator.py` — `LogReportGenerator`: ~~markdown~~ → HTML report with S1-S10 sections + before/after + analysis narrative
  - `index_generator.py` — `regenerate_index()`: navigation shell generator for `.lab-runtime/logs/`
  - `token.py` — filename coupling (.html extension)
- **Dependencies**: All previous tasks

### T-HR-29: Final regression verification
- **Action**: Run full enrichment lab test suite:
  ```bash
  cd tools/puzzle-enrichment-lab && python -B -m pytest tests/ -m "not slow" --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -q --no-header --tb=short -p no:cacheprovider
  ```
- **Dependencies**: All previous tasks
- **Verification**: 201+ tests pass, 0 new failures

---

## Task Dependency Graph

```
Phase 1 (Sequential):
  T-HR-1 → T-HR-2
  T-HR-1 → T-HR-3

Phase 2 (Sequential chain, depends on T-HR-1):
  T-HR-4 → T-HR-5 → T-HR-6 → T-HR-7 → T-HR-8 → T-HR-9 → T-HR-10 → T-HR-11 → T-HR-12 → T-HR-13

Phase 3 (Parallel start with Phase 2, sequential within):
  [P] T-HR-14 ─┐
  [P] T-HR-15 ─┤→ T-HR-16 ─┐
               │            ├→ T-HR-18
  T-HR-17 ────────────────────┘

Phase 4 (Fully parallel with Phases 2-3):
  [P] T-HR-19
  [P] T-HR-20 → T-HR-21
  [P] T-HR-22

Phase 5 (After Phases 2-4):
  T-HR-23 (depends on Phase 2+3)
  T-HR-24 (depends on T-HR-19)
  T-HR-25 (verify only)
  T-HR-26 (verify only)
  T-HR-27 (depends on T-HR-20)

Phase 6 (Last):
  T-HR-28 → T-HR-29
```

---

## Verification Checklist

- [ ] `generate()` returns string starting with `<!DOCTYPE html>`
- [ ] S1 contains trace_id count
- [ ] S2 contains relative path from workspace root
- [ ] S3 contains avg KataGo queries per puzzle
- [ ] S5 glossary is versioned and comprehensive (15+ terms)
- [ ] S6 contains real threshold values (t_good, t_bad, t_hotspot)
- [ ] S9 contains correlation completeness percentage
- [ ] Before/after table renders for single puzzle with color coding
- [ ] Before/after table renders for batch with `<details>` sections
- [ ] Analysis narrative includes winrate, agreement, depth, queries, confidence
- [ ] Navigation shell lists all reports with iframe loading
- [ ] Token produces `.html` extension
- [ ] All existing tests updated and passing
- [ ] AGENTS.md report/ section updated
- [ ] Full regression: 201+ tests pass
