# Governance Decisions — Backend Dead Code Cleanup

**Initiative**: 20260324-1500-feature-backend-dead-code-cleanup  
**Last Updated**: 2026-03-24

---

## Gate 1: Charter Preflight Review

**Decision**: `approve_with_conditions`  
**Status Code**: `GOV-CHARTER-CONDITIONAL`  
**Date**: 2026-03-24

### Member Reviews

| GV-ID | Member | Domain | Vote | Key Comment |
|-------|--------|--------|------|-------------|
| GV-1 | Principal Engineer | Architecture | approve | 3-phase approach correctly isolates risk layers |
| GV-2 | Staff Engineer | Backend | approve | Dead code verification thorough via grep |
| GV-3 | Security Engineer | Security | approve | No new attack surface; deletion-only reduces it |
| GV-4 | QA Lead | Testing | approve | Test gates at each phase are critical |
| GV-5 | DevOps Engineer | Infrastructure | approve | No CI/CD impact for dead code removal |
| GV-6 | Go Domain Expert | Domain | approve | No puzzle logic affected |
| GV-7 | Documentation Lead | Docs | approve | Docs cleanup included per project policy |
| GV-8 | Python Packaging Expert | Packaging | concern | CA-9 gap: `adapters/__init__.py` imports UrlAdapter from dead `url.py` |
| GV-9 | Release Manager | Release | concern | Package-vs-module resolution nuance undocumented |
| GV-10 | Test Strategist | Testing | approve | Orphan test deletion reduces noise |

### Required Changes

| RC-ID | Severity | Description | Status |
|-------|----------|-------------|--------|
| RC-1 | **BLOCKING** | Add `adapters/__init__.py` edit to Phase 2 scope: remove `UrlAdapter` import (line 27) and `__all__` entry. Without this, deleting `url.py` causes ImportError. | ✅ Addressed — added to charter Phase 2 and AC-13 |
| RC-2 | recommended | Document Python package-vs-module resolution: explain why deleting `local.py`, `sanderland.py`, `travisgk.py`, `kisvadim.py` is safe (Python resolves `local/` package before `local.py` module). | ✅ Addressed — documented in plan and analysis |
| RC-3 | recommended | Fix AGENTS.md ghost reference to `adapters/url/` directory (no such directory exists). | ✅ Addressed — already in Phase 3 AGENTS.md fixes |

### New Questions (Auto-Resolved per Governance Recommendation)

| q_id | question | recommended | user_response | status |
|------|----------|-------------|---------------|--------|
| Q11 | Confirm `adapters/__init__.py` edit in Phase 2 (remove `UrlAdapter` import + `__all__` entry)? | A: Yes | A — Per RC-1, required to prevent ImportError | ✅ resolved |
| Q12 | Confirm AGENTS.md `url/` ghost reference fix in Phase 3? | A: Yes | A — Per RC-3, part of docs accuracy sweep | ✅ resolved |

### Handover

- **From**: Governance-Panel (charter mode)
- **To**: Feature-Planner
- **Message**: Charter approved with conditions. RC-1 is blocking — must add `adapters/__init__.py` edit to Phase 2 before proceeding to options.
- **Required Next Actions**: Address RC-1, then proceed to options drafting.
- **Artifacts to Update**: `00-charter.md` (add __init__.py edit), `10-clarifications.md` (Q11/Q12)
- **Blocking Items**: RC-1 (now resolved)

---

## Gate 2: Options Election

**Decision**: `approve`  
**Status Code**: `GOV-OPTIONS-APPROVED`  
**Date**: 2026-03-24  
**Result**: Unanimous (10/10 approve OPT-1)

### Selected Option

| Field | Value |
|-------|-------|
| `option_id` | `OPT-1` |
| `title` | 3-Phase Risk-Layered |
| `selection_rationale` | Dependency-graph-aligned phasing, orphan test co-deletion avoids OPT-3 breakage, better failure attribution than OPT-2, 3 governance gates is balanced overhead. |

### Must-Hold Constraints

1. Phase 1 MUST co-delete orphan tests with their source modules — never separate them.
2. Phase 2 MUST edit `adapters/__init__.py` in the same atomic phase as `url.py` deletion (RC-1).
3. Each phase MUST pass `pytest backend/ -m "not (cli or slow)"` before proceeding.
4. Phase 2 MUST validate `python -m backend.puzzle_manager sources` post-cleanup.

### Member Reviews

| GV-ID | Member | Domain | Vote | Key Comment |
|-------|--------|--------|------|-------------|
| GV-1 | Cho Chikun 9p | Tsumego authority | approve OPT-1 | Phasing mirrors dependency graph — core first, then adapter layer, then docs |
| GV-2 | Lee Sedol 9p | Intuitive fighter | approve OPT-1 | Pragmatic middle ground; OPT-2 also acceptable but OPT-1 safer |
| GV-3 | Shin Jinseo 9p | AI-era professional | approve OPT-1 | Phased gates provide defense-in-depth on top of verified dead code |
| GV-4 | Ke Jie 9p | Strategic thinker | approve OPT-1 | Repeatable pattern for future cleanup; clear progress reporting |
| GV-5 | Principal Staff Engineer A | Systems architect | approve OPT-1 | **OPT-3 defect**: Phase 2 test-only deletion creates test collection failures |
| GV-6 | Principal Staff Engineer B | Pipeline engineer | approve OPT-1 | Phase 2 gate validates `discover_adapters()` explicitly |
| GV-7 | Hana Park 1p | Player experience | approve OPT-1 | Zero player impact; 3 verification gates strongest guarantee |
| GV-8 | Mika Chen | DevTools UX | approve OPT-1 | Removing dead code reduces cognitive load; doc fix isolation clean |
| GV-9 | Dr. David Wu | KataGo/engine | approve OPT-1 | No enrichment components affected |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve OPT-1 | Dead modules already replaced; co-deletion prevents dangling artifacts |

### Handover

- **From**: Governance-Panel (options mode)
- **To**: Feature-Planner
- **Message**: OPT-1 unanimously approved. Proceed to plan drafting with 3 phases + 4 must-hold constraints.
- **Required Next Actions**: Update status.json, draft 30-plan.md, 40-tasks.md, 20-analysis.md
- **Blocking Items**: None

## Gate 3: Plan Review

**Decision**: `approve`  
**Status Code**: `GOV-PLAN-APPROVED`  
**Date**: 2026-03-24  
**Result**: Unanimous (10/10 approve)

### Pre-Checks

16/16 checks pass. All artifacts exist, option election complete, must-hold constraints mapped, confidence floor met (95 >= 80), risks mitigated.

### Codebase Verification Spot-Checks

| SV-ID | Claim | Result |
|-------|-------|--------|
| SV-1 | `adapters/__init__.py` imports UrlAdapter at ~L27 | ✅ Confirmed (line 28) |
| SV-2 | `stages/protocol.py` has `views_dir` property | ✅ Confirmed (line 66) |
| SV-3 | AGENTS.md says "Typer" | ✅ Confirmed (lines 26, 175) |
| SV-4 | Dead files exist on disk | ✅ Confirmed (all 13 + 14 + ghost dir) |
| SV-5 | Zero production imports of dead modules | ✅ Confirmed via grep |
| SV-6 | `adapters/ogs/` is ghost directory | ✅ Confirmed (no .py files) |
| SV-7 | Docs targeted for deletion/archive exist | ✅ Confirmed (all 5) |

### Member Reviews

| GV-ID | Member | Domain | Vote | Key Comment |
|-------|--------|--------|------|-------------|
| GV-1 | Cho Chikun 9p | Tsumego authority | approve | Clean structural surgery — no puzzle logic touched |
| GV-2 | Lee Sedol 9p | Intuitive fighter | approve | Aggressive but verified — each deletion confirmed via grep |
| GV-3 | Shin Jinseo 9p | AI-era professional | approve | Research excludes live modules correctly (F8, F9) |
| GV-4 | Ke Jie 9p | Strategic thinker | approve | Archive strategy (AD-5) preserves historical context |
| GV-5 | Principal Staff A | Systems architect | approve | Package-vs-module resolution correctly analyzed (RE-14..17) |
| GV-6 | Principal Staff B | Pipeline engineer | approve | Test strategy sound; phase gates match project conventions |
| GV-7 | Hana Park 1p | Player experience | approve | Zero player impact; triple verification via phase gates |
| GV-8 | Mika Chen | DevTools UX | approve | AGENTS.md fixes improve developer experience |
| GV-9 | Dr. David Wu | KataGo/engine | approve | No enrichment components in scope |
| GV-10 | Dr. Shin Jinseo | Tsumego correctness | approve | Dead level_mapper replaced by live classifier.py |

### Minor Observations (Non-Blocking)

| OB-ID | Observation |
|-------|------------|
| OB-1 | `40-tasks.md` summary stats have arithmetic inconsistencies (actual task tables are authoritative) |
| OB-2 | Plan references UrlAdapter at "line 27" but actual is line 28 |
| OB-3 | Orphan test count refined from ~18 (charter) to 21 (plan) — acknowledged in analysis CC-2 |

### Required Changes

None.

### Handover

- **From**: Governance-Panel (plan mode)
- **To**: Plan-Executor
- **Message**: Plan unanimously approved. Execute 3-phase plan per `30-plan.md` and `40-tasks.md`. All 4 must-hold constraints approved and must be honored.
- **Required Next Actions**: Update status.json, fix RC-1, prepare for closeout.
- **Blocking Items**: None

## Gate 4: Implementation Review

**Decision**: `approve`  
**Status Code**: `GOV-REVIEW-APPROVED`  
**Date**: 2026-03-24  
**Result**: Unanimous (10/10 approve)

### Code Review Results

| Review | Verdict | Findings |
|--------|---------|----------|
| CR-ALPHA | pass_with_findings | CRA-1 (minor): stale import in adapter-development.md |
| CR-BETA | pass_with_findings | CRB-1 (minor): same as CRA-1 |

### AC Verification

13/13 ACs met. All verified via filesystem inspection and grep.

### Member Reviews (Summary)

All 10 members approve. Key confirmations:
- Zero player impact (GV-7)
- AGENTS.md accuracy improved (GV-8)
- No enrichment/KataGo components affected (GV-9, GV-10)
- Package-vs-module resolution verified (GV-3, GV-5)
- Pipeline integrity maintained via sources command (GV-6)

### Required Changes

| RC-ID | Severity | Description | Status |
|-------|----------|-------------|--------|
| RC-1 | minor | Fix stale import in adapter-development.md: change `adapters.base` → `adapters` | ✅ Fixed |

### Handover

- **From**: Governance-Panel (review mode)
- **To**: Plan-Executor
- **Message**: Implementation approved. Fix RC-1, proceed to closeout.
- **Blocking Items**: None

## Gate 5: Closeout Audit

**Decision**: `approve_with_conditions`  
**Status Code**: `GOV-CLOSEOUT-CONDITIONAL`  
**Date**: 2026-03-24  
**Result**: Unanimous (10/10 approve)

### Required Changes

| RC-ID | Severity | Description | Status |
|-------|----------|-------------|--------|
| RC-1 | non-blocking | Update `status.json` with Gate 4 + closeout entries | ✅ Done |

### Handover

- **From**: Governance-Panel (closeout mode)
- **To**: Plan-Executor
- **Message**: Initiative approved for closure. Branch ready for merge.
- **Blocking Items**: None

---

## Final Gate Summary

| Gate | Decision | Status Code | Unanimous |
|------|----------|-------------|-----------|
| 1. Charter | approve_with_conditions | GOV-CHARTER-CONDITIONAL | 8/10 (conditions met) |
| 2. Options | approve | GOV-OPTIONS-APPROVED | 10/10 |
| 3. Plan | approve | GOV-PLAN-APPROVED | 10/10 |
| 4. Review | approve | GOV-REVIEW-APPROVED | 10/10 |
| 5. Closeout | approve_with_conditions | GOV-CLOSEOUT-CONDITIONAL | 10/10 (conditions met) |
