# Analysis: enrich_single.py SRP Refactor

**Initiative ID:** 20260313-1400-refactor-enrich-single-srp  
**Last Updated:** 2026-03-13

---

## Planning Confidence & Risk

| Metric | Value | Rationale |
|--------|-------|-----------|
| Planning Confidence Score | 85 | -15 for Q3 feasibility uncertainty (resolved: NOT feasible, keep modular) |
| Risk Level | medium | Cross-cutting notify/timing changes across 1,726 lines; 25-field PipelineContext ownership must be tracked |
| Research invoked | Yes | Feature-Researcher for Q3 feasibility (eager imports) and stage boundary line ranges |

---

## Cross-Artifact Consistency Checks

| finding_id | severity | artifact | finding | status |
|------------|----------|----------|---------|--------|
| F1 | LOW | status.json ↔ 40-tasks.md | `tasks` phase updated to `in_progress` in status.json. | ✅ pass |
| F2 | LOW | status.json ↔ 20-analysis.md | `analyze` phase updated to `in_progress` in status.json. | ✅ pass |
| F3 | MEDIUM | 30-plan.md ↔ 40-tasks.md | Plan §2b says solve_paths is `lines 276–720 (~445 lines)`. Tasks T6 matches (`lines 276–720, ~445 lines`). ✅ consistent. | ✅ pass |
| F4 | LOW | 30-plan.md ↔ 40-tasks.md | Plan says orchestrator target is `~120-150 lines`. Task T13 says `≤ 150 lines`. T19 says `≤ 150 lines`. ✅ consistent. | ✅ pass |
| F5 | LOW | 00-charter.md ↔ 40-tasks.md | Charter Success Criterion #1: `< 200 lines`. Plan/tasks say `≤ 150 lines`. Tasks are stricter — acceptable (overachieving). | ✅ pass |
| F6 | LOW | 10-clarifications.md ↔ 40-tasks.md | Q5:B (group by concern, ~5-6 modules) → Tasks have 8 stage modules (T5-T12). Includes solve_paths which is a special case (pre-existing 3-path dispatch). Still grouped by concern — acceptable mapping. | ✅ pass |
| F7 | LOW | 10-clarifications.md ↔ 30-plan.md | Q7:A (auto-wrap) → Plan §1d StageRunner with auto-wrap. ✅ consistent. | ✅ pass |
| F8 | LOW | 10-clarifications.md ↔ 30-plan.md | Q8:A (stage-declared policy) → Plan specifies ErrorPolicy per stage. ✅ consistent. | ✅ pass |
| F9 | LOW | 10-clarifications.md ↔ 40-tasks.md | Q9:B (rely on existing tests) → Task T18 verifies existing suite passes. No new test creation tasks. ✅ consistent. | ✅ pass |
| F10 | LOW | 10-clarifications.md ↔ 40-tasks.md | Q2:A (delete old code) → Task T15 removes dead code, T19 final cleanup. ✅ consistent. | ✅ pass |
| F11 | LOW | 70-governance.md ↔ 30-plan.md | Options RC-1 (Runner Sunset Criteria) → Plan has "Runner Sunset Criteria" section. ✅ addressed. | ✅ pass |
| F12 | LOW | 70-governance.md ↔ 30-plan.md | Options RC-2 (Field Ownership Table) → Plan has 25-row field ownership table. ✅ addressed. | ✅ pass |
| F13 | MEDIUM | 70-governance.md ↔ 40-tasks.md | Must-Hold Constraint #5 "Existing tests pass unchanged" → T14 DoD updated to explicitly include test file import updates. | ✅ pass |
| F14 | LOW | 25-options.md ↔ 30-plan.md | Selected option OPT-1 → Plan implements Stage Runner Pattern. ✅ consistent. | ✅ pass |

---

## Coverage Map (Goal → Task IDs)

| coverage_id | charter_goal | task_ids | covered? |
|-------------|-------------|----------|----------|
| C1 | SRP decomposition: each module has exactly one reason to change | T2, T5-T12, T13 | ✅ covered |
| C2 | DRY elimination: remove duplication between lab modules | T3 (result_builders), T4 (notify/timing runner), T13 (eliminate inline boilerplate) | ✅ covered |
| C3 | Interface-first design: Protocol ABCs for backend swap-in | T2 (protocols.py) | ✅ covered |
| C4 | Pipeline-ready interfaces: pluggable into backend stages | T2 (EnrichmentStage protocol), T4 (StageRunner) | ✅ covered |
| C5 | All changes within puzzle-enrichment-lab | All tasks scope to `tools/puzzle-enrichment-lab/` | ✅ covered |
| C6 | enrich_single.py < 200 lines | T13 (≤150), T15 (dead code removal), T19 (final verify) | ✅ covered |
| C7 | Zero behavioral change (tests pass) | T18 (full test suite) | ✅ covered |
| C8 | Legacy code removal (Q2:A) | T15 (delete dead code), T19 (final cleanup) | ✅ covered |
| C9 | Documentation update | T16 (lab README), T17 (stages README) | ✅ covered |

---

## Unmapped Tasks

| task_id | title | justification |
|---------|-------|---------------|
| T1 | Create stages/ sub-package | Prerequisite infrastructure — supports C1, C3 |
| T14 | Update imports across lab | Mechanical cleanup — supports C7, C8 |

All tasks are traced to charter goals or are necessary supporting infrastructure. No orphan tasks.

---

## Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| R1 | downstream | `cli.py` — imports `enrich_single_puzzle` | Low | T14 updates import path | T14 | ✅ addressed |
| R2 | downstream | `bridge.py` — imports `enrich_single_puzzle` | Low | T14 updates import path | T14 | ✅ addressed |
| R3 | downstream | `tests/test_enrich_single.py` — calls `enrich_single_puzzle` | Low | T14 updates test imports; T18 verifies | T14, T18 | ✅ addressed |
| R4 | downstream | `tests/` — any test importing internal helpers | Medium | T14 grep + fix all `from.*enrich_single import` | T14 | ✅ addressed |
| R5 | lateral | `models/enrichment_state.py` — evolves into PipelineContext foundation | Low | T2 creates PipelineContext; EnrichmentRunState embedded as field | T2 | ✅ addressed |
| R6 | lateral | `analyzers/observability.py` — notify callbacks | Low | Runner wraps notify; observability.py unchanged | T4, T13 | ✅ addressed |
| R7 | lateral | `analyzers/sgf_enricher.py` — called by teaching stage | Low | Teaching stage imports sgf_enricher directly | T12 | ✅ addressed |
| R8 | lateral | `analyzers/technique_classifier.py` — called during assembly/teaching | Low | Stage imports from existing module | T11, T12 | ✅ addressed |
| R9 | lateral | `analyzers/hint_generator.py` — called during teaching stage | Low | Stage imports from existing module | T12 | ✅ addressed |
| R10 | lateral | `analyzers/estimate_difficulty.py` — called during difficulty stage | Low | Stage imports from existing module | T10 | ✅ addressed |
| R11 | lateral | `analyzers/generate_refutations.py` — called during refutation stage | Low | Stage imports from existing module | T9 | ✅ addressed |
| R12 | upstream | `backend/puzzle_manager/core/` — read-only reference for protocol design | None | No backend changes. Protocol ABCs in lab only | T2 | ✅ addressed |
| R13 | lateral | `analyzers/config_lookup.py` — result assembly helpers | Low | Any needed helpers imported by assembly_stage | T11 | ✅ addressed |
| R14 | lateral | `analyzers/property_policy.py` — property policies for enrichment | Low | Stages import from existing module | T5, T11 | ✅ addressed |
| R15 | downstream | `scripts/run_calibration.py` — imports `enrich_single_puzzle` (line 41) | Low | T14 grep + fix all `from.*enrich_single import` | T14 | ✅ addressed |

---

## Constitution / Project Guideline Compliance

| compliance_id | rule | compliant? | evidence |
|--------------|------|-----------|----------|
| PG1 | "tools/ must NOT import from backend/" | ✅ Yes | Charter §Non-Goals; Q3 resolved: keep lab modular |
| PG2 | Dead code policy: delete, don't deprecate | ✅ Yes | Q2:A; Tasks T15, T19 |
| PG3 | No emojis in production UI | N/A | No frontend changes |
| PG4 | SOLID/DRY/KISS/YAGNI | ✅ Yes | Plan §SOLID mapping; Options §Assessment |
| PG5 | "Type Safety — TypeScript strict" | N/A | Python-only refactor |
| PG6 | "Python 3.11+ with type hints" | ✅ Yes | PipelineContext uses typed dataclass fields; no `dict[str, Any]` (Must-Hold #1) |
| PG7 | Git safety — no stash/reset/clean | ✅ Yes | Plan §Rollback: branch-only, no destructive ops |
| PG8 | "Never auto-proceed on structural changes" | ✅ Yes | Full governance workflow completed |
| PG9 | Documentation update with every change | ✅ Yes | Tasks T16, T17 |
| PG10 | "Modify >5 files → localize?" | ✅ Acknowledged | 12 new files necessary for SRP decomposition of 1,726-line monolith; governance-approved |

---

## Findings Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 2 | All pass |
| LOW | 12 | All pass |

### Action Items Before Governance Review

All action items resolved. Artifacts are consistent.
