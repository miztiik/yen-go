# Governance Decisions — Enrichment Lab GUI v4

**Initiative ID:** 20260309-1000-feature-enrichment-lab-gui-v4  
**Last Updated:** 2026-03-09

---

## Decision 1: Charter Review (2026-03-09)

| Field | Value |
|-------|-------|
| Gate | charter-review |
| Decision | **approve_with_conditions** |
| Status code | `GOV-CHARTER-CONDITIONAL` |
| Unanimous | No (5 approve, 1 concern) |

### Panel Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Charter correctly identifies KataGo validation vs solving paths. ac_level indicator (G7) is pedagogically sound. "Python does all analysis" eliminates hybrid confusion. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Fresh-build is correct instinct after 3 failures. Board library choice deferred to options appropriately. G4 ambitious but feasible. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | KataGo limitation analysis thorough. Flags engine concurrency question for G8 — must investigate in options. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 9 goals deliver complete developer visualization workflow. ac_level is critical. G8 may need fallback if engine serializes. |
| GV-5 | Principal Staff Engineer A | Systems architect | concern | Scope well-bounded. Three concerns: (1) status.json legacy conflict, (2) charter silent on code copying, (3) engine concurrency investigation needed. |
| GV-6 | Principal Staff Engineer B | Data pipeline | approve | SSE catalog complete. Bridge.py well-structured. C7 additive-only protects working code. |

### Required Changes (All Resolved)

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Fix status.json: set legacy_code_removal.remove_old_code=false | ✅ Applied |
| RC-2 | Add "Code Reuse Policy" section to charter | ✅ Applied |
| RC-3 | Track engine concurrency investigation as options deliverable | ✅ Added as Q9 in clarifications |

### Engine Concurrency Investigation (RC-3 Resolution)

Investigated `LocalEngine.analyze()` in `engine/local_subprocess.py`:
- Uses `threading.Lock()` (line 35, 168) — **serializes all analysis queries**
- `/api/analyze` during active pipeline enrichment will **block** until current pipeline query finishes
- KataGo subprocess handles one query at a time (request → response → next request)
- **Conclusion:** G8 (analysis dots during enrichment) is feasible but timing-dependent. The `/api/analyze` call will queue behind active pipeline queries. This is acceptable for a single-user developer tool — user sees analysis dots with a slight delay after each pipeline stage completes its engine query.
- **Fallback not needed:** Since the lock serializes rather than rejects, the request won't fail — it just waits.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved with conditions (all resolved). Proceed to options phase. |
| required_next_actions | Draft 25-options.md evaluating: (1) board library, (2) frontend tech stack, (3) code reuse strategy, (4) solution tree approach |
| blocking_items | None |

---

## Decision 2: Options Election (2026-03-09)

| Field | Value |
|-------|-------|
| Gate | options-review |
| Decision | **approve** |
| Status code | `GOV-OPTIONS-APPROVED` |
| Unanimous | Yes (6/6) |
| Selected option | **OPT-1: GhostBan Board + Custom SVG Tree + Vanilla JS + Vite** |

### Selection Rationale

1. Eliminates Preact Signals coordinate transposition bug class (root cause of 3 prior failures)
2. Canvas board + overlay reproduces goproblems.com Research(Beta) architecture (validated by R-24)
3. Custom SVG tree gives full control for G4 requirements (correct/wrong coloring + policy priors)
4. Vanilla JS + Vite is KISS-optimal: no framework, dev proxy included, ~5 deps
5. All 9 goals and 10 ACs achievable. Zero bridge.py modifications.

### Must-Hold Constraints

1. C1: No backend/puzzle_manager imports
2. C2: Lives in `tools/puzzle-enrichment-lab/gui/`
3. C5: Python-only analysis
4. C6: No TF.js
5. C7: No bridge.py contract changes (additive only if needed)
6. C8: Single-user

### Panel Reviews

| review_id | member | domain | vote | key point |
|-----------|--------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Custom SVG tree gives deterministic policy-annotated coloring without library constraints |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Breaks 3-failure pattern by removing framework layer |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | GhostBan canvas = goproblems.com production stack |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | OPT-2 cannot deliver G3/G8 without re-inventing canvas |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | OPT-3 disqualified by HIGH-prob unmitigated risk |
| GV-6 | Principal Staff Engineer B | Data pipeline | approve | 15 SSE events map cleanly; zero bridge.py surface area |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | OPT-1 unanimously approved. Proceed to plan drafting. |
| required_next_actions | Draft plan + tasks + analysis, submit for plan review |
| blocking_items | None |

---

## Decision 3: Plan Review (2026-03-09)

| Field | Value |
|-------|-------|
| Gate | plan-review |
| Decision | **approve_with_conditions** |
| Status code | `GOV-PLAN-CONDITIONAL` |
| Unanimous | No (5 approve, 1 concern) |

### Panel Reviews

| review_id | member | domain | vote | key point |
|-----------|--------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Solution tree spec with correct/wrong coloring from C[] property is pedagogically sound |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Coordinate contract (no mat[row][col] intermediate) breaks 3-failure cycle |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Engine serialization acceptable; analysis dots algorithm matches KataGo standards |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 15 SSE→component mapping eliminates integration ambiguity |
| GV-5 | Principal Staff Engineer A | Systems architect | concern | Documentation Plan format incomplete; file count discrepancy |
| GV-6 | Principal Staff Engineer B | Data pipeline | approve | C7 fully respected; regression test coverage adequate |

### Required Changes (All Resolved)

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Update Documentation Plan to required schema (files_to_create/files_to_update/why_updated/cross-refs). Note DOC-4 REPLACES old content. | ✅ Applied |
| RC-2 | Fix file count: gui/src/ has 10 files, not 9 | ✅ Applied |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved. Execute OPT-1 per 15-task plan. Coordinate contract is the critical design decision — enforce it in T3. |
| required_next_actions | Execute T1-T15 per phase DAG |
| blocking_items | None |
---

## Decision 4: Plan Re-Review After OPT-1R Revision (2026-03-10)

| Field | Value |
|-------|-------|
| Gate | plan-review (re-review) |
| Decision | **change_requested** → resolved to **approve** |
| Status code | `GOV-PLAN-REVISE` → `GOV-PLAN-APPROVED` |
| Panel | 6 members (4 concern, 2 change_requested) |

### What Changed (OPT-1 → OPT-1R)

| Component | OPT-1 (old) | OPT-1R (revised) |
|-----------|-------------|------------------|
| Tree | Custom SVG (~300 lines) | BesoGo treePanel + ~50 lines mods |
| Build tool | Vite + npm | bridge.py StaticFiles (2 lines Python) |
| Dependencies | 5 npm packages | 0 |
| Total scope | ~1700-2000 lines | ~900-1100 lines |
| New feature | — | G10: Interactive analysis (place stone → analyze) |
| Pipeline bar | 9 stages, no run_id | 10 stages, green/red pills, run_id + trace_id + ac_level |

### Required Changes (All Resolved)

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Remove stale OPT-1 tasks from 40-tasks.md | ✅ Deleted |
| RC-2 | Remove stale OPT-1 content from 30-plan.md | ✅ Deleted |
| RC-3 | Update status.json: confidence=85, phase=plan | ✅ Applied |
| RC-4 | Add G10 to charter, fix AC1 (remove npm reference) | ✅ Applied |
| RC-5 | Clarify module loading strategy (ES modules for src, script tags for libs) | ✅ Applied |

### Panel Reviews

| review_id | member | vote | key point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | concern→resolved | BesoGo tree mods verified feasible. Stale content fixed. |
| GV-2 | Lee Sedol (9p) | change_requested→resolved | Dual task list removed. |
| GV-3 | Shin Jinseo (9p) | concern→resolved | G10 added to charter. |
| GV-4 | Ke Jie (9p) | concern→resolved | AC1 fixed. |
| GV-5 | Principal Staff Engineer A | change_requested→resolved | All stale content removed. Status.json corrected. |
| GV-6 | Principal Staff Engineer B | concern→resolved | Stale SSE mapping removed. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | OPT-1R plan approved after all 5 RCs resolved. Execute T1-T13 per phase DAG. Architecture: GhostBan canvas + BesoGo tree + vanilla JS + bridge.py StaticFiles. Zero npm dependencies. |
| required_next_actions | Execute T1-T13 |
| blocking_items | None |

---

## Decision 5: Implementation Review (2026-03-10)

| Field | Value |
|-------|-------|
| Gate | implementation-review |
| Decision | **approve_with_conditions** |
| Status code | `GOV-REVIEW-CONDITIONAL` |
| Unanimous | No (5 approve, 1 concern) |

### Panel Reviews

| review_id | member | vote | key point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | Tree coloring from C[] comments is pedagogically sound |
| GV-2 | Lee Sedol (9p) | approve | Interactive analysis (G10) is strong creative addition |
| GV-3 | Shin Jinseo (9p) | approve | KataGo analysis integration correct; engine serialization properly handled |
| GV-4 | Ke Jie (9p) | approve | ac_level badge is most valuable diagnostic signal |
| GV-5 | Principal Staff Engineer A | concern | Stray frame.ts contradicts coordinate contract |
| GV-6 | Principal Staff Engineer B | approve | SSE implementation solid; escHtml uses correct DOM pattern |

### Required Changes (Resolved)

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Delete stray `gui/src/lib/frame.ts` | ✅ Deleted |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation approved. RC-1 resolved. Proceed to closeout. |
| blocking_items | None |

---

## Decision 6: Closeout Audit (2026-03-10)

| Field | Value |
|-------|-------|
| Gate | closeout |
| Decision | **approve_with_conditions** |
| Status code | `GOV-CLOSEOUT-CONDITIONAL` |
| Unanimous | Yes (6/6 approve) |

### Required Changes (Resolved)

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Update Q9/Q10 in clarifications from pending to resolved | ✅ Applied |

### Panel Consensus

All 6 members approved closeout. Documentation quality verified (5 checks pass). 10 closeout checks pass. Initiative complete.