# Governance Decisions: Tsumego Frame Flood-Fill Rewrite

**Initiative ID**: `20260312-1400-feature-tsumego-frame-flood-fill`
**Last Updated**: 2026-03-12

---

## Gate 1: Charter Review

**Date**: 2026-03-12
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-CHARTER-CONDITIONAL`

### Panel Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Five issues are causally linked. Dead checker stones are a correctness violation. BFS flood-fill producing connected components matches classical Go territory concept. | R-6 (normalize gap), R-14 (KaTrain verbatim), AC1-AC4 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | "No wall is better than bad wall" — keep border wall but fix integration (seed attacker BFS from border cells, R-22). BFS-from-seed is deterministic and reproducible. | Q4-resolution, R-22 seed strategy, C3 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Dead checker stones critically harmful to KataGo ownership network. Score-neutral fill (G3) is correct. | ISSUE-1 causal chain, R-5, G3/AC5 |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Frame corruption affects downstream difficulty classification and hint generation. 5 issues in 1 initiative justified by shared root cause. | Risk table, NG1, downstream impacts |
| GV-5 | Principal Staff Engineer A | Systems architect | approve_with_conditions | Charter well-structured. Condition: status.json must be updated (RC-1). NormalizedPosition needs swap_xy field (RC-2, advisory). | status.json, NormalizedPosition dataclass |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve_with_conditions | Research quality high (confidence 55→88). Affected files list should include NormalizedPosition model changes (RC-2). | Test classes verified, offence_to_win caller analysis |

### Required Changes

| RC-id | Description | Status |
|-------|-------------|--------|
| RC-1 | Update status.json.phase_state.charter to "approved" | ✅ applied |
| RC-2 | Include NormalizedPosition model extension (swap_xy) in options/plan scope | ✅ tracked for options |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved. Proceed to options. Include ≥2 comparative options (normalize-only vs normalize+BFS). All options must preserve C1-C7 constraints and legality guards. |
| required_next_actions | 1. Apply RC-1 2. Apply RC-2 in options scope 3. Draft 25-options.md with ≥2 options 4. Submit to Governance-Panel mode=options |
| blocking_items | RC-1 (applied) |

---

## Gate 2: Options Election

**Date**: 2026-03-12
**Decision**: `approve`
**Status Code**: `GOV-OPTIONS-APPROVED`

### Selected Option

| Field | Value |
|-------|-------|
| option_id | **OPT-3** |
| title | Full Rewrite + Validation Hardening |
| selection_rationale | Only option meeting all 6 goals. User explicitly requested validation (Q5:A). Unanimous 6/6 panel approval. |
| must_hold_constraints | MH-1: denormalize round-trip test with swap_xy=True. MH-2: Disconnected = BFS component count > 1. MH-3: Dead stone = zero same-color ortho neighbors. MH-4: Legality guards preserved unchanged. MH-5: offence_to_win fully deleted. MH-6: Validation failure returns original position. |

### Panel Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Dead checker stones are a correctness violation. BFS mirrors natural territory growth. Validation provides provable correctness. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | "No wall is better than bad wall" — OPT-3 provides both correct algorithm AND safety net. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Dead stones corrupt KataGo ownership network. Score-neutral fill correct. offence_to_win is dead code. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | 5 issues causally linked — partial fixes leave chain intact. OPT-3 breaks every link. |
| GV-5 | Staff Engineer A | Systems architect | approve | Changes isolated. Validation follows existing defensive patterns. offence_to_win never passed by callers. |
| GV-6 | Staff Engineer B | Data pipeline | approve | BFS on 9×9 is microsecond-scale. Diagnostic dump supports observability. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | OPT-3 selected unanimously. Proceed to plan + tasks + analysis. Include MH-1 through MH-6. |
| blocking_items | (none) |

---

## Gate 3: Plan Review

**Date**: 2026-03-12
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`

### Panel Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | BFS mirrors natural territory growth. Score-neutral 50/50 is correct game theory. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Border + BFS seeding correct. Multi-seed fallback handles edge cases. Hard-fail is right. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Dead checker stones corrupt ownership network. Clean fill = clean ownership. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | All 5 issues addressed. 13 tasks in 6 phases with clear dependency graph. |
| GV-5 | Staff Engineer A | Systems architect | concern→RC | status.json state gap (RC-3). FrameResult.normalized misses swap_xy (RC-4). |
| GV-6 | Staff Engineer B | Data pipeline | approve | BFS microsecond-scale perf. Diagnostic SGF dump supports observability. |

### Required Changes

| RC-id | Description | Status |
|-------|-------------|--------|
| RC-3 | Fix status.json phase states (analyze→approved, plan→approved, tasks→approved) | ✅ applied |
| RC-4 | Update FrameResult.normalized to include swap_xy (line 798) | ✅ tracked in T1 |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved. Execute T1-T13 in phase order. Apply RC-4 during T1. Run pytest at phase boundaries. All MH-1 through MH-6 must be verified. |
| blocking_items | RC-3 (applied), RC-4 (tracked in T1) |

---

## Gate 4: Implementation Review

**Date**: 2026-03-12
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-REVIEW-CONDITIONAL`

### Panel Summary
- 4 Go professionals: approve (unanimous)
- 2 Staff Engineers: approve_with_conditions (stale doc references)
- All 6 goals met, all MH constraints verified, 3 deviations justified

### Required Changes

| RC-id | Description | Status |
|-------|-------------|--------|
| RC-5 | Update Known Limitations §1 — replace scan-direction language | ✅ applied |
| RC-6 | Update Alternatives table — Yen-Go territory split description | ✅ applied |
| RC-7 | Remove "Adaptive fill scan direction concept (C2)" reference | ✅ applied |
| RC-8 | Zone-Based Fill section properties table — marked as V2 historical | ✅ applied |

---

## Gate 5: Closeout Audit

**Date**: 2026-03-12
**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`

### Panel Summary
- Unanimous 6/6 approval
- 14/14 closeout checklist items pass
- All RCs applied, all goals met, all MH constraints verified
- No required changes

---
