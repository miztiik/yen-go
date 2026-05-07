# Governance Decisions: enrich_single.py Decomposition

**Last Updated:** 2026-03-09

---

## Options Election — GOV-OPTIONS-APPROVED

**Gate:** options-review  
**Decision:** approve  
**Status Code:** GOV-OPTIONS-APPROVED  
**Unanimous:** Yes (6/6)

### Selected Option

| Field               | Value                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| option_id           | OPT-1                                                                                                                                                                                                                                                                                                                                                                           |
| title               | Layered SRP Extraction                                                                                                                                                                                                                                                                                                                                                          |
| selection_rationale | Directly addresses all charter goals (independent iteration, SRP compliance, cognitive load reduction) with minimum abstraction (one dataclass + one shared module). Per-phase rollback. SOLID/DRY/KISS/YAGNI compliant. OPT-2 rejected (YAGNI — async protocol untested, no new stages planned). OPT-3 rejected (doesn't solve core problem — orchestrator still 1,085 lines). |

### Must-Hold Constraints

| MH-ID | Constraint                                                                                               |
| ----- | -------------------------------------------------------------------------------------------------------- |
| MH-1  | `config_lookup.py` MUST expose `clear_config_caches()` for test isolation                                |
| MH-2  | Phase 1 MUST include a test validating config path resolution                                            |
| MH-3  | `EnrichmentRunState` MUST be a `@dataclass` (not dict or TypedDict)                                      |
| MH-4  | Each phase MUST be independently deployable and revertible (one commit per phase)                        |
| MH-5  | `_ai_solve_failed` set-in-except-and-fall-through pattern MUST be preserved exactly on the state carrier |
| MH-6  | Zero functional changes — all existing tests must pass after each phase                                  |

### Panel Support

| review_id | member                     | domain                      | vote    | supporting_comment                                                                                                              |
| --------- | -------------------------- | --------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------- |
| GV-1      | Cho Chikun (9p)            | Classical tsumego authority | approve | 3 code paths correspond to 3 pedagogically distinct puzzle input types. No solution tree/validation changes.                    |
| GV-2      | Lee Sedol (9p)             | Intuitive fighter           | approve | Per-phase rollback is key differentiator. `EnrichmentRunState` converts invisible variables into inspectable contract.          |
| GV-3      | Shin Jinseo (9p)           | AI-era professional         | approve | AI-Solve path extraction preserves `await` semantics. Partial-failure flag on dataclass preserves set-and-fall-through pattern. |
| GV-4      | Ke Jie (9p)                | Strategic thinker           | approve | Config DRY fix alone is worth the initiative. Phased approach delivers Phase 1 value independently.                             |
| GV-5      | Principal Staff Engineer A | Systems architect           | approve | Adapts backend `StageContext` pattern without importing from backend. Requires `clear_config_caches()` test helper.             |
| GV-6      | Principal Staff Engineer B | Data pipeline engineer      | approve | Config path fragility fix eliminates latent bug. Requires path resolution test in Phase 1.                                      |

### Handover

| Field          | Value                                                                                                                      |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- |
| from_agent     | Governance-Panel                                                                                                           |
| to_agent       | Refactor-Planner                                                                                                           |
| message        | Proceed to plan phase with OPT-1. Each of 4 phases must be independently committable. Respect all 6 must-hold constraints. |
| blocking_items | None                                                                                                                       |

---

## Plan Review — GOV-PLAN-APPROVED

**Gate:** plan-review  
**Decision:** approve  
**Status Code:** GOV-PLAN-APPROVED  
**Unanimous:** Yes (6/6)

### Required Changes

| rc_id | severity | description                                                                                | target_artifact    | blocking |
| ----- | -------- | ------------------------------------------------------------------------------------------ | ------------------ | -------- |
| RC-1  | LOW      | `status.json` phase states stale — update `analyze`, `tasks`, `plan` to reflect completion | `status.json`      | No       |
| RC-2  | LOW      | T8 DoD should include README/docstring mention of `config_lookup.py` as shared module      | `40-tasks.md` (T8) | No       |

### Panel Support

| review_id | member                     | domain                      | vote    | supporting_comment                                                                                                                                                                             | evidence                                                                             |
| --------- | -------------------------- | --------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| GV-1      | Cho Chikun (9p)            | Classical tsumego authority | approve | 3 extracted code paths map to 3 pedagogically distinct puzzle input types. MH-5 preserves critical invariant. Phase boundaries are clean.                                                      | Charter §Functional Groups; Research Appendix A R-ES-04/05/06; MH-5 traced to T14+T9 |
| GV-2      | Lee Sedol (9p)             | Intuitive fighter           | approve | Per-phase rollback is strongest safety property. `EnrichmentRunState` converts 9 invisible locals into inspectable, mockable contract. T13 return type is pragmatic.                           | Plan §Phase 3; Research Appendix B state dependency graph; T13 DoD                   |
| GV-3      | Shin Jinseo (9p)           | AI-era professional         | approve | AI-Solve path extraction preserves `await` semantics. MH-5 correctly mandates dedicated test before wiring and after extraction. `notify_fn` carrier avoids noisy signatures.                  | Clarifications Q8; Plan §Phase 3 risks; enrich_single.py L508 async signature        |
| GV-4      | Ke Jie (9p)                | Strategic thinker           | approve | Phase 1 delivers standalone DRY value even if later phases deferred. Orchestrator 1,085→~200 lines is readable in single screen. Exactly 2 new files + 1 function move — no over-engineering.  | Options §OPT-1; verified 4-file duplication via grep                                 |
| GV-5      | Principal Staff Engineer A | Systems architect           | approve | `clear_config_caches()` replaces fragile `_TAG_SLUG_TO_ID = None` pattern — correctness improvement. TDD ordering catches extraction errors at creation. All 3 callers import only public API. | Test imports L23-L28; caller verification; Analysis §6 CC-6                          |
| GV-6      | Principal Staff Engineer B | Data pipeline engineer      | approve | Phase validation gates mirror backend stage-gate model. Line count verified: 180+55+355=590. Performance neutral. `state.notify_fn` preserves GUI progress display.                            | Plan §Validation Matrix; Research §2.2; run_calibration.py L41                       |

### Handover

| Field                 | Value                                                                                                                                                                                                                                                                                                                                                                                              |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| from_agent            | Governance-Panel                                                                                                                                                                                                                                                                                                                                                                                   |
| to_agent              | Plan-Executor                                                                                                                                                                                                                                                                                                                                                                                      |
| message               | Plan approved unanimously. Execute 4 phases in order (P1→P2→P3→P4). Each phase must pass its validation gate (T8/T12/T18/T21) before proceeding. Respect all 6 must-hold constraints — MH-5 is highest-risk. Apply RC-1 (status.json sync) and RC-2 (T8 README mention) during execution. Use `pytest -m "not (cli or slow)"` for fast validation between tasks; full `pytest` at each phase gate. |
| required_next_actions | 1. Update `status.json` (RC-1). 2. Add README mention to T8 DoD (RC-2). 3. Execute P1 (T1→T8). 4. Execute P2 (T9→T12). 5. Execute P3 (T13→T18). 6. Execute P4 (T19→T21). 7. Update `70-governance-decisions.md` with execution log. 8. Submit for governance closeout review.                                                                                                                      |
| artifacts_to_update   | `status.json`, `40-tasks.md`, create `50-execution-log.md`, create `60-validation-report.md`                                                                                                                                                                                                                                                                                                       |
| blocking_items        | None                                                                                                                                                                                                                                                                                                                                                                                               |

---

## Implementation Review — GOV-REVIEW-APPROVED

**Gate:** implementation-review  
**Decision:** approve  
**Status Code:** GOV-REVIEW-APPROVED  
**Date:** 2026-03-09  
**Unanimous:** Yes (6/6)

### Member Reviews

| review_id | member                     | domain                      | vote    |
| --------- | -------------------------- | --------------------------- | ------- |
| GV-1      | Cho Chikun (9p)            | Classical tsumego authority | approve |
| GV-2      | Lee Sedol (9p)             | Intuitive fighter           | approve |
| GV-3      | Shin Jinseo (9p)           | AI-era professional         | approve |
| GV-4      | Ke Jie (9p)                | Strategic thinker           | approve |
| GV-5      | Principal Staff Engineer A | Systems architect           | approve |
| GV-6      | Principal Staff Engineer B | Data pipeline engineer      | approve |

### Summary

All 6 must-hold constraints verified through direct code inspection and test evidence. 125 baseline tests pass identically across all phases confirming zero functional changes. 60 new tests provide regression coverage for extracted modules. Architecture compliance clean — no `tools/` → `backend/` imports, correct dependency direction, no circular imports. Pre-existing `classify_techniques` bug correctly scoped out and documented.

### Handover

| Field                 | Value                                                                                                          |
| --------------------- | -------------------------------------------------------------------------------------------------------------- |
| from_agent            | Governance-Panel                                                                                               |
| to_agent              | Plan-Executor                                                                                                  |
| decision              | approve                                                                                                        |
| status_code           | GOV-REVIEW-APPROVED                                                                                            |
| required_next_actions | 1. Update status.json to closeout. 2. Optionally file separate issue for pre-existing classify_techniques bug. |
| blocking_items        | None                                                                                                           |
