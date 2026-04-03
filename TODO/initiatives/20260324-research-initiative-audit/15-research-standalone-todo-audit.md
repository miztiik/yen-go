# Research Brief: Standalone TODO Files & Recent Research — Actionability & Staleness Audit

> **Initiative**: 20260324-research-initiative-audit
> **Date**: 2026-03-24
> **Artifact**: `15-research-standalone-todo-audit.md`
> **Scope**: 18 standalone TODO markdowns, 6 TODO sub-directories, 5 recent research initiatives
> **Goal**: Identify stale, superseded, and actionable items for planner prioritization

---

## 1. Research Question and Boundaries

**Question**: Which standalone TODO files are stale/superseded/completed vs. still actionable? Which recent research initiatives have unconsumed findings?

**Boundaries**:
- First 80 lines of each standalone TODO file read for status/date/content
- Directory listings for sub-project TODOs
- Full read of 5 recent research initiative `15-research.md` files
- Cross-referenced against codebase evidence (grep for implementation signals)

---

## Part A: Standalone TODO Markdowns

| R-ID | File | Status | Last Updated | Key Action Items Remaining | Implemented |
|------|------|--------|-------------|---------------------------|-------------|
| A-1 | `ai-solve-enrichment-plan.md` | **Superseded** | 2026-03-03 | None — superseded by v2 then v3 | No (v1 never implemented; design only) |
| A-2 | `ai-solve-enrichment-plan-v2.md` | **Superseded** | 2026-03-03 | None — superseded by v3 | No (v2 never implemented; design only) |
| A-3 | `ai-solve-enrichment-plan-v3.md` | **Active (blocked)** | 2026-03-04 | 220 tests pass but 20 gaps found; see remediation sprints. Review Panel gates pending. | Partial — scaffolding complete, gaps identified |
| A-4 | `ai-solve-remediation-sprints.md` | **Active** | 2026-03-04 | Sprint 1 all 5 items marked `[x]` complete (GOV-REVIEW-CONDITIONAL 2026-03-20, 7/7). Sprint 2-5 status unknown (need deeper read). | Partial — Sprint 1 done |
| A-5 | `backend-trace-search-optimization.md` | **Stale** | 2026-02-24 | All 4 steps not started. String pre-filter + JSON indexes for trace search. | Partial — `parse_root_properties_only()` exists (D4 from perf plan), but the trace search indexing (Steps 2-4) is NOT implemented. Initiative `20260319-1000-feature-trace-search-optimization` exists. |
| A-6 | `filtering-ux-audit-and-plan.md` | **Stale** | 2026-02-25 | 50+ UX gaps identified (sort, filter by status, emoji removal, tag multi-select). SQLite architecture has since replaced view-file approach. | No — audit findings not actioned. Architecture shifted to SQLite; many items need re-assessment against DB-backed queries. |
| A-7 | `frontend-perf-audit.md` | **Partially actioned** | 2026-02-15 | T-PERF-001 (memo): DONE — `SolverView` wrapped in `memo()`. T-PERF-002-008: Not started. | Partial — T-PERF-001 implemented (confirmed `export default memo(SolverView)`). Board shadow T01 also partially actioned. |
| A-8 | `frontend-perf-optimizations.md` | **Stale** | 2026-02-24 | Extracted from audit. T-PERF-002 (audio defer), T-PERF-004 (CSS transitions), T-PERF-006 (code splitting), T-PERF-007 (vendor chunks), T-PERF-008 (app.tsx decomp). | No |
| A-9 | `hinting-unification-transition-plan-v1.md` | **Stale** | 2026-03-04 | Contract-first integration (DD-1 through DD-6), parity tests, replacement readiness metric. Two independent systems still exist. | No — both systems remain independent. Research `20260318-research-hinting-system-comparison` confirmed divergence. |
| A-10 | `kishimoto-mueller-search-optimizations.md` | **Active** | 2026-03-04 | 5 design decisions (DD-KM1 through KM5). Adapts df-pn search techniques for 30-50% query budget reduction. Pending Review Panel approval. | Partial — config extension (Phase 2) all done, Phases 3-6 code complete per tasks file. Gate reviews pending. |
| A-11 | `kishimoto-mueller-tasks.md` | **Active** | 2026-03-04 | Phase 2 (config): all T003-T017 `[x]`. Phase 3 (transposition): T018-T027 `[x]`. Phase 4 (simulation): T028-T038 `[x]`. Gate reviews T017a, T027a pending. | Yes (code) — all implementation tasks checked off. Only gate reviews remain. |
| A-12 | `multi-dimensional-puzzle-filtering.md` | **Superseded** | 2026-02-17 | Superseded by `plan-compact-schema-filtering.md` (now in COMPLETED/). Further superseded by SQLite architecture. | Partial — concept implemented via different architecture (SQLite DB-1 with SQL queries vs. client-side array filtering). |
| A-13 | `plan-analyze-enhancement.md` | **Stale** | 2026-02-22 | 8 changes: YG preserve-first, comment cleaning, ko enum alignment, CJK stripping, dead code removal. All "Not Started". | No |
| A-14 | `plan-composable-fragments-architecture.md` | **Superseded** | 2026-02-22 | Was "Snapshot-Centric Query Architecture Plan V2". P0-P5 implemented; P2-P3 architect-reviewed but no staff review. Phase tracking shows gates OPEN. | Partial — P0-P5 implemented, gates open. Superseded by SQLite migration (`20260313-2200-feature-sqlite-puzzle-index`). View/shard system replaced by DB-1. |
| A-15 | `plan-hint-system-redesign.md` | **Stale** | 2026-02-22 | Phase 1: 4 key-mismatch bug fixes + tagger `capture-race` false positive. Phase 2-5: full hint tier redesign. | No — B1 key mismatches, B2 tagger bug, full redesign all unstarted. |
| A-16 | `plan-rebuild-centric-pipeline-v12.md` | **Completed** | 2026-02-20 | Was full architectural rewrite. Phase 1-2 complete (YM property + trace elimination). Phase 3A+3B complete (inventory + PipelineLock). Phases 5-6 pending (unclear). | Mostly — Phase 1-3B complete with staff review. `parse_pipeline_meta()` and `PipelineLock` confirmed in codebase. |
| A-17 | `plan-rush-play-enhancement.md` | **Superseded/Stale** | 2026-02-17 | Depends on `plan-compact-schema-filtering.md` Phases 0-8 (now superseded by SQLite). Level selection bug, duration slider, tag filter. | Partial — Rush mode exists and is functional. Level selection bug may still exist. SQLite path changed prerequisites. |
| A-18 | `plan-standardize-config-schemas.md` | **Stale** | 2026-02-18 | 4 new schemas, metadata standardization across 10 config files, field renames, README rewrite. | No |
| A-19 | `solver-ui-polish.md` | **Partially actioned** | 2026-02-17 | 13 tasks (T01-T14). T01 board shadow: appears done. T03 toolbar: unknown. T06 duplicate sound: unknown. | Partial — T01 board shadow confirmed via CSS evidence. Other tasks unverified. |

### Part A.2: TODO Sub-Directories

| R-ID | Directory | Contents | Status | Notes |
|------|-----------|----------|--------|-------|
| A-20 | `katago-puzzle-enrichment/` | 15 files: 8 ADRs (001-011), research docs, README, results | **Archive-worthy** | Rich design history for enrichment lab. ADR 008 (ai-solve) and 009 (KM optimizations) still referenced by active plans. |
| A-21 | `lab-web-katrain/` | 12 files: product scope, architecture, implementation plan, milestones, contracts, schemas | **Stale** | Planned browser-based KaTrain. Never implemented. Research reference only. |
| A-22 | `puzzle-quality-scorer/` | 3 files: implementation plan, README, reference dir | **Stale** | Quality scoring research. Referenced by capability audit but explicitly deferred. |
| A-23 | `puzzle-quality-strategy/` | 4 files: research, implementation plan, D2 classifier research, README | **Stale** | Quality strategy research. D2 classifier improvement explicitly deferred. |
| A-24 | `xuanxuango/` | 1 file: 2026-03-04 solver research | **Stale** | Xuan Xuan Qi Jing Go solver research. One-off investigation. |
| A-25 | `COMPLETED/` | 2 files: `plan-backend-performance-at-scale.md`, `plan-compact-schema-filtering.md` | **Completed** | Backend perf plan (0% status but concepts partially adopted). Compact schema plan (~39% complete, superseded by SQLite). |

---

## Part B: Recent Research Initiatives (March 14-24)

| R-ID | Research ID | Topic | Key Finding | Consumed By | Pending Actions |
|------|-------------|-------|-------------|-------------|-----------------|
| B-1 | `20260317-research-capability-audit` | Comprehensive YenGo capability inventory | 24 production frontend features, 11 backend capabilities, 7 partially-built features. 14 computed enrichment signals discarded before output. Highest-value gap: enrichment quality self-assessment (H5). | Meta-research — informed prioritization broadly. `15-research-ng-gap-audit.md` found Benson's algorithm implemented but no alpha-beta/minimax search. `15-research-enrichment-lab-accretion.md` found 14 computed signals not making it to final output. | Q1: Should discarded signals populate DB-1 `attrs`? Q2: Achievement system UI needs building. Q3: Statistics page needs building. |
| B-2 | `20260318-research-hinting-system-comparison` | Backend vs. Lab hint system comparison | Lab has engine-derived advantages (DetectionResult evidence, instinct, level-adaptive). Backend has board-simulation advantages (atari verification, liberty analysis). 30 structured comparison rows across input signals, output format, and unique capabilities. | Transition plan `hinting-unification-transition-plan-v1.md` references this. No implementation initiative consumed it. | Q4: Two independent systems remain. Research provides comparison matrix needed for consolidation. |
| B-3 | `20260319-research-katago-allowmoves-occupied` | KataGo behavior with occupied coords in allowMoves | **Confirmed safe**: KataGo silently ignores occupied coordinates. Source code proof: legality check happens BEFORE `avoidMoveUntilByLoc` filtering. No performance penalty beyond trivially wasted policy mass (~0.1%). | Directly actionable for `entropy_roi.py` (E-1b lacks occupancy filtering). | Q5: Low-priority optimization — filter occupied coords in `get_roi_allow_moves()`. Not a correctness bug. |
| B-4 | `20260322-research-external-sources-fixture-sourcing` | External-sources inventory for calibration fixture replacement | `goproblems_difficulty_based/` is A+ quality (technique×difficulty pre-categorized, rich metadata). 16 collections inventoried. 8 technique gaps identified for fixture replacement. | Referenced by `20260322-1500-feature-technique-calibration-fixtures`. | Q6: 8 fixture gaps need replacement SGFs from identified collections. |
| B-5 | `20260324-research-enrichment-lab-test-audit` | Test suite health audit (84 files, ~27.4K lines) | **4 fully duplicated files** (2,237 lines of 100% copy-paste). 7 config test files redundantly verify Pydantic defaults. Achievable target: 55 files, ~19K lines (35% reduction). | Directly consumed — duplicate detector test files already deleted in this session. Initiative `20260324-2200-feature-enrichment-lab-test-audit` exists. | Q7: Config test consolidation (7→2-3 files) and refutation quality phase consolidation (4→1-2 files) still pending. |

---

## 5. Staleness Classification Summary

### Files Safe to Archive (Superseded/Completed) — 7 files

| R-ID | File | Reason |
|------|------|--------|
| S-1 | `ai-solve-enrichment-plan.md` | Superseded by v3 (explicitly stated in v3 header) |
| S-2 | `ai-solve-enrichment-plan-v2.md` | Superseded by v3 (explicitly stated in v3 header) |
| S-3 | `multi-dimensional-puzzle-filtering.md` | Superseded by SQLite architecture + compact schema plan |
| S-4 | `plan-composable-fragments-architecture.md` | Superseded by SQLite migration; shard/snapshot system replaced |
| S-5 | `plan-rebuild-centric-pipeline-v12.md` | Phases 1-3B complete; architecture adopted into codebase |
| S-6 | `COMPLETED/plan-compact-schema-filtering.md` | SQLite supersedes; already in COMPLETED but only ~39% done |
| S-7 | `COMPLETED/plan-backend-performance-at-scale.md` | 0% status; concepts partially adopted (`parse_root_properties_only`) |

### Files Needing Re-Assessment (Stale but Potentially Valuable) — 7 files

| R-ID | File | Why Re-Assessment Needed |
|------|------|--------------------------|
| S-8 | `filtering-ux-audit-and-plan.md` | 50+ UX findings still valid conceptually but architecture is now SQLite. |
| S-9 | `frontend-perf-optimizations.md` | T-PERF-006 (code splitting) and T-PERF-007 (vendor chunks) are high-value. |
| S-10 | `plan-hint-system-redesign.md` | B1-B2 bugs are real and unfixed. Full redesign may conflict with unification. |
| S-11 | `plan-analyze-enhancement.md` | YG preserve-first and CJK stripping are still useful. |
| S-12 | `plan-standardize-config-schemas.md` | Config schema standardization is evergreen but low priority. |
| S-13 | `plan-rush-play-enhancement.md` | Rush works but prerequisites changed (SQLite). Level bug may persist. |
| S-14 | `backend-trace-search-optimization.md` | Trace indexing still unimplemented. Feature initiative exists. |

### Active/Actionable — 4 files

| R-ID | File | Next Action |
|------|------|-------------|
| S-15 | `ai-solve-enrichment-plan-v3.md` | Complete remediation sprints 2-5; pass gate reviews |
| S-16 | `ai-solve-remediation-sprints.md` | Sprint 1 done; proceed through sprints 2-5 |
| S-17 | `kishimoto-mueller-search-optimizations.md` | All code done; pass gate reviews T017a, T027a |
| S-18 | `kishimoto-mueller-tasks.md` | Gate reviews only — all implementation `[x]` |

### Sub-Directories

| R-ID | Directory | Recommendation |
|------|-----------|----------------|
| S-19 | `katago-puzzle-enrichment/` | **Keep** — active ADR references from v3 plan and KM optimizations |
| S-20 | `lab-web-katrain/` | **Archive** — never implemented, no active references |
| S-21 | `puzzle-quality-scorer/` | **Archive** — explicitly deferred |
| S-22 | `puzzle-quality-strategy/` | **Archive** — explicitly deferred |
| S-23 | `xuanxuango/` | **Archive** — one-off research with no follow-up |

---

## 6. Planner Recommendations

1. **Archive 7 superseded/completed files** (S-1 through S-7) to `TODO/ARCHIVED/` to reduce root-level noise. These are design history, not actionable work. Preserves git history.

2. **Prioritize gate reviews for KM optimizations** (S-17, S-18): All implementation code is done and tested. Only Review Panel sign-offs remain. This is the nearest "value unlock" — 30-50% query budget reduction in enrichment lab.

3. **Fix the 4 hint key mismatches** from `plan-hint-system-redesign.md` (A-15, S-10): B1 bugs are confirmed real (tag slugs don't match TECHNIQUE_HINTS keys → silent YH2 hint failures). Low effort, high correctness impact.

4. **Create a fresh filtering UX audit** against the SQLite/DB-1 architecture (A-6, S-8): The Feb 25 audit was thorough but targets the view-file architecture. Many findings are now trivially solvable via SQL queries. A refreshed audit would produce immediately actionable items.

---

## 7. Confidence and Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 88 |
| `post_research_risk_level` | low |

**Confidence note**: High confidence on staleness/superseded classifications — based on explicit `Supersedes:` headers and architecture changes (SQLite migration). Medium confidence on "partially actioned" items — verified key signals (memo wrapper, box-shadow, parse_root_properties_only) but didn't exhaustively verify every sub-task.

**Risk**: Low. Main risk is archiving a file that still has one useful nugget. Mitigation: move to ARCHIVED (not delete), and extract specific actionable items (like B1-B2 hint bugs) into fresh initiatives before archiving.

---

## Open Questions

| q_id | Question | Options | Recommended | User Response | Status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should discarded enrichment signals populate DB-1 `attrs` column? | A: Persist all 14 / B: Top 5 / C: Defer | B: Top 5 (policy_entropy, correct_move_rank, TreeCompleteness, goal, enrichment_quality_level) | — | ❌ pending |
| Q2 | Should achievement system UI be prioritized? | A: Next sprint / B: Backlog / C: Cut | B: Backlog | — | ❌ pending |
| Q3 | Archive strategy for superseded TODO files? | A: TODO/COMPLETED/ / B: TODO/ARCHIVED/ / C: Delete | B: TODO/ARCHIVED/ (distinguishes completed vs superseded) | — | ❌ pending |
| Q4 | Should hinting unification be a near-term initiative? | A: Yes / B: Keep independent / C: Fix bugs only | C: Fix B1-B2 bugs only, defer full unification | — | ❌ pending |
| Q5 | Filter occupied coords in `get_roi_allow_moves()`? | A: Yes / B: No (confirmed harmless) | A: Yes, one-line cleanliness fix | — | ❌ pending |
| Q6 | Proceed with fixture sourcing from goproblems_difficulty_based? | A: Yes / B: Research more | A: Yes | — | ❌ pending |
| Q7 | Proceed with enrichment lab test consolidation? | A: Full cleanup / B: Duplicates only / C: Defer | A: Full cleanup (35% line reduction achievable) | — | ❌ pending |
