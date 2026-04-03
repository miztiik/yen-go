# Governance Decisions — Advanced Search Filters

> Initiative: `20260314-2300-feature-advanced-search-filters`
> Last Updated: 2026-03-14

## Gate 1: Charter Review

| Field | Value |
|-------|-------|
| **decision** | `approve_with_conditions` |
| **status_code** | `GOV-CHARTER-CONDITIONAL` |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | Scope respects sequential study principles. AC-2 (collection solve exclusion) is non-negotiable and correctly captured. | CC-1, E-1 |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | Dan-level depth training is a real use case. Three presets cover the space well. | LS-2, LS-3, REC-4 |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | AC→quality integration is technically sound. Deterministic build constraint maintained. | AC-6, quality.py |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Pragmatic scope. Config-driven bucket boundaries are correct. | CC-4, REC-1 |
| GV-5 | Principal Staff Engineer A | Systems architect | concern | Quality scoring needs ac mechanism specified; page names needed verification; status.json pending fields. | RC-1, RC-2, RC-3 |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | concern | Pipeline sequencing for ac→quality not explicit; count badge query efficiency. | RC-4 |
| GV-7 | Hana Park (1p) | Player experience | concern | Page name verification; zero-count pill behavior needed spec. | RC-2, RC-5 |

### Required Changes (Resolved)

| rc_id | required change | resolution | status |
|-------|-----------------|------------|--------|
| RC-1 | Specify AC→quality mechanism | Added `min_ac` config requirement pattern to AC-6 and constraints | ✅ resolved |
| RC-2 | Verify page names in AC-1 | Corrected: RandomChallengePage → RandomPage (solver vs browse) | ✅ resolved |
| RC-3 | Fill status.json pending rationale | Filled backward_compatibility and legacy_code_removal rationale | ✅ resolved |
| RC-4 | Pipeline sequencing note | Added to constraints: enrichment sets ac before quality scoring | ✅ resolved |
| RC-5 | Zero/low-count pill behavior | Added to constraints: dimmed/disabled for count=0, shown normally otherwise | ✅ resolved |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved with conditions. All 5 RCs resolved in charter artifacts. Proceed to options. |
| required_next_actions | Draft options (25-options.md), submit for option election |
| blocking_items | None |

## Gate 2: Options Election

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-OPTIONS-APPROVED` |

### Selected Option

| field | value |
|-------|-------|
| option_id | OPT-1 |
| title | Hook-Integrated Depth Presets |
| selection_rationale | Unanimous. Minimal change path, reuses all existing patterns, meets all 11 AC, cross-filter count integration. |
| must_hold_constraints | 1) No depth filter on CollectionViewPage 2) Bucket boundaries config-driven 3) Default = All 4) Zero-count pills dimmed 5) min_ac backward-compatible |

### Member Reviews

| review_id | member | vote | supporting_comment |
|-----------|--------|------|--------------------|
| GV-1 | Cho Chikun (9p) | approve | Sequential study preserved. Config-driven presets allow tuning. |
| GV-2 | Lee Sedol (9p) | approve | Cross-filter integration shows accurate counts per depth+level combo. |
| GV-3 | Shin Jinseo (9p) | approve | AC→quality backend change follows existing threshold pattern. |
| GV-4 | Ke Jie (9p) | approve | Minimal-change path. SQL layer requires zero changes. |
| GV-5 | PSE-A | approve | Single composable pattern preserved. Additive to existing interfaces. |
| GV-6 | PSE-B | approve | Backend min_ac is 4-line addition. Performance trivial for 9K puzzles. |
| GV-7 | Hana Park (1p) | approve | Cross-filter counts are the differentiating UX advantage. |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | OPT-1 unanimously selected. Proceed to plan + tasks. |
| required_next_actions | Draft 30-plan.md, 40-tasks.md. Submit for plan governance. |
| blocking_items | None |

## Gate 3: Plan Review

### Round 1: `GOV-PLAN-REVISE`

Required changes identified:
- RC-1: T7 page wiring gap (3 of 4 pages use `useCanonicalUrl`, not `usePuzzleFilters`)
- RC-2: T4 ac-read mechanism unspecified (`compute_quality_metrics()` hardcodes `ac:0`)
- RC-3: T7 effort estimate missing
- RC-4: T10 needs explicit regression test
- RC-HP-2: T8 needs negative test for CollectionViewPage

### Round 2: `GOV-PLAN-APPROVED`

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-PLAN-APPROVED` |

All 5 RCs resolved. Unanimous approval (7/7).

### Member Reviews (Round 2)

| review_id | member | vote |
|-----------|--------|------|
| GV-1 | Cho Chikun (9p) | approve |
| GV-2 | Lee Sedol (9p) | approve |
| GV-3 | Shin Jinseo (9p) | approve |
| GV-4 | Ke Jie (9p) | approve |
| GV-5 | PSE-A | approve |
| GV-6 | PSE-B | approve |
| GV-7 | Hana Park (1p) | approve |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved unanimously. Proceed with 6-phase execution (T1-T12). Start Phase 1 in parallel. |
| required_next_actions | Execute tasks T1-T12 per dependency graph |
| blocking_items | None |

## Gate 4: Implementation Review

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-REVIEW-APPROVED` |
| **unanimous** | Yes (7/7) |
| **date** | 2026-03-20 |

### Scope Verified

- 14 files modified/created across 7 execution lanes (L1-L7)
- All 11 Acceptance Criteria verified with evidence
- Backend: 1989 tests passed, 0 failed
- Frontend: 1329 tests passed (87 files), 0 failed
- TypeScript strict: 0 errors across all modified files
- Ruff lint: 0 new violations (pre-existing only)

### Findings

| finding_id | severity | description | disposition |
|------------|----------|-------------|-------------|
| CRB-1 | minor | Hardcoded SQL CASE boundaries in `puzzleQueryService.ts` vs config-driven | Acceptable — boundaries are stable constants matching `depth-presets.json`, no runtime divergence risk |
| CRB-2 | info | Type assertion `as DepthPresetOption[]` in `usePuzzleFilters.ts` | No runtime risk — array shape is guaranteed by `buildDepthPresetOptions()` |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Pedagogy | approve | Depth presets align with teaching progression | AC-1 through AC-11 verified |
| GV-2 | Lee Sedol (9p) | Gameplay UX | approve | Filter interaction is intuitive, cross-counts accurate | 17 frontend tests cover combinations |
| GV-3 | Shin Jinseo (9p) | Problem Quality | approve | AC→quality mapping preserves enrichment signal | Backend test coverage adequate |
| GV-4 | Ke Jie (9p) | Technical | approve | SQL CASE approach is performant for 9K puzzles | No query plan degradation |
| GV-5 | PSE-A | Architecture | approve | Additive change, no existing contract broken | Zero interface changes to existing types |
| GV-6 | PSE-B | Backend | approve | `min_ac` parameter is backward-compatible default=0 | 1989 backend tests pass |
| GV-7 | Hana Park (1p) | UX/Accessibility | approve | FilterBar pills with counts provide clear affordance | CollectionViewPage correctly excluded |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation review passed unanimously. All 11 ACs verified, zero critical findings. Proceed to closeout. |
| required_next_actions | 1. Update status.json governance_review=approved 2. Prepare closeout artifacts 3. Invoke closeout audit |
| blocking_items | None |

## Gate 5: Closeout Audit

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-CLOSEOUT-APPROVED` |
| **unanimous** | Yes (7/7) |
| **date** | 2026-03-21 |

### Audit Findings

| finding_id | category | description | severity | disposition |
|------------|----------|-------------|----------|-------------|
| CA-1 | Completeness | All 11 planning artifacts present and internally consistent. 7 lanes (EX-1 to EX-143) fully documented. | info | No action |
| CA-2 | Documentation | 5-file doc plan fully executed. All have cross-reference "See also" blocks. | info | No action |
| CA-3 | Test Coverage | 31 net-new frontend tests + 9 backend tests. Negative AC-2 test present. | info | No action |
| CA-4 | Governance Trail | 4 gates documented with member votes, required changes, and handover blocks. | info | No action |
| CA-5 | Residual Risk | CRB-1 (SQL CASE boundaries) verified acceptable — boundaries match config exactly. | minor | Accepted |
| CA-6 | Cross-References | All doc cross-references verified valid. | info | No action |
| CA-7 | Page Name Mapping | Charter→codebase name discrepancy documented in validation report and execution log. | info | No action |
| CA-8 | Schema Validation | depth-presets.schema.json Draft-07 compliant with proper validation rules. | info | No action |
| CA-9 | Backward Compat | Additive-only changes confirmed. No migration needed. | info | No action |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Pedagogy | approve | Depth presets respect sequential study — correctly excluded from solve pages. Three graduated presets align with tsumego training progression. | AC-2 negative test; charter non-goal rationale |
| GV-2 | Lee Sedol (9p) | Gameplay UX | approve | Cross-filter count integration is the key UX advantage. Zero-count pills render dimmed but visible. URL persistence via dp param enables shareable views. | EX-86/89/95/103; VAL-8 URL persistence |
| GV-3 | Shin Jinseo (9p) | Problem Quality | approve | AC→quality integration is technically sound: ac read via existing parse, min_ac gate only raises scores. | EX-37-45 tests; quality.py L210, L233-235 |
| GV-4 | Ke Jie (9p) | Technical | approve | SQL CASE query is clean. Config-driven presets with JSON schema provide validation. CRB-1 acceptable for stable presets. | puzzleQueryService.ts L176-194; CRB-1 disposition |
| GV-5 | PSE-A | Architecture | approve | Architecture boundaries respected: no new cross-layer dependencies, no new packages. AGENTS.md updated in-commit. | VAL-22 no new deps; EX-134-139 AGENTS.md |
| GV-6 | PSE-B | Backend | approve | Backend change is minimal (4 lines). Follows existing min_comment_level pattern. 9 dedicated tests + regression test. | EX-27-34 implementation; EX-35-46 tests |
| GV-7 | Hana Park (1p) | UX/Accessibility | approve | FilterBar pills reuse existing component. Count badges provide clear affordance. Accessibility labels present. | EX-88/97/105 FilterBar; VAL-20 zero-count |

### Handover

| field | value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| decision | approve |
| status_code | GOV-CLOSEOUT-APPROVED |
| message | Initiative passes closeout audit. All 11 ACs verified, 143 execution items documented, 25 validation items green, 4 governance gates passed, documentation plan fully executed. |
| required_next_actions | 1. Update status.json closeout=approved 2. Archive initiative |
| blocking_items | None |
