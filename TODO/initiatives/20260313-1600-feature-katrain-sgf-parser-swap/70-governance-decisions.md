# Governance Decisions — KaTrain SGF Parser Swap

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Last Updated**: 2026-03-13

---

## Charter Review (2026-03-13)

| Field | Value |
|-------|-------|
| **decision** | `approve_with_conditions` |
| **status_code** | `GOV-CHARTER-CONDITIONAL` |
| **gate** | `charter-review` |
| **unanimous** | `false` |

### Member Reviews

| review_id | member | domain | vote | supporting_comment |
|-----------|--------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Tsumego correctness inference stays untouched. KaTrain is production-tested. Move-type change is type-system, not correctness. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Two independent copies is pragmatic. Dead code deletion is clean. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | KaTrain is battle-tested. chardet strip is correct. No exotic SGF edge cases in fixtures. |
| GV-4 | Ke Jie (9p) | Strategic thinker | concern | sgf_enricher.py dual-parser rewrite needs validation in options phase. → RC-2 |
| GV-5 | PSE-A | Systems architect | concern | Three clerical gaps in status.json, AC-2 scope, rollback strategy. → RC-1, RC-3, RC-4 |
| GV-6 | PSE-B | Data pipeline engineer | approve | Pipeline data flow unaffected. Backend facade strategy is correct. |

### Required Changes

| rc_id | Description | Status |
|-------|-------------|--------|
| RC-1 | Update `status.json` decision rationale fields | ✅ resolved |
| RC-2 | Options phase must validate sgf_enricher.py integration pattern | ❌ deferred to options |
| RC-3 | Fix AC-2 verification scope to project-wide | ✅ resolved |
| RC-4 | Add rollback strategy to charter | ✅ resolved |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter conditionally approved. Fix RC-1/3/4, then proceed to options. RC-2 deferred to options deliverable. |
| re_review_requested | false |

---

## Options Election (2026-03-13)

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-OPTIONS-APPROVED` |
| **gate** | `options-review` |
| **unanimous** | `true` |

### Selected Option

| Field | Value |
|-------|-------|
| option_id | OPT-1 |
| title | Full KaTrain Adoption — Replace Core Types |
| selection_rationale | Only option satisfying all Q1-Q7 without tech debt. Maximum KaTrain fidelity. RC-2 validated. |
| must_hold_constraints | 1. stdlib-only KaTrain copy. 2. Independent copies (no cross-imports). 3. Backend facade preserved. 4. tsumego_analysis.py wrapper. 5. Phased commits. 6. AC-1-10 verified. 7. parse_root_properties_only preserved. |

### Member Reviews

| review_id | member | vote | key_point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | Tsumego analysis cleanly separated into wrapper. Correctness inference unchanged. |
| GV-2 | Lee Sedol (9p) | approve | Bold clean cut. Consumer updates mechanical. Half-measures cause real bugs. |
| GV-3 | Shin Jinseo (9p) | approve | KaTrain battle-tested. chardet strip safe. Property normalization is a bonus. |
| GV-4 | Ke Jie (9p) | approve | RC-2 satisfied. Move type richness benefits downstream analysis. |
| GV-5 | PSE-A | approve | Full Q1-Q7 compliance. RC-2 integration proof complete (13 API calls mapped). |
| GV-6 | PSE-B | approve | Pipeline consumers shielded. parse_root_properties_only preserved. |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | OPT-1 unanimously elected. Proceed to plan + tasks + analysis. No conditions. |
| blocking_items | none |

---

## Plan Review (2026-03-13)

| Field | Value |
|-------|-------|
| **decision** | `approve_with_conditions` |
| **status_code** | `GOV-PLAN-CONDITIONAL` |
| **gate** | `plan-review` |
| **unanimous** | `false` |

### Member Reviews

| review_id | member | vote | key_point |
|-----------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | approve | Tsumego correctness preserved in wrapper. Parsing vs analysis separation clean. |
| GV-2 | Lee Sedol (9p) | approve | Bold clean cut. Consumer updates mechanical. T3 and T7 are creative work. |
| GV-3 | Shin Jinseo (9p) | approve | Battle-tested parser. chardet strip safe. place_handicap_stones retained. |
| GV-4 | Ke Jie (9p) | approve | RC-2 integration proof gives confidence. `.move` assertions will catch misses. |
| GV-5 | PSE-A | concern | Doc plan missing 4 global docs referencing sgfmill. test_sgf_enricher direct import. → RC-1, RC-2 |
| GV-6 | PSE-B | approve | Backend facade shields 15+ consumers. parse_root_properties_only preserved. |

### Required Changes

| rc_id | Description | Status |
|-------|-------------|--------|
| RC-1 | Extend doc plan with D-4 through D-7 for 4 global docs; add tasks T24-T27 | ✅ resolved |
| RC-2 | Explicitly note test_sgf_enricher.py direct sgfmill import in T14 | ✅ resolved |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner → Plan-Executor |
| message | Plan approved. RC-1/RC-2 resolved. Proceed to executor handoff. No re-review needed. |
| blocking_items | none |
