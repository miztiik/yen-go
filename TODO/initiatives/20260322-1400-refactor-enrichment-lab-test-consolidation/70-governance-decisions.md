# Governance Decisions — Enrichment Lab Test Suite Consolidation

> Last Updated: 2026-03-22

## Decision Log

### GD-1: Initial Plan Review (2026-03-22)

**Gate:** plan-review
**Decision:** `change_requested`
**Status Code:** GOV-PLAN-REVISE

**Required Changes Issued:**

| RC ID | Category | Description | Status |
|-------|----------|-------------|--------|
| RC-1 | Blocking | Create initiative directory with full artifact set | ✅ Resolved — all artifacts created |
| RC-2 | Blocking | Conduct options election (lane ordering, L4 scope) | ✅ Resolved — OPT-B selected, documented in 25-options.md |
| RC-3 | Blocking | Lane 1 explicit class-to-file migration mapping | ✅ Resolved — table in 30-plan.md with 18 classes → 13 targets |
| RC-4 | Blocking | Ripple-effect analysis with DRY initiative | ✅ Resolved — zero conflicts (20-analysis.md) |
| RC-5 | Major | Specify migration atomicity | ✅ Resolved — one commit per sprint file (C6) |
| RC-6 | Major | Verify pythonpath resolves all 4 sys.path patterns | ✅ Resolved — task L3-T2 covers this |
| RC-7 | Major | Mandate docstring preservation | ✅ Resolved — constraint C3, AC5 |
| RC-8 | Major | Zero assertion changes acceptance criterion | ✅ Resolved — constraint C2, AC6 |
| RC-9 | Minor | Automated removal approach for sys.path | ✅ Resolved — script in L3-T3 |
| RC-10 | Minor | Document _prepare_input signature differences | ✅ Resolved — comparison table in 20-analysis.md |

**Panel Member Reviews:**

| Member | Vote | Key Concern |
|--------|------|-------------|
| GV-1 (Cho Chikun 9p) | change_requested | Migration mapping must be unambiguous |
| GV-2 (Lee Sedol 9p) | concern | Atomic vs incremental migration |
| GV-3 (Shin Jinseo 9p) | concern | pythonpath scope masking imports |
| GV-4 (Ke Jie 9p) | concern | Provenance loss in migration |
| GV-5 (PSE-A) | change_requested | Missing initiative artifacts |
| GV-6 (PSE-B) | change_requested | Missing explicit mapping table |
| GV-7 (Hana Park 1p) | concern | Test assertion preservation |
| GV-8 (Mika Chen) | approve | No DevTools UX impact |

**Code Reviewer Reports:**

| Reviewer | Verdict | Key Finding |
|----------|---------|-------------|
| CR-ALPHA | FAIL (on original plan) | Sprint files NOT superseded — different gap ID namespaces, 72 unique tests |
| CR-BETA | pass_with_findings | CRB-1: migrate don't delete; CRB-2: sys.path DRY violation |

---

### GD-2: Plan Re-submission Approval

**Gate:** plan-review (re-submission)
**Decision:** `approve`
**Status Code:** GOV-PLAN-APPROVED
**Note:** All 10 RCs addressed. Plan approved for execution.

---

### GD-3: Implementation Review (2026-03-22)

**Gate:** implementation-review
**Decision:** `approve`
**Status Code:** GOV-REVIEW-APPROVED
**Unanimous:** true (8/8)

**Code Reviewer Reports:**

| Reviewer | Verdict | Key Finding |
|----------|---------|-------------|
| CR-ALPHA | pass | All AC met; docstrings preserved; 2442 test count verified |
| CR-BETA | pass | No architecture violations; DRY improved; import hygiene clean |

**Panel Member Votes:**

| Member | Vote | Key Comment |
|--------|------|-------------|
| GV-1 (Cho Chikun 9p) | approve | Tsumego tests correctly co-located with domain files |
| GV-2 (Lee Sedol 9p) | approve | Clean semantic grouping; L4 deferral acceptable |
| GV-3 (Shin Jinseo 9p) | approve | AI solve remediation tests and engine tests intact |
| GV-4 (Ke Jie 9p) | approve | Discoverability dramatically improved |
| GV-5 (PSE-A) | approve | pythonpath config correct; no stale imports |
| GV-6 (PSE-B) | approve | Observability tests correctly consolidated |
| GV-7 (Hana Park 1p) | approve | Zero assertion changes; no player impact |
| GV-8 (Mika Chen) | approve | Developer discoverability dramatically improved |

**Minor Observations (non-blocking):**
- CRA-1: Stale .pytest_cache — auto-resolves on next --cache-clear
- CRB-1: Dead `_LAB` variable in test_ai_analysis_result.py — pre-existing
- CRB-2: Lane 4 deferral documented
