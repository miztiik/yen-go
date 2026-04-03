# Governance Decisions — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Charter Preflight

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-CHARTER-CONDITIONAL`

### Member Reviews

| gov_id | Member | Domain | Vote | Comment | Evidence |
|--------|--------|--------|------|---------|----------|
| GV-1 | Architecture Reviewer | architecture | approve_with_conditions | Well-scoped to tools/ isolation boundary. Concern: atomic test-update strategy for fixture renames needed. | test_architecture.py enforces no-backend-import. benchmark/ has 49 curated SGFs. test_fixture_coverage.py hardcodes paths. |
| GV-2 | Quality Engineering Reviewer | quality-engineering | approve_with_conditions | 5-dimension calibration is right granularity. 85% target is pragmatic. Needs: AC-1 denominator definition, measurement mechanism. | ALL_TAG_FIXTURES has 35+ entries. TECHNIQUE_FIXTURE_AUDIT.md shows 12/35 passing. |
| GV-3 | Go Domain Expert (1p) | go-domain | approve | 7 REMOVE candidates correctly identified (fuseki/joseki/endgame are NOT tsumego). kisvadim-goproblems sourcing is excellent. G-3 should reference config/tags.json as authority. | config/tags.json v8.3 defines 28 tags. kisvadim has 60+ pro-curated collections. |
| GV-4 | Risk/Compliance Reviewer | risk-compliance | approve_with_conditions | Risk medium (confidence 75) is realistic. Level 3-4 change needs correction-level declaration + phased execution. Git safety acknowledgment needed. | 01-correction-levels.md Level 3 criteria. CLAUDE.md git safety rules. |

### Conditions (All Addressed in Charter Revision)

| cond_id | Condition | Severity | Status |
|---------|-----------|----------|--------|
| COND-1 | Declare correction level + phased execution plan | Required | ✅ addressed |
| COND-2 | Define pass-rate denominator & measurement mechanism | Required | ✅ addressed |
| COND-3 | Specify atomic test-update strategy for fixture renames | Required | ✅ addressed |
| COND-4 | Git safety acknowledgment for fixture file operations | Recommended | ✅ addressed |

### Handover

- **From**: Governance-Panel
- **To**: Feature-Planner
- **Message**: Charter CONDITIONALLY APPROVED. All 4 conditions addressed in charter revision. Proceed to options generation.
- **Must-Hold Constraints**: C-1 (existing sources), C-2 (benchmark read-only), C-4 (skip if no KataGo), tools isolation boundary, git safety (selective staging), config/tags.json authoritative for 28-tag list
- **Blocking Items**: None

## Options Election

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-OPTIONS-CONDITIONAL`
**Selected Option**: `OPT-3` — Python Registry + Parametrized Tests

### Member Reviews

| gov_id | Member | Domain | Vote | Comment |
|--------|--------|--------|------|---------|
| GV-5 | Architecture Reviewer | architecture | approve_with_conditions | OPT-3 merges two proven patterns (ALL_TAG_FIXTURES + golden5 engine). One file, one dict, zero new infra patterns. Textbook KISS. |
| GV-6 | Quality Engineering Reviewer | quality-engineering | approve_with_conditions | Registry absorbs fixture churn (15 pending audit actions). Dict edit vs method rewrite. Parametrize gives free pytest -k filtering. |
| GV-7 | Go Domain Expert (1p) | go-domain | approve_with_conditions | Registry separates technique identity from verification. Expected_tags must be list[str] for multi-technique fixtures. |
| GV-8 | Risk/Compliance Reviewer | risk-compliance | approve | Lowest risk: 1 new file, 0 new deps, 0 CI impact on fast paths. Easy rollback (delete 1 file). |

### Selection Rationale

OPT-3 selected because it: (1) reuses two proven codebase patterns without new abstractions, (2) scores highest on KISS/YAGNI/DRY, (3) supports automatic coverage verification against config/tags.json, (4) absorbs fixture churn during remediation with minimal diff noise.

### Must-Hold Constraints (7)

| mh_id | Constraint |
|-------|-----------|
| MH-1 | Registry dict MUST include all 5 calibration dimensions per entry. Use None/empty for 'not yet calibrated' — never omit keys. |
| MH-2 | expected_tags MUST be list[str]. Assertion checks subset membership, not exact equality. |
| MH-3 | Registry MUST have programmatic cross-check test against config/tags.json. |
| MH-4 | Test MUST use @pytest.mark.slow and @pytest.mark.integration markers. |
| MH-5 | REMOVE/REPLACE fixtures from audit MUST be excluded or skip-marked. |
| MH-6 | Edge-case fields (ko_context, move_order, board_size) MUST be optional with defaults. |
| MH-7 | Registry dict MUST live at module level for importability. |

### Rejected Options

| opt_id | Title | Rejection Reason |
|--------|-------|-----------------|
| OPT-1 | Golden-5 Extension | DRY violation: 28 hand-coded methods with scattered expected values, ~700 LOC boilerplate |
| OPT-2 | Data-Driven JSON | YAGNI: 35+ new JSON files, new schema, merge conflicts during concurrent remediation |

### Handover

- **From**: Governance-Panel → **To**: Feature-Planner
- **Message**: OPT-3 approved with 7 must-hold constraints. Proceed to detailed plan.
- **Blocking Items**: None

## Plan Review

**Decision**: `approve_with_conditions`
**Status Code**: `GOV-PLAN-CONDITIONAL`

### Member Reviews

| gov_id | Member | Domain | Vote | Comment |
|--------|--------|--------|------|---------|
| GV-9 | Architecture Reviewer | architecture | approve_with_conditions | OPT-3 faithfully implemented. C1/C6: golden5 fixture conflict resolved via T8.1 replace-in-place. C3: miai→living fixed in T10/T17. |
| GV-10 | Quality Engineering Reviewer | quality-engineering | approve_with_conditions | 5 parametrized dimensions provide excellent coverage. C4: living added to PH-A sourcing. C2/C5: 25 active + 3 excluded = 28 total. |
| GV-11 | Go Domain Expert (1p) | go-domain | approve | Audit technique classifications correct. 7 REMOVE decisions sound. Living tag gap identified and resolved. Throw-in tiebreak: keep as throw-in. |
| GV-12 | Risk/Compliance Reviewer | risk-compliance | approve_with_conditions | Phased execution correct. C1/C6: golden5+REMOVE deletion merged into same atomic commit via T8.1. |

### Conditions (All Resolved in Plan/Tasks Amendment)

| cond_id | Condition | Severity | Resolution | Status |
|---------|-----------|----------|------------|--------|
| C1 | golden5 depends on simple_life_death.sgf + tesuji.sgf (REMOVE'd) | BLOCKING | T8.1: replace-in-place (keep filename, swap content), same atomic commit | ✅ addressed |
| C2 | joseki/fuseki/endgame need EXCLUDED_NON_TSUMEGO_TAGS | HIGH | T17: EXCLUDED_NON_TSUMEGO_TAGS set; T20: cross-check excludes them | ✅ addressed |
| C3 | miai→living tag mapping (ID 14 = 'living') | BLOCKING | T10: fix ALL_KNOWN_TAG_SLUGS; T17: registry uses 'living' | ✅ addressed |
| C4 | 'living' tag has no fixture — add to PH-A sourcing | HIGH | T1 updated: 'living' in explicit sourcing target list | ✅ addressed |
| C5 | Registry count: 25 active + 3 excluded = 28 total | LOW | Plan text clarified | ✅ addressed |
| C6 | Sequencing hazard: deletion before golden5 update | BLOCKING (merged with C1) | T8.1 in same atomic commit as T7-T9 | ✅ addressed |

### Final Handover

- **From**: Governance-Panel → **To**: Plan-Executor
- **Message**: Plan CONDITIONALLY APPROVED. All 6 conditions addressed in plan/tasks amendment. PH-A can proceed immediately. PH-B through PH-E proceed after PH-A completes.
- **Blocking Items**: None remaining — all 2 BLOCKING conditions resolved
- **Must-Hold Constraints**: MH-1 through MH-7 all verified in plan. MH-3 cross-check includes EXCLUDED_NON_TSUMEGO_TAGS handling.

---

## Implementation Review

**Decision**: `approve`
**Status Code**: `GOV-EXEC-APPROVED`

### Member Reviews

| GV-4 | Member | Domain | Vote | Supporting Comment | Evidence |
|------|--------|--------|------|--------------------|----------|
| GV-4a | Go Domain Expert | Go/Tsumego Quality | APPROVE | All 5 replaced fixtures are legitimate goproblems puzzles with correct PL[], solution branches, appropriate difficulty. living_puzzle.sgf is textbook vital-point-for-two-eyes. Non-tsumego exclusions correct. | Verified SGF headers, PL settings, solution trees for all replacements |
| GV-4b | Software Architect | Code Structure/SOLID | APPROVE | TechniqueSpec TypedDict with NotRequired is clean, type-safe. Module-level TECHNIQUE_REGISTRY follows existing patterns. EXCLUDED_NON_TSUMEGO_TAGS is DRY. Class-scoped engine avoids per-test startup. | 25 entries, 5+4 fields, SingleEngineManager quick_only mode |
| GV-4c | Quality Engineer | Test Coverage/Regression | APPROVE | 5 parametrized × 25 = 125 calibration assertions. 3 unit cross-checks. Golden5 backward compat confirmed (B2, board_size=19). 337+1624+8 tests pass, 0 regressions. 26 pre-existing failures unrelated. | Modified-file tests: 337 passed. Backend: 1624 passed. Integrity: 8 passed |
| GV-4d | Documentation Reviewer | Docs/AGENTS.md | APPROVE | AGENTS.md updated with test_technique_calibration.py and extended-benchmark/. TECHNIQUE_FIXTURE_AUDIT.md marks Stage 2/2b complete. Extended-benchmark README.md has provenance table. | Entries verified in AGENTS.md, audit doc, README |

### Support Summary

All 4 reviewers approve without conditions. Implementation complete, correct, aligned with OPT-3.
- MH-1 through MH-7 satisfied
- C1 through C6 conditions met
- 7/7 acceptance criteria verified
- 9/9 ripple effects validated
- 0 regressions introduced

### Handover

- **From**: Governance-Panel → **To**: Plan-Executor
- **Message**: Implementation APPROVED. Ready for closeout audit.

---

## Closeout Audit

**Decision**: `approve`
**Status Code**: `GOV-CLOSEOUT-APPROVED`

All scope items delivered, tests pass, docs updated, governance approved. Initiative closed.
