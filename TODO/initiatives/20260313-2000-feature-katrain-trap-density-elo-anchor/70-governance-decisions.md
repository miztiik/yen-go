# Governance Decisions — KaTrain Trap Density + Elo-Anchor

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`

---

## Gate 1: Charter + Options Review (Combined)

**Date**: 2026-03-13  
**Decision**: `approve`  
**Status Code**: `GOV-OPTIONS-APPROVED`  
**Unanimous**: Yes (6/6)

### Selected Option

| Field | Value |
|-------|-------|
| `option_id` | OPT-3 |
| `title` | Score-Based Trap Density with Configurable Floor + Elo-Anchor Hard Gate |
| `selection_rationale` | OPT-3 captures KaTrain's core insight (score > winrate; floor > zero) while adapting the mechanism for tsumego domain. Per-puzzle floor more appropriate than OPT-1's per-refutation `adj_weight` for 1-3 refutation puzzles. Config-driven tunability satisfies KISS/YAGNI. |
| `must_hold_constraints` | 1. `trap_density_floor` and `score_normalization_cap` MUST be config keys. 2. Floor fires only when ≥1 refutation exists. 3. `override_threshold_levels` MUST be config-driven. 4. KaTrain CALIBRATED_RANK_ELO attributed with MIT license comment. 5. `score_delta` is a model field, not inline computation. |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|-------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Score-based is pedagogically superior. Elo hard gate correct — difficulty must be accurate. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | OPT-3's per-puzzle floor preserves variance. OPT-1 would destroy signal for 1-3 refutations. |
| GV-3 | Shin Jinseo (9p) | AI-era pro | approve | `scoreLead` is correct signal. Threading path clean. Normalization cap of 30 is natural ceiling. |
| GV-4 | Ke Jie (9p) | Strategic | approve | OPT-3 protects zero-density for "obvious but deadly" moves. 2-level Elo threshold is good starting point. |
| GV-5 | Principal Staff Engineer A | Systems arch | approve | OPT-3 wins on architecture — both floor and cap config-driven. MIT attribution via code comment sufficient. |
| GV-6 | Principal Staff Engineer B | Data pipeline | approve | Score normalization sound. `score_normalization_cap: 30` may need adjustment for capturing races — config-driven so non-blocking. |

### Resolved Questions

| Question | Decision |
|----------|----------|
| Q6: adj_weight pattern | OPT-3 (configurable per-puzzle floor, not KaTrain's per-refutation adj_weight) |
| Elo override threshold | 2 levels — appropriate for 9-level system. Config-driven. |
| KaTrain MIT attribution | Code comment sufficient |

### Handover

| Field | Value |
|-------|-------|
| `from_agent` | Governance-Panel |
| `to_agent` | Feature-Planner |
| `message` | Charter and OPT-3 approved unanimously. Proceed to plan + tasks. |
| `required_next_actions` | 1. Create `30-plan.md`. 2. Create `40-tasks.md`. 3. Submit for plan governance review. |
| `blocking_items` | None |

---

## Gate 2: Plan Review

**Date**: 2026-03-13  
**Decision**: `approve_with_conditions`  
**Status Code**: `GOV-PLAN-CONDITIONAL`  
**Unanimous**: No (3 approve, 3 concern → all resolved to RCs)

### Required Changes (Resolved)

| rc_id | severity | description | status |
|-------|----------|-------------|--------|
| RC-1 | MEDIUM | Fix sign error in D2 curated enrichment: `mi.score_lead - root_score` (no flip needed — same perspective as `winrate_delta = wr - root_wr`) | ✅ Fixed in 30-plan.md |
| RC-2 | LOW | Document policy→Elo mapping approach in T6: logarithmic interpolation via rank midpoints | ✅ Added to 40-tasks.md T6 |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|-------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | concern→resolved | Score-based correct. Sign error in curated enrichment would inflate difficulty. → RC-1 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Plan correctly adapts KaTrain. Fallback to winrate_delta is transitional. |
| GV-3 | Shin Jinseo (9p) | AI-era pro | concern→resolved | Policy→Elo mapping underspecified → RC-2 |
| GV-4 | Ke Jie (9p) | Strategic | approve | Task decomposition well-structured. 2-level threshold sensible. |
| GV-5 | PSE-A | Systems arch | concern→resolved | Sign error + Elo mapping risk → RC-1 + RC-2 |
| GV-6 | PSE-B | Data pipeline | approve | Score cap 30.0 reasonable. Batch observability path correct. |

### Handover

| Field | Value |
|-------|-------|
| `from_agent` | Governance-Panel |
| `to_agent` | Feature-Planner → Plan-Executor |
| `message` | Plan approved with conditions (RC-1, RC-2 resolved). Proceed to executor handoff. |
| `re_review_requested` | false |

---

## Gate 3: Implementation Review

**Date**: 2026-03-13
**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`
**Unanimous**: Yes (6/6)

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|-------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Score-based trap density is pedagogically correct — scoreLead reflects actual points lost. Floor of 0.05 ensures no puzzle with known wrong moves is rated trivially. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Per-puzzle floor preserves variance while guaranteeing minimum. Disabled-gate test gives operators safe off-switch. |
| GV-3 | Shin Jinseo (9p) | AI-era pro | approve | score_lead is correct signal. Perspective flip in generate_single_refutation correct; no flip in _enrich_curated_policy correct. RC-1 properly resolved. |
| GV-4 | Ke Jie (9p) | Strategic | approve | 2-level override threshold appropriate for 9-level system. Coverage gap logging is honest. |
| GV-5 | PSE-A | Systems arch | approve | Clean architecture, proper defaults, Pydantic validation. No new dependencies. 275/275 regression. |
| GV-6 | PSE-B | Data pipeline | approve | Score normalization cap empirically reasonable. Curated enrichment enriches both signals. Orchestrator threads initial_score cleanly. |

### Must-Hold Constraints Verified

| # | Constraint | Status |
|---|-----------|--------|
| 1 | floor + cap are config keys | ✅ |
| 2 | Floor fires only when ≥1 refutation | ✅ |
| 3 | override_threshold_levels config-driven | ✅ |
| 4 | KaTrain MIT attribution | ✅ |
| 5 | score_delta is model field | ✅ |

### Handover

| Field | Value |
|-------|-------|
| `from_agent` | Governance-Panel |
| `to_agent` | Plan-Executor |
| `message` | Implementation approved unanimously. Proceed to closeout. |
| `required_next_actions` | 1. Update status.json governance_review: approved. 2. Submit for closeout audit. |
| `blocking_items` | None |

---

## Gate 4: Closeout Audit

**Date**: 2026-03-13
**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`
**Unanimous**: Yes (6/6)

### Handover

| Field | Value |
|-------|-------|
| `from_agent` | Governance-Panel |
| `to_agent` | User (initiative complete) |
| `message` | Initiative passes closeout audit. All four gates (scope, tests, docs, governance) verified. |
| `blocking_items` | None |
