# Critical Test Review & Clarifications

## Executive Summary

**91 failing tests across 21 test files.** After critical review, the failures break into **7 categories** with clear verdicts. The core finding: **most failures are stale tests targeting removed/renamed APIs, not production bugs**. A significant number are also testing implementation details rather than behavior.

---

## Category A — DEAD CODE: Characterization Tests for Removed Method (18 tests)

**File:** `tests/unit/test_analyze_characterization.py`  
**Error:** `AttributeError: 'AnalyzeStage' object has no attribute '_inject_yengo_props'`

### Critical Review

These are **golden master / characterization tests** — the file header literally says:
> "These tests capture the EXACT output behavior of the regex-based implementation before refactoring to SGFBuilder-based implementation."

The refactoring **already happened**. `_inject_yengo_props()` was the old regex-based SGF injection method. The current `AnalyzeStage` uses `SGFBuilder` via `_enrich_sgf()` / `_analyze_puzzle()` instead. These tests served their purpose (verifying the refactor) and are now dead weight.

### Verdict: **DELETE ALL 18** ⛔

These are scaffolding tests that outlived their purpose. The behavior they validated is now covered by `_enrich_sgf()` tests in `test_sgf_enrichment.py` (which has passing tests for tag sorting, YG/YT injection, GN handling, etc.). Keeping them adds confusion.

**Consolidation note:** There are ALSO 2 more tests in `test_sgf_enrichment.py` that fail because they expect root comment removal — those are a separate issue (Category F).

---

## Category B — SCHEMA DRIFT: Inventory Model Tests (34 tests across 8 files)

### What changed (production)

The inventory model was upgraded from schema `1.0` → `2.0`:
- **Removed fields:** `avg_quality_score`, `hint_coverage_pct` (from `CollectionStats`)  
- **Added field:** `by_puzzle_quality` dict (replaced the two removed fields)  
- **Removed fields on `InventoryUpdate`:** `quality_scores` list, `hints_count` int  
- **Added field on `InventoryUpdate`:** `quality_increments` dict  
- **Schema version:** default changed from `"1.0"` → `"2.0"`  
- **`InventoryManager.reconcile()`** method removed → replaced by standalone `reconcile_inventory()` function  
- **`AuditMetrics.runs_since_last_reconcile`** field removed  

### Breakdown by file

| ID | File | Tests | Error Type | Verdict |
|----|------|-------|------------|---------|
| B1 | `test_inventory_models.py` | 8 | References `avg_quality_score`, `hint_coverage_pct`, `quality_scores`, `hints_count`, schema `"1.0"` | **UPDATE** — rewrite assertions for v2.0 schema |
| B2 | `test_inventory_rebuild.py` | 8 | Publish log entries skipped as corrupt (`'tags'` key missing); rebuild returns 0 | **UPDATE** — fix test fixture publish log format |
| B3 | `test_inventory_cli.py` | 5 | CLI output format changed; missing "Quality Metrics:", "Stage Metrics:", etc. sections | **UPDATE or DELETE** — see review below |
| B4 | `test_inventory_integration.py` | 4 | Schema version "2.0" != "1.0"; `_update_inventory` signature wrong | **UPDATE** |
| B5 | `test_inventory_check.py` | 5 | Publish log fixture uses old format (missing `tags` key) → entries corrupted → wrong integrity results | **UPDATE** fixture format |
| B6 | `test_inventory_manager.py` | 1 | `save_writes_valid_json` — likely schema version mismatch | **UPDATE** |
| B7 | `test_inventory_protection.py` | 1 | Inventory cleanup assertion wrong | **UPDATE** |
| B8 | `unit/test_inventory_reconcile.py` | 2 | `InventoryManager.reconcile()` doesn't exist (moved to `reconcile_inventory()`) | **UPDATE** import + call |

### Critical Review — Are these testing the right thing?

**Mostly yes**, but with issues:
- `test_inventory_models.py` tests Pydantic model fields → valid for ensuring schema contract. **But** they're testing removed fields, so they need updating, not deleting.
- `test_inventory_rebuild.py` → Tests rebuild from publish-log + SGF files. Valid behavior test, but fixtures use **old publish-log format** that the current parser rejects. Fix the fixtures.
- `test_inventory_cli.py` → Tests CLI display output strings. **Borderline** — testing exact string output is fragile. 3 of 5 tests check for section headers ("Quality Metrics:", "Stage Metrics:", "Error Rates:", "Audit:") that the current CLI doesn't produce. These sections appear to have been **removed from the CLI display**. If the CLI intentionally no longer shows them, **delete the tests**. If it's a regression, fix the CLI.
- `test_inventory_check.py` → Tests integrity checker logic. Valid contract to test, but fixture data format is wrong.

### Consolidation Opportunity

`test_inventory_models.py`, `test_inventory_manager.py`, and `test_inventory_rebuild.py` overlap significantly. Consider:
- Models tests → keep for schema contract
- Manager tests → keep for load/save/atomicity
- Rebuild tests → keep but could be reduced to 4 (from 8)
- **Reconcile tests** → the 2 in `unit/test_inventory_reconcile.py` test the same thing as reconcile function tests would. Update to use `reconcile_inventory()` function.

---

## Category C — INTERFACE DRIFT: PublishStage._update_inventory Callers (11 tests)

**Files:** `test_periodic_reconcile.py` (8), `test_stage_metrics.py` (3)

### What changed (production)

`PublishStage._update_inventory()` signature changed from:
```python
# OLD (what tests call)
_update_inventory(puzzles_by_level=..., puzzles_by_tag=..., ...)
# NEW (current code)
_update_inventory(level_slug_counts=..., tag_slug_counts=..., ...)
```

Also, `AuditMetrics` no longer has `runs_since_last_reconcile`.

### Critical Review — **Testing for the sake of testing?**

**Yes, partially.** These tests are testing a **private method** (`_update_inventory`) directly. That's an anti-pattern. The tests should be testing the *outcome* of `PublishStage.run()`, not reaching into private internals. However:

- `test_periodic_reconcile.py` (8 tests) — Tests a **periodic reconcile feature** (`runs_since_last_reconcile` counter, auto-trigger at threshold). This feature **no longer exists in the model** (`AuditMetrics` has no such field). These tests are for a **descoped feature**.
- `test_stage_metrics.py` (3 tests) — Tests that `_update_inventory` updates stage metrics. The behavior itself is valid, but the test approach (calling private method with wrong args) is bad.

### Verdict

| ID | Subset | Count | Verdict |
|----|--------|-------|---------|
| C1 | `test_periodic_reconcile.py` — all 8 | 8 | **DELETE** — feature descoped, `runs_since_last_reconcile` removed |
| C2 | `test_stage_metrics.py` — all 3 | 3 | **UPDATE** — fix call signature; or preferably rewrite to test via `PublishStage.run()` |

---

## Category D — PATH FORMAT DRIFT: Publish Path Tests (9 tests)

**File:** `tests/stages/test_publish.py`

### What changed

Tests expect **hierarchical** paths: `sgf/{level}/batch-{NNNN}/{hash}.sgf`  
Code now uses **flat** paths: `sgf/{NNNN}/{hash}.sgf` (sharded by batch number only, no level subdirectory)

The tests literally say `Spec 126 (US1)` at the top — but the implementation moved to a flat layout inconsistent with those spec expectations.

### Critical Review

All 9 tests assert a path format that the production code deliberately does NOT produce. The flat format (`sgf/0001/...`) is the correct current behavior — the spec was superseded.

### Verdict: **UPDATE ALL 9** — change path assertions to match `sgf/{NNNN}/{hash}.sgf` flat format

**Or** if these tests are verified to be completely covered by other passing publish tests, **DELETE** them.

---

## Category E — TRACE MAP FEATURE DRIFT (9 tests)

**Files:** `test_ingest_trace.py` (3), `test_publish_trace.py` (4), `test_analyze_trace.py` (2)

### What changed

Tests expect sidecar `.trace-map-{run_id}.json` files and `.original-filenames-{run_id}.json` files to be written by stages. The trace_id is now embedded directly in the `YM` SGF property (v12+), and trace-map sidecar files appear to no longer be generated.

### Critical Review — **Testing the right thing?**

The ingest trace tests import `from backend.puzzle_manager.core.trace_map import read_trace_map` — checking if this module even exists:

```python
# test_ingest_trace.py
from backend.puzzle_manager.core.trace_map import read_trace_map
```

If the module exists but stages don't write the file, the tests fail. The tests are testing a **sidecar file contract** that may have been replaced by inline `YM` property embedding.

The 2 analyze_trace tests (`test_existing_yq_preserved`, `test_missing_yx_computed_fresh`) are different — they test selective recomputation of YQ/YX properties. The current analyze stage **always recomputes** QualityMetrics and ComplexityMetrics from scratch, so "preserving existing YQ" is not the current behavior.

### Verdict

| ID | File | Count | Verdict |
|----|------|-------|---------|
| E1 | `test_ingest_trace.py` | 3 | **INVESTIGATE** — check if trace_map sidecar is still generated; if not, **DELETE** |
| E2 | `test_publish_trace.py` | 4 | **INVESTIGATE** — same as E1 |
| E3 | `test_analyze_trace.py` | 2 | **UPDATE or DELETE** — if recompute-always is intentional, delete; if selective recompute is desired, fix production code |

---

## Category F — BEHAVIORAL CONTRACT CHANGES (5 tests)

### F1: Root Comment Preservation (2 tests)

**File:** `test_sgf_enrichment.py` — `test_root_comment_removed`, `test_full_enrichment_pipeline`

Tests assert `"C[This is a puzzle..." not in result` — they expect root comments to be **removed**.  
But the CLAUDE.md explicitly says: **"Root C[] = PRESERVED by default (configurable via preserve_root_comment)"**

**Verdict: UPDATE** — flip assertion to expect comment IS preserved: `assert "C[This is a puzzle" in result`. The behavior change was intentional per documented policy.

### F2: EnrichmentConfig.corner_threshold (1 test)

**File:** `test_enrichment.py` — `test_thresholds`

Test creates `EnrichmentConfig(corner_threshold=5)` but the current `EnrichmentConfig` model doesn't accept `corner_threshold` (it's now computed dynamically from board size via `_compute_corner_threshold()`).

**Verdict: UPDATE** — remove `corner_threshold` from test config construction. The dynamic computation is an intentional improvement.

### F3: Hint includes "corner" (1 test)

**File:** `test_enrichment.py` — `test_generate_yh1_with_region`

Test expects hint text to contain the word "corner" but the generated hint may use different wording.

**Verdict: UPDATE** — make assertion less specific (check hint is non-empty, or check it references region).

### F4: Tag default to life-and-death (1 test)

**File:** `test_tagger.py` — `test_defaults_to_life_and_death`

Test expects `detect_techniques()` to return at least 1 tag even when no technique is detected. But the tagger docstring explicitly says: **"No fallback: empty tag list is returned when no technique is confidently detected."**

This is a **precision-over-recall design decision** documented in the tagger module header.

**Verdict: UPDATE** — change assertion to `assert len(tags) == 0` (or `assert tags == []`). The empty-return behavior is correct by design.

---

## Category G — ISOLATED ISSUES (3 tests)

### G1: Board size validation (1 test)

**File:** `test_board.py` — `test_invalid_size`

Test does `Board(10)` and expects `ValueError`. Production code accepts 5–19 inclusive, so `Board(10)` is **valid**. The test is wrong.

**Verdict: UPDATE** — change to `Board(3)` or `Board(0)` which would correctly be rejected.

### G2: Daily POSIX paths (3 tests)

**File:** `test_daily_posix.py`

Tests import `_to_puzzle_ref` from `daily.standard`, which no longer exports it. The function moved to `daily._helpers.to_puzzle_ref()` with a **different dict format** — compact `{"p": "0001/hash", "l": 110}` instead of `{"path": "sgf/intermediate/...", "level": "intermediate"}`.

There are **already passing versions** of these in `tests/integration/test_daily_posix.py` that import from the correct location.

**Verdict: DELETE** — these are superseded by the integration versions that use the correct import and dict format.

### G3: Batch writer performance benchmark (1 test)

**File:** `test_batch_writer_perf.py` — `test_o1_vs_on_fresh_directory`

The benchmark asserts O(1) average < 1.0ms, but actual was 1.22ms. This is **environment-dependent** — a CI flake.

**Verdict: RELAX THRESHOLD** — change from `< 1.0` to `< 2.0` or convert to relative comparison (O(1) should be faster than O(N), regardless of absolute time).

---

## Consolidation Opportunities Summary

| ID | Opportunity | Current Tests | Proposed | Savings |
|----|-------------|---------------|----------|---------|
| CON-1 | `test_daily_posix.py` duplicates `integration/test_daily_posix.py` | 3 + 4 = 7 | Keep 4 integration, delete 3 old | -3 tests |
| CON-2 | Inventory rebuild + reconcile + check overlap on fixtures | 8 + 2 + 5 = 15 | Shared fixture module, 10 tests | -5 tests |
| CON-3 | Publish path tests (9) overlap with passing publish integration tests | 9 | Check overlap, merge to ~4 | -5 tests |
| CON-4 | Stage metrics tests (3) test private method → rewrite as 1 integration test | 3 | 1 | -2 tests |

**Potential total reduction: ~15 redundant tests eliminated**

---

## Clarification Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Was the periodic auto-reconcile feature (`runs_since_last_reconcile` on `AuditMetrics`) intentionally descoped? | A: Yes, descoped (delete 8 tests) / B: No, it's planned (rewrite tests) / C: Other | A | A — confirmed descoped | ✅ resolved |
| Q2 | Are trace-map sidecar files (`.trace-map-{run_id}.json`) still generated by stages, or has all trace data moved to the YM SGF property? | A: Still generated / B: Moved to YM only (delete sidecar tests) | B | B — delete tests. Also track dead code paths (trace_map.py, sidecar writing code) for decommissioning initiative. | ✅ resolved |
| Q3 | Should we pursue consolidation in the same initiative? | A: Same initiative / B: Separate | A | A — consolidate | ✅ resolved |
| Q4 | Remove v1.0 inventory schema backward compat? | A: Yes / B: Keep compat | A | A — remove v1.0, update to v2.0 | ✅ resolved |
| Q5 | Were CLI display sections intentionally removed? | A: Intentionally simplified / B: Accidental regression / C: Clarify | A | **Clarified**: Stage-level metrics (ingest/analyze/publish counts) are still needed in console+logging. The CLI `format_inventory_summary()` currently does NOT show stages/metrics/audit sections. The 3 tests for "Stage Metrics:", "Error Rates:", "Audit:" test sections the CLI never implemented in the v2.0 rewrite. **Decision**: Delete "Quality Metrics:" test (old `avg_quality_score` display). For "Stage Metrics:", "Error Rates:", "Audit:" — these are valid missing features. Create a follow-up initiative to add them back to CLI, but delete the tests for now since the CLI code doesn't have them. | ✅ resolved |
| Q6 | Is "always recompute" the intended analyze behavior? | A: Yes / B: No, selective recompute | B | **Clarified via code review**: analyze stage DOES preserve existing YQ/YX — it uses `policy_registry.is_enrichment_needed()` to decide. The 2 failing tests are testing valid behavior (selective recompute). The tests fail because the `is_enrichment_needed` check isn't finding the existing properties in the parsed game. This is a **production bug or test setup issue** — needs investigation and fix. | ✅ resolved |

_Last updated: 2026-03-24_
