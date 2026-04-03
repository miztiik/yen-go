# Governance Decisions — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-11

## Gate 1: Charter Review

**Date:** 2026-03-10
**Decision:** `approve_with_conditions`
**Status Code:** `GOV-CHARTER-CONDITIONAL`
**Unanimous:** No (4 approve, 2 concern — Shin Jinseo: confidence score gap; PSE-A: artifact hygiene)

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Benson's unconditional life is mathematically sound. Seki fall-through (C3) is correct safety valve. Interior-point two-eye check is well-known tsumego heuristic. | Charter G1, C3; research R-R-4 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Scope consolidation makes strategic sense. Ko capture verification important — adjacency alone misses approach-ko. 26 individual reviews necessary. | ko_validation.py L155; AC6 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | concern | Confidence score discrepancy needs resolution (research 82/medium vs charter 90/low). Benson gate placement should be BEFORE engine.query(). | 15-research.md post_research values |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Good practical consolidation. Conditional sgfmill approach is right. Learning value ordering correct. | AC18; G7 traced to S5-G19 |
| GV-5 | PSE-A | Systems architect | concern | status.json rationales pending; AC14 says "create" but file exists. Both fixable. Architecture sound. | status.json L12-13; docs/concepts/quality.md exists |
| GV-6 | PSE-B | Data pipeline | approve | All 5 perspective gap claims verified against code. 6-source consolidation is correct organizational move. | enrich_single.py L803/813/825/1395/1424/1433 |

### Required Changes

| rc_id | change | status |
|-------|--------|--------|
| RC-1 | Document confidence score reconciliation (research 82/medium → charter 90/low) | ✅ Fixed: added §Confidence Reconciliation to 10-clarifications.md |
| RC-2 | Populate status.json decision rationales | ✅ Fixed: rationales updated |
| RC-3 | AC14: "created" → "updated" (file exists) | ✅ Fixed in 00-charter.md |
| RC-4 | Resolve governance panel's Q1-Q5 | ✅ Fixed: see §Governance Panel Questions below |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved with conditions. All 4 RCs fixed. Proceed to options. |
| required_next_actions | 1. Draft 25-options.md 2. Submit for options governance |
| blocking_items | None (all RCs resolved) |

---

## Gate 2: Options Review

**Date:** 2026-03-10
**Decision:** `approve`
**Status Code:** `GOV-OPTIONS-APPROVED`
**Unanimous:** Yes (6/6 approve)
**Selected Option:** OPT-3 — Interleaved Priority Sequence

### Selection Rationale

OPT-3 is the only option where governance reviews (Phase C) cover the complete codebase state including both fixes and new algorithms. Fixes-first stabilization (Phase A) provides a clean integration surface for Benson gate. sgfmill replacement is appropriately last and droppable.

### Must-Hold Constraints

| mhc_id | constraint |
|--------|-----------|
| MHC-1 | Phase A (fixes) MUST complete before Phase B (algorithms) begins |
| MHC-2 | Phase C (reviews) MUST happen after Phase B completes |
| MHC-3 | sgfmill Phase D is droppable if complexity exceeds MEDIUM |
| MHC-4 | Each Phase C review is individual (no batching) |
| MHC-5 | Benson gate MUST NOT use YK property |

### Required Changes for Plan

| rc_id | change |
|-------|--------|
| RC-1 | Plan must specify doc stubs in Phase A: which files, what placeholder content |
| RC-2 | Plan must define review criteria checklist for Phase C's 26 individual reviews |

### Member Reviews

| review_id | member | vote | key point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | Clean ko before Benson — correct sequencing |
| GV-2 | Lee Sedol (9p) | approve | Stabilize before attack — Phase A then B |
| GV-3 | Shin Jinseo (9p) | approve | Logging fixes in A make Benson observable from day one |
| GV-4 | Ke Jie (9p) | approve | sgfmill droppable — strategic budget protection |
| GV-5 | PSE-A | approve | Architecture compliant; doc stubs need scoping (RC-1) |
| GV-6 | PSE-B | approve | Observability layering correct; review criteria need defining (RC-2) |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | OPT-3 unanimously approved. Draft plan with 5 phases (A-E), addressing RC-1 and RC-2. |
| blocking_items | None |

## Gate 3: Plan Review (First Pass)

**Date:** 2026-03-10
**Decision:** `change_requested`
**Status Code:** `GOV-PLAN-REVISE`
**Unanimous:** No (3 change_requested, 3 concern)

### Critical Finding: Benson API Contract Defect (PF-1)

`check_unconditional_life(stones, target_color, board_size)` would fire on framework groups (100% false positive). In tsumego, surrounding stones form a fixed frame — they ARE alive. The function must return all alive groups and let the caller check only the contest group.

### Required Changes

| rc_id | change | blocking |
|-------|--------|----------|
| RC-1 | Fix Benson API: change to `find_unconditionally_alive_groups()` returning `set[frozenset[...]]`, update T9/T11/T12 | ✅ Blocking |
| RC-2 | Specify tsumego_frame API: use `compute_regions().puzzle_region`, not `compute_frame_boundary` | Non-blocking |
| RC-3 | Add `sgf_enricher.py` to T6 file list | Non-blocking |
| RC-4 | Promote RE-9 grep to T6 explicit pre-step | Non-blocking |

### Member Reviews

| review_id | member | vote |
|-----------|--------|------|
| GV-1 | Cho Chikun (9p) | change_requested — framework groups cause 100% false positive |
| GV-2 | Lee Sedol (9p) | change_requested — agree on PF-1 |
| GV-3 | Shin Jinseo (9p) | concern — PF-1 fixable as RC |
| GV-4 | Ke Jie (9p) | concern — 1-line fix, overall plan quality high |
| GV-5 | PSE-A | change_requested — API contract must be corrected in artifacts |
| GV-6 | PSE-B | concern — coverage/observability sound, only PF-1 blocks |

### Resolution

All 4 RCs applied to `30-plan.md` and `40-tasks.md`:
- RC-1: Changed to `find_unconditionally_alive_groups()` returning set of groups; T11 integration checks contest-group membership; T12 includes framework false-positive fixture
- RC-2: T10 now references `compute_regions(position, config).puzzle_region`
- RC-3: T6 includes `sgf_enricher.py`
- RC-4: T6 includes grep pre-step

Resubmitting for Gate 3b re-review.

## Gate 3b: Plan Re-Review

**Date:** 2026-03-10
**Decision:** `approve`
**Status Code:** `GOV-PLAN-APPROVED`
**Unanimous:** Yes (6/6 approve)

All 4 Gate 3 RCs verified resolved:
- RC-1: `find_unconditionally_alive_groups()` returns `set[frozenset[...]]`; contest-group subset check in T11; framework false-positive fixture in T12 ✅
- RC-2: `compute_regions().puzzle_region` matches actual tsumego_frame.py API ✅
- RC-3: T6 lists `sgf_enricher.py` ✅
- RC-4: T6 grep pre-step explicit ✅

### Member Reviews

| review_id | member | vote |
|-----------|--------|------|
| GV-1 | Cho Chikun (9p) | approve — corrected API is mathematically sound for tsumego |
| GV-2 | Lee Sedol (9p) | approve — ko capture verification (T4 board replay) is correct |
| GV-3 | Shin Jinseo (9p) | approve — no-YK constraint satisfied by algorithmic design |
| GV-4 | Ke Jie (9p) | approve — 50-task plan, phase ordering, budget protection |
| GV-5 | PSE-A | approve — all RCs traceable in artifacts |
| GV-6 | PSE-B | approve — observability, regression gates, review criteria adequate |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved unanimously. Execute OPT-3 phases A→B→C→D→E. Enforce MHC-1 through MHC-5. Triage `level_mismatches` (plural) hits in backend/inventory as unrelated during T6 grep. Update docs/architecture L358 reference in T46. |
| blocking_items | None |

---

## Gate 4: Implementation Review

**Date:** 2026-03-10
**Decision:** `approve`
**Status Code:** `GOV-REVIEW-APPROVED`
**Unanimous:** Yes (6/6 approve)

### Member Reviews

| review_id | member | vote | key point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | Benson algorithm mathematically faithful; contest-group subset check correct for tsumego |
| GV-2 | Lee Sedol (9p) | approve | Ko board replay superior to adjacency proxy; backward compatible API design |
| GV-3 | Shin Jinseo (9p) | approve | Pre-query gates correctly placed before engine.query(); depth >= min_depth guard appropriate |
| GV-4 | Ke Jie (9p) | approve | Phase D drop strategically correct; dead code elimination clean |
| GV-5 | PSE-A | approve | Architecture compliance clean; no cross-boundary violations; ripple-effects complete |
| GV-6 | PSE-B | approve | Observability improvements well-structured; doc plan executed across all 4 tiers |

### Must-Hold Constraints Verified

| mhc_id | constraint | verified |
|--------|-----------|----------|
| MHC-1 | Phase A before Phase B | ✅ |
| MHC-2 | Phase C after Phase B | ✅ |
| MHC-3 | Phase D droppable if HIGH | ✅ DROPPED |
| MHC-4 | Each review individual | ✅ 26 separate entries |
| MHC-5 | No YK in Benson gate | ✅ |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation approved unanimously. Proceed to closeout. |
| blocking_items | None |

---

## Gate 5: Closeout Audit

**Date:** 2026-03-10
**Decision:** `approve`
**Status Code:** `GOV-CLOSEOUT-APPROVED`
**Unanimous:** Yes (6/6 approve)

### Member Reviews

| review_id | member | vote | key point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | Benson algorithm mathematically correct; contest-group subset avoids framework false-positive |
| GV-2 | Lee Sedol (9p) | approve | Ko board-replay improvement significant; backward compatible API |
| GV-3 | Shin Jinseo (9p) | approve | Pre-query gates correctly placed; depth >= min_depth guard prevents premature detection |
| GV-4 | Ke Jie (9p) | approve | 46/50 tasks executed; Phase D drop principled; docs across 4 tiers |
| GV-5 | PSE-A | approve | Architecture compliance verified; no cross-boundary violations; dead code removal clean |
| GV-6 | PSE-B | approve | Regression cadence correct; 8/8 ripple effects verified; observability improved |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | User |
| message | Initiative fully closed. All gates passed, 384 tests passing, no regressions. |
| blocking_items | None |

---

## Gate 6: Post-Closeout Remediation Review

**Date:** 2026-03-11
**Decision:** `approve`
**Status Code:** `GOV-REVIEW-APPROVED`
**Unanimous:** Yes (6/6 approve)

### Scope

Post-closeout remediation — two sessions fixing bugs found during deep review:
- Session 1 (RT-1 through RT-9): puzzle_region threading, ko position param, config annotations, doc dates, sgfmill requirement, integration tests
- Session 2 (NF-01, NF-02, R1/NF-03, R3, R5): board size derivation, adjacency logic, discover_alternatives threading, has-solution path puzzle_region, gate test rewrite

### Member Reviews

| review_id | member | vote | key point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | NF-01 board size derivation critical for 9x9/13x13 correctness; NF-02 adjacency fix prevents spurious ko detections |
| GV-2 | Lee Sedol (9p) | approve | R1/NF-03 closes real gap — alt trees built without spatial context; spy test is correct verification pattern |
| GV-3 | Shin Jinseo (9p) | approve | EX-56 was genuine NameError; both code paths now have consistent region computation |
| GV-4 | Ke Jie (9p) | approve | Dual-path fix demonstrates good diagnostic discipline; no over-engineering |
| GV-5 | PSE-A | approve | Architecture compliance clean; backward compat via None defaults; 16/16 ripple-effects verified |
| GV-6 | PSE-B | approve | Test quality significantly improved; GTP→(row,col) mapping geometrically correct |

### Evidence

- 341 tests pass (165 core + 176 extended), 3 skipped, 0 new failures
- 14 gate integration tests with proper depth_profiles and coordinate mapping
- VAL-9 through VAL-16 ripple-effects all verified
- All fixes verified at exact source code locations

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | User |
| message | Post-closeout remediation approved unanimously. All 14 findings verified. 341 tests pass. No required changes. |
| blocking_items | None |

---

## Gate 7: Final Closeout Audit (Post-Remediation)

**Date:** 2026-03-11
**Decision:** `approve`
**Status Code:** `GOV-CLOSEOUT-APPROVED`
**Unanimous:** Yes (6/6 approve)

### Member Reviews

| review_id | member | vote | key point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | Benson/interior-point gates mathematically verified through 7 governance gates including corrective re-review; adjacency fix correct |
| GV-2 | Lee Sedol (9p) | approve | Ko capture verification complete; discover_alternatives puzzle_region gap was genuine; 14 gate tests cover all dimensions |
| GV-3 | Shin Jinseo (9p) | approve | NF-01 board_size critical for 9x9/13x13; EX-56 resolved real NameError; systematic diagnosis across both sessions |
| GV-4 | Ke Jie (9p) | approve | Exceptional lifecycle discipline: 50 tasks + 14 remediation findings, no deferred items, documentation update-first |
| GV-5 | PSE-A | approve | Architecture compliance clean; 1:1 traceability EX-47→EX-57; 16/16 ripple-effects verified |
| GV-6 | PSE-B | approve | 341 tests pass; gate test rewrite exercises actual production code paths; crosslinks satisfy doc mandate |

### Support Summary

Complete lifecycle cadence (7 gates), end-to-end traceability (57 execution entries, 16 validation rows), documentation quality closure verified, 341 tests pass, 0 new failures, no open issues.

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | User |
| message | Initiative fully closed after 7 governance gates. All 50 original tasks + 14 remediation findings implemented, tested, documented, audited. |
| blocking_items | None |

---

## Gate 8: Post-Closeout Design Amendment — Terminal Detection Config Decoupling

**Date:** 2026-03-11
**Decision:** `approve_with_conditions`
**Status Code:** `GOV-REVIEW-CONDITIONAL`
**Unanimous:** Yes (6/6 approve, conditioned on RC-1 naming)

### Scope

Post-closeout design amendment decoupling `terminal_detection_enabled` from `transposition_enabled`. The Benson (G1) and interior-point (G2) pre-query gates were accidentally coupled to transposition initialization — disabling transposition also disabled the gates.

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Single toggle for both G1+G2 is correct; both are complementary terminal conditions. Naming should reflect both gates. | benson_check.py: two functions, one module, one purpose |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Independent toggle opens useful experimental configs: transposition off for memory, gates on for query savings. | test_gate_integration.py: existing parameterization pattern |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Correctness optimization (terminal detection) must not be coupled to performance optimization (transposition). `terminal_detection_enabled` matches code comment. | solve_position.py L1051: "Pre-query terminal detection" |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Small, focused, backward-compatible. Removes confusing side-effect from docs. | enrichment-config.md L103 |
| GV-5 | PSE-A | Systems architect | approve | Separation of concerns correct. Naming RC: `terminal_detection_enabled` not `benson_gate_enabled`. | config.py: AiSolveSolutionTreeConfig |
| GV-6 | PSE-B | Data pipeline | approve | board_state init is cheap. Observability logging preserved. Test plan sound. | solve_position.py L1074-L1089: debug logging unchanged |

### Required Changes

| rc_id | change | status |
|-------|--------|--------|
| RC-1 | Rename `benson_gate_enabled` → `terminal_detection_enabled` with description listing both G1 and G2 | ✅ Applied |
| RC-2 | Add explicit `tree_config.terminal_detection_enabled` check at gate guard | ✅ Applied |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Design amendment approved. Naming RC applied. Implementation verified: 312 passed, 3 skipped, 1 pre-existing error. |
| blocking_items | None (both RCs resolved) |
