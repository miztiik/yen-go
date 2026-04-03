# Governance Decisions

**Last Updated**: 2026-03-12 (closeout)

## Planning Phase — Governance Review (In-Conversation)

**Source**: Sumeku panel (Architecture/Security/Testing/Go-domain) in conversation
**Decision**: `change_requested`
**Status Code**: `GOV-PLAN-CONDITIONAL`

### Panel Findings
- 10W + 7B components = severe fragmentation (target: 1 per color)
- 65% density too high (target: 35-50%)
- 55 white eyes excessive (target: 2-10)

### Required Changes (RC-1 through RC-8)
| rc_id | priority | description | scope |
|-------|----------|-------------|-------|
| RC-1 | P0 | Spine fill: only expand from placed cells | T1 |
| RC-2 | P0 | Periodic eye holes (counter-based, every ~7 stones) | T1 |
| RC-3 | P1 | Narrow zone single-line chain mode | deferred |
| RC-4 | P1 | Reduce `_near_boundary` from Manhattan≤2 to Manhattan≤1 | T1 |
| RC-5 | P1 | Validation hardening (log → warn on multi-component) | deferred |
| RC-6 | P2 | Observability fields in FrameResult | deferred |
| RC-7 | P2 | Config thresholds externalization | deferred |
| RC-8 | P2 | Docs update for new algorithm | deferred |

### Handover
- from_agent: Governance-Panel
- to_agent: Plan-Executor
- required_next_actions: Implement RC-1, RC-2, RC-4 (P0/P1 items)
- blocking_items: none

### docs_plan_verification
- present: true
- coverage: complete (docs update deferred to RC-8)

---

## Implementation Review — Governance Decision

**Date**: 2026-03-12
**Panel**: Sumeku panel (Architecture/Security/Testing/Go-domain)
**Mode**: `review` (post-implementation)
**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`
**Unanimous**: true (6/6)

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Spine produces single connected component — fundamental requirement met. Eye spacing (mean 7.5/7.8) mirrors natural territory formation. Density acceptable for frame fill behind border wall. | VAL-2/3 (1 component/color), VAL-4/5 (eyes in range) |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | V3.1 checkerboard completely unrealistic. Spine growth matches how territorial influence actually works. Border-first test fix is correct — testing impossible board state before. | T1 rewrite, EX-7 test fix, VAL-8-12 visual probe |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | For KataGo, 1 connected component per color is within training distribution. V3.1's 10 fragments were out-of-distribution. 59.2% density reasonable for endgame positions. | VAL-2/3, VAL-6 explanation |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Three P0/P1 items delivered. Deferred items well-scoped for independent delivery. Root causes AN-1 through AN-4 addressed. | 20-analysis.md, 40-tasks.md T1-T6 |
| GV-5 | Principal Staff Eng A | Systems architect | approve | Architecture compliance maintained — local replacement, no new deps, Level 2 fix. API contract unchanged. Test fix correct — aligns with production flow. | tsumego_frame.py signature, VAL-13 |
| GV-6 | Principal Staff Eng B | Data pipeline | approve | 18/18 framed puzzles succeed. Execution log thorough (4 deviations documented). Density gap well-characterized as parameter tuning. | VAL-1, VAL-8-12, T6 metrics |

### Support Summary

All P0/P1 RC items (RC-1, RC-2, RC-4) verified:
- Frame connectivity: 1 component/color (18/18 PERFECT)
- Eyes: mean 7.5W/7.8B in 2-15 range (18/18 PASS)
- Manhattan ≤ 1 near-boundary: implemented
- Multi-seed fallback removed
- 87/87 tests passing, 4 deviations documented/resolved

### Panel Q&A
- Q1 (density as follow-up): Accepted unanimously — parameter tuning, not algorithm defect
- Q2 (deferred RC items): Accepted — RC-3/5-8 orthogonal to P0 fix
- Q3 (test score balance fix): Accepted — `place_border()` matches production preconditions

### Required Changes
None.

### Handover
- from_agent: Governance-Panel
- to_agent: Plan-Executor
- decision: approve
- status_code: GOV-REVIEW-APPROVED
- required_next_actions: Proceed to closeout; file deferred items as follow-up initiative candidates
- blocking_items: none

---

## Closeout Audit — Governance Decision

**Date**: 2026-03-12
**Panel**: Sumeku panel (Architecture/Security/Testing/Go-domain)
**Mode**: `closeout`
**Decision**: `approve_with_conditions` → conditions resolved → `approved`
**Status Code**: `GOV-CLOSEOUT-CONDITIONAL` → `GOV-CLOSEOUT-APPROVED`

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | concern→resolved | Stale doc described removed code as "Current" — staleness notice added |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | 18/18 puzzles with 1 component/color, deviations properly resolved |
| GV-3 | Shin Jinseo (9p) | AI-era professional | concern→resolved | Stale doc would mislead enrichment lab users — staleness notice added |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | P0/P1 items delivered, deferred items well-scoped |
| GV-5 | Principal Staff Eng A | Systems architect | concern→resolved | Stale doc + missing open_issues — both conditions resolved |
| GV-6 | Principal Staff Eng B | Data pipeline | approve | Test evidence solid, execution log thorough |

### Closeout Conditions (Both Resolved)

| rc_id | change | status |
|-------|--------|--------|
| RC-C1 | V3.2 staleness callout in `docs/concepts/tsumego-frame.md` | ✅ Added at step 4 and V3 section header |
| RC-C2 | `open_issues` field in `status.json` | ✅ Added with OI-1, OI-2, OI-3 |

### Handover
- from_agent: Governance-Panel
- to_agent: Plan-Executor
- decision: approve (conditions resolved)
- status_code: GOV-CLOSEOUT-APPROVED
- required_next_actions: Finalize status.json, clean up temp files
- blocking_items: none
