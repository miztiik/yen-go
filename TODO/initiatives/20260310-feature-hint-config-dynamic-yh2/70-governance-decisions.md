# Governance Decisions — Config-Driven YH1 + Dynamic YH2 Reasoning

**Initiative ID:** 20260310-feature-hint-config-dynamic-yh2  
**Last Updated:** 2026-03-10

---

## Decision 1: Options Election (2026-03-10)

| Field | Value |
|-------|-------|
| Gate | options-review |
| Decision | **approve_with_conditions** |
| Status code | `GOV-OPTIONS-CONDITIONAL` |
| Unanimous | Yes |
| Selected option | **Option B: Enriched YH2 Reasoning** |

### Selection Rationale

Best balance of hint quality improvement with minimal risk. Config-driven YH1 + dynamic reasoning addresses gaps without removing atari detection or requiring engine signals.

### Required Changes (All Resolved)

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Create initiative artifacts | ✅ Applied |
| RC-2 | Audit existing atari hints | ✅ Resolved (kept with R5 gating, no removal) |
| RC-3 | Include documentation plan | ✅ Applied in 30-plan.md |

---

## Decision 2: Post-Implementation Review (2026-03-10)

| Field | Value |
|-------|-------|
| Gate | implementation-review |
| Decision | **change_requested** |
| Status code | `GOV-REVIEW-REVISE` |
| Unanimous | Yes (6/6) |

### Defects Found

| defect_id | severity | file | description | status |
|-----------|----------|------|-------------|--------|
| D-1 | HIGH | test_enrichment.py | `test_reasoning_includes_secondary_tag` used `has_solution=False` (default). Dynamic block gated on `has_solution` never entered. Test would FAIL. | ✅ Fixed — added `has_solution=True` |
| D-2 | MEDIUM | test_enrichment.py | `test_reasoning_no_secondary_for_single_tag` same issue — passed vacuously. | ✅ Fixed — added `has_solution=True` |

### Required Changes

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Fix `test_reasoning_includes_secondary_tag`: add `has_solution=True` | ✅ Applied |
| RC-2 | Fix `test_reasoning_no_secondary_for_single_tag`: add `has_solution=True` | ✅ Applied |
| RC-3 | Create post-implementation artifacts | ✅ Applied |
| RC-4 | Update status.json | ✅ Applied |
| RC-5 | Run test suite and confirm pass | ❌ Pending (no terminal access) |

### Panel Reviews

| review_id | member | domain | vote | key point |
|-----------|--------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | change_requested | Secondary tag feature pedagogically valuable but test D-1 will fail |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | change_requested | Depth + refutation calibration is high-value. Fix D-1/D-2 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | change_requested | Config loading clean. Module-level cache never reset in tests — non-blocking |
| GV-4 | Ke Jie (9p) | Strategic thinker | change_requested | Composite hint format has strong learning value. D-1 blocks merge |
| GV-5 | Principal Staff Eng A | Systems architect | change_requested | Implementation quality good. Post-impl artifacts missing |
| GV-6 | Principal Staff Eng B | Data pipeline | change_requested | Helpers well-scoped. D-1 must be fixed. Tests need execution |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Two test defects fixed. Post-implementation artifacts created. Run test suite to complete validation. |
| blocking_items | RC-5: test execution pending |

---

## Decision 3: Implementation Review (Re-review) (2026-03-10)

| Field | Value |
|-------|-------|
| Gate | implementation-review-2 |
| Decision | **approve** |
| Status code | `GOV-REVIEW-APPROVED` |
| Unanimous | Yes (6/6) |

### Context

Re-review after D-1, D-2, RC-5, and T10 (R5 assertion) fixes applied. Full regression: 2065 passed, 0 failed.

### Panel Reviews

| review_id | member | domain | vote | key point |
|-----------|--------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Japanese terminology aligns with standard tsumego pedagogy. Secondary tag cross-reference pedagogically valuable. |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Dynamic reasoning (depth + refutation count) calibrates solver expectations effectively. |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Config-first + cache pattern robust. No KataGo dependencies. |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Composite hint format adds actionable information. `has_solution` gate validated. |
| GV-5 | Principal Staff Eng A | Systems architect | approve | SOLID compliance, no new deps, 2065/2065 pass. DEV-1b (dead code) acceptable — KISS. |
| GV-6 | Principal Staff Eng B | Data pipeline | approve | Helpers well-scoped, no performance regression (226 tests in 0.40s). |

### Resolved Items from Decision 2

| RC-id | Item | Status |
|-------|------|--------|
| RC-1 | Fix D-1: `test_reasoning_includes_secondary_tag` | ✅ Fixed |
| RC-2 | Fix D-2: `test_reasoning_no_secondary_for_single_tag` | ✅ Fixed |
| RC-3 | Create post-implementation artifacts | ✅ Applied |
| RC-4 | Update status.json | ✅ Applied |
| RC-5 | Run test suite and confirm pass | ✅ 2065 passed, 0 failed |

### Additional Fixes (beyond Decision 2 scope)

| Fix | Description | Assessment |
|-----|-------------|------------|
| T10a | `test_atari_suppressed_when_irrelevant` — assertion updated for config text format | Justified ripple from config-driven change |
| T10b | `test_player_atari_suppressed_when_move_does_not_save` — same | Justified |

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Approved. Proceed to closeout governance audit. |
| blocking_items | none |

---

## Decision 4: Closeout Audit (2026-03-10)

| Field | Value |
|-------|-------|
| Gate | closeout |
| Decision | **approve** |
| Status code | `GOV-CLOSEOUT-APPROVED` |
| Unanimous | Yes (6/6) |

### Closure Evidence Verified

| Check | Status |
|-------|--------|
| Scope complete (7/7 acceptance criteria) | ✅ |
| Tests pass (2065/2065 backend, 226/226 enrichment) | ✅ |
| Documentation updated (hints.md) | ✅ |
| Governance trail (3 prior decisions) | ✅ |
| All artifacts current | ✅ |
| Documentation rationale quality | ✅ |
| Cross-references present | ✅ |

### Panel Reviews

| review_id | member | domain | vote | key point |
|-----------|--------|--------|------|-----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | Japanese terminology aligns with published problem collections |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Refutation count primes solvers for creative alternatives |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Config-first + fallback robust against corruption |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Composite YH2 builds conceptual connections |
| GV-5 | Principal Staff Eng A | Systems architect | approve | SOLID compliance, zero new deps, KISS-acceptable dead code |
| GV-6 | Principal Staff Eng B | Data pipeline | approve | No performance regression, observability preserved |

### Residual Risks

- LOW: `TECHNIQUE_HINTS` tuple[0] dead code retained as fallback (documented DEV-1b)
- LOW: 4 alias tags without config entries (backward-compatibility, rarely encountered)

> **See also:**
> - [Charter](./00-charter.md)
> - [Plan](./30-plan.md)
> - [Execution Log](./50-execution-log.md)
> - [Validation Report](./60-validation-report.md)
