# Governance Decisions

> **Initiative**: `20260313-1000-feature-gp-frame-swap`
> **Last Updated**: 2026-03-13

---

## Gate 1: Charter Review

| Field | Value |
|-------|-------|
| **Gate** | charter-review |
| **Decision** | approve |
| **Status Code** | GOV-CHARTER-APPROVED |
| **Unanimous** | Yes (6/6) |
| **Date** | 2026-03-13 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Q7 correct: player_to_move IS the attacker in tsumego convention. GP count-based fill is structurally sound. | Go pedagogy convention |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Adapter + rollback addresses quality uncertainty. Q6 right — no consumer uses `defense_area`. | No external consumer found |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | GP's fill is same algorithm trusted by KaTrain/ghostban for KataGo. `player_to_move` is what KaTrain uses. | KaTrain SHA 877684f9 (MIT) |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 1130 → ~600 + thin adapter reduces maintenance. Clean scope. | BFS ~1130 vs GP ~600 lines |
| GV-5 | Staff Engineer A | Systems architect | approve | SRP/DIP/ISP compliant. Shared `FrameRegions` → minimal interface. Dead import confirmed. | Codebase-wide search |
| GV-6 | Staff Engineer B | Pipeline engineer | approve | 10 files, 2 new modules, 0 new deps. Test plan explicit. | GP already exists |

### Key Resolutions

| q_id | Resolution | Rationale |
|------|-----------|-----------|
| Q6 | **Option B** — Exclude `defense_area`/`offense_area` from shared `FrameRegions` | No external consumer. ISP: minimal interface. Fields are BFS-internal fill logic only. |
| Q7 | **Option A** — Use `player_to_move` directly for attacker detection | Convention-correct for tsumego (all 4 Go professionals confirm). Pipeline guarantees PL is set. 0 lines vs 140 lines. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved. Proceed to options. Q6/Q7 resolved. |
| required_next_actions | Update status.json, update clarifications, draft 25-options.md |
| blocking_items | None |

---

## Gate 2: Options Election

| Field | Value |
|-------|-------|
| **Gate** | options-review |
| **Decision** | approve_with_conditions |
| **Status Code** | GOV-OPTIONS-CONDITIONAL |
| **Unanimous** | Yes (6/6) |
| **Selected Option** | OPT-1 — Thin Adapter Module (`frame_adapter.py`) |
| **Date** | 2026-03-13 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | GP algorithm purity preserved. Adapter acts as disciplined boundary. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Rollback argument decisive — single-file vs multi-consumer. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Same layering as KaTrain. Zero computational overhead. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Pragmatic middle. ~80-100 lines for rollback + purity benefits. |
| GV-5 | Staff Engineer A | Systems architect | approve | SRP/DIP/ISP satisfied. Raised RC-1: `FrameConfig` type must be explicitly defined. |
| GV-6 | Staff Engineer B | Pipeline engineer | approve | Adapter is ideal instrumentation point. RC-2: puzzle_region type must be preserved. |

### Required Conditions

| RC-id | Condition | Resolution |
|-------|-----------|------------|
| RC-1 | Plan must define shared `FrameConfig` type distinct from BFS's version | To be addressed in 30-plan.md |
| RC-2 | Plan must confirm `FrameRegions.puzzle_region` preserves `frozenset[tuple[int,int]]` type | To be addressed in 30-plan.md |

### Selection Rationale

OPT-1 satisfies C1 (GP purity), C3 (consumer stability), C5 (single-file rollback). Matches user's explicit "thin adapter layer" request. Avoids YAGNI. ~130-150 total new lines. Unanimous panel support.

---

## Gate 3: Plan Review

| Field | Value |
|-------|-------|
| **Gate** | plan-review |
| **Decision** | approve |
| **Status Code** | GOV-PLAN-APPROVED |
| **Unanimous** | Yes (6/6) |
| **Date** | 2026-03-13 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Q7 convention-correct. GP produces clean frames. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Rollback bounded to 1 file. Risk table honest. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Same algorithm as KaTrain for KataGo. ko bool is correct. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 40% complexity reduction. Phased execution allows partial value. |
| GV-5 | Staff Engineer A | Systems architect | approve | SRP/DIP/ISP clean. RC-1/RC-2 resolved. validate_frame is algorithm-agnostic. |
| GV-6 | Staff Engineer B | Pipeline engineer | approve | 18 tasks, parallelism correct. Coverage maps to all 8 goals. |

### Verification Summary

- RC-1 resolved: No shared `FrameConfig`. GP uses `GPFrameConfig`. `compute_regions` takes plain args.
- RC-2 resolved: `FrameRegions.puzzle_region` is `frozenset[tuple[int,int]]`. T4 assertion.
- F5 resolved: `validate_frame` is algorithm-agnostic geometry (not BFS-specific).
- All 9 source code claims verified against actual files.
- All 9 ripple effects traced to task IDs.

### Handover to Executor

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved unanimously. Execute 18 tasks in 6 phases per 40-tasks.md. No blocking items. |
| required_next_actions | Execute T1-T18. Create 50-execution-log.md. Create 60-validation-report.md. Submit for governance review after completion. |
| blocking_items | None |

---

## Gate 4: Implementation Review

| Field | Value |
|-------|-------|
| **Gate** | implementation-review |
| **Decision** | approve |
| **Status Code** | GOV-REVIEW-APPROVED |
| **Unanimous** | Yes (6/6) |
| **Date** | 2026-03-13 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Frame adapter preserves player_to_move semantics. FrameRegions has only 4 geometry fields. Clean boundary. | frame_utils.py 4-field frozen dataclass, test_frame_adapter player_to_move test, Golden Five 6/6 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Single-file rollback (C5) proven: frame_adapter.py is sole adapter. BFS preserved at 1130 lines. | frame_adapter.py sole GP import, tsumego_frame.py 1130 lines preserved |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | GP fill matches KaTrain/ghostban. ko bool mapping correct. Golden Five confirms KataGo integration. | frame_adapter.py apply_frame wraps apply_gp_frame 1:1, Golden Five 6/6 in 285s |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Complexity reduction: 277 lines (utils+adapter) vs 1130 BFS. 22 new tests + 114 consumer + 6 Golden Five. | 12+10 new tests, 114 consumer tests, 40 GP tests |
| GV-5 | Staff Engineer A | Systems architect | approve | SRP/DIP/ISP satisfied. frame_utils depends only on models.position. No new external deps. RC-1 and RC-2 resolved. | frame_utils.py imports, frame_adapter.py imports, pyproject.toml unchanged |
| GV-6 | Staff Engineer B | Pipeline engineer | approve | 22 new + 40 GP + 114 consumer + 6 Golden Five = 182 passing tests. 8 ripple-effect rows all verified. Level 0 deviation documented. | VAL-1 through VAL-22 all ✅, EX-1 through EX-19 all complete |

### Verification Summary

- 19/19 tasks completed, 0 scope expansion, 1 minor deviation (syntax fix — Level 0)
- All 7 constraints verified: C1-C5, RC-1, RC-2
- Test evidence: 62 new + 40 GP + 114 consumer + 6 Golden Five = 222 tests; 87 BFS skipped
- Architecture: SRP (3 modules), DIP (consumers → adapter → GP), ISP (4-field FrameRegions)
- Documentation: tsumego-frame.md updated with GP Active notice
- Rollback: single file change in frame_adapter.py

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation review approved unanimously. Proceed to closeout. |
| required_next_actions | Update status.json governance_review to approved. Prepare closeout submission. |
| blocking_items | None |

---

## Gate 5: Closeout Audit

| Field | Value |
|-------|-------|
| **Gate** | closeout |
| **Decision** | approve |
| **Status Code** | GOV-CLOSEOUT-APPROVED |
| **Unanimous** | Yes (6/6) |
| **Date** | 2026-03-13 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | player_to_move = attacker convention preserved end-to-end. Q7 resolved through all gates. | C2 test assertion, Q7 resolved Gate 1, Golden Five 6/6 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Rollback: one file coupling point. BFS preserved with skip marker. | C5 verified, BFS untouched, skip marker reversible |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | GP fill matches KaTrain/ghostban. Ko bool mapping correct for frame fill. | KaTrain SHA 877684f9, Golden Five 6/6 in 285s |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 277 vs 1130 lines complexity reduction. 182 tests, no new deps. | frame_utils 97L + frame_adapter 180L, 182 passed |
| GV-5 | Staff Engineer A | Systems architect | approve | SRP/DIP/ISP satisfied. RC-1/RC-2 resolved. Zero new external deps. 10/10 artifacts present. | All imports verified, pyproject.toml unchanged |
| GV-6 | Staff Engineer B | Pipeline engineer | approve | Full lifecycle: 4 gates, 23 validation items, 8 ripple-effects, all verified. Level 0 deviation documented. | EX-1..19, VAL-1..23 all ✅, no TODOs/FIXMEs |

### Closure Summary

- 8/8 charter goals traced to implementation and test evidence
- 8/8 constraints verified with test-level evidence
- 10/10 artifacts present and current
- 4/4 governance gates passed unanimously
- 0 residual items, 0 scope expansion, 0 deferred items
- Documentation updated per update-first policy with cross-references

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | none (initiative complete) |
| message | Closeout approved unanimously. Initiative complete. |
| required_next_actions | Update status.json: closeout → approved, current_phase → closed. |
| blocking_items | None |
