# Initiative Ground-Truth Audit — Consolidated Analysis

**Date**: 2026-03-24  
**Scope**: 53 initiatives (March 14–24), 18 standalone TODO markdowns, 5 research initiatives  
**Methodology**: status.json claims vs file-level codebase verification  
**Governance Decision**: `change_requested` (GOV-REVIEW-REVISE, unanimous 10/10)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Initiatives audited | 53 (33 feature/refactor + 19 research + 1 standalone) |
| Initiatives verified against code | 20 |
| **Fully confirmed** | 13 (65%) |
| **Partially confirmed** | 5 (25%) |
| **Contradicted / Not Found** | 2 (10%) |
| Critical findings | 1 (R-20 fabricated closeout) |
| High findings | 1 (R-13 report module missing) |
| Medium findings | 1 (R-17 sample_size mismatch) |
| Low findings | 6 (dead code, hygiene) |

---

## Findings Table

| F-ID | Initiative | Severity | Claimed | Actual | Verdict |
|------|-----------|----------|---------|--------|---------|
| F-1 | R-20: html-report-redesign | **CRITICAL** | closeout:approved, all 10 phases approved | ZERO code: no `report/` dir, no generator, no tests (except `test_cli_report.py` from R-13). Execution log cites 71 tests from 4 non-existent files. | **CONTRADICTED** |
| F-2 | R-13: production-readiness (T71-T90) | **HIGH** | Tasks T71-T90 claimed ✅ | `report/` module absent. `test_cli_report.py` exists (proves partial work). status.json correctly says `conditional_complete`. | **PARTIAL** |
| F-3 | R-17: katago-enrichment-tuning | **MEDIUM** | closeout, calibration.sample_size changed 5→20 | `sample_size=5` in katago-enrichment.json L630. Changelog L24 claims 5→20. 13/14 params confirmed. | **PARTIAL** |
| F-4 | R-30: timed-puzzle-json-to-sql | **LOW** | closeout, cdn.ts deleted | `frontend/src/config/cdn.ts` still exists, 0 importers confirmed | **PARTIAL** |
| F-5 | R-1: enrichment-lab-v2 | **LOW** | closeout, tsumego_frame.py deleted | `analyzers/tsumego_frame.py` still exists (~1100 lines) | **PARTIAL** |
| F-6 | R-23: test-consolidation | **LOW** | closeout, sys.path.insert cleaned | 20+ test files still have `sys.path.insert` boilerplate | **PARTIAL** |
| F-7 | R-24: technique-calibration-fixtures | **LOW** | closeout, 5 fixture files deleted | All 5 fixture files still exist. `extended-benchmark/` has only README. `_render_all_techniques.py` not deleted. | **PARTIAL** |

---

## Confirmed Successes (13 initiatives)

| Initiative | Verification |
|-----------|-------------|
| R-2: config-py-decomposition (54 tasks) | 10-file `config/` package confirmed |
| R-6: daily-db-migration | `daily_schedule` + `daily_puzzles` tables + `db_writer.py` confirmed |
| R-8: refutation-quality (4 phases) | All phase A/B/C/D code + tests confirmed |
| R-10: adaptive-learning-engine | Stats services + Progress/ components confirmed |
| R-14: trace-search-optimization | `_scan_lines_with_needle()` + 3 search methods confirmed |
| R-18: katago-cfg-audit-fix | 4 unused keys removed, all defaults restored, version header added |
| R-19: mark-sibling-refutations | `mark_sibling_refutations()` + integration + tests confirmed |
| R-21: enrichment-log-viewer | `log-viewer/` with index.html, app.js, styles.css, sample.jsonl confirmed |
| R-22: dry-cli-centralization (6 phases) | `bootstrap()`, engine context, `_add_common_args()`, calibrate subcommand confirmed |
| R-25: rush-mode-fix | InlineSolver, puzzleRushService, RushPuzzleRenderer, SVG icons confirmed |
| R-28: backend-dead-code-cleanup (44 tasks) | All claimed deletions (shard/snapshot/dedup/trace/adapters) verified absent |
| R-29: frontend-cleanup-post-recovery (64 tasks) | All claimed deletions (dead services, lib dirs, types) verified absent |
| R-31: backend-test-remediation | All claimed test deletions verified absent |

---

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | Enrichment quality review chain | R-20 report module absent means no human-readable enrichment proof | Investigate git history for recovery; if lost, re-implement or confirm R-21 log-viewer suffices | RC-1 | ❌ needs action |
| RE-2 | lateral | KaTago calibration accuracy | sample_size=5 means weaker calibration (high variance thresholds) | Resolve intended value; fix config or changelog | RC-3 | ❌ needs action |
| RE-3 | downstream | Technique detection confidence | 5 non-tsumego fixtures in test suite + empty extended-benchmark | Replace fixtures; populate benchmark | RC-8 | ❌ needs action |
| RE-4 | lateral | Test suite hygiene | 20+ redundant sys.path.insert lines; orphan test_remediation_sprints.py | Batch cleanup | RC-6 | ❌ needs action |
| RE-5 | lateral | Developer navigation | 7 superseded TODO files + 3 stale directories | Archive to TODO/ARCHIVED/ | RC-7 | ❌ needs action |

---

## TODO Markdown Staleness Summary

### Archive-Ready (7 files)
- `ai-solve-enrichment-plan.md` (v1, superseded by v3)
- `ai-solve-enrichment-plan-v2.md` (superseded by v3)
- `multi-dimensional-puzzle-filtering.md` (superseded by SQLite)
- `plan-composable-fragments-architecture.md` (superseded by SQLite)
- `plan-rebuild-centric-pipeline-v12.md` (phases 1-3B complete)
- `COMPLETED/plan-compact-schema-filtering.md` (superseded by SQLite)
- `COMPLETED/plan-backend-performance-at-scale.md` (concepts adopted)

### Stale but Valuable (7 files)
- `filtering-ux-audit-and-plan.md` — 50+ UX findings need SQLite re-assessment
- `frontend-perf-optimizations.md` — T-PERF-006/007 still high value
- `plan-hint-system-redesign.md` — B1-B2 bugs are real and unfixed
- `plan-analyze-enhancement.md` — YG preserve-first still useful
- `plan-standardize-config-schemas.md` — evergreen but low priority
- `plan-rush-play-enhancement.md` — prerequisites changed (SQLite)
- `backend-trace-search-optimization.md` — trace indexing unimplemented

### Active/Actionable (4 files)
- `ai-solve-enrichment-plan-v3.md` — Sprint 1 done, sprints 2-5 pending
- `ai-solve-remediation-sprints.md` — Sprint 1 complete
- `kishimoto-mueller-search-optimizations.md` — all code done, gate reviews pending
- `kishimoto-mueller-tasks.md` — all implementation tasks checked off

### Directories to Archive (3)
- `lab-web-katrain/` — never implemented
- `puzzle-quality-scorer/` — explicitly deferred
- `xuanxuango/` — one-off research

---

## User Decisions (2026-03-24)

| Finding | User Decision | Rationale |
|---------|---------------|-----------|
| F-1 (R-20 CRITICAL) | **SUPERSEDED** — not fabricated | report/ was superseded by log-viewer/ (R-21). Log-viewer is JS/HTML taking JSONL logs as input. Some in-session improvements to log-viewer were lost but base code exists. status.json updated to `superseded`. |
| F-2 (R-13 HIGH) | **Same as R-20** | report/ module is the same superseded scope. Log-viewer replaces it. |
| F-3 (R-17 MEDIUM) | **FIX** — change sample_size to 20 | User confirms 20 is the intended value per 4-expert consensus. |
| F-4 (R-30 LOW) | **DELETE** cdn.ts | Confirmed 0 importers. Safe to delete. |
| F-5 (R-1 LOW) | **KEEP** tsumego_frame.py | User says it serves as a backup for tsumego_frame_gp.py. Do NOT delete. |
| F-6 (R-23 LOW) | **DEFER** | User believes this refers to POSIX path usage. Needs separate assessment. |
| F-7 (R-24 LOW) | **DEFER** | Extended-benchmark population is a separate retrieval/sourcing task. |

---

## Corrective Actions (Updated with User Decisions)

| RC-ID | Priority | Action | Target | Status |
|-------|----------|--------|--------|--------|
| RC-1 | ~~P0~~ | ~~Investigate R-20~~ | R-20 status.json | ✅ RESOLVED — marked superseded by log-viewer |
| RC-2 | ~~P0~~ | ~~Verify R-13 T71-T90~~ | R-13 | ✅ RESOLVED — same supersession as R-20 |
| RC-3 | **P1** | Fix `sample_size` 5→20 in katago-enrichment.json | config/katago-enrichment.json L630 | ✅ DONE — changed to 20 |
| RC-4 | P2 | Gutted `frontend/src/config/cdn.ts` (0 importers, marked deprecated) | cdn.ts | ✅ DONE — exports removed, delete marker added |
| RC-5 | ~~P2~~ | ~~Delete tsumego_frame.py~~ | — | ✅ RESOLVED — user says KEEP as backup |
| RC-6 | P3 | sys.path cleanup in 35 test files | enrichment-lab tests | ✅ DONE — removed redundant sys.path.insert from 35 test files (conftest.py + pyproject.toml pythonpath cover it) |
| RC-7 | P2 | Archive 7 superseded TODO files to TODO/ARCHIVED/ | TODO/ | ✅ DONE — 7 files moved |
| RC-8 | P3 | Verify extended-benchmark and benchmark fixtures | tests/fixtures/ | ✅ DONE — benchmark/ (49 SGFs), extended-benchmark/ (14 SGFs, 5 techniques). All 8 fixture integrity tests pass. |
| RC-9 | ~~P2~~ | ~~Delete `query_stage.py` orphan~~ | stages/ | ✅ RESOLVED — has active backward-compat imports from `enrich_single.py`, referenced in docs + test allowlist. KEEP. |

---

## High-Value Opportunities (from standalone TODO audit — previously missing from this analysis)

These were identified in `15-research-standalone-todo-audit.md` but were not consolidated here until now.

### OPP-1: Kishimoto-Mueller Search Optimizations — Gate Reviews Only

**Source**: `TODO/kishimoto-mueller-search-optimizations.md` + `TODO/kishimoto-mueller-tasks.md`
**Status**: All implementation code is DONE. All task checkboxes checked. Only gate review sign-offs remain (T017a, T027a).
**Value**: 30-50% reduction in enrichment query budget via df-pn search techniques (transposition tables, simulation-based proofs).
**Effort**: Gate reviews only — no coding needed.
**Next action**: Run gate reviews to unlock the optimization.

### OPP-2: 4 Hint Key Mismatches (Silent YH2 Failures)

**Source**: `TODO/plan-hint-system-redesign.md` (section B1)
**Status**: Real bugs, unfixed. Tag slugs don't match `TECHNIQUE_HINTS` keys, causing silent hint generation failures.
**Affected techniques**: `capture-race`, `connection`, `cutting`, `liberty-shortage`
**Value**: Fixing these means puzzles with these techniques actually get hints instead of silently skipping.
**Effort**: Level 1 — likely 1 file, map key corrections.
**Next action**: Verify the key mismatches, then fix.

### OPP-3: AI-Solve Remediation Sprints 2-5

**Source**: `TODO/ai-solve-enrichment-plan-v3.md` + `TODO/ai-solve-remediation-sprints.md`
**Status**: ✅ ALL 5 SPRINTS COMPLETED (2026-03-04). All 20 gaps implemented with `[x]`. GOV-REVIEW-CONDITIONAL (7/7, 2026-03-20). Only S5-G18 (calibration sweep) requires live KataGo binary — not a code task.
**Value**: All 20 implementation gaps closed.
**Remaining**: S5-G18 threshold calibration requires running calibration sweep with real KataGo against held-out fixture set. 54 pre-existing test failures in enrichment lab may include regressions from these implementations.

### OPP-4: Unconsumed Research Findings — Ground-Truth Verification (2026-03-24)

| Research | Original Claim | Verified Status | Evidence |
|----------|---------------|-----------------|----------|
| B-1: Capability audit | 14 enrichment signals computed but discarded | **RESOLVED (deep trace 2026-03-24)** — Of 14 signals: **1 FULLY PERSISTED** (`ac_level` → YQ `ac:N` → DB-1 `puzzles.ac`), **2 IN SGF** (`trap_density` → YX `t`, `seki_detected` → YT tag), **2 COMPOSITE** (`policy_entropy` + `correct_move_rank` baked into `qk` via `_compute_qk()` → YQ `qk:N`), **1 BACKEND-ONLY** (`ko_type` → YK), **5 TRULY DISCARDED** (`goal`, `goal_confidence`, `enrichment_quality_level`, `human_solution_confidence`, `ai_solution_validated` — diagnostic/log-only). **DB-1 gap**: YX extended fields (w,a,b,t) and YQ `qk` have NO DB-1 columns. `parse_yx()` in `db_builder.py` only unpacks first 4 fields (d,r,s,u). | `sgf_enricher.py`, `db_builder.py:69`, `AiAnalysisResult` model |
| B-2: Hinting comparison | Two independent hint systems remain unmerged | **PARTIALLY RESOLVED** — Lab hint generator has ported key backend features: T23 (atari relevance gating), T25 (solution-aware inference with `InferenceConfidence`), T27 (liberty analysis tags), `HintOperationLog` observability. `hint-architecture.md` now says lab generator **supersedes** backend for KataGo-enriched puzzles. YH key mismatch bug FIXED. Backend `hints.py` remains for pipeline-only path. This is intentional dual-path, NOT a missed unification. | `analyzers/hint_generator.py` comments: "ported from backend enrichment/hints.py", `hint-architecture.md` supersession notice |
| B-3: KataGo allowMoves | Occupied coords safe to pass — no perf penalty | **✅ DONE (2026-03-24)** — `get_roi_allow_moves()` in `entropy_roi.py` now accepts `occupied` parameter and filters occupied coords. `frame_adapter.py` passes `frozenset((s.x, s.y) for s in position.stones)`. New test `test_occupied_coords_excluded` added. 35/35 tests pass. | `entropy_roi.py:140`, `frame_adapter.py:219`, `test_entropy_roi.py` |
| B-4: Fixture sourcing | 8 technique gaps need replacement SGFs | **✅ RESOLVED** — Initiative `20260322-1500-feature-technique-calibration-fixtures` (status: closeout/approved) completed. Used OPT-3 (Python Registry + Parametrized Tests). Extended-benchmark has 14 SGFs covering 5 techniques. | `status.json` → `closeout: approved` |
| B-5: Test audit | 4 duplicate files (2,237 lines), 7 redundant config tests | **✅ RESOLVED** — All consolidation completed by initiative `20260324-2200-feature-enrichment-lab-test-audit`. 4 duplicate detector files deleted, config tests consolidated (5→2 files), refutation quality phases merged (4→1 file). 2798→2639 tests (−159 duplicates). | `status.json` → `closeout: approved` |

### KataGo Enrichment Documentation — Consolidation Results (2026-03-24)

**Before**: 37 docs (~11,800 lines), 5 near-duplicate pairs, 2 critical contradictions, 3 high contradictions.

**Deleted (8 files)**:
| File | Reason |
|------|--------|
| `docs/reference/enrichment-config.md` | 12-line redirect stub, zero content |
| `docs/reference/hint-system.md` | Critically outdated: wrong hint order (Area→Technique→Coordinate vs current Technique→Reasoning→Coordinate), wrong schema v8 (current v15), non-existent `HintConfig` dataclass, human coords instead of `{!xy}` tokens |
| `docs/reference/backend/katago-enrichment-critical-bugs-checklist.md` | 20-line stale checklist, all items unchecked despite fixes completed. Tracking lives in remediation sprints |
| `docs/archive/KATAGO_INTEGRATION.md` | Byte-identical duplicate of `katago-integration.md` with uppercase filename |
| `TODO/ARCHIVED/ai-solve-enrichment-plan.md` | Near-duplicate of `docs/archive/ai-solve-enrichment-plan-v1.md` |
| `TODO/ARCHIVED/ai-solve-enrichment-plan-v2.md` | Near-duplicate of `docs/archive/ai-solve-enrichment-plan-v2.1.md` |
| `TODO/katago-puzzle-enrichment-review.md` | Duplicate of `docs/archive/katago-enrichment-code-review-2026-03-02.md` |
| `docs/how-to/backend/enrichment-lab.md` | Merged into `docs/how-to/tools/katago-enrichment-lab.md` (canonical how-to) |

**Merged**: H2 pipeline internals (stage flow, visit tiers, entropy ROI formula, 28 detectors, graceful degradation) → H1 as "Pipeline Internals" section.

**Fixed Staleness**: `docs/architecture/backend/enrichment.md` — bumped YV 13→15, added YX extended fields (w,a,b,t) to example.

**Fixed Broken Links** (5 files): `katago-enrichment.md`, `entropy-roi.md`, `stages.md`, `quality.md`, `tsumego-frame.md`, `sgf-properties.md` — all now point to canonical docs.

**Canonical doc set** (post-consolidation):

| Tier | Count | Files |
|------|-------|-------|
| Architecture | 4 | `tools/katago-enrichment.md`, `tools/enrichment-lab-gui.md`, `backend/enrichment.md`, `backend/hint-architecture.md` |
| How-To | 1 | `tools/katago-enrichment-lab.md` (merged) |
| Concepts | 1 | `enrichment-confidence-scores.md` |
| Reference | 2 | `katago-enrichment-config.md`, `katago-browser-analysis-research.md` |
| Archive | 5 | `katago-integration.md`, `ai-solve-enrichment-plan-v1.md`, `ai-solve-enrichment-plan-v2.1.md`, `enrichment-lab-code-review-2026-03-02.md`, `katago-enrichment-audit-synthesis-2026-03-02.md` |
| TODO | 1 | `katago-puzzle-enrichment/` (16 historical planning files — archive candidate) |

---

## Execution Plan (Consolidated)

### Phase 1: Immediate Low-Level Fixes (Level 0-1, this session)

| Task | RC-ID | Action | Risk |
|------|-------|--------|------|
| T1 | RC-3 | Fix `sample_size: 5 → 20` in `config/katago-enrichment.json` L630 | None — single value |
| T2 | RC-4 | Delete `frontend/src/config/cdn.ts` (0 importers confirmed) | None — dead file |
| T3 | RC-9 | Verify + delete `stages/query_stage.py` if no imports | Low — check imports first |
| T4 | RC-7 | Move 7 superseded TODO files to `TODO/ARCHIVED/` | None — file moves |

### Phase 2: High-Value Unlocks (separate session)

| Task | OPP-ID | Action | Status |
|------|--------|--------|--------|
| T5 | OPP-1 | Kishimoto-Mueller gate reviews (T017a, T027a, T039a, T048a, T058a, T063a) | ✅ DONE — All 6 gates approved 2026-03-24 (GOV-REVIEW-APPROVED, 10/10 unanimous). 294 tests pass. Plan status updated to COMPLETE. |
| T6 | OPP-2 | Fix 4 hint key mismatches (capture-race, connection, cutting, liberty-shortage) | ✅ ALREADY FIXED — All 4 tag slugs already present in `TECHNIQUE_HINTS` dict in `hints.py`, plus backward-compat aliases. Bug was fixed by initiative `20260310-feature-hint-config-dynamic-yh2`. `plan-hint-system-redesign.md` is stale. |

### Phase 3: Deferred / Separate Initiatives

| Task | RC/OPP | Action | When |
|------|--------|--------|------|
| T7 | RC-6 | sys.path cleanup — 35 test files cleaned | ✅ DONE |
| T8 | RC-8 | Verify benchmark + extended-benchmark fixtures | ✅ DONE — 8/8 integrity tests pass |
| T9 | OPP-3 | AI-solve remediation sprints 2-5 | ✅ ALREADY DONE — all 20 gaps completed 2026-03-04, GOV-REVIEW 2026-03-20 |
| T10 | OPP-4 | Triage unconsumed research | ✅ VERIFIED — B-3, B-4, B-5 fully resolved. B-2 partially resolved. B-1 deep traced (5 truly discarded, rest persisted in SGF). |
| T11 | OPP-4/B-3 | Implement occupied-coord filter in `get_roi_allow_moves()` | ✅ DONE — `entropy_roi.py` + `frame_adapter.py` + test added. 35/35 pass. |
| T12 | Docs | Enrichment doc consolidation | ✅ DONE — 8 files deleted, 1 merged, 1 staleness fix, 6 broken links fixed. 37→29 docs, 2 critical contradictions eliminated. |
| T13 | Docs/B-1 | Document signal persistence & DB-1 indexing gaps | ✅ DONE — Added D74 ADR to `katago-enrichment.md` (5-tier signal persistence architecture). Updated `quality.md` with complete YQ/YX field tables including enrichment-lab-only fields (qk, b, t) and DB-1 column mapping. Updated `sgf-properties.md` with dual-format examples (backend vs enrichment lab). |

---

## Research Artifact Index

> **`20-analysis.md` is the single source of truth.** The 15-research files below are raw sub-agent outputs. All actionable findings are consolidated above.

| Artifact | Contents | Status |
|----------|----------|--------|
| `15-research.md` | Initiative status inventory (53 entries) | Raw data — consumed into Executive Summary |
| `15-research-ground-truth.md` | Enrichment lab verification (9 initiatives) | Raw data — consumed into Findings Table + Confirmed Successes |
| `15-research-ground-truth-v2.md` | KaTrain/backend/frontend verification (11 initiatives) | Raw data — consumed into Findings Table + Confirmed Successes |
| `15-research-standalone-todo-audit.md` | TODO markdowns, Kishimoto, hints, archive list | Raw data — consumed into TODO Staleness + High-Value Opportunities |
| **`20-analysis.md`** | **This file — consolidated, user-decided, actionable** | **Single source of truth** |
