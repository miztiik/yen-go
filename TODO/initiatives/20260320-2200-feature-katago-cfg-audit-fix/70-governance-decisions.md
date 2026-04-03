# Governance Decisions — KataGo .cfg Audit & Fix

**Initiative ID**: `20260320-2200-feature-katago-cfg-audit-fix`

---

## Gate 1: Charter Approval

**Date**: 2026-03-20
**Decision**: `approve`
**Status Code**: `GOV-CHARTER-APPROVED`

| gv_id | member | domain | vote | supporting_comment |
|-------|--------|--------|------|--------------------|
| GV-1 | KataGo-Engine-Expert | Engine Internals | approve | Audit findings accurate. 4 keys correctly identified as unused/deprecated. |
| GV-2 | KataGo-Tsumego-Expert | Tsumego Optimization | approve | Charter scope appropriate for config-level fix. |
| GV-3 | Staff Engineer 1 | Code Quality | approve | Clear acceptance criteria. Level 2 classification correct. |
| GV-4 | Staff Engineer 2 | Architecture | approve | No architectural impact. Config-only scope well-bounded. |
| GV-5 | Pro Player 1 | Go Domain | approve | Exploration suppression fix addresses real puzzle quality concern. |
| GV-6 | Pro Player 2 | Go Domain | approve | Early temperature boost for tesuji discovery is sound. |
| GV-7 | Player Experience | UX | approve | No user-facing changes. Pure backend config. |

**Support Summary**: 7/7 unanimous. Charter is well-scoped, Level 2 appropriate, acceptance criteria measurable.

---

## Gate 2: Options Approval

**Date**: 2026-03-20
**Decision**: `approve`
**Status Code**: `GOV-OPTIONS-APPROVED`
**Selected Option**: OPT-B (Tsumego-Optimized)

| gv_id | member | domain | vote | supporting_comment |
|-------|--------|--------|------|--------------------|
| GV-8 | KataGo-Engine-Expert | Engine Internals | approve OPT-B | Default restoration (OPT-A) is safe but misses tsumego opportunity. OPT-B's tempEarly=1.5 is well-bounded. |
| GV-9 | KataGo-Tsumego-Expert | Tsumego Optimization | approve OPT-B | 1.5 early temperature specifically helps discover low-prior tesuji. Critical for puzzle quality. |
| GV-10 | Staff Engineer 1 | Code Quality | approve OPT-B | OPT-B adds one parameter change over OPT-A. Minimal additional risk. |
| GV-11 | Staff Engineer 2 | Architecture | approve OPT-B | All options are config-only. OPT-B maximizes value. |
| GV-12 | Pro Player 1 | Go Domain | approve OPT-B | Tesuji discovery boost is exactly what tsumego analysis needs. |
| GV-13 | Pro Player 2 | Go Domain | approve OPT-B | OPT-C too aggressive. OPT-B strikes the right balance. |
| GV-14 | Player Experience | UX | approve OPT-B | Better puzzle analysis → better experience. |

**Support Summary**: 7/7 unanimous for OPT-B. Tsumego-Optimized approach provides meaningful upside with bounded risk.

---

## Gate 3: Plan Approval

**Date**: 2026-03-20
**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`

| gv_id | member | domain | vote | supporting_comment |
|-------|--------|--------|------|--------------------|
| GV-15 | KataGo-Engine-Expert | Engine Internals | approve | Parameter values and commentary accurate. |
| GV-16 | KataGo-Tsumego-Expert | Tsumego Optimization | approve | Test coverage for removed keys is good practice. |
| GV-17 | Staff Engineer 1 | Code Quality | approve with condition | Condition: update stale inline comment referencing `scoreUtilityFactor` → `staticScoreUtilityFactor` |
| GV-18 | Staff Engineer 2 | Architecture | approve | Parallel lane plan is appropriate for 3-file scope. |
| GV-19 | Pro Player 1 | Go Domain | approve | Plan aligns with charter goals. |
| GV-20 | Pro Player 2 | Go Domain | approve | Validation plan adequate. |
| GV-21 | Player Experience | UX | approve | No user impact. |

**Support Summary**: 7/7 (1 conditional). Condition: fix stale comment at line ~154 referencing `scoreUtilityFactor`.

### Handover

```json
{
  "from_agent": "Governance-Panel",
  "to_agent": "Plan-Executor",
  "message": "Plan approved with minor condition (stale comment fix). Execute OPT-B.",
  "required_next_actions": ["Execute T1-T10", "Fix stale scoreUtilityFactor comment"],
  "artifacts_to_update": ["50-execution-log.md", "60-validation-report.md", "70-governance-decisions.md", "status.json"],
  "blocking_items": []
}
```

### docs_plan_verification

```json
{
  "present": true,
  "coverage": "complete"
}
```

---

## Gate 4: Implementation Review

**Date**: 2026-03-21
**Decision**: `approve`
**Status Code**: `GOV-REVIEW-APPROVED`

| gv_id | member | domain | vote | supporting_comment | evidence |
|-------|--------|--------|------|--------------------|----------|
| GV-22 | KataGo-Engine-Expert | Engine Internals | approve | All 9 parameter changes correct. Version header accurate. | .cfg diff verified |
| GV-23 | KataGo-Tsumego-Expert | Tsumego Optimization | approve | `rootPolicyTemperatureEarly=1.5` correctly applied with good commentary. | .cfg lines 245-260 |
| GV-24 | Staff Engineer 1 | Code Quality | approve | Stale comment condition (CRA-1) resolved. Tests comprehensive. | test file has 11 tests |
| GV-25 | Staff Engineer 2 | Architecture | approve | No architectural violations. Config-only change. | No pipeline code touched |
| GV-26 | Pro Player 1 | Go Domain | approve | Parameter rationale in comments is excellent. | .cfg inline comments |
| GV-27 | Pro Player 2 | Go Domain | approve | Exploration defaults will improve puzzle analysis quality. | .cfg values verified |
| GV-28 | Player Experience | UX | approve | No user-facing regression possible. | Config-only scope |

**Support Summary**: 7/7 unanimous. All acceptance criteria met. CRA-1 (stale comment) resolved.

**Finding CRA-1** (resolved): Line ~154 had stale comment referencing `scoreUtilityFactor` → fixed to `staticScoreUtilityFactor`.

### Test Evidence

| evidence_id | test_suite | result | detail |
|-------------|-----------|--------|--------|
| EV-1 | Config tests | ✅ 11/11 passed | `test_tsumego_config.py` including `test_removed_keys_absent` |
| EV-2 | Enrichment lab regression | ✅ 570 passed, 11 failed (pre-existing) | No new failures |
| EV-3 | Backend unit tests | ✅ 1603 passed, 0 failed | Full backend suite clean |

---

## Gate 5: Closeout Audit

**Date**: 2026-03-21
**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`

| gv_id | member | domain | vote | supporting_comment | evidence |
|-------|--------|--------|------|--------------------|----------|
| GV-29 | KataGo-Engine-Expert | Engine Internals | approve | .cfg v2 is production-ready. All deprecated keys removed. | Final .cfg state |
| GV-30 | KataGo-Tsumego-Expert | Tsumego Optimization | approve | Tsumego-optimized parameters well-documented. | Changelog in .cfg |
| GV-31 | Staff Engineer 1 | Code Quality | approve | Test coverage complete. AGENTS.md updated. | Test + doc verification |
| GV-32 | Staff Engineer 2 | Architecture | approve | Clean execution. No scope creep. | Execution log |
| GV-33 | Pro Player 1 | Go Domain | approve | End-to-end quality excellent. | Full evidence chain |
| GV-34 | Pro Player 2 | Go Domain | approve | Initiative achieves stated goals. | Charter vs. deliverables |
| GV-35 | Player Experience | UX | approve | No residual risks for users. | No user-facing changes |

**Support Summary**: 7/7 unanimous closeout approval. Initiative fully delivered.

### Finalization Gate

```json
{
  "scope_complete": true,
  "validation_passed": true,
  "docs_updated": true,
  "governance_approved": true,
  "artifacts_synced": true,
  "closeout_eligible": true
}
```